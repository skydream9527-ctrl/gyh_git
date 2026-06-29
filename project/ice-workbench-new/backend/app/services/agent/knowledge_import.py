"""Cross-agent knowledge imports.

Allows an agent to declare read-only references to other agents' knowledge
subdirectories via `agent.json.knowledge_imports`. This enables cooperation
without duplicating files.

Example agent.json:
    {
      "knowledge_imports": [
        "data-analysis/knowledge/metrics",
        "ab-experiment/knowledge/rules"
      ]
    }

At prompt assembly time, the imported knowledge paths are resolved and their
content is made available to the `read_agent_knowledge` tool (read-only).
"""
from __future__ import annotations

from pathlib import Path

from ...core.storage import get_paths


def resolve_knowledge_imports(agent_id: str) -> list[dict]:
    """Resolve the knowledge_imports declared in an agent's config.

    Returns a list of {"agent_id", "subpath", "abs_path", "exists"} dicts
    for each declared import. Does NOT load content — that's done on-demand
    by the read_agent_knowledge tool when the LLM requests it.
    """
    from . import agents_svc

    cfg = agents_svc.get_agent(agent_id) or {}
    imports = cfg.get("knowledge_imports") or []
    if not isinstance(imports, list):
        return []

    paths = get_paths()
    resolved: list[dict] = []

    for import_path in imports:
        if not isinstance(import_path, str) or not import_path.strip():
            continue
        # Format: "{source_agent_id}/knowledge/{subpath}"
        parts = import_path.strip().split("/", 2)
        if len(parts) < 2:
            continue

        source_agent = parts[0]
        # Rest after the agent_id (e.g. "knowledge/metrics")
        rel = "/".join(parts[1:])

        abs_path = paths.agents / source_agent / rel
        resolved.append({
            "agent_id": source_agent,
            "subpath": rel,
            "abs_path": str(abs_path),
            "exists": abs_path.exists(),
        })

    return resolved


def read_imported_knowledge(agent_id: str, source_agent: str, path: str) -> dict:
    """Read a file from an imported agent's knowledge directory.

    Args:
        agent_id: the requesting agent (must have the import declared)
        source_agent: the agent whose knowledge is being read
        path: relative path within the source agent's knowledge/ dir

    Returns:
        {"content": str, "path": str} or {"error_code": ..., "message": ...}
    """
    from . import agents_svc

    cfg = agents_svc.get_agent(agent_id) or {}
    imports = cfg.get("knowledge_imports") or []

    # Verify the requesting agent has declared this import
    allowed = False
    for imp in imports:
        if isinstance(imp, str) and imp.startswith(f"{source_agent}/"):
            allowed = True
            break

    if not allowed:
        return {
            "error_code": "IMPORT_NOT_DECLARED",
            "message": f"Agent '{agent_id}' has not declared a knowledge_import from '{source_agent}'",
        }

    paths = get_paths()
    # Resolve and validate path safety
    knowledge_base = paths.agents / source_agent / "knowledge"
    if not knowledge_base.exists():
        return {
            "error_code": "KNOWLEDGE_NOT_FOUND",
            "message": f"Agent '{source_agent}' has no knowledge directory",
        }

    target = (knowledge_base / path).resolve()
    try:
        target.relative_to(knowledge_base.resolve())
    except ValueError:
        return {
            "error_code": "PATH_TRAVERSAL",
            "message": "Path escapes the knowledge directory",
        }

    if not target.exists() or not target.is_file():
        return {
            "error_code": "FILE_NOT_FOUND",
            "message": f"File not found: {path}",
        }

    try:
        content = target.read_text(encoding="utf-8")
        return {"content": content, "path": str(target), "source_agent": source_agent}
    except (OSError, UnicodeDecodeError) as exc:
        return {"error_code": "READ_ERROR", "message": str(exc)[:200]}


def render_import_hints(agent_id: str) -> str:
    """Render a short hint section for the system prompt listing available imports.

    Only includes imports whose source directories actually exist.
    """
    resolved = resolve_knowledge_imports(agent_id)
    available = [r for r in resolved if r["exists"]]
    if not available:
        return ""

    lines = ["## 可引用的外部 Knowledge (knowledge_imports)"]
    for r in available:
        lines.append(
            f'- `{r["agent_id"]}/{r["subpath"]}` — '
            f'调 `read_agent_knowledge(path="{r["subpath"]}/...", source_agent="{r["agent_id"]}")` 读取'
        )
    return "\n".join(lines)
