"""产物路由：任务产物列表 / 创建 / 内容 / 状态 / 保存到空间。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.deps import get_current_user
from app.core.errors import ok
from app.services import artifact_svc

router = APIRouter(prefix="/tasks/{task_id}/artifacts", tags=["artifacts"])


class CreateArtifactReq(BaseModel):
    title: str
    kind: str = "doc"
    content: str = ""
    filename: str | None = None


class StatusReq(BaseModel):
    status: str


class SaveToSpaceReq(BaseModel):
    level: str  # project | team | user
    project_id: str = ""
    team_id: str = ""


@router.get("")
def list_artifacts(task_id: str, user: dict = Depends(get_current_user)) -> dict:
    return ok(artifact_svc.list_artifacts(task_id))


@router.post("")
def create_artifact(task_id: str, body: CreateArtifactReq, user: dict = Depends(get_current_user)) -> dict:
    result = artifact_svc.create_artifact(
        task_id, title=body.title, kind=body.kind, content=body.content, filename=body.filename,
    )
    return ok(result)


@router.get("/{artifact_id}")
def get_artifact(task_id: str, artifact_id: str, user: dict = Depends(get_current_user)) -> dict:
    return ok(artifact_svc.get_artifact_content(task_id, artifact_id))


@router.put("/{artifact_id}/status")
def set_status(task_id: str, artifact_id: str, body: StatusReq, user: dict = Depends(get_current_user)) -> dict:
    return ok(artifact_svc.set_status(task_id, artifact_id, body.status))


@router.post("/{artifact_id}/save")
def save_to_space(task_id: str, artifact_id: str, body: SaveToSpaceReq, user: dict = Depends(get_current_user)) -> dict:
    result = artifact_svc.save_to_space(
        task_id, artifact_id, level=body.level,
        project_id=body.project_id, team_id=body.team_id, user_id=user["id"],
    )
    return ok(result)
