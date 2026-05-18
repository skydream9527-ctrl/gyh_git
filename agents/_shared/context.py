"""Context 协议读 / 写助手。

- `ContextLoader` — 把三层 memory 拼成字符串，交给 PromptBuilder 注入（对话开头用）
- `MemoryWriter` — 封装「写子文件 + 更新 MEMORY.md 索引」两步为一次调用（agent 写记忆用）

协议定义见同目录 `context-protocol.md`。
"""

from __future__ import annotations

import contextvars
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

# Per-request 当前请求的 ContextPaths。runtime 在 handle_message 开头 set，
# 结束 finally 里 reset；memory tool handler 通过 get_current_paths() 读取。
# 用 contextvars 而不是实例字段是因为 tool handler 是无状态 closure，
# 没有自然的地方把当前 user_id/task_id 传进来。
_current_paths: contextvars.ContextVar["ContextPaths | None"] = contextvars.ContextVar(
    "current_context_paths", default=None
)


def set_current_paths(paths: "ContextPaths | None") -> contextvars.Token:
    """Bind `paths` as the current-request ContextPaths; returns a reset token."""
    return _current_paths.set(paths)


def reset_current_paths(token: contextvars.Token) -> None:
    """Restore prior ContextPaths binding (pairs with `set_current_paths`)."""
    _current_paths.reset(token)


def get_current_paths() -> "ContextPaths | None":
    """Read the current request's ContextPaths, or None if none is bound."""
    return _current_paths.get()

MAX_MEMORY_INDEX_LINES = 200
MAX_MEMORY_FILE_CHARS = 8000
MAX_TASK_STATE_CHARS = 4000

MemoryType = Literal["user", "feedback", "project", "reference"]
_VALID_MEMORY_TYPES: frozenset[str] = frozenset({"user", "feedback", "project", "reference"})
_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:[-_][a-z0-9]+)*$")


@dataclass
class ContextPaths:
    """所有 context 文件的根目录与键。workspace_root 通常是 ice-workbench 仓库根。"""

    workspace_root: Path
    user_id: str | None = None
    agent_id: str | None = None
    task_id: str | None = None

    def user_memory_dir(self) -> Path | None:
        if not self.user_id:
            return None
        return self.workspace_root / "users" / self.user_id / "memory"

    def agent_memory_dir(self) -> Path | None:
        if not self.user_id or not self.agent_id:
            return None
        return self.workspace_root / "users" / self.user_id / "memory" / "agents" / self.agent_id

    def task_state_file(self) -> Path | None:
        if not self.task_id:
            return None
        return self.workspace_root / "tasks" / self.task_id / "STATE.md"


class ContextLoader:
    """按协议读 user memory / agent memory / task state。

    缺文件就返回空字符串，不抛异常 —— agent 在没有任何上下文的情况下也能工作。
    """

    def __init__(self, paths: ContextPaths):
        self._paths = paths

    def load_user_memory(self) -> str:
        return self._load_memory_dir(self._paths.user_memory_dir(), label="User Memory")

    def load_agent_memory(self) -> str:
        return self._load_memory_dir(self._paths.agent_memory_dir(), label="Agent Memory")

    def load_task_state(self) -> str:
        path = self._paths.task_state_file()
        if not path or not path.exists():
            return ""
        try:
            content = path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            logger.warning("read task state failed: %s", exc)
            return ""
        if len(content) > MAX_TASK_STATE_CHARS:
            content = content[:MAX_TASK_STATE_CHARS] + "\n\n...(truncated)"
        return content

    def _load_memory_dir(self, memory_dir: Path | None, label: str) -> str:
        """协议：先读 MEMORY.md 索引，再依次拼入被索引的子文件内容。"""
        if not memory_dir or not memory_dir.exists():
            return ""

        index_path = memory_dir / "MEMORY.md"
        if not index_path.exists():
            return ""

        try:
            index_text = index_path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            logger.warning("read %s MEMORY.md failed: %s", label, exc)
            return ""

        if not index_text:
            return ""

        lines = index_text.splitlines()
        if len(lines) > MAX_MEMORY_INDEX_LINES:
            logger.warning(
                "%s MEMORY.md has %d lines (>%d), truncating",
                label,
                len(lines),
                MAX_MEMORY_INDEX_LINES,
            )
            lines = lines[:MAX_MEMORY_INDEX_LINES]

        parts = ["### Index", "\n".join(lines)]
        referenced_files = _extract_referenced_files(lines)

        for rel_path in referenced_files:
            file_path = memory_dir / rel_path
            if not file_path.exists():
                logger.debug("memory file referenced but not found: %s", file_path)
                continue
            try:
                body = file_path.read_text(encoding="utf-8").strip()
            except OSError as exc:
                logger.warning("read memory file %s failed: %s", file_path, exc)
                continue
            if len(body) > MAX_MEMORY_FILE_CHARS:
                body = body[:MAX_MEMORY_FILE_CHARS] + "\n\n...(truncated)"
            parts.append(f"### {rel_path}\n\n{body}")

        return "\n\n".join(parts)


def _extract_referenced_files(lines: list[str]) -> list[str]:
    """从 MEMORY.md 的 `- [Title](file.md) — hook` 行中抓出 `file.md` 列表。

    只认相对路径的 .md 引用；忽略绝对 URL / 子目录可再加。
    """
    pattern = re.compile(r"\[[^\]]+\]\(([^)]+\.md)\)")
    seen: set[str] = set()
    ordered: list[str] = []
    for line in lines:
        for match in pattern.findall(line):
            if match.startswith(("http://", "https://", "/")):
                continue
            if match in seen:
                continue
            seen.add(match)
            ordered.append(match)
    return ordered


class MemoryWriter:
    """写 memory / task state 的封装。

    为什么需要：按协议每条 memory 要求做两件事 ——（1）写 `<slug>.md` 单条记忆，
    带标准 frontmatter；（2）在同目录 `MEMORY.md` 索引追加或更新一行。
    手动 `write_file` 两次 + 维护索引格式易错；`MemoryWriter` 把这两步合为一次调用。

    典型用法：
        writer = MemoryWriter(paths)
        writer.save_agent_memory(
            slug="default-business-line",
            title="默认业务线",
            hook="用户连续 3 次选 CC",
            type_="user",
            body="用户多次选中内容中心业务线，默认优先该业务线。",
        )
    """

    def __init__(self, paths: ContextPaths):
        self._paths = paths

    # ---- User Global Memory ----

    def save_user_memory(
        self,
        *,
        slug: str,
        title: str,
        hook: str,
        type_: MemoryType,
        body: str,
    ) -> Path:
        """在 `users/{uid}/memory/` 下写单条记忆并同步更新 MEMORY.md 索引。"""
        return self._save(
            self._paths.user_memory_dir(),
            slug=slug,
            title=title,
            hook=hook,
            type_=type_,
            body=body,
            label="user memory",
        )

    def delete_user_memory(self, slug: str) -> bool:
        """删除 user memory 的单条文件 + 从索引里移除。返回文件是否之前存在。"""
        return self._delete(self._paths.user_memory_dir(), slug)

    # ---- Agent-scoped Memory ----

    def save_agent_memory(
        self,
        *,
        slug: str,
        title: str,
        hook: str,
        type_: MemoryType,
        body: str,
    ) -> Path:
        """在 `users/{uid}/memory/agents/{agent_id}/` 下写单条记忆 + 更新索引。"""
        return self._save(
            self._paths.agent_memory_dir(),
            slug=slug,
            title=title,
            hook=hook,
            type_=type_,
            body=body,
            label="agent memory",
        )

    def delete_agent_memory(self, slug: str) -> bool:
        return self._delete(self._paths.agent_memory_dir(), slug)

    # ---- Task State ----

    def save_task_state(self, content: str) -> Path:
        """按协议全文覆盖 `tasks/{tid}/STATE.md`。"""
        path = self._paths.task_state_file()
        if path is None:
            raise ValueError(
                "task_id not set on ContextPaths; cannot save task state."
            )
        _atomic_write(path, content.rstrip() + "\n")
        return path

    # ---- Internal helpers ----

    def _save(
        self,
        dir_: Path | None,
        *,
        slug: str,
        title: str,
        hook: str,
        type_: str,
        body: str,
        label: str,
    ) -> Path:
        if dir_ is None:
            raise ValueError(
                f"{label} directory unavailable (missing user_id or agent_id in ContextPaths)"
            )
        _validate_slug(slug)
        _validate_type(type_)
        if not title.strip():
            raise ValueError("title must be non-empty")
        if not hook.strip():
            raise ValueError("hook must be non-empty")

        file_path = dir_ / f"{slug}.md"
        _atomic_write(file_path, _render_memory_file(slug, hook, type_, body))
        self._upsert_index(dir_, slug=slug, title=title, hook=hook)
        return file_path

    def _delete(self, dir_: Path | None, slug: str) -> bool:
        if dir_ is None or not dir_.exists():
            return False
        _validate_slug(slug)
        file_path = dir_ / f"{slug}.md"
        existed = file_path.exists()
        if existed:
            file_path.unlink()
        self._remove_from_index(dir_, slug)
        return existed

    def _upsert_index(self, dir_: Path, *, slug: str, title: str, hook: str) -> None:
        """Upsert one `- [title](slug.md) — hook` line in MEMORY.md.

        Preserves any existing non-matching lines (headings, blank lines, etc.)
        so operators can add section markers to MEMORY.md without losing them.
        """
        index_path = dir_ / "MEMORY.md"
        lines = (
            index_path.read_text(encoding="utf-8").splitlines()
            if index_path.exists()
            else []
        )
        new_line = f"- [{title}]({slug}.md) — {hook}"
        match = re.compile(rf"\]\({re.escape(slug)}\.md\)")
        updated: list[str] = []
        replaced = False
        for line in lines:
            if match.search(line):
                if not replaced:
                    updated.append(new_line)
                    replaced = True
                # 若同一 slug 被写过多行（不规范），只留一条
            else:
                updated.append(line)
        if not replaced:
            updated.append(new_line)
        _atomic_write(index_path, "\n".join(updated).rstrip() + "\n")

    def _remove_from_index(self, dir_: Path, slug: str) -> None:
        index_path = dir_ / "MEMORY.md"
        if not index_path.exists():
            return
        lines = index_path.read_text(encoding="utf-8").splitlines()
        match = re.compile(rf"\]\({re.escape(slug)}\.md\)")
        kept = [ln for ln in lines if not match.search(ln)]
        if len(kept) == len(lines):
            return
        _atomic_write(index_path, "\n".join(kept).rstrip() + "\n")


def _validate_slug(slug: str) -> None:
    if not _SLUG_PATTERN.match(slug):
        raise ValueError(
            f"invalid slug {slug!r}: must be lowercase alphanumeric with - or _ separators"
        )


def _validate_type(type_: str) -> None:
    if type_ not in _VALID_MEMORY_TYPES:
        raise ValueError(
            f"invalid memory type {type_!r}; must be one of {sorted(_VALID_MEMORY_TYPES)}"
        )


def _render_memory_file(slug: str, description: str, type_: str, body: str) -> str:
    """按协议的 frontmatter 规范序列化单条 memory 文件内容。"""
    body_stripped = body.strip()
    return (
        "---\n"
        f"name: {slug}\n"
        f"description: {description}\n"
        "metadata:\n"
        f"  type: {type_}\n"
        "---\n"
        "\n"
        f"{body_stripped}\n"
    )


def _atomic_write(path: Path, content: str) -> None:
    """Write + rename atomically so crashes don't leave half-written files."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)