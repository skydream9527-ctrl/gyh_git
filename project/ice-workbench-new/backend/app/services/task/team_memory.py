"""Team Memory layer — shared knowledge scoped to a team.

Design:
- Each team has `teams/{team_id}/memory/MEMORY.md` + per-entry `*.md` files
- A user's team is resolved from `users/{uid}/profile.json.team`
- Team memory entries are read-only for individual agents (written via admin
  or auto-promotion from user memory)
- ContextLoader injects team memory at the lowest priority layer

Storage layout:
    teams/{team_id}/
    ├── meta.json              # {"id", "name", "members": [...]}
    └── memory/
        ├── MEMORY.md          # index (same format as user memory)
        └── *.md               # individual entries
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from ...core.storage import get_paths, read_json, write_json
from ...core.storage.lock import multi_lock

# Re-use the same types and helpers from context_svc
from .context_svc import (
    _MAX_CONTEXT_BYTES,
    _MEMORY_TYPES,
    MemoryEntry,
    MemoryScope,
    _atomic_write_text,
    _delete_from_index,
    _parse_memory_index,
    _read_text,
    _sanitize_slug,
    _upsert_index,
)

TeamMemoryScope = Literal["team"]


# ─── User → Team Resolution ──────────────────────────────────────────────────


def resolve_user_team(user_id: str) -> str | None:
    """Look up a user's team from their profile.json.

    Returns the team_id string or None if the user has no team assigned.
    """
    paths = get_paths()
    profile = read_json(paths.user_profile(user_id))
    if not profile:
        return None
    team = profile.get("team")
    if not team or not isinstance(team, str):
        return None
    return team.strip() or None


def list_team_members(team_id: str) -> list[str]:
    """List user IDs belonging to a team (from team meta.json).

    Falls back to scanning user profiles if meta.json doesn't have a members list.
    """
    paths = get_paths()
    meta = read_json(paths.team_meta(team_id))
    if meta and isinstance(meta.get("members"), list):
        return meta["members"]
    return []


def ensure_team(team_id: str, *, name: str | None = None) -> Path:
    """Ensure team directory and meta.json exist. Returns the team dir path."""
    paths = get_paths()
    team_dir = paths.team_dir(team_id)
    team_dir.mkdir(parents=True, exist_ok=True)
    paths.team_memory_dir(team_id).mkdir(parents=True, exist_ok=True)
    meta_path = paths.team_meta(team_id)
    if not meta_path.exists():
        write_json(meta_path, {
            "id": team_id,
            "name": name or team_id,
            "members": [],
        })
    return team_dir


# ─── Team Memory Writer ──────────────────────────────────────────────────────


class TeamMemoryWriter:
    """Write memory entries to the team-level memory store.

    Mirrors the MemoryWriter API from context_svc but scoped to teams/{team_id}/memory/.
    """

    def __init__(self, team_id: str):
        self.team_id = team_id
        self.paths = get_paths()

    def _base_and_index(self) -> tuple[Path, Path]:
        base = self.paths.team_memory_dir(self.team_id)
        index = self.paths.team_memory_index(self.team_id)
        return base, index

    def save_memory(
        self,
        *,
        slug: str,
        title: str,
        hook: str,
        type_: str,
        body: str,
        author_id: str | None = None,
    ) -> dict:
        """Save a memory entry to the team memory store."""
        slug = _sanitize_slug(slug)
        if type_ not in _MEMORY_TYPES:
            raise ValueError("type must be one of: user, feedback, project, reference")
        if not body or not isinstance(body, str):
            raise ValueError("body must be a non-empty string")

        base, index = self._base_and_index()
        base.mkdir(parents=True, exist_ok=True)
        memory_path = base / f"{slug}.md"

        index_text = _upsert_index(index, slug=slug, title=title or slug, hook=hook or title or slug)
        file_text = _team_memory_file(slug, hook or title or slug, type_, body, author_id=author_id)

        with multi_lock([memory_path, index]):
            _atomic_write_text(memory_path, file_text)
            _atomic_write_text(index, index_text)

        return {"saved": True, "team_id": self.team_id, "slug": slug, "path": str(memory_path)}

    def delete_memory(self, *, slug: str) -> dict:
        """Delete a memory entry from the team memory store."""
        slug = _sanitize_slug(slug)
        base, index = self._base_and_index()
        memory_path = base / f"{slug}.md"
        index_text = _delete_from_index(index, slug=slug)

        with multi_lock([memory_path, index]):
            existed = memory_path.exists()
            try:
                memory_path.unlink()
            except FileNotFoundError:
                pass
            _atomic_write_text(index, index_text)

        return {"deleted": existed, "team_id": self.team_id, "slug": slug}


# ─── Team Memory Loader ──────────────────────────────────────────────────────


def load_team_memory_section(team_id: str, query: str | None = None) -> str:
    """Load team memory and format it as a context section for injection.

    Returns empty string if the team has no memory or team_id is None.
    """
    if not team_id:
        return ""
    paths = get_paths()
    base = paths.team_memory_dir(team_id)
    index = paths.team_memory_index(team_id)

    index_text = _read_text(index, max_bytes=_MAX_CONTEXT_BYTES)
    if not index_text:
        return ""

    from .memory_lifecycle import enrich_entries
    from .memory_ranking import rank_entries

    # Enrich from backing files so confidence/recency rank correctly. No bump:
    # team memory is read-only for individual agents (written via admin /
    # auto-promotion), so a user's read must not mutate shared usage counters.
    entries = rank_entries(
        enrich_entries(_parse_memory_index(index_text), base),
        query,
        limit=10,
        token_budget_chars=2000,
    )
    if not entries:
        return ""

    from .context_svc import _safe_child

    index_subset = "\n".join(entry.line for entry in entries)
    chunks = [f"## Team Memory ({team_id})", "### Selected entries", index_subset]
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
            chunks.append("[Context truncated: team memory section exceeded size limit.]")
            break
        chunks.append(f"### {target.name}\n{text}")

    return "\n\n".join(chunks)


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _team_memory_file(
    slug: str,
    hook: str,
    type_: str,
    body: str,
    *,
    author_id: str | None = None,
) -> str:
    """Render a team memory file with frontmatter."""
    from .memory_lifecycle import _now

    lines = [
        "---",
        f"name: {slug}",
        f"description: {hook.strip()}",
        f"created_at: {_now()}",
        f"updated_at: {_now()}",
        "metadata:",
        f"  type: {type_}",
        "  scope: team",
    ]
    if author_id:
        lines.append(f"  author: {author_id}")
    lines.extend(["---", "", body.rstrip(), ""])
    return "\n".join(lines)
