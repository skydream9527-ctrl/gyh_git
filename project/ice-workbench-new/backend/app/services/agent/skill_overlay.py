"""Team-level skill overlays.

Allows teams to customize global skill behavior without forking the skill.
Overlays are stored in `teams/{team_id}/skill_overlays/{skill_id}.md` and
contain partial markdown that is appended to (or replaces sections of) the
global SKILL.md content when the agent reads it.

Storage layout:
    teams/{team_id}/
    └── skill_overlays/
        ├── kyuubi.md           # overrides for the kyuubi skill
        └── nl-mapping-table-sql.md

Overlay format (simple append or section-replace):
    ---
    mode: append          # "append" | "replace_section"
    target_section: null  # heading to replace (for replace_section mode)
    ---

    ## 团队定制：CC 业务线表名映射
    - `dim_content_center_item` → CC 内容表
    - `fact_cc_consume` → CC 消费事实表

Merge behavior:
- `append`: overlay content is appended after the base SKILL.md content
- `replace_section`: finds the heading matching `target_section` in base
  SKILL.md and replaces that section with overlay content
"""
from __future__ import annotations

import re
from pathlib import Path

from ...core.storage import get_paths


def get_overlay_path(team_id: str, skill_id: str) -> Path:
    """Return the path to a team's skill overlay file."""
    paths = get_paths()
    return paths.team_dir(team_id) / "skill_overlays" / f"{skill_id}.md"


def has_overlay(team_id: str, skill_id: str) -> bool:
    """Check if a team has an overlay for a given skill."""
    return get_overlay_path(team_id, skill_id).exists()


def apply_overlay(base_content: str, team_id: str, skill_id: str) -> str:
    """Apply a team's skill overlay to the base SKILL.md content.

    Args:
        base_content: the original global SKILL.md content
        team_id: the team whose overlay to apply
        skill_id: the skill being read

    Returns:
        Merged content (base + overlay applied). Returns base_content unchanged
        if no overlay exists or if the overlay is invalid.
    """
    overlay_path = get_overlay_path(team_id, skill_id)
    if not overlay_path.exists():
        return base_content

    try:
        raw = overlay_path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):
        return base_content

    if not raw:
        return base_content

    mode, target_section, overlay_body = _parse_overlay(raw)

    if mode == "replace_section" and target_section:
        return _replace_section(base_content, target_section, overlay_body)
    else:
        # Default: append
        return f"{base_content.rstrip()}\n\n---\n\n## Team Overlay ({team_id})\n\n{overlay_body}"


def list_overlays(team_id: str) -> list[str]:
    """List all skill IDs that have overlays for a team."""
    paths = get_paths()
    overlay_dir = paths.team_dir(team_id) / "skill_overlays"
    if not overlay_dir.is_dir():
        return []
    return [
        p.stem for p in overlay_dir.iterdir()
        if p.is_file() and p.suffix == ".md"
    ]


# ─── Internal Helpers ─────────────────────────────────────────────────────────


def _parse_overlay(raw: str) -> tuple[str, str | None, str]:
    """Parse overlay file into (mode, target_section, body)."""
    # Check for frontmatter
    if raw.startswith("---"):
        lines = raw.split("\n")
        closing = None
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                closing = i
                break
        if closing:
            fm_lines = lines[1:closing]
            body = "\n".join(lines[closing + 1:]).strip()
            mode = "append"
            target = None
            for ln in fm_lines:
                if ln.strip().startswith("mode:"):
                    mode = ln.split(":", 1)[1].strip()
                elif ln.strip().startswith("target_section:"):
                    val = ln.split(":", 1)[1].strip()
                    target = val if val and val != "null" else None
            return mode, target, body

    # No frontmatter — treat as pure append content
    return "append", None, raw


def _replace_section(base: str, heading: str, replacement: str) -> str:
    """Replace a section (from heading to next same-level heading) in base.

    If the heading is not found, falls back to append behavior.
    """
    # Find the heading in base
    escaped = re.escape(heading)
    pattern = re.compile(
        rf"^(#{{1,6}})\s+{escaped}\s*$",
        re.MULTILINE | re.IGNORECASE,
    )
    match = pattern.search(base)
    if not match:
        # Heading not found — append
        return f"{base.rstrip()}\n\n{replacement}"

    heading_level = len(match.group(1))
    section_start = match.start()
    after_heading = match.end()

    # Find next heading at same or higher level (fewer or equal # chars)
    rest = base[after_heading:]
    next_heading = re.search(
        rf"^#{{{1},{heading_level}}}\s+",
        rest,
        re.MULTILINE,
    )
    if next_heading:
        section_end = after_heading + next_heading.start()
    else:
        section_end = len(base)

    # Rebuild: before section + heading line + replacement + after section
    before = base[:section_start]
    after = base[section_end:]
    return f"{before}{match.group(0)}\n\n{replacement}\n\n{after.lstrip()}"
