"""项目服务：CRUD + 成员管理。项目必须归属于团队。

存储：teams/{tid}/projects/{pid}/project.json
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.core.errors import APIError, ErrorCode
from app.core.storage import paths
from app.core.storage.jsonio import iter_dirs, read_json, write_json


def get_project(team_id: str, project_id: str) -> dict:
    meta = read_json(paths.project_json(team_id, project_id))
    if meta is None:
        raise APIError(404, ErrorCode.NOT_FOUND, f"项目不存在: {project_id}")
    return meta


def list_projects(team_id: str, *, user_id: str | None = None) -> list[dict]:
    """列出团队下所有项目。如指定 user_id 则只返回该用户参与的。"""
    out: list[dict] = []
    for d in iter_dirs(paths.team_dir(team_id) / "projects"):
        meta = read_json(d / "project.json", default={"id": d.name, "name": d.name})
        if user_id:
            members = meta.get("members", [])
            if not any(m.get("user_id") == user_id for m in members):
                continue
        out.append({
            "id": meta.get("id", d.name),
            "name": meta.get("name", d.name),
            "team_id": team_id,
            "type": meta.get("type", "project"),
            "member_count": len(meta.get("members", [])),
        })
    return out


def create_project(team_id: str, project_id: str, *, name: str, owner_id: str) -> dict:
    """创建项目。创建者自动为 owner。"""
    # 确保团队存在
    from app.services.team_svc import get_team
    get_team(team_id)  # 不存在会 raise

    pj = paths.project_json(team_id, project_id)
    if read_json(pj) is not None:
        raise APIError(409, ErrorCode.CONFLICT, f"项目已存在: {project_id}")

    meta = {
        "id": project_id,
        "team_id": team_id,
        "name": name,
        "type": "project",
        "members": [{"user_id": owner_id, "role": "owner"}],
        "created_at": _now_iso(),
    }
    paths.ensure(pj)
    write_json(pj, meta)
    return meta


def update_project(team_id: str, project_id: str, *, name: str | None = None) -> dict:
    """更新项目信息。"""
    meta = get_project(team_id, project_id)
    if name is not None:
        meta["name"] = name
    meta["updated_at"] = _now_iso()
    write_json(paths.project_json(team_id, project_id), meta)
    return meta


def delete_project(team_id: str, project_id: str) -> None:
    """删除项目（标记删除）。个人项目不可删除。"""
    meta = get_project(team_id, project_id)
    if meta.get("type") == "personal":
        raise APIError(400, ErrorCode.BAD_REQUEST, "个人项目不可删除")
    meta["deleted_at"] = _now_iso()
    write_json(paths.project_json(team_id, project_id), meta)


# ─── 成员管理 ───

def add_member(team_id: str, project_id: str, user_id: str, role: str = "member") -> dict:
    _validate_role(role)
    meta = get_project(team_id, project_id)
    members = meta.get("members", [])

    if any(m.get("user_id") == user_id for m in members):
        raise APIError(409, ErrorCode.CONFLICT, f"用户 {user_id} 已是项目成员")

    members.append({"user_id": user_id, "role": role})
    meta["members"] = members
    meta["updated_at"] = _now_iso()
    write_json(paths.project_json(team_id, project_id), meta)
    return meta


def remove_member(team_id: str, project_id: str, user_id: str) -> dict:
    meta = get_project(team_id, project_id)
    members = meta.get("members", [])
    entry = next((m for m in members if m.get("user_id") == user_id), None)

    if entry is None:
        raise APIError(404, ErrorCode.NOT_FOUND, f"用户 {user_id} 不是项目成员")
    if entry.get("role") == "owner":
        raise APIError(400, ErrorCode.BAD_REQUEST, "不能移除项目 owner")

    meta["members"] = [m for m in members if m.get("user_id") != user_id]
    meta["updated_at"] = _now_iso()
    write_json(paths.project_json(team_id, project_id), meta)
    return meta


# ─── 内部 ───

def _validate_role(role: str) -> None:
    if role not in ("owner", "admin", "member"):
        raise APIError(400, ErrorCode.BAD_REQUEST, f"无效角色: {role}")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
