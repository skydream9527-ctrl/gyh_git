"""团队服务：CRUD + 成员管理（owner/admin/member）。

存储：teams/{tid}/team.json（G3 文件优先）。
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.core.errors import APIError, ErrorCode
from app.core.storage import paths
from app.core.storage.jsonio import iter_dirs, read_json, write_json


# ─── 查询 ───

def list_teams(*, user_id: str | None = None) -> list[dict]:
    """列出团队。如指定 user_id 则只返回该用户所属团队。"""
    out: list[dict] = []
    for d in iter_dirs(paths.root() / "teams"):
        meta = read_json(d / "team.json", default={"id": d.name, "name": d.name})
        if user_id:
            members = meta.get("members", [])
            if not any(m.get("user_id") == user_id for m in members):
                continue
        out.append(_team_summary(meta))
    return out


def get_team(team_id: str) -> dict:
    meta = read_json(paths.team_json(team_id))
    if meta is None:
        raise APIError(404, ErrorCode.NOT_FOUND, f"团队不存在: {team_id}")
    return meta


def list_projects(team_id: str) -> list[dict]:
    out: list[dict] = []
    for d in iter_dirs(paths.team_dir(team_id) / "projects"):
        meta = read_json(d / "project.json", default={"id": d.name, "name": d.name})
        out.append({"id": d.name, "name": meta.get("name", d.name), "team_id": team_id})
    return out


# ─── 创建 / 更新 ───

def create_team(team_id: str, *, name: str, owner_id: str) -> dict:
    """创建团队，创建者自动为 owner。"""
    tj = paths.team_json(team_id)
    if read_json(tj) is not None:
        raise APIError(409, ErrorCode.CONFLICT, f"团队已存在: {team_id}")

    meta = {
        "id": team_id,
        "name": name,
        "type": "team",
        "members": [{"user_id": owner_id, "role": "owner"}],
        "created_at": _now_iso(),
    }
    paths.ensure(tj)
    write_json(tj, meta)
    return meta


def update_team(team_id: str, *, name: str | None = None) -> dict:
    """更新团队信息（名称）。"""
    meta = get_team(team_id)
    if name is not None:
        meta["name"] = name
    meta["updated_at"] = _now_iso()
    write_json(paths.team_json(team_id), meta)
    return meta


def delete_team(team_id: str) -> None:
    """删除团队（标记删除）。"""
    meta = get_team(team_id)
    if meta.get("type") == "personal":
        raise APIError(400, ErrorCode.BAD_REQUEST, "个人空间不可删除")
    meta["deleted_at"] = _now_iso()
    write_json(paths.team_json(team_id), meta)


# ─── 成员管理 ───

def add_member(team_id: str, user_id: str, role: str = "member") -> dict:
    """添加成员。"""
    _validate_role(role)
    meta = get_team(team_id)
    members = meta.get("members", [])

    if any(m.get("user_id") == user_id for m in members):
        raise APIError(409, ErrorCode.CONFLICT, f"用户 {user_id} 已是团队成员")

    members.append({"user_id": user_id, "role": role})
    meta["members"] = members
    meta["updated_at"] = _now_iso()
    write_json(paths.team_json(team_id), meta)
    return meta


def remove_member(team_id: str, user_id: str) -> dict:
    """移除成员。owner 不可移除（需先转让）。"""
    meta = get_team(team_id)
    members = meta.get("members", [])
    entry = next((m for m in members if m.get("user_id") == user_id), None)

    if entry is None:
        raise APIError(404, ErrorCode.NOT_FOUND, f"用户 {user_id} 不是团队成员")
    if entry.get("role") == "owner":
        raise APIError(400, ErrorCode.BAD_REQUEST, "不能移除 owner，请先转让所有权")

    meta["members"] = [m for m in members if m.get("user_id") != user_id]
    meta["updated_at"] = _now_iso()
    write_json(paths.team_json(team_id), meta)
    return meta


def change_role(team_id: str, user_id: str, new_role: str) -> dict:
    """变更成员角色。"""
    _validate_role(new_role)
    meta = get_team(team_id)
    members = meta.get("members", [])
    entry = next((m for m in members if m.get("user_id") == user_id), None)

    if entry is None:
        raise APIError(404, ErrorCode.NOT_FOUND, f"用户 {user_id} 不是团队成员")

    entry["role"] = new_role
    meta["updated_at"] = _now_iso()
    write_json(paths.team_json(team_id), meta)
    return meta


# ─── 内部 ───

def _team_summary(meta: dict) -> dict:
    return {
        "id": meta.get("id", ""),
        "name": meta.get("name", ""),
        "type": meta.get("type", "team"),
        "member_count": len(meta.get("members", [])),
    }


def _validate_role(role: str) -> None:
    if role not in ("owner", "admin", "member"):
        raise APIError(400, ErrorCode.BAD_REQUEST, f"无效角色: {role}")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
