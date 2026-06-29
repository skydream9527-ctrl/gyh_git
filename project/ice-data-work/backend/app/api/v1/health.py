from __future__ import annotations

from fastapi import APIRouter

from app import __version__
from app.core.config import get_settings
from app.core.errors import ok

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    s = get_settings()
    return ok(
        {
            "status": "healthy",
            "version": __version__,
            "data_root": str(s.data_root),
            "llm_enabled": s.llm_enabled,
            "pgvector_enabled": s.pgvector_enabled,
            "features": {
                "twin": s.twin_enabled,
                "self_evolve": s.self_evolve_enabled,
                "daemon": s.daemon_enabled,
                "cross_twin": s.cross_twin_enabled,
            },
        }
    )
