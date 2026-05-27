"""Platform-generated read-only "builtin" docs that surface in the public-files
area: platform guide + one page per published agent + one page per agentic skill.

Source of truth lives on disk (files/使用指南.md, agents/<id>/{agent.json,prompt/system.md},
skills/<id>/{SKILL.md,INTRO.zh.md}). Content is rendered on read — no files are
written to disk for these entries, so agent/skill edits reflect immediately.

Public API surface via file_svc routing:
- `list_docs()` → FileMeta-shaped dicts with id prefixes `builtin-guide|-agent-|-skill-`
- `read_doc(doc_id)` → same envelope shape as file_svc.read_public_file

Delete/write paths must reject any id starting with `BUILTIN_PREFIX`.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from ..core.errors import APIError, ErrorCode
from ..core.storage import get_paths, read_json

BUILTIN_PREFIX = "builtin-"
_ID_GUIDE = "builtin-guide"
_ID_AGENT = "builtin-agent-"
_ID_SKILL = "builtin-skill-"


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _stat_iso(p: Path) -> str:
    try:
        return datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc).isoformat()
    except OSError:
        return _now_iso()


def _meta(doc_id: str, name: str, mtime: str, size: int, kind: str) -> dict:
    return {
        "id": doc_id,
        "name": name,
        "scope": "public",
        "task_id": None,
        "path": f"__builtin__/{doc_id}",
        "file_type": "text",
        "format": "md",
        # 与 file_svc.list_public_files 保持字段名一致，前端 fmtSize 读 size_bytes
        "size_bytes": size,
        "size": size,
        "is_pinned": False,
        "created_at": mtime,
        "updated_at": mtime,
        "owner_id": None,
        "owner_name": "平台",
        # Custom flags the frontend reads to render the badge / hide edit controls
        "builtin": True,
        "builtin_kind": kind,  # "guide" | "agent" | "skill"
    }


# ---- enumeration ----


def list_docs() -> list[dict]:
    paths = get_paths()
    out: list[dict] = []

    # 1) Platform guide — prefer files/平台使用指南.md, fall back to files/使用指南.md
    guide = _find_guide_source()
    if guide:
        text = _safe_read(guide)
        out.append(
            _meta(
                _ID_GUIDE,
                "平台使用指南.md",
                _stat_iso(guide),
                len(text.encode("utf-8")),
                "guide",
            )
        )

    # 2) Per published agent — agents/<id>/agent.json with publish_status=published
    agents_root = paths.agents
    if agents_root.exists():
        for d in sorted(agents_root.iterdir()):
            if not d.is_dir() or d.name.startswith(".") or d.name.startswith("_"):
                continue
            cfg = read_json(d / "agent.json")
            if not cfg or cfg.get("publish_status") != "published":
                continue
            rendered = _render_agent_doc(d, cfg)
            out.append(
                _meta(
                    _ID_AGENT + cfg["id"],
                    f"Agent · {cfg.get('name', cfg['id'])}.md",
                    _stat_iso(d / "agent.json"),
                    len(rendered.encode("utf-8")),
                    "agent",
                )
            )

    # 3) Per agentic skill — skills/<id>/SKILL.md with frontmatter
    skills_root = paths.skills
    if skills_root.exists():
        for d in sorted(skills_root.iterdir()):
            if not d.is_dir() or d.name.startswith("."):
                continue
            skill_md = d / "SKILL.md"
            if not skill_md.exists():
                continue
            rendered = _render_skill_doc(d)
            out.append(
                _meta(
                    _ID_SKILL + d.name,
                    f"Skill · {d.name}.md",
                    _stat_iso(skill_md),
                    len(rendered.encode("utf-8")),
                    "skill",
                )
            )

    return out


# ---- read ----


def is_builtin(doc_id: str) -> bool:
    return doc_id.startswith(BUILTIN_PREFIX)


def read_doc(doc_id: str) -> dict:
    paths = get_paths()
    if doc_id == _ID_GUIDE:
        guide = _find_guide_source()
        if not guide:
            raise APIError(404, ErrorCode.RESOURCE_NOT_FOUND, "平台使用指南缺失")
        text = _safe_read(guide)
        meta = _meta(_ID_GUIDE, "平台使用指南.md", _stat_iso(guide), len(text.encode("utf-8")), "guide")
        return {"meta": meta, "content": text}

    if doc_id.startswith(_ID_AGENT):
        aid = doc_id[len(_ID_AGENT):]
        d = paths.agents / aid
        cfg = read_json(d / "agent.json")
        if not cfg:
            raise APIError(404, ErrorCode.RESOURCE_NOT_FOUND, f"Agent {aid} 不存在")
        if cfg.get("publish_status") != "published":
            raise APIError(404, ErrorCode.RESOURCE_NOT_FOUND, f"Agent {aid} 尚未上线")
        text = _render_agent_doc(d, cfg)
        meta = _meta(
            doc_id,
            f"Agent · {cfg.get('name', aid)}.md",
            _stat_iso(d / "agent.json"),
            len(text.encode("utf-8")),
            "agent",
        )
        return {"meta": meta, "content": text}

    if doc_id.startswith(_ID_SKILL):
        sid = doc_id[len(_ID_SKILL):]
        d = paths.skills / sid
        if not (d / "SKILL.md").exists():
            raise APIError(404, ErrorCode.RESOURCE_NOT_FOUND, f"Skill {sid} 不存在")
        text = _render_skill_doc(d)
        meta = _meta(
            doc_id,
            f"Skill · {sid}.md",
            _stat_iso(d / "SKILL.md"),
            len(text.encode("utf-8")),
            "skill",
        )
        return {"meta": meta, "content": text}

    raise APIError(404, ErrorCode.RESOURCE_NOT_FOUND, "内置文档不存在")


# ---- renderers ----


def _find_guide_source() -> Path | None:
    files = get_paths().files
    for name in ("平台使用指南.md", "使用指南.md"):
        p = files / name
        if p.exists():
            return p
    return None


def _safe_read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except OSError:
        return ""


def _render_agent_doc(agent_dir: Path, cfg: dict) -> str:
    name = cfg.get("name", agent_dir.name)
    paradigm = cfg.get("paradigm", "")
    icon = cfg.get("icon", "")
    desc = cfg.get("description", "")
    system_prompt = cfg.get("system_prompt", "")
    sp_file = agent_dir / "prompt" / "system.md"
    if sp_file.exists():
        sp_text = _safe_read(sp_file).strip()
        if sp_text:
            system_prompt = sp_text

    parts: list[str] = []
    parts.append(f"# {icon} {name}".strip())
    parts.append("")
    parts.append(f"- **ID**: `{cfg.get('id', agent_dir.name)}`")
    parts.append(f"- **范式 (paradigm)**: `{paradigm}`")
    parts.append(f"- **状态**: 已上线")
    parts.append("")
    if desc:
        parts.append("## 一句话介绍")
        parts.append("")
        parts.append(desc)
        parts.append("")

    # Knowledge (optional)
    kb_dir = agent_dir / "knowledge"
    if kb_dir.exists() and kb_dir.is_dir():
        kb_items = [p.name for p in sorted(kb_dir.iterdir()) if not p.name.startswith(".")]
        if kb_items:
            parts.append("## 绑定的知识库")
            parts.append("")
            for k in kb_items:
                parts.append(f"- `{k}`")
            parts.append("")

    if system_prompt:
        parts.append("## System Prompt（执行规则）")
        parts.append("")
        parts.append("```")
        parts.append(system_prompt.strip())
        parts.append("```")
        parts.append("")

    parts.append("---")
    parts.append("")
    parts.append("> 本文档由平台从 `agents/" + agent_dir.name + "/` 自动生成，只读。修改 agent 配置后刷新会同步更新。")
    return "\n".join(parts).rstrip() + "\n"


def _render_skill_doc(skill_dir: Path) -> str:
    skill_md = skill_dir / "SKILL.md"
    intro_zh = skill_dir / "INTRO.zh.md"

    body_parts: list[str] = []
    body_parts.append(f"# 🧰 Skill · {skill_dir.name}")
    body_parts.append("")

    # Frontmatter description if present
    fm = _parse_frontmatter(skill_md)
    if fm.get("description"):
        body_parts.append("## 一句话介绍")
        body_parts.append("")
        body_parts.append(fm["description"].strip())
        body_parts.append("")

    # Chinese intro takes priority as the user-facing doc
    if intro_zh.exists():
        zh_text = _safe_read(intro_zh).strip()
        if zh_text:
            body_parts.append("## 中文说明")
            body_parts.append("")
            body_parts.append(zh_text)
            body_parts.append("")

    # Operator-level SKILL.md body (without frontmatter)
    sk_body = _strip_frontmatter(_safe_read(skill_md)).strip()
    if sk_body:
        body_parts.append("## 详细说明（SKILL.md）")
        body_parts.append("")
        body_parts.append(sk_body)
        body_parts.append("")

    body_parts.append("---")
    body_parts.append("")
    body_parts.append("> 本文档由平台从 `skills/" + skill_dir.name + "/` 自动生成，只读。")
    return "\n".join(body_parts).rstrip() + "\n"


def _parse_frontmatter(md_path: Path) -> dict:
    if not md_path.exists():
        return {}
    text = _safe_read(md_path)
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    out: dict = {}
    block_key: str | None = None
    block_lines: list[str] = []
    for raw in parts[1].splitlines():
        line = raw.rstrip()
        if block_key is None:
            if ":" in line and not line.startswith(("  ", "\t")):
                k, _, v = line.partition(":")
                k = k.strip()
                v = v.strip()
                if v in ("|", "|-"):
                    block_key = k
                    block_lines = []
                else:
                    out[k] = v.strip('"').strip("'")
        else:
            if line.startswith(("  ", "\t")) or not line.strip():
                block_lines.append(line.lstrip())
            else:
                out[block_key] = "\n".join(block_lines).strip()
                block_key = None
                block_lines = []
    if block_key is not None:
        out[block_key] = "\n".join(block_lines).strip()
    return out


def _strip_frontmatter(text: str) -> str:
    if not text.startswith("---"):
        return text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return text
    return parts[2].lstrip("\n")
