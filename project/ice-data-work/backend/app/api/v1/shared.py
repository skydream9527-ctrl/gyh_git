"""共享空间路由：项目/团队共享 files/knowledge/artifacts（成员 gate）。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.deps import get_current_user, require_member
from app.core.errors import ok
from app.services import shared_svc

router = APIRouter(prefix="/teams/{team_id}", tags=["shared"])


class WriteItemReq(BaseModel):
    name: str
    content: str


# ─── 团队级共享 ───

@router.get("/shared/{kind}")
def list_team_shared(
    team_id: str, kind: str,
    user: dict = Depends(require_member("team_id")),
) -> dict:
    return ok(shared_svc.list_items("team", kind, tid=team_id))


@router.get("/shared/{kind}/{name}")
def read_team_shared(
    team_id: str, kind: str, name: str,
    user: dict = Depends(require_member("team_id")),
) -> dict:
    return ok(shared_svc.read_item("team", kind, name, tid=team_id))


@router.post("/shared/{kind}")
def write_team_shared(
    team_id: str, kind: str, body: WriteItemReq,
    user: dict = Depends(require_member("team_id")),
) -> dict:
    return ok(shared_svc.write_item("team", kind, body.name, body.content, tid=team_id))


# ─── 项目级共享 ───

@router.get("/projects/{project_id}/shared/{kind}")
def list_project_shared(
    team_id: str, project_id: str, kind: str,
    user: dict = Depends(require_member("team_id")),
) -> dict:
    return ok(shared_svc.list_items("project", kind, tid=team_id, pid=project_id))


@router.post("/projects/{project_id}/shared/{kind}")
def write_project_shared(
    team_id: str, project_id: str, kind: str, body: WriteItemReq,
    user: dict = Depends(require_member("team_id")),
) -> dict:
    return ok(shared_svc.write_item("project", kind, body.name, body.content, tid=team_id, pid=project_id))


@router.get("/projects/{project_id}/assets")
def project_assets(
    team_id: str, project_id: str,
    user: dict = Depends(require_member("team_id")),
) -> dict:
    """汇总项目可见的全部共享资产（项目级 + 团队级），供知识/产物页层级筛选。"""
    return ok(shared_svc.list_all_for_project(team_id, project_id))
