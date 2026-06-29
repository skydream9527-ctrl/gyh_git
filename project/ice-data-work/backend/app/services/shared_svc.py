"""共享空间服务：项目/团队共享 files/knowledge/artifacts（材料三 §6/§7）。

按层隔离（D-07）：
    团队级 → teams/{tid}/shared/{kind}/
    项目级 → teams/{tid}/projects/{pid}/shared/{kind}/
kind ∈ {files, knowledge, artifacts}。成员资格 gate 在 API 层。
读取在组装点过滤；写入直接落（成员有写权）。
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.core.errors import APIError, ErrorCode
from app.core.storage import paths
from app.core.storage.jsonio import write_text

VALID_KINDS = {"files", "knowledge", "artifacts"}


def _base(level: str, kind: str, *, tid: str, pid: str = ""):
    if kind not in VALID_KINDS:
        raise APIError(400, ErrorCode.BAD_REQUEST, f"无效 kind: {kind}")
    if level == "team":
        if not tid:
            raise APIError(400, ErrorCode.BAD_REQUEST, "team 级需 tid")
        return paths.team_shared(tid, kind)
    if level == "project":
        if not (tid and pid):
            raise APIError(400, ErrorCode.BAD_REQUEST, "project 级需 tid + pid")
        return paths.project_shared(tid, pid, kind)
    raise APIError(400, ErrorCode.BAD_REQUEST, f"无效 level: {level}")


def list_items(level: str, kind: str, *, tid: str, pid: str = "") -> list[dict]:
    """列出某层某类的共享条目。"""
    base = _base(level, kind, tid=tid, pid=pid)
    if not base.exists():
        return []
    out: list[dict] = []
    for f in sorted(base.iterdir()):
        if f.is_file() and not f.name.startswith("."):
            stat = f.stat()
            out.append({
                "name": f.name,
                "size": stat.st_size,
                "updated_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                "level": level,
                "kind": kind,
            })
    return out


def read_item(level: str, kind: str, name: str, *, tid: str, pid: str = "") -> dict:
    """读取共享条目内容。"""
    base = _base(level, kind, tid=tid, pid=pid)
    if ".." in name or name.startswith("/"):
        raise APIError(400, ErrorCode.BAD_REQUEST, "非法文件名")
    target = base / name
    if not target.exists() or not target.is_file():
        raise APIError(404, ErrorCode.NOT_FOUND, f"共享条目不存在: {name}")
    return {"name": name, "content": target.read_text(encoding="utf-8"), "level": level, "kind": kind}


def write_item(level: str, kind: str, name: str, content: str, *, tid: str, pid: str = "") -> dict:
    """写入/更新共享条目。"""
    base = _base(level, kind, tid=tid, pid=pid)
    if ".." in name or name.startswith("/") or not name:
        raise APIError(400, ErrorCode.BAD_REQUEST, "非法文件名")
    target = base / name
    paths.ensure(target)
    write_text(target, content)
    return {"name": name, "level": level, "kind": kind, "bytes": len(content.encode("utf-8"))}


def list_all_for_project(tid: str, pid: str) -> dict:
    """汇总某项目可见的全部共享资产（项目级 + 所属团队级），供知识/产物页层级筛选。"""
    return {
        "project": {k: list_items("project", k, tid=tid, pid=pid) for k in VALID_KINDS},
        "team": {k: list_items("team", k, tid=tid) for k in VALID_KINDS},
    }
