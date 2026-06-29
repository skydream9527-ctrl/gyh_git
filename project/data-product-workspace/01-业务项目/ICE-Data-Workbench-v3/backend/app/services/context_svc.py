"""Claude-Code-style memory and task-state context for Agents."""
from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from ..core.storage import get_paths
from ..core.storage.lock import multi_lock

MemoryScope = Literal["user", "agent"]
MemoryType = Literal["user", "feedback", "project", "reference"]

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,80}$")
_MEMORY_TYPES = {"user", "feedback", "project", "reference"}
_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
_MAX_CONTEXT_BYTES = 500 * 1024
_MAX_MEMORY_FILE_BYTES = 100 * 1024


@dataclass(frozen=True)
class ContextPaths:
    user_id: str | None = None
    agent_id: str | None = None
    task_id: str | None = None


@dataclass(frozen=True)
class MemoryEntry:
    slug: str
    title: str
    hook: str
    rel_path: str
    line: str


def _sanitize_slug(slug: str) -> str:
    value = (slug or "").strip()
    if not _SLUG_RE.match(value) or ".." in value:
        raise ValueError("slug must be 2-81 chars: lowercase letters, digits, '_' or '-'")
    return value


def _safe_child(base: Path, rel: str) -> Path | None:
    raw = (rel or "").strip()
    if not raw or raw.startswith("/") or ".." in Path(raw).parts:
        return None
    target = (base / raw).resolve()
    try:
        target.relative_to(base.resolve())
    except ValueError:
        return None
    return target


def _read_text(path: Path, *, max_bytes: int = _MAX_MEMORY_FILE_BYTES) -> str:
    try:
        if not path.exists() or not path.is_file():
            return ""
        size = path.stat().st_size
        if size > max_bytes:
            return f"[Skipped: {path.name} is {size} bytes, limit {max_bytes}.]"
        return path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):
        return ""


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_name, path)
    finally:
        try:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
        except OSError:
            pass


def _memory_file(slug: str, hook: str, type_: str, body: str) -> str:
    return (
        "---\n"
        f"name: {slug}\n"
        f"description: {hook.strip()}\n"
        "metadata:\n"
        f"  type: {type_}\n"
        "---\n\n"
        f"{body.rstrip()}\n"
    )


def _upsert_index(index_path: Path, *, slug: str, title: str, hook: str) -> str:
    line = f"- [{title.strip() or slug}]({slug}.md) - {hook.strip()}"
    existing = _read_text(index_path, max_bytes=_MAX_CONTEXT_BYTES)
    lines = [ln for ln in existing.splitlines() if ln.strip()] if existing else []
    replaced = False
    for idx, ln in enumerate(lines):
        if f"]({slug}.md)" in ln:
            lines[idx] = line
            replaced = True
            break
    if not replaced:
        lines.append(line)
    if len(lines) > 200:
        lines = lines[-200:]
    return "\n".join(lines).rstrip() + "\n"


def _delete_from_index(index_path: Path, *, slug: str) -> str:
    existing = _read_text(index_path, max_bytes=_MAX_CONTEXT_BYTES)
    lines = [ln for ln in existing.splitlines() if f"]({slug}.md)" not in ln]
    return ("\n".join(lines).rstrip() + "\n") if lines else ""


def _tokenize(text: str) -> set[str]:
    return {t.lower() for t in re.findall(r"[\w\u4e00-\u9fff]+", text or "") if len(t) > 1}


def _parse_memory_index(index_text: str) -> list[MemoryEntry]:
    entries: list[MemoryEntry] = []
    for line in index_text.splitlines():
        match = re.search(r"-\s*\[([^\]]+)\]\(([^)]+)\)\s*(?:[-—]\s*)?(.*)", line.strip())
        if not match:
            continue
        rel = match.group(2).strip()
        slug = Path(rel).stem
        entries.append(
            MemoryEntry(
                slug=slug,
                title=match.group(1).strip(),
                rel_path=rel,
                hook=match.group(3).strip(),
                line=line.strip(),
            )
        )
    return entries


def _rank_entries(entries: list[MemoryEntry], query: str | None, *, limit: int) -> list[MemoryEntry]:
    if not entries or not query:
        return entries[:limit]
    q_tokens = _tokenize(query)
    if not q_tokens:
        return entries[:limit]

    scored: list[tuple[int, int, MemoryEntry]] = []
    for idx, entry in enumerate(entries):
        haystack = _tokenize(f"{entry.slug} {entry.title} {entry.hook}")
        score = len(q_tokens.intersection(haystack))
        if score:
            scored.append((score, -idx, entry))
    if not scored:
        return entries[: min(limit, 3)]
    scored.sort(reverse=True)
    return [entry for _, _, entry in scored[:limit]]


class MemoryWriter:
    def __init__(self, ctx: ContextPaths):
        self.ctx = ctx
        self.paths = get_paths()

    def _scope_paths(self, scope: MemoryScope) -> tuple[Path, Path]:
        if not self.ctx.user_id:
            raise ValueError("memory writes need user_id")
        if scope == "user":
            base = self.paths.user_memory_dir(self.ctx.user_id)
            return base, self.paths.user_memory_index(self.ctx.user_id)
        if scope == "agent":
            if not self.ctx.agent_id:
                raise ValueError("agent memory writes need agent_id")
            base = self.paths.user_agent_memory_dir(self.ctx.user_id, self.ctx.agent_id)
            return base, self.paths.user_agent_memory_index(self.ctx.user_id, self.ctx.agent_id)
        raise ValueError("scope must be 'user' or 'agent'")

    def save_memory(
        self,
        *,
        scope: MemoryScope,
        slug: str,
        title: str,
        hook: str,
        type_: str,
        body: str,
    ) -> dict:
        slug = _sanitize_slug(slug)
        if type_ not in _MEMORY_TYPES:
            raise ValueError("type must be one of: user, feedback, project, reference")
        if not body or not isinstance(body, str):
            raise ValueError("body must be a non-empty string")
        base, index = self._scope_paths(scope)
        memory_path = base / f"{slug}.md"
        index_text = _upsert_index(index, slug=slug, title=title or slug, hook=hook or title or slug)
        file_text = _memory_file(slug, hook or title or slug, type_, body)
        with multi_lock([memory_path, index]):
            _atomic_write_text(memory_path, file_text)
            _atomic_write_text(index, index_text)
        return {"saved": True, "scope": scope, "slug": slug, "path": str(memory_path)}

    def delete_memory(self, *, scope: MemoryScope, slug: str) -> dict:
        slug = _sanitize_slug(slug)
        base, index = self._scope_paths(scope)
        memory_path = base / f"{slug}.md"
        index_text = _delete_from_index(index, slug=slug)
        with multi_lock([memory_path, index]):
            existed = memory_path.exists()
            try:
                memory_path.unlink()
            except FileNotFoundError:
                pass
            _atomic_write_text(index, index_text)
        return {"deleted": existed, "scope": scope, "slug": slug}

    def save_task_state(self, content: str) -> dict:
        if not self.ctx.task_id:
            raise ValueError("task_state_save needs task_id")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("content must be a non-empty string")
        path = self.paths.task_state_md(self.ctx.task_id)
        _atomic_write_text(path, content.rstrip() + "\n")
        return {"saved": True, "path": str(path), "size_bytes": len(content.encode("utf-8"))}


class ContextLoader:
    def __init__(self, ctx: ContextPaths, *, query: str | None = None, memory_limit: int = 5):
        self.ctx = ctx
        self.paths = get_paths()
        self.query = query
        self.memory_limit = max(1, memory_limit)

    def _load_memory_dir(self, title: str, base: Path, index: Path) -> str:
        index_text = _read_text(index, max_bytes=_MAX_CONTEXT_BYTES)
        if not index_text:
            return ""
        entries = _rank_entries(_parse_memory_index(index_text), self.query, limit=self.memory_limit)
        if not entries:
            return ""
        index_subset = "\n".join(entry.line for entry in entries)
        chunks = [f"## {title}", "### Selected MEMORY.md entries", index_subset]
        total = len(index_subset.encode("utf-8"))
        seen: set[Path] = set()
        for entry in entries:
            target = _safe_child(base, entry.rel_path)
            if target is None or target in seen:
                continue
            seen.add(target)
            text = _read_text(target)
            if not text:
                continue
            total += len(text.encode("utf-8"))
            if total > _MAX_CONTEXT_BYTES:
                chunks.append("[Context truncated: memory section exceeded size limit.]")
                break
            chunks.append(f"### {target.name}\n{text}")
        return "\n\n".join(chunks)

    def build_context_section(self) -> str:
        sections: list[str] = []
        if self.ctx.user_id:
            sections.append(
                self._load_memory_dir(
                    "User Global Memory",
                    self.paths.user_memory_dir(self.ctx.user_id),
                    self.paths.user_memory_index(self.ctx.user_id),
                )
            )
            if self.ctx.agent_id:
                sections.append(
                    self._load_memory_dir(
                        "Agent Memory",
                        self.paths.user_agent_memory_dir(self.ctx.user_id, self.ctx.agent_id),
                        self.paths.user_agent_memory_index(self.ctx.user_id, self.ctx.agent_id),
                    )
                )
        if self.ctx.task_id:
            state = _read_text(self.paths.task_state_md(self.ctx.task_id), max_bytes=_MAX_CONTEXT_BYTES)
            if state:
                sections.append(f"## Task State\n{state}")
        body = "\n\n".join(s for s in sections if s)
        if not body:
            return ""
        return "# Runtime Context\n\n" + body

    def describe(self) -> dict:
        def _describe_memory(base: Path, index: Path) -> dict:
            index_text = _read_text(index, max_bytes=_MAX_CONTEXT_BYTES)
            entries = _rank_entries(_parse_memory_index(index_text), self.query, limit=self.memory_limit)
            return {
                "index_path": str(index),
                "exists": bool(index_text),
                "selected": [
                    {
                        "slug": e.slug,
                        "title": e.title,
                        "hook": e.hook,
                        "path": str(base / e.rel_path),
                    }
                    for e in entries
                ],
            }

        out: dict = {"query": self.query, "memory_limit": self.memory_limit}
        if self.ctx.user_id:
            out["user_memory"] = _describe_memory(
                self.paths.user_memory_dir(self.ctx.user_id),
                self.paths.user_memory_index(self.ctx.user_id),
            )
            if self.ctx.agent_id:
                out["agent_memory"] = _describe_memory(
                    self.paths.user_agent_memory_dir(self.ctx.user_id, self.ctx.agent_id),
                    self.paths.user_agent_memory_index(self.ctx.user_id, self.ctx.agent_id),
                )
        if self.ctx.task_id:
            state_path = self.paths.task_state_md(self.ctx.task_id)
            out["task_state"] = {
                "path": str(state_path),
                "exists": state_path.exists(),
                "size_bytes": state_path.stat().st_size if state_path.exists() else 0,
            }
        return out
