"""ContextAssembler：多参与者上下文分层组装（技术内核，材料二 §5）。

每个对话回合按层组装，带来源标注，访问控制内嵌于读取点（TDR-3）：
    优先级（保留顺序）：任务 > A2A 接手 > 参与者 > 用户 > 项目 > 团队
    超预算时按优先级从低层丢弃。

记忆注入采用"先过滤（访问边界）再排序（top-k 检索）"（M3-T04）：
    - 工具 Agent：by-user/{当前用户} + by-team/{任务团队}，越界不读
    - Twin：仅本人用户空间记忆
    - 检索走 memory_retrieval（关键词版；pgvector 开启且可连时语义检索，否则降级）

A2A 接手层（M7-T04）：被转交方注入"谁因何转交 + 前序产出摘要"，避免重复劳动；
    访问控制不放宽——接手 Agent 仍按 by-user 读自己的经验，不读他人空间。
"""
from __future__ import annotations

from app.core.storage import paths
from app.core.storage.jsonio import read_json
from app.services import conversation_svc, memory_retrieval, memory_svc

# 粗略 token 预算（字符近似，1 token ≈ 1.5 中文字符 / 4 英文字符，这里用字符上限保守）
DEFAULT_CHAR_BUDGET = 48000
RETRIEVAL_K = 5


def assemble_context(
    task: dict,
    *,
    speaker: dict,
    acting_user_id: str,
    char_budget: int = DEFAULT_CHAR_BUDGET,
    handoff: dict | None = None,
) -> list[dict]:
    """组装 messages。speaker={type,id} 为本轮发言/执行主体。

    handoff（M7-T04，可选）：本跳由 A2A 转交接力而来时 {from,to,reason}，
    为接手方注入"谁因何转交 + 前序产出摘要"，避免重复劳动；访问控制不放宽。

    返回 [{"role": "system|user|assistant", "content": "...", "_layer": "...", "_source": "..."}]。
    调用方剥离 _layer/_source 后送 LLM；保留用于审计/可解释。
    """
    task_id = task["id"]
    layers: list[dict] = []

    # ① 任务层（最高优先级）
    layers.append(_sys(_task_system(task), "task", f"task:{task_id}"))

    working = _read_text(paths.task_working_memory(task_id))
    if working:
        layers.append(_sys(f"## 任务工作记忆\n{working}", "task", f"task:{task_id}/working"))

    file_index = _task_file_index(task_id)
    if file_index:
        layers.append(_sys(f"## 任务文件索引\n{file_index}", "task", f"task:{task_id}/files"))

    # ①' A2A 接手层（M7-T04）：被转交方注入"谁因何转交 + 前序产出摘要"
    if handoff:
        layers.append(_sys(_a2a_system(task_id, handoff), "a2a", f"task:{task_id}/handoff"))

    # 检索 query：任务标题 + 近 N 轮对话
    query = _retrieval_query(task)

    # ② 参与者层（每个 agent/twin 一份，带来源标注 + 访问控制 + top-k 检索）
    for p in task.get("participants", []):
        if p.get("ref_type") == "user":
            continue  # 用户无 agent.md
        layers.extend(_participant_layers(p, task=task, acting_user_id=acting_user_id, query=query))

    # ③ 用户层（操作者偏好：检索 top-k 相关）
    pref_entries = memory_svc.read_memory_entries(
        paths.twin_dir(acting_user_id) / "memory" / "preferences.memory.md"
    )
    pref_hits = memory_retrieval.retrieve(pref_entries, query, k=RETRIEVAL_K)
    if pref_hits:
        layers.append(_sys(
            "## 用户偏好\n" + _render_entries(pref_hits),
            "user", f"user:{acting_user_id}/preferences",
        ))

    # ④ 项目/团队层（共享知识切片）
    shared = _project_team_shared(task.get("project_id", ""))
    if shared:
        layers.append(_sys(shared, "project", f"project:{task.get('project_id')}"))

    # ⑤ 近 N 轮对话（作为 user/assistant 序列，最后追加）
    convo = _recent_conversation(task_id)

    # 预算裁剪：系统层按优先级保留，对话尽量保留
    clamped = _budget_clamp(layers, char_budget - _total_chars(convo))
    return clamped + convo


# ─────────────────── 分层构造 ───────────────────

def _task_system(task: dict) -> str:
    parts = task.get("participants", [])
    pdesc = ", ".join(f"{p.get('ref_type')}:{p.get('ref_id')}({p.get('role')})" for p in parts)
    return (
        f"# 任务：{task.get('title', '')}\n"
        f"- 任务ID: {task.get('id')}\n"
        f"- 类型: {task.get('type')}（{'数据分析' if task.get('type') == 'data' else '通用'}）\n"
        f"- 状态: {task.get('status')}\n"
        f"- 项目: {task.get('project_id')}\n"
        f"- 参与者: {pdesc}\n"
        f"\n这是一个多参与者协作任务。请根据你的角色（agent.md）协作完成。"
    )


def _a2a_system(task_id: str, handoff: dict) -> str:
    """A2A 接手层（M7-T04）：注入转交来源 + 理由 + 前序产出摘要，避免重复劳动。"""
    frm = handoff.get("from", "")
    reason = handoff.get("reason", "") or "（未注明理由）"
    parts = [
        "# 协作接力（A2A）",
        f"- 你是接手方：**{frm}** 因「{reason}」把任务转交给你。",
        "- 请基于前序产出继续推进，**不要重复**已完成的工作；产出后如仍需他方协作，可再次按约定转交。",
    ]
    prior = conversation_svc.last_content_by(task_id, frm) if frm else ""
    if prior:
        parts.append(f"\n## {frm} 的前序产出（摘要）\n{prior}")
    return "\n".join(parts)


def _participant_layers(p: dict, *, task: dict, acting_user_id: str, query: str = "") -> list[dict]:
    """单个参与者的注入：agent.md + pinned + 记忆切片(访问控制 + top-k 检索) + 任务 notes。"""
    out: list[dict] = []
    ref_type = p.get("ref_type")
    ref_id = p.get("ref_id")
    task_id = task["id"]

    if ref_type == "agent":
        agent_md = _read_text(paths.agent_md(ref_id))
        if agent_md:
            out.append(_sys(agent_md, "participant", f"agent:{ref_id}/agent.md"))
        # 访问控制：工具 Agent 只读 by-user/{当前用户}；先过滤再 top-k 检索
        usage_entries = memory_svc.read_memory_entries(paths.agent_user_memory(ref_id, acting_user_id))
        usage_hits = memory_retrieval.retrieve(usage_entries, query, k=RETRIEVAL_K)
        if usage_hits:
            out.append(_sys(f"## {ref_id} 对你的经验\n" + _render_entries(usage_hits), "participant",
                            f"agent:{ref_id}/by-user:{acting_user_id}"))
        # 团队共享经验：by-team/{任务所属团队}
        tid = _team_of_project(task.get("project_id", ""))
        if tid:
            team_entries = memory_svc.read_memory_entries(paths.agent_team_memory(ref_id, tid))
            team_hits = memory_retrieval.retrieve(team_entries, query, k=RETRIEVAL_K)
            if team_hits:
                out.append(_sys(f"## {ref_id} 团队共享经验\n" + _render_entries(team_hits), "participant",
                                f"agent:{ref_id}/by-team:{tid}"))
        # M6（D-13）：注入 Agent 可见 Skill（团队共享 + 当前用户私有草稿）+ knowledge（何时用）
        skills_text = _agent_skills_layer(ref_id, acting_user_id)
        if skills_text:
            out.append(_sys(skills_text, "participant", f"agent:{ref_id}/skills"))
    elif ref_type == "twin":
        # Twin：注入用户空间记忆（仅本人）
        twin_uid = _twin_owner(ref_id)
        twin_md = _read_text(paths.twin_agent_md(twin_uid)) if twin_uid else ""
        if twin_md:
            out.append(_sys(twin_md, "participant", f"twin:{ref_id}/agent.md"))
        if twin_uid:
            pinned = _read_text(paths.twin_dir(twin_uid) / "memory" / "pinned.memory.md")
            if pinned:
                out.append(_sys(f"## Twin pinned 记忆\n{pinned}", "participant",
                                f"twin:{ref_id}/pinned"))
            # Twin 偏好/决策记忆 top-k
            twin_entries = memory_svc.read_memory_entries(
                paths.twin_dir(twin_uid) / "memory" / "preferences.memory.md"
            )
            twin_hits = memory_retrieval.retrieve(twin_entries, query, k=RETRIEVAL_K)
            if twin_hits:
                out.append(_sys(f"## Twin 相关记忆\n" + _render_entries(twin_hits), "participant",
                                f"twin:{ref_id}/memory"))

    # 任务级参与者笔记（全量，小）
    notes = _read_text(paths.task_participant_notes(task_id, ref_id))
    if notes and len(notes.strip()) > 0:
        out.append(_sys(f"## {ref_type}:{ref_id} 任务笔记\n{notes}", "participant",
                        f"task:{task_id}/notes:{ref_id}"))
    return out


def _retrieval_query(task: dict) -> str:
    """构造检索 query：任务标题 + 近 N 轮对话文本。"""
    parts = [task.get("title", "")]
    recent = conversation_svc.recent_turns_text(task["id"], limit=6)
    if recent:
        parts.append(recent)
    return "\n".join(p for p in parts if p)


def _render_entries(entries: list[dict]) -> str:
    """把检索到的记忆条目渲染为带 MEM-id 与来源的文本。"""
    lines: list[str] = []
    for e in entries:
        mem_id = e.get("mem_id", "MEM-?")
        conf = e.get("confidence", "medium")
        line = f"- [{mem_id} · {conf}] {e.get('content', '')}"
        if e.get("source"):
            line += f"  (source: {e['source']})"
        lines.append(line)
    return "\n".join(lines)


def _project_team_shared(project_id: str) -> str:
    """项目/团队共享知识（关键词版：直接读 shared/knowledge 摘要）。"""
    tid = _team_of_project(project_id)
    if not tid:
        return ""
    chunks: list[str] = []
    pj_know = paths.project_shared(tid, project_id, "knowledge")
    tm_know = paths.team_shared(tid, "knowledge")
    for label, base in (("项目知识", pj_know), ("团队知识", tm_know)):
        if base.exists():
            files = [f for f in base.glob("*.md")][:3]
            for f in files:
                txt = _read_text(f)
                if txt:
                    chunks.append(f"### {label}: {f.name}\n{txt[:2000]}")
    return "## 共享知识\n" + "\n\n".join(chunks) if chunks else ""


def _recent_conversation(task_id: str, *, limit: int = 12) -> list[dict]:
    """近 N 轮转为 role 序列。speaker 信息编码到 content 前缀。"""
    turns = conversation_svc.get_conversation(task_id, limit=limit)
    out: list[dict] = []
    for t in turns:
        sp = t.get("speaker", {})
        role = "user" if sp.get("type") == "user" else "assistant"
        prefix = "" if role == "user" else f"[{sp.get('type')}:{sp.get('id')}] "
        out.append({"role": role, "content": prefix + t.get("content", ""),
                    "_layer": "conversation", "_source": f"turn:{t.get('id')}"})
    return out


# ─────────────────── 预算与工具 ───────────────────

def _budget_clamp(layers: list[dict], budget: int) -> list[dict]:
    """超预算时按优先级丢弃低层（team < project < user < participant < a2a < task）。

    任务层与 A2A 接手层不丢（转交上下文必须保留）。None-safe：用待丢弃索引集合计算余量。
    """
    priority = {"task": 0, "a2a": 1, "participant": 2, "user": 3, "project": 4, "team": 5}
    if _total_chars(layers) <= budget:
        return layers

    dropped: set[int] = set()

    def remaining() -> int:
        return sum(len(layers[i].get("content", "")) for i in range(len(layers)) if i not in dropped)

    # 从最低优先级（数字大）开始丢；同层后出现的先丢
    order = sorted(range(len(layers)),
                   key=lambda i: (-priority.get(layers[i].get("_layer", "task"), 0), -i))
    for i in order:
        if remaining() <= budget:
            break
        if layers[i].get("_layer") in ("task", "a2a"):
            continue
        dropped.add(i)
    return [layer for i, layer in enumerate(layers) if i not in dropped]


def _total_chars(layers: list[dict]) -> int:
    return sum(len(layer.get("content", "")) for layer in layers)


def _task_file_index(task_id: str) -> str:
    base = paths.task_files(task_id, "output")
    if not base.exists():
        return ""
    files = sorted(f.name for f in base.iterdir() if f.is_file())
    return "\n".join(f"- {f}" for f in files) if files else ""


def _team_of_project(project_id: str) -> str:
    """从 project_id 反查 team_id（遍历，v1 简单实现；后续接索引）。"""
    if not project_id:
        return ""
    from app.core.storage.jsonio import iter_dirs
    for tdir in iter_dirs(paths.root() / "teams"):
        pj = tdir / "projects" / project_id / "project.json"
        if pj.exists():
            return tdir.name
    return ""


def _twin_owner(twin_ref: str) -> str:
    """twin ref_id 形如 'twin-{uid}' 或直接 uid。"""
    if twin_ref.startswith("twin-"):
        return twin_ref[len("twin-"):]
    return twin_ref


def _read_text(path) -> str:
    try:
        if path.exists() and path.is_file():
            return path.read_text(encoding="utf-8")
    except Exception:
        pass
    return ""


def _sys(content: str, layer: str, source: str) -> dict:
    return {"role": "system", "content": content, "_layer": layer, "_source": source}


def strip_meta(messages: list[dict]) -> list[dict]:
    """剥离 _layer/_source，得到可直接送 LLM 的 messages。"""
    return [{"role": m["role"], "content": m["content"]} for m in messages]


# ─────────────────── Agent 可见 Skill 注入（M6 / D-13）───────────────────

def _agent_skills_layer(agent_id: str, uid: str) -> str:
    """注入 Agent 可见的 Skill（团队共享 + 当前用户私有草稿）+ knowledge（何时用）。

    受 IDW_SELF_EVOLVE_ENABLED 灰度控制（默认关，关时不注入）。
    隔离：只读当前用户的私有绑定，不泄漏他人草稿（与 D-06 一致）。
    """
    from app.core.config import get_settings
    if not get_settings().self_evolve_enabled:
        return ""
    from app.services import skill_evolve_svc, skill_svc

    try:
        bindings = skill_evolve_svc.list_agent_bindings(agent_id, uid=uid)
    except Exception:
        return ""

    knowledge = bindings.get("skill_knowledge", {})
    lines: list[str] = []
    for sid in bindings.get("team_skills", []):
        try:
            sk = skill_svc.get_skill(sid)
        except Exception:
            continue
        lines.append(_format_skill_line(sk, knowledge.get(sid, ""), tag="团队共享"))
    for item in bindings.get("user_skills", []):
        sid = item.get("skill_id", "")
        try:
            sk = skill_svc.get_skill(sid, uid=uid)
        except Exception:
            continue
        lines.append(_format_skill_line(sk, item.get("knowledge", ""), tag="我的草稿"))

    if not lines:
        return ""
    return "## 可用 Skills（D-13 自演进）\n" + "\n".join(lines)


def _format_skill_line(sk: dict, know: str, *, tag: str) -> str:
    params = ", ".join(p.get("name", "") for p in sk.get("input_schema", []))
    line = (f"- **{sk.get('name', '')}** (`{sk.get('id', '')}` · {sk.get('runtime', '')} · "
            f"v{sk.get('version', 1)} · {tag}) 入参: {params or '无'}")
    if know:
        line += f"\n  何时用: {know}"
    return line
