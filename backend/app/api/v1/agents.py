from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Query

from ...core.deps import get_current_user
from ...core.errors import APIError, ErrorCode, ok
from ...core.storage import get_paths
from ...services import agent_workflow_svc, agents_svc

router = APIRouter()


# 展示在前端的扩展白名单（可预览 / 可读内容）+ 允许的二进制标注
_TEXT_EXTS = {
    "md", "txt", "json", "yaml", "yml", "py", "ts", "tsx", "js", "css",
    "html", "htm", "sh", "sql", "toml", "ini", "cfg", "env", "rst",
    "mdc",  # cursor rules
}
_SKIP_DIRS = {"__pycache__", ".venv", "venv", ".git", "node_modules", ".ruff_cache", ".mypy_cache", ".pytest_cache"}
# 单文件预览上限（字节），超出只读前部 + 尾部标注
_MAX_READ_BYTES = 500_000


def _agent_root(agent_id: str) -> Path:
    if not agent_id or "/" in agent_id or "\\" in agent_id or agent_id.startswith("."):
        raise APIError(400, ErrorCode.VALIDATION_ERROR, "agent_id 非法")
    root = (get_paths().agents / agent_id).resolve()
    if not root.exists() or not root.is_dir():
        raise APIError(404, ErrorCode.RESOURCE_NOT_FOUND, "Agent 不存在")
    return root


def _is_text(rel: str) -> bool:
    ext = rel.rsplit(".", 1)[-1].lower() if "." in rel else ""
    return ext in _TEXT_EXTS


@router.get("")
async def list_agents(_: dict = Depends(get_current_user)):
    items = agents_svc.list_agents()
    return ok({"items": items, "total": len(items)})


@router.get("/{agent_id}")
async def get_agent(agent_id: str, _: dict = Depends(get_current_user)):
    a = agents_svc.get_agent(agent_id)
    if not a:
        raise APIError(404, ErrorCode.RESOURCE_NOT_FOUND, "Agent 不存在")
    return ok(a)


@router.get("/{agent_id}/workflows")
async def list_agent_workflows(agent_id: str, _: dict = Depends(get_current_user)):
    _agent_root(agent_id)
    items = agent_workflow_svc.list_workflows(agent_id)
    return ok({"items": items, "total": len(items), "agent_id": agent_id})


@router.get("/{agent_id}/files")
async def list_agent_files(agent_id: str, _: dict = Depends(get_current_user)):
    """List every file under agents/<agent_id>/ (recursive, skipping caches).
    Returned entries carry relative path + size + text-ness for the UI.
    """
    root = _agent_root(agent_id)
    items: list[dict] = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        # Skip caches / hidden
        if any(part in _SKIP_DIRS for part in p.parts):
            continue
        if p.name.startswith(".") and p.name not in (".env.example",):
            continue
        rel = p.relative_to(root).as_posix()
        try:
            size = p.stat().st_size
        except OSError:
            continue
        items.append({
            "path": rel,
            "name": p.name,
            "size": size,
            "dir": str(Path(rel).parent).replace(".", "") or "",
            "text": _is_text(rel),
            "ext": rel.rsplit(".", 1)[-1].lower() if "." in rel else "",
        })
    items.sort(key=lambda x: (x["dir"], x["name"].lower()))
    return ok({"items": items, "total": len(items), "agent_id": agent_id})


@router.get("/{agent_id}/files/read")
async def read_agent_file(
    agent_id: str,
    path: str = Query(..., description="relative path inside the agent directory"),
    _: dict = Depends(get_current_user),
):
    root = _agent_root(agent_id)
    # Normalize + prevent traversal
    rel = path.strip().lstrip("/")
    if ".." in rel.split("/") or rel.startswith("/"):
        raise APIError(400, ErrorCode.VALIDATION_ERROR, "path 非法")
    target = (root / rel).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        raise APIError(400, ErrorCode.VALIDATION_ERROR, "path 越界") from None
    if not target.exists() or not target.is_file():
        raise APIError(404, ErrorCode.RESOURCE_NOT_FOUND, "文件不存在")
    size = target.stat().st_size
    if not _is_text(rel):
        return ok({
            "path": rel, "name": target.name, "size": size,
            "binary": True, "content": None,
        })
    raw = target.read_bytes()
    truncated = False
    if len(raw) > _MAX_READ_BYTES:
        raw = raw[:_MAX_READ_BYTES]
        truncated = True
    text = raw.decode("utf-8", errors="replace")
    if truncated:
        text += f"\n\n... [截断：文件共 {size} 字节，仅展示前 {_MAX_READ_BYTES} 字节] ..."
    return ok({
        "path": rel, "name": target.name, "size": size,
        "binary": False, "content": text, "truncated": truncated,
    })
