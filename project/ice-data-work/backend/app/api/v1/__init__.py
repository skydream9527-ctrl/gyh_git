"""v1 路由聚合，统一前缀 /api/v1。新资源在此注册。"""
from __future__ import annotations

from fastapi import APIRouter

from . import (
    admin,
    agents,
    artifacts,
    auth,
    governance,
    health,
    memory,
    projects,
    shared,
    skills,
    tasks,
    teams,
    twin,
    users,
    ws,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(teams.router)
api_router.include_router(projects.router)
api_router.include_router(shared.router)
api_router.include_router(twin.router)
api_router.include_router(tasks.router)
api_router.include_router(artifacts.router)
api_router.include_router(agents.router)
api_router.include_router(memory.router)
api_router.include_router(memory.approvals_router)
api_router.include_router(governance.router)
api_router.include_router(admin.router)
api_router.include_router(skills.router)
api_router.include_router(ws.router)
