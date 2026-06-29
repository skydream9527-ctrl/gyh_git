"""Claude-Code-style memory and task-state context for Agents.

P0 enhancements (2026-06):
- MemoryEntry carries lifecycle metadata (confidence, usage_count, last_hit_at, created_at)
- BM25 + recency + confidence composite scoring replaces naive keyword matching
- Token-budget dynamic truncation replaces fixed memory_limit=5
- Task State writes append incremental diffs to HISTORY.jsonl
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from ...core.storage import get_paths
from ...core.storage.lock import multi_lock

MemoryScope = Literal["user", "agent"]
MemoryType = Literal["user", "feedback", "project", "reference"]

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,80}$")
_MEMORY_TYPES = {"user", "feedback", "project", "reference"}
_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
_MAX_CONTEXT_BYTES = 500 * 1024
_MAX_MEMORY_FILE_BYTES = 100 * 1024

# Default token budget for memory injection (chars ≈ tokens × 2 for zh/en mix)
_DEFAULT_TOKEN_BUDGET_CHARS = 4000


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
    # --- P0 lifecycle metadata (optional for backward compat) ---
    confidence: float = 1.0         # 0.0–1.0; higher = more trusted
    usage_count: int = 0            # times this entry was hit during retrieval
    last_hit_at: str | None = None  # ISO timestamp of last retrieval hit
    created_at: str | None = None   # ISO timestamp of creation
    # --- P1 visibility (optional for backward compat) ---
    visibility: str = "private"     # "private" | "team" | "org"


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


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


# Fixed render order for frontmatter fields this feature owns. Unknown fields are
# preserved and emitted after these scalars; the `metadata` block always renders
# last so the on-disk shape stays compatible with the legacy `_memory_file` output.
_FRONTMATTER_FIELD_ORDER = ("name", "description", "created_at", "updated_at")
_FRONTMATTER_EXTRA_KEY = "__extra_lines__"


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parse a minimal `---`-fenced frontmatter block into (fields, body).

    Supports top-level `key: value` pairs and a single level of `metadata:`
    nesting (indented sub-keys collected into a nested dict under "metadata").
    Any line that cannot be parsed is preserved verbatim under a reserved key so
    a later render round-trips it. Never raises: text without a leading `---`
    fence (or an unterminated fence) returns ({}, original_text).
    """
    if not text:
        return {}, text or ""
    stripped = text.lstrip("\n")
    lines = stripped.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}, text
    closing = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            closing = i
            break
    if closing is None:
        return {}, text

    fm_lines = lines[1:closing]
    body = "\n".join(lines[closing + 1:]).strip("\n")

    fields: dict = {}
    extra: list[str] = []
    metadata: dict = {}
    in_metadata = False
    for ln in fm_lines:
        if not ln.strip():
            continue
        if in_metadata and (ln.startswith(" ") or ln.startswith("\t")):
            sub = ln.strip()
            if ":" in sub:
                k, v = sub.split(":", 1)
                metadata[k.strip()] = v.strip()
            else:
                extra.append(ln)
            continue
        in_metadata = False
        match = re.match(r"^([^:]+):\s?(.*)$", ln)
        if not match:
            extra.append(ln)
            continue
        key = match.group(1).strip()
        val = match.group(2)
        if key == "metadata" and val.strip() == "":
            in_metadata = True
            metadata = {}
            fields["metadata"] = metadata
        else:
            fields[key] = val.strip()
    # Drop an empty metadata container so it round-trips cleanly (nothing to keep).
    if fields.get("metadata") == {}:
        fields.pop("metadata", None)
    if extra:
        fields[_FRONTMATTER_EXTRA_KEY] = extra
    return fields, body


def _render_frontmatter(fields: dict, body: str) -> str:
    """Render fields + body back into a `---`-fenced frontmatter document.

    Known fields render first in a fixed order (name, description, created_at,
    updated_at), then any unknown fields in insertion order, then the nested
    `metadata` block, then any preserved unparseable lines. Round-trips unknown
    fields written by other producers.
    """
    fields = dict(fields or {})
    extra_lines = fields.pop(_FRONTMATTER_EXTRA_KEY, [])
    metadata = fields.pop("metadata", None)

    out: list[str] = ["---"]
    emitted: set[str] = set()
    for key in _FRONTMATTER_FIELD_ORDER:
        if key in fields:
            out.append(f"{key}: {fields[key]}")
            emitted.add(key)
    for key, val in fields.items():
        if key in emitted:
            continue
        out.append(f"{key}: {val}")
    if isinstance(metadata, dict) and metadata:
        out.append("metadata:")
        for k, v in metadata.items():
            out.append(f"  {k}: {v}")
    for ln in extra_lines:
        out.append(ln)
    out.append("---")

    rendered = "\n".join(out)
    body_text = (body or "").strip("\n")
    if body_text:
        return f"{rendered}\n\n{body_text}\n"
    return f"{rendered}\n"


def _scan_sensitive(content: str, patterns: list[tuple[str, re.Pattern]]) -> str | None:
    """Scan content against compiled sensitive patterns.

    Returns the *category name* of the first matching pattern, or None when no
    pattern matches. Never returns the matched substring value itself, so the
    caller can surface a category in an error message without leaking the
    secret. Patterns is a list of (category, compiled_regex) pairs as produced
    by `Settings.memory_sensitive_patterns`.
    """
    if not content or not patterns:
        return None
    for category, pattern in patterns:
        try:
            if pattern.search(content):
                return category
        except re.error:
            # A pattern that somehow fails at match time is skipped rather than
            # blocking the scan; compilation already happened at config time.
            continue
    return None


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
    """Delegate to memory_ranking.rank_entries (BM25 + metadata composite)."""
    from .memory_ranking import rank_entries
    return rank_entries(entries, query, limit=limit, token_budget_chars=_DEFAULT_TOKEN_BUDGET_CHARS)


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
        confidence: float = 1.0,
        visibility: str = "private",
    ) -> dict:
        slug = _sanitize_slug(slug)
        if type_ not in _MEMORY_TYPES:
            raise ValueError("type must be one of: user, feedback, project, reference")
        if not body or not isinstance(body, str):
            raise ValueError("body must be a non-empty string")
        if visibility not in ("private", "team", "org"):
            raise ValueError("visibility must be one of: private, team, org")
        confidence = max(0.0, min(1.0, confidence))

        # Write-time sensitive scan: refuse to persist secrets into long-lived
        # memory. Only the matched *category* is surfaced to the caller — never
        # the matched value — so an error message can't leak the secret itself.
        from ...core.config import get_settings

        patterns = get_settings().memory_sensitive_patterns
        for field_name, value in (("title", title), ("hook", hook), ("body", body)):
            category = _scan_sensitive(value or "", patterns)
            if category:
                raise ValueError(
                    f"refusing to save memory: {field_name} appears to contain "
                    f"sensitive content (category: {category})"
                )

        base, index = self._scope_paths(scope)
        memory_path = base / f"{slug}.md"

        # Preserve lifecycle counters across upserts: re-saving an existing slug
        # must not reset created_at / usage_count / last_hit_at (see
        # agents/_shared/context-protocol.md). New entries start fresh.
        created_at: str | None = None
        usage_count = 0
        last_hit_at: str | None = None
        existing = _read_text(memory_path)
        if existing:
            prev_fields, _ = _parse_frontmatter(existing)
            created_at = prev_fields.get("created_at") or None
            prev_meta = prev_fields.get("metadata") or {}
            try:
                usage_count = int(prev_meta.get("usage_count", 0))
            except (TypeError, ValueError):
                usage_count = 0
            last_hit_at = prev_meta.get("last_hit_at") or None

        index_text = _upsert_index(index, slug=slug, title=title or slug, hook=hook or title or slug)

        from .memory_lifecycle import render_memory_file

        file_text = render_memory_file(
            slug,
            hook or title or slug,
            type_,
            body,
            created_at=created_at,
            confidence=confidence,
            usage_count=usage_count,
            last_hit_at=last_hit_at,
            visibility=visibility,
        )
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
        had_previous = path.exists() and path.stat().st_size > 0
        _atomic_write_text(path, content.rstrip() + "\n")

        # Append incremental record to HISTORY.jsonl
        from .memory_lifecycle import append_task_history
        history_path = self.paths.task_state_history(self.ctx.task_id)
        append_task_history(
            history_path,
            content=content,
            agent_id=self.ctx.agent_id,
            had_previous=had_previous,
        )

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
        from .memory_lifecycle import bump_entries, enrich_entries

        # Enrich from the backing files first so confidence/recency factors are
        # real (not defaults), then rank with the BM25 composite scorer.
        parsed = enrich_entries(_parse_memory_index(index_text), base)
        entries = _rank_entries(parsed, self.query, limit=self.memory_limit)
        if not entries:
            return ""
        # Record retrieval hits: bump usage_count / last_hit_at on the selected
        # entries so recency ranking and the auto-promote threshold actually move.
        # Best-effort — bump_entries never raises into the prompt-assembly path.
        bump_entries(entries, base)
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
            # P1: Team Memory layer (lowest-priority persistent memory)
            try:
                from .team_memory import load_team_memory_section, resolve_user_team
                team_id = resolve_user_team(self.ctx.user_id)
                if team_id:
                    sections.append(load_team_memory_section(team_id, self.query))
            except Exception:
                pass  # team memory is best-effort; never block prompt assembly
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
            from .memory_lifecycle import enrich_entries

            # Mirror the injection path's ranking (enrich → rank) but never bump:
            # describe() is introspection and must not mutate usage counters.
            parsed = enrich_entries(_parse_memory_index(index_text), base)
            entries = _rank_entries(parsed, self.query, limit=self.memory_limit)
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
