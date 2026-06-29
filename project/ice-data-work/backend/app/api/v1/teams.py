"""团队路由：CRUD + 成员管理（需认证）。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.deps import get_current_user, require_member
from app.core.errors import ok
from app.core.permissions import MemberRole
from app.services import team_svc

router = APIRouter(prefix="/teams", tags=["teams"])


class CreateTeamReq(BaseModel):
    id: str
    name: str


class UpdateTeamReq(BaseModel):
    name: str | None = None


class MemberReq(BaseModel):
    user_id: str
    role: str = "member"


# ─── 团队 CRUD ───

@router.get("")
def list_teams(user: dict = Depends(get_current_user)) -> dict:
    """列出当前用户所属的所有团队。"""
    teams = team_svc.list_teams(user_id=user["id"])
    return ok(teams)


@router.post("")
def create_team(body: CreateTeamReq, user: dict = Depends(get_current_user)) -> dict:
    """创建团队（当前用户为 owner）。"""
    result = team_svc.create_team(body.id, name=body.name, owner_id=user["id"])
    return ok(result)


@router.get("/{team_id}")
def get_team(team_id: str, user: dict = Depends(get_current_user)) -> dict:
    return ok(team_svc.get_team(team_id))


@router.put("/{team_id}")
def update_team(
    team_id: str,
    body: UpdateTeamReq,
    user: dict = Depends(require_member("team_id", min_role=MemberRole.ADMIN)),
) -> dict:
    return ok(team_svc.update_team(team_id, name=body.name))


@router.delete("/{team_id}")
def delete_team(
    team_id: str,
    user: dict = Depends(require_member("team_id", min_role=MemberRole.OWNER)),
) -> dict:
    team_svc.delete_team(team_id)
    return ok(None, message="已删除")


# ─── 成员管理 ───

@router.post("/{team_id}/members")
def add_member(
    team_id: str,
    body: MemberReq,
    user: dict = Depends(require_member("team_id", min_role=MemberRole.ADMIN)),
) -> dict:
    return ok(team_svc.add_member(team_id, body.user_id, body.role))


@router.delete("/{team_id}/members/{user_id}")
def remove_member(
    team_id: str,
    user_id: str,
    user: dict = Depends(require_member("team_id", min_role=MemberRole.ADMIN)),
) -> dict:
    return ok(team_svc.remove_member(team_id, user_id))


@router.put("/{team_id}/members/{user_id}/role")
def change_role(
    team_id: str,
    user_id: str,
    body: MemberReq,
    user: dict = Depends(require_member("team_id", min_role=MemberRole.OWNER)),
) -> dict:
    return ok(team_svc.change_role(team_id, user_id, body.role))


# ─── 项目列表（属于团队下）───

@router.get("/{team_id}/projects")
def list_projects(team_id: str, user: dict = Depends(get_current_user)) -> dict:
    return ok(team_svc.list_projects(team_id))
