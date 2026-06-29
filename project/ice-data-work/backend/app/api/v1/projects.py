"""项目路由：CRUD + 成员管理（隶属于团队）。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.deps import get_current_user, require_member
from app.core.errors import ok
from app.core.permissions import MemberRole
from app.services import project_svc

router = APIRouter(prefix="/teams/{team_id}/projects", tags=["projects"])


class CreateProjectReq(BaseModel):
    id: str
    name: str


class UpdateProjectReq(BaseModel):
    name: str | None = None


class MemberReq(BaseModel):
    user_id: str
    role: str = "member"


@router.get("")
def list_projects(team_id: str, user: dict = Depends(get_current_user)) -> dict:
    projects = project_svc.list_projects(team_id)
    return ok(projects)


@router.post("")
def create_project(
    team_id: str,
    body: CreateProjectReq,
    user: dict = Depends(require_member("team_id", min_role=MemberRole.MEMBER)),
) -> dict:
    result = project_svc.create_project(team_id, body.id, name=body.name, owner_id=user["id"])
    return ok(result)


@router.get("/{project_id}")
def get_project(team_id: str, project_id: str, user: dict = Depends(get_current_user)) -> dict:
    return ok(project_svc.get_project(team_id, project_id))


@router.put("/{project_id}")
def update_project(
    team_id: str,
    project_id: str,
    body: UpdateProjectReq,
    user: dict = Depends(require_member("team_id", min_role=MemberRole.ADMIN)),
) -> dict:
    return ok(project_svc.update_project(team_id, project_id, name=body.name))


@router.delete("/{project_id}")
def delete_project(
    team_id: str,
    project_id: str,
    user: dict = Depends(require_member("team_id", min_role=MemberRole.OWNER)),
) -> dict:
    project_svc.delete_project(team_id, project_id)
    return ok(None, message="已删除")


# ─── 成员管理 ───

@router.post("/{project_id}/members")
def add_member(
    team_id: str,
    project_id: str,
    body: MemberReq,
    user: dict = Depends(require_member("team_id", min_role=MemberRole.ADMIN)),
) -> dict:
    return ok(project_svc.add_member(team_id, project_id, body.user_id, body.role))


@router.delete("/{project_id}/members/{member_id}")
def remove_member(
    team_id: str,
    project_id: str,
    member_id: str,
    user: dict = Depends(require_member("team_id", min_role=MemberRole.ADMIN)),
) -> dict:
    return ok(project_svc.remove_member(team_id, project_id, member_id))
