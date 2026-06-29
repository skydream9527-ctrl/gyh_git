"""Memory Lifecycle Manager — decay, archive, and auto-promote.

Runs as a background sweep (invoked per-user at session end or by a scheduler).

Lifecycle rules:
- **Decay**: `project` entries not hit in 30+ days → marked `stale` in frontmatter
- **Archive**: `stale` entries not confirmed in 7+ days → moved to archive/ dir,
  removed from MEMORY.md index (recoverable, not deleted)
- **Auto-promote**: Agent Memory entries with usage_count >= 3 AND used by >= 2
  distinct users → promoted to Team Memory (with author attribution)
"""
from __future__ import annotations

import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ...core.storage import get_paths, read_json
from ...core.storage.lock import multi_lock
from .context_svc import (
    _MAX_CONTEXT_BYTES,
    _atomic_write_text,
    _delete_from_index,
    _parse_frontmatter,
    _parse_memory_index,
    _read_text,
    _render_frontmatter,
)

# ─── Configuration ────────────────────────────────────────────────────────────

STALE_THRESHOLD_DAYS = 30      # project entries unhit for this long → stale
ARCHIVE_THRESHOLD_DAYS = 7     # stale entries unconfirmed for this long → archived
PROMOTE_USAGE_MIN = 3          # minimum usage_count to consider promotion
PROMOTE_DISTINCT_USERS_MIN = 2 # minimum distinct users for auto-promote


# ─── MemoryLifecycleManager ──────────────────────────────────────────────────


class MemoryLifecycleManager:
    """Manages the lifecycle of memory entries for a user.

    Typical usage:
        manager = MemoryLifecycleManager(user_id="u1")
        report = manager.run_sweep()
    """

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.paths = get_paths()
        self._now = datetime.now(tz=timezone.utc)

    def run_sweep(self) -> dict:
        """Run full lifecycle sweep: decay → archive → (promote is separate).

        Returns a summary dict with counts of affected entries.
        """
        decayed = self._sweep_decay_and_archive(
            base=self.paths.user_memory_dir(self.user_id),
            index=self.paths.user_memory_index(self.user_id),
            archive=self.paths.user_memory_archive_dir(self.user_id),
        )

        # Also sweep each agent memory dir
        agents_dir = self.paths.user_memory_dir(self.user_id) / "agents"
        agent_results: dict[str, dict] = {}
        if agents_dir.is_dir():
            for agent_dir in agents_dir.iterdir():
                if not agent_dir.is_dir() or agent_dir.name.startswith("."):
                    continue
                aid = agent_dir.name
                r = self._sweep_decay_and_archive(
                    base=agent_dir,
                    index=agent_dir / "MEMORY.md",
                    archive=agent_dir / "archive",
                )
                if r["stale_marked"] or r["archived"]:
                    agent_results[aid] = r

        return {
            "user_memory": decayed,
            "agent_memories": agent_results,
        }

    def _sweep_decay_and_archive(self, base: Path, index: Path, archive: Path) -> dict:
        """Sweep a single memory directory for stale/archivable entries."""
        stale_marked: list[str] = []
        archived: list[str] = []

        index_text = _read_text(index, max_bytes=_MAX_CONTEXT_BYTES)
        if not index_text:
            return {"stale_marked": stale_marked, "archived": archived}

        entries = _parse_memory_index(index_text)
        for entry in entries:
            mem_path = base / entry.rel_path
            if not mem_path.exists():
                continue

            text = _read_text(mem_path)
            if not text:
                continue

            fields, body = _parse_frontmatter(text)
            metadata = fields.get("metadata") or {}
            mem_type = metadata.get("type", "")
            status = metadata.get("status", "")

            # Only project-type entries are subject to decay
            if mem_type != "project":
                continue

            last_hit = metadata.get("last_hit_at")
            days_since_hit = self._days_since(last_hit, fallback_field=fields.get("updated_at"))

            if status == "stale":
                # Already stale — check if ready to archive
                stale_since = metadata.get("stale_since")
                days_stale = self._days_since(stale_since)
                if days_stale >= ARCHIVE_THRESHOLD_DAYS:
                    self._archive_entry(mem_path, base, index, archive, entry.slug)
                    archived.append(entry.slug)
            elif days_since_hit >= STALE_THRESHOLD_DAYS:
                # Mark as stale
                self._mark_stale(mem_path, fields, body)
                stale_marked.append(entry.slug)

        return {"stale_marked": stale_marked, "archived": archived}

    def _days_since(self, iso_ts: str | None, fallback_field: str | None = None) -> float:
        """Calculate days since a timestamp. Uses fallback if primary is missing."""
        ts = iso_ts or fallback_field
        if not ts:
            return 999.0  # treat missing timestamps as very old
        try:
            dt = datetime.fromisoformat(ts)
            return max(0.0, (self._now - dt).total_seconds() / 86400)
        except (ValueError, TypeError):
            return 999.0

    def _mark_stale(self, path: Path, fields: dict, body: str) -> None:
        """Set metadata.status = stale and record stale_since timestamp."""
        metadata = fields.get("metadata") or {}
        metadata["status"] = "stale"
        metadata["stale_since"] = self._now.isoformat()
        fields["metadata"] = metadata
        fields["updated_at"] = self._now.isoformat()
        new_text = _render_frontmatter(fields, body)
        with multi_lock([path]):
            _atomic_write_text(path, new_text)

    def _archive_entry(
        self, mem_path: Path, base: Path, index: Path, archive: Path, slug: str
    ) -> None:
        """Move a memory file to archive/ and remove from index."""
        archive.mkdir(parents=True, exist_ok=True)
        dest = archive / mem_path.name
        shutil.move(str(mem_path), str(dest))
        # Remove from index
        index_text = _delete_from_index(index, slug=slug)
        with multi_lock([index]):
            _atomic_write_text(index, index_text)


# ─── Auto-Promote ────────────────────────────────────────────────────────────


def auto_promote_candidates(agent_id: str) -> list[dict]:
    """Find Agent Memory entries eligible for promotion to Team Memory.

    Scans ALL users' agent memory for the given agent_id, looking for entries
    with:
      - usage_count >= PROMOTE_USAGE_MIN
      - used by >= PROMOTE_DISTINCT_USERS_MIN different users (same slug)

    Returns a list of candidate dicts: {"slug", "title", "hook", "type", "body", "authors"}
    """
    paths = get_paths()
    users_dir = paths.users
    if not users_dir.is_dir():
        return []

    # Collect: slug → {users who have it, metadata from highest-usage version}
    slug_data: dict[str, dict] = {}

    for user_dir in users_dir.iterdir():
        if not user_dir.is_dir() or user_dir.name.startswith("."):
            continue
        uid = user_dir.name
        agent_mem_dir = paths.user_agent_memory_dir(uid, agent_id)
        if not agent_mem_dir.is_dir():
            continue

        index_path = agent_mem_dir / "MEMORY.md"
        index_text = _read_text(index_path, max_bytes=_MAX_CONTEXT_BYTES)
        if not index_text:
            continue

        entries = _parse_memory_index(index_text)
        for entry in entries:
            mem_path = agent_mem_dir / entry.rel_path
            if not mem_path.exists():
                continue
            text = _read_text(mem_path)
            if not text:
                continue

            fields, body = _parse_frontmatter(text)
            metadata = fields.get("metadata") or {}
            try:
                usage = int(metadata.get("usage_count", 0))
            except (TypeError, ValueError):
                usage = 0

            if usage < PROMOTE_USAGE_MIN:
                continue

            slug = entry.slug
            if slug not in slug_data:
                slug_data[slug] = {
                    "slug": slug,
                    "title": entry.title,
                    "hook": entry.hook,
                    "type": metadata.get("type", "feedback"),
                    "body": body,
                    "authors": set(),
                    "max_usage": usage,
                }
            slug_data[slug]["authors"].add(uid)
            if usage > slug_data[slug]["max_usage"]:
                slug_data[slug]["max_usage"] = usage
                slug_data[slug]["body"] = body
                slug_data[slug]["title"] = entry.title
                slug_data[slug]["hook"] = entry.hook

    # Filter by distinct-users threshold
    candidates = []
    for data in slug_data.values():
        if len(data["authors"]) >= PROMOTE_DISTINCT_USERS_MIN:
            candidates.append({
                "slug": data["slug"],
                "title": data["title"],
                "hook": data["hook"],
                "type": data["type"],
                "body": data["body"],
                "authors": sorted(data["authors"]),
                "max_usage": data["max_usage"],
            })

    return candidates


def promote_to_team(agent_id: str, team_id: str, *, dry_run: bool = False) -> list[dict]:
    """Find promotable entries and write them to Team Memory.

    Args:
        agent_id: the agent whose memory to scan for promotion candidates
        team_id: target team to promote into
        dry_run: if True, only return candidates without writing

    Returns:
        List of promoted (or would-promote) entries.
    """
    from .team_memory import TeamMemoryWriter, ensure_team

    candidates = auto_promote_candidates(agent_id)
    if not candidates or dry_run:
        return candidates

    ensure_team(team_id)
    writer = TeamMemoryWriter(team_id)
    promoted: list[dict] = []

    for c in candidates:
        # Don't overwrite existing team memory with same slug
        paths = get_paths()
        existing = paths.team_memory_dir(team_id) / f"{c['slug']}.md"
        if existing.exists():
            continue
        writer.save_memory(
            slug=c["slug"],
            title=c["title"],
            hook=c["hook"],
            type_=c["type"],
            body=f"{c['body']}\n\n_Auto-promoted from agent `{agent_id}` "
                 f"(used by {len(c['authors'])} users, max usage: {c['max_usage']})._",
            author_id=", ".join(c["authors"]),
        )
        promoted.append(c)

    return promoted
