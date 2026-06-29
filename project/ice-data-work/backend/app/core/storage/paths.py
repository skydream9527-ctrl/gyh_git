"""四层空间路径解析（总纲 §4.2 / 材料三 §6、§11）。

四层：任务空间 tasks/ · Agent 空间 agents/ · 用户空间 users/ · 团队/项目空间 teams/。
所有用户/任务/团队数据路径必须经此模块，禁止内联拼接（守 G3 不变量）。
所有外部传入的 id 经 _seg() 校验，防止路径穿越（.. / 绝对路径 / 分隔符）。
"""
from __future__ import annotations

import re
from pathlib import Path

from app.core.config import get_settings

_SEG_RE = re.compile(r"^[A-Za-z0-9._@-]{1,128}$")


def _seg(value: str, *, field: str = "id") -> str:
    """校验单个路径段：禁止空、.. 、/ 、绝对路径等。"""
    v = (value or "").strip()
    if not _SEG_RE.match(v) or v in {".", ".."}:
        raise ValueError(f"非法 {field}: {value!r}")
    return v


def root() -> Path:
    return get_settings().data_root


def ensure(p: Path) -> Path:
    """确保目录存在（文件路径则确保其父目录）。返回原路径。"""
    target = p if p.suffix == "" else p.parent
    target.mkdir(parents=True, exist_ok=True)
    return p


# ---------- ① 用户空间 users/{uid}/ ----------
def user_dir(uid: str) -> Path:
    return root() / "users" / _seg(uid, field="user_id")

def user_profile(uid: str) -> Path:
    return user_dir(uid) / "profile.json"

def twin_dir(uid: str) -> Path:
    return user_dir(uid) / "twin"

def twin_json(uid: str) -> Path:
    return twin_dir(uid) / "twin.json"

def twin_agent_md(uid: str) -> Path:
    return twin_dir(uid) / "agent.md"

def twin_memory(uid: str, name: str) -> Path:
    return twin_dir(uid) / "memory" / f"{_seg(name, field='memory')}.memory.md"

def user_memory_dir(uid: str) -> Path:
    return user_dir(uid) / "memory"

def user_artifacts(uid: str) -> Path:
    return user_dir(uid) / "artifacts"

def user_audit(uid: str) -> Path:
    return user_dir(uid) / "audit.jsonl"


# ---------- ② Agent 空间 agents/{aid}/ ----------
def agent_dir(aid: str) -> Path:
    return root() / "agents" / _seg(aid, field="agent_id")

def agent_json(aid: str) -> Path:
    return agent_dir(aid) / "agent.json"

def agent_md(aid: str) -> Path:
    return agent_dir(aid) / "agent.md"

def agent_user_memory(aid: str, uid: str) -> Path:
    """情景记忆按用户分区（D-06，默认隔离）。"""
    return agent_dir(aid) / "memory" / "by-user" / _seg(uid, field="user_id") / "usage.memory.md"

def agent_team_memory(aid: str, tid: str) -> Path:
    """显式『贡献给团队』后的共享经验（按团队隔离）。"""
    return agent_dir(aid) / "memory" / "by-team" / _seg(tid, field="team_id") / "shared.memory.md"

def agent_user_skill_bindings(aid: str, uid: str) -> Path:
    """用户私有给该 Agent 加的 Skill 绑定（D-13）。"""
    return agent_dir(aid) / "bindings" / "by-user" / _seg(uid, field="user_id") / "skills.json"


# ---------- ③ 团队/项目空间 teams/{tid}/ ----------
def team_dir(tid: str) -> Path:
    return root() / "teams" / _seg(tid, field="team_id")

def team_json(tid: str) -> Path:
    return team_dir(tid) / "team.json"

def team_shared(tid: str, kind: str) -> Path:
    """kind ∈ {files, knowledge, memory, artifacts}。"""
    return team_dir(tid) / "shared" / _seg(kind, field="kind")

def project_dir(tid: str, pid: str) -> Path:
    return team_dir(tid) / "projects" / _seg(pid, field="project_id")

def project_json(tid: str, pid: str) -> Path:
    return project_dir(tid, pid) / "project.json"

def project_shared(tid: str, pid: str, kind: str) -> Path:
    return project_dir(tid, pid) / "shared" / _seg(kind, field="kind")


# ---------- ④ 任务空间 tasks/{tid}/ ----------
def task_dir(task_id: str) -> Path:
    return root() / "tasks" / _seg(task_id, field="task_id")

def task_json(task_id: str) -> Path:
    return task_dir(task_id) / "task.json"

def task_conversation(task_id: str) -> Path:
    return task_dir(task_id) / "conversation.jsonl"

def task_tool_calls(task_id: str) -> Path:
    return task_dir(task_id) / "tool_calls.jsonl"

def task_files(task_id: str, kind: str = "output") -> Path:
    """kind ∈ {input, output}。"""
    if kind not in {"input", "output"}:
        raise ValueError(f"非法 files kind: {kind!r}")
    return task_dir(task_id) / "files" / kind

def task_working_memory(task_id: str) -> Path:
    return task_dir(task_id) / "memory" / "working.memory.md"

def task_candidates(task_id: str) -> Path:
    return task_dir(task_id) / "memory" / "candidates.jsonl"

def task_skill_candidates(task_id: str) -> Path:
    return task_dir(task_id) / "skill_candidates.jsonl"

def task_sandbox(task_id: str) -> Path:
    """代码沙盒工作根目录（置于 output 下，便于产物回填 + 被空间文件扫描复用）。"""
    return task_files(task_id, "output") / "_sandbox"

def task_participant_notes(task_id: str, ref_id: str) -> Path:
    return task_dir(task_id) / "participants" / _seg(ref_id, field="participant") / "notes.md"

def task_approvals(task_id: str) -> Path:
    return task_dir(task_id) / "approvals.jsonl"

def task_audit(task_id: str) -> Path:
    return task_dir(task_id) / "audit.jsonl"

def task_plan(task_id: str) -> Path:
    """任务计划（M7-T06）：steps[] 编排真相源，走 file_transaction。"""
    return task_dir(task_id) / "plan.json"

def task_proposals(task_id: str) -> Path:
    """主动提议队列（M7-T11）：Twin/Agent 主动产出的待确认建议。"""
    return task_dir(task_id) / "proposals.jsonl"


# ---------- Skill（团队共享 + 用户草稿，D-13）----------
def skill_dir(sid: str) -> Path:
    return root() / "skills" / _seg(sid, field="skill_id")

def skill_json(sid: str) -> Path:
    return skill_dir(sid) / "skill.json"

def skill_version(sid: str, n: int) -> Path:
    return skill_dir(sid) / "versions" / str(int(n))

def user_skill_dir(uid: str, sid: str) -> Path:
    return user_dir(uid) / "skills" / _seg(sid, field="skill_id")


# ---------- 派生索引 ----------
def index_db() -> Path:
    return get_settings().cache_dir / "index.db"


# 顶层 G3 目录（lifespan 启动时确保存在）
TOP_LEVEL_DIRS = ("agents", "skills", "teams", "users", "tasks", "files", ".cache")


def ensure_top_level() -> None:
    for d in TOP_LEVEL_DIRS:
        (root() / d).mkdir(parents=True, exist_ok=True)
