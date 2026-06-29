from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ...core.deps import get_current_user
from ...core.errors import ok
from ...core.storage import get_index_db
from ...services import agents_svc, file_svc
from ...services.task import fts_svc

router = APIRouter()


@router.get("")
async def search(
    q: str = Query(..., min_length=1),
    type: str | None = Query(None),
    user: dict = Depends(get_current_user),
):
    db = get_index_db()
    out: dict[str, list[dict]] = {"tasks": [], "agents": [], "skills": [], "files": []}
    if type in (None, "task"):
        rows = await db.fetchall(
            "SELECT id, name, paradigm, owner_id FROM tasks_index WHERE name LIKE ? LIMIT 20",
            [f"%{q}%"],
        )
        out["tasks"] = [{"id": r["id"], "name": r["name"], "paradigm": r["paradigm"]} for r in rows]
    if type in (None, "agent"):
        out["agents"] = [a for a in agents_svc.list_agents() if q.lower() in a["name"].lower()]
    if type in (None, "skill"):
        out["skills"] = [s for s in agents_svc.list_skills() if q.lower() in s["name"].lower()]
    if type in (None, "file"):
        out["files"] = [
            f for f in await file_svc.list_public_files() if q.lower() in f["name"].lower()
        ]
    return ok(out)


@router.get("/fulltext")
async def fulltext_search(
    q: str = Query(..., min_length=1, max_length=200),
    task_id: str | None = Query(None),
    source_type: str | None = Query(None, description="'message' or 'file'"),
    limit: int = Query(30, ge=1, le=100),
    user: dict = Depends(get_current_user),
):
    """Full-text search across conversation messages and task output files.

    Uses SQLite FTS5 for fast fuzzy matching with ranked results and snippets.
    Results include highlighted snippets showing the match context.
    """
    results = await fts_svc.search(
        query=q,
        task_id=task_id,
        source_type=source_type,
        limit=limit,
    )
    return ok({"items": results, "total": len(results), "query": q})


@router.post("/fulltext/rebuild")
async def rebuild_fts_index(
    user: dict = Depends(get_current_user),
):
    """Rebuild the full-text search index from filesystem. Admin operation."""
    if user.get("auth_role") not in ("admin", "super_admin"):
        from ...core.errors import APIError, ErrorCode
        raise APIError(403, ErrorCode.PERMISSION_DENIED, "仅管理员可重建索引")
    stats = await fts_svc.rebuild_all()
    return ok({"rebuilt": True, **stats})
