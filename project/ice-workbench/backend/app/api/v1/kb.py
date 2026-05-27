"""User-facing knowledge base endpoints.

Non-admin read-only access to enabled KBs. Admin-only create/update/delete/sync
lives in admin_resources.py. These routes power Dashboard's 📚 知识库 tab and
Workspace's left-sidebar 📚 知识库 section.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ...core.deps import get_current_user
from ...core.errors import ok
from ...services import kb_svc

router = APIRouter()


def _public_view(kb: dict) -> dict:
    """Strip fields that aren't useful to end users (config keys, timestamps
    admins use)."""
    return {
        "id": kb.get("id"),
        "name": kb.get("name"),
        "description": kb.get("description"),
        "source_type": kb.get("source_type"),
        "doc_count": kb.get("doc_count") or 0,
        "last_sync_at": kb.get("last_sync_at"),
        "enabled": kb.get("enabled", True),
    }


@router.get("/kb")
async def list_kbs(_: dict = Depends(get_current_user)):
    items = [_public_view(k) for k in kb_svc.list_kbs() if k.get("enabled", True)]
    return ok({"items": items, "total": len(items)})


@router.get("/kb/{kb_id}/articles")
async def list_articles(kb_id: str, _: dict = Depends(get_current_user)):
    items = kb_svc.list_articles(kb_id)
    return ok({"items": items, "total": len(items)})


@router.get("/kb/{kb_id}/articles/{article_id}")
async def get_article(kb_id: str, article_id: str, _: dict = Depends(get_current_user)):
    article = await kb_svc.get_article(kb_id, article_id)
    return ok(article)
