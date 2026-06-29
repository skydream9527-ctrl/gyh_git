"""产物服务：任务产出物管理（3 态 + 渐进展开 + 保存为产物选层级）。

产物 3 态：draft（草稿）→ published（已发布）→ archived（归档）。
落盘：任务产物在 tasks/{tid}/files/output/；"保存为产物"晋升到项目/团队/用户空间。
任务的 artifacts[] 索引记录在 task.json。
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.core.errors import APIError, ErrorCode
from app.core.storage import paths
from app.core.storage.jsonio import read_json, write_json, write_text
from app.core.storage.transaction import file_transaction

ARTIFACT_DRAFT = "draft"
ARTIFACT_PUBLISHED = "published"
ARTIFACT_ARCHIVED = "archived"

VALID_KINDS = {"report", "doc", "table", "code", "chart"}


def list_artifacts(task_id: str) -> list[dict]:
    """列出任务的产物索引（task.json#artifacts）。"""
    meta = read_json(paths.task_json(task_id))
    if meta is None:
        raise APIError(404, ErrorCode.NOT_FOUND, f"任务不存在: {task_id}")
    return meta.get("artifacts", [])


def create_artifact(
    task_id: str, *, title: str, kind: str = "doc", content: str = "",
    filename: str | None = None,
) -> dict:
    """在任务输出区创建产物（draft）。"""
    meta = read_json(paths.task_json(task_id))
    if meta is None:
        raise APIError(404, ErrorCode.NOT_FOUND, f"任务不存在: {task_id}")
    if kind not in VALID_KINDS:
        raise APIError(400, ErrorCode.BAD_REQUEST, f"无效产物类型: {kind}")

    aid = f"art_{uuid.uuid4().hex[:10]}"
    fname = filename or f"{aid}.md"
    out_path = paths.task_files(task_id, "output") / fname
    paths.ensure(out_path)
    write_text(out_path, content)

    artifact = {
        "id": aid,
        "title": title,
        "kind": kind,
        "status": ARTIFACT_DRAFT,
        "filename": fname,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    artifacts = meta.get("artifacts", [])
    artifacts.append(artifact)
    meta["artifacts"] = artifacts
    meta["updated_at"] = _now_iso()
    write_json(paths.task_json(task_id), meta)
    return artifact


def get_artifact_content(task_id: str, artifact_id: str) -> dict:
    """读取产物内容（渐进展开第 3 态：内容）。"""
    artifact = _find_artifact(task_id, artifact_id)
    out_path = paths.task_files(task_id, "output") / artifact["filename"]
    content = out_path.read_text(encoding="utf-8") if out_path.exists() else ""
    return {**artifact, "content": content}


def set_status(task_id: str, artifact_id: str, status: str) -> dict:
    """变更产物状态。"""
    if status not in (ARTIFACT_DRAFT, ARTIFACT_PUBLISHED, ARTIFACT_ARCHIVED):
        raise APIError(400, ErrorCode.BAD_REQUEST, f"无效产物状态: {status}")
    meta = read_json(paths.task_json(task_id))
    if meta is None:
        raise APIError(404, ErrorCode.NOT_FOUND, f"任务不存在: {task_id}")
    artifacts = meta.get("artifacts", [])
    target = next((a for a in artifacts if a["id"] == artifact_id), None)
    if target is None:
        raise APIError(404, ErrorCode.NOT_FOUND, f"产物不存在: {artifact_id}")
    target["status"] = status
    target["updated_at"] = _now_iso()
    meta["updated_at"] = _now_iso()
    write_json(paths.task_json(task_id), meta)
    return target


def save_to_space(
    task_id: str, artifact_id: str, *, level: str, project_id: str = "", team_id: str = "",
    user_id: str = "",
) -> dict:
    """保存为产物到指定层级空间（project/team/user）。原子操作。"""
    artifact = _find_artifact(task_id, artifact_id)
    src = paths.task_files(task_id, "output") / artifact["filename"]
    if not src.exists():
        raise APIError(404, ErrorCode.NOT_FOUND, "产物文件不存在")
    content = src.read_text(encoding="utf-8")

    if level == "project":
        if not (team_id and project_id):
            raise APIError(400, ErrorCode.BAD_REQUEST, "项目级需 team_id + project_id")
        dst = paths.project_shared(team_id, project_id, "artifacts") / artifact["filename"]
    elif level == "team":
        if not team_id:
            raise APIError(400, ErrorCode.BAD_REQUEST, "团队级需 team_id")
        dst = paths.team_shared(team_id, "artifacts") / artifact["filename"]
    elif level == "user":
        if not user_id:
            raise APIError(400, ErrorCode.BAD_REQUEST, "用户级需 user_id")
        dst = paths.user_artifacts(user_id) / artifact["filename"]
    else:
        raise APIError(400, ErrorCode.BAD_REQUEST, f"无效层级: {level}")

    paths.ensure(dst)
    with file_transaction([dst]):
        write_text(dst, content)

    # 标记已发布
    set_status(task_id, artifact_id, ARTIFACT_PUBLISHED)
    return {"artifact_id": artifact_id, "level": level, "saved_to": str(dst.name)}


def _find_artifact(task_id: str, artifact_id: str) -> dict:
    meta = read_json(paths.task_json(task_id))
    if meta is None:
        raise APIError(404, ErrorCode.NOT_FOUND, f"任务不存在: {task_id}")
    target = next((a for a in meta.get("artifacts", []) if a["id"] == artifact_id), None)
    if target is None:
        raise APIError(404, ErrorCode.NOT_FOUND, f"产物不存在: {artifact_id}")
    return target


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
