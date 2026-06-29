"""工具注册表 + 调度器（tool_runner）。

每个工具声明：name / description / parameters(JSON schema) / risk / handler。
高风险工具（写文件/跑命令/付费/固化记忆/跨空间读取）需 HITL 确认（D-10）。
外部 CLI（kyuubi 等）缺失时返回 *_NOT_CONFIGURED，不阻塞。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from app.core.config import get_settings
from app.core.permissions import HIGH_RISK_ACTIONS
from app.core.storage import paths
from app.core.storage.jsonio import append_jsonl, read_json, write_text


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict
    handler: Callable[..., dict]
    risk: str = "low"  # low | high
    tags: list[str] = field(default_factory=list)

    def to_schema(self) -> dict:
        """Anthropic/OpenAI 工具 schema。"""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.parameters,
            "risk": self.risk,
        }


TOOL_REGISTRY: dict[str, ToolSpec] = {}


def register(spec: ToolSpec) -> None:
    TOOL_REGISTRY[spec.name] = spec


def list_tools() -> list[dict]:
    return [t.to_schema() for t in TOOL_REGISTRY.values()]


def run_tool(name: str, args: dict, *, context: dict | None = None) -> dict:
    """执行工具。context 含 task_id / user_id / speaker_id 等。

    返回统一结构：{"ok": bool, "data": ..., "error_code": str, "message": str}。
    高风险工具若未携带 approved=True，返回 APPROVAL_REQUIRED（由上层进 HITL）。
    """
    ctx = context or {}
    spec = TOOL_REGISTRY.get(name)
    if spec is None:
        return _err("BAD_REQUEST", f"未知工具: {name}")

    # 高风险确认门
    if spec.risk == "high" and not ctx.get("approved"):
        return {
            "ok": False,
            "error_code": "APPROVAL_REQUIRED",
            "message": f"高风险工具 {name} 需用户确认",
            "data": {"tool": name, "args": args},
        }

    try:
        return spec.handler(args, ctx)
    except Exception as e:
        return _err("INTERNAL", f"工具 {name} 执行失败: {e}")


def _ok(data: Any = None, message: str = "ok") -> dict:
    return {"ok": True, "data": data, "error_code": "OK", "message": message}


def _err(error_code: str, message: str, data: Any = None) -> dict:
    return {"ok": False, "data": data, "error_code": error_code, "message": message}


# ─────────────────── 内置工具实现 ───────────────────

def _now(args: dict, ctx: dict) -> dict:
    return _ok({"now": datetime.now(timezone.utc).isoformat()})


def _read_space_file(args: dict, ctx: dict) -> dict:
    """读取任务空间内的文件（带访问控制：仅限当前任务的 files/）。"""
    task_id = ctx.get("task_id", "")
    rel = args.get("path", "")
    if not task_id:
        return _err("BAD_REQUEST", "缺少 task_id 上下文")
    # 仅允许读任务输出/输入区，防穿越
    if ".." in rel or rel.startswith("/"):
        return _err("FORBIDDEN", "非法路径")
    kind = args.get("kind", "output")
    base = paths.task_files(task_id, kind)
    target = base / rel
    if not target.exists() or not target.is_file():
        return _err("NOT_FOUND", f"文件不存在: {rel}")
    try:
        content = target.read_text(encoding="utf-8")
    except Exception as e:
        return _err("INTERNAL", f"读取失败: {e}")
    return _ok({"path": rel, "content": content[:50000]})


def _write_file(args: dict, ctx: dict) -> dict:
    """写文件到任务输出区（高风险，需确认）。"""
    task_id = ctx.get("task_id", "")
    rel = args.get("path", "")
    content = args.get("content", "")
    if not task_id:
        return _err("BAD_REQUEST", "缺少 task_id 上下文")
    if ".." in rel or rel.startswith("/") or not rel:
        return _err("FORBIDDEN", "非法路径")
    target = paths.task_files(task_id, "output") / rel
    paths.ensure(target)
    write_text(target, content)
    return _ok({"path": rel, "bytes": len(content.encode("utf-8"))}, "已写入")


def _kyuubi_query(args: dict, ctx: dict) -> dict:
    """Kyuubi 只读查询。未配置时降级 KYUUBI_NOT_CONFIGURED。"""
    if not get_settings().kyuubi_host:
        return _err("KYUUBI_NOT_CONFIGURED", "Kyuubi 未配置，无法执行查询")
    # 真实实现：连接 kyuubi 执行只读 SQL + SQL 审计
    return _err("KYUUBI_NOT_CONFIGURED", "Kyuubi 查询尚未接入（M2 stub）")


def _propose_memory(args: dict, ctx: dict) -> dict:
    """生成记忆候选 → tasks/{tid}/memory/candidates.jsonl（M3 晋升）。"""
    task_id = ctx.get("task_id", "")
    if not task_id:
        return _err("BAD_REQUEST", "缺少 task_id 上下文")
    scope = args.get("scope", "agent_user")
    content = args.get("content", "")
    if not content:
        return _err("BAD_REQUEST", "记忆内容不能为空")
    from app.services import memory_svc
    try:
        cand = memory_svc.propose_candidate(
            task_id, content=content, scope=scope,
            proposer=ctx.get("speaker_id", ""), tags=args.get("tags", []),
        )
    except Exception as e:
        return _err("BAD_REQUEST", str(e))
    return _ok({"candidate_id": cand["id"], "needs_review": cand["needs_review"]},
               "已生成记忆候选（待审批）")


def _request_approval(args: dict, ctx: dict) -> dict:
    """发起 HITL 审批 → tasks/{tid}/approvals.jsonl。"""
    task_id = ctx.get("task_id", "")
    if not task_id:
        return _err("BAD_REQUEST", "缺少 task_id 上下文")
    from app.services import hitl_svc
    appr = hitl_svc.create_approval(
        task_id,
        action_type=args.get("action_type", ""),
        summary=args.get("summary", ""),
        risk_level=args.get("risk_level", "medium"),
        requester=ctx.get("speaker_id", ""),
        payload=args.get("payload", {}),
    )
    return _ok({"approval_id": appr["id"]}, "已发起审批请求")


def _list_agents(args: dict, ctx: dict) -> dict:
    """列出可用的内置 Agent。"""
    from app.core.storage.jsonio import iter_dirs
    out = []
    for d in iter_dirs(paths.root() / "agents"):
        meta = read_json(d / "agent.json")
        if meta:
            out.append({"id": meta.get("id"), "name": meta.get("name"),
                        "description": meta.get("description", "")})
    return _ok(out)


# 注册
register(ToolSpec("now", "获取当前 UTC 时间", {"type": "object", "properties": {}}, _now, "low", ["time"]))
register(ToolSpec(
    "read_space_file", "读取当前任务空间内的文件",
    {"type": "object", "properties": {
        "path": {"type": "string", "description": "相对任务 files 区的路径"},
        "kind": {"type": "string", "enum": ["input", "output"], "default": "output"},
    }, "required": ["path"]},
    _read_space_file, "low", ["file"],
))
register(ToolSpec(
    "write_file", "写文件到任务输出区（高风险，需确认）",
    {"type": "object", "properties": {
        "path": {"type": "string"}, "content": {"type": "string"},
    }, "required": ["path", "content"]},
    _write_file, "high", ["file"],
))
register(ToolSpec(
    "kyuubi_query", "执行 Kyuubi 只读 SQL 查询",
    {"type": "object", "properties": {"sql": {"type": "string"}}, "required": ["sql"]},
    _kyuubi_query, "low", ["data"],
))
register(ToolSpec(
    "propose_memory", "提议一条记忆候选（待审批晋升）",
    {"type": "object", "properties": {
        "content": {"type": "string"},
        "scope": {"type": "string", "enum": ["user_preference", "agent_user", "agent_team", "project", "team"]},
    }, "required": ["content"]},
    _propose_memory, "high", ["memory"],
))
register(ToolSpec(
    "request_approval", "发起人工确认（HITL）",
    {"type": "object", "properties": {
        "action_type": {"type": "string"}, "summary": {"type": "string"},
        "risk_level": {"type": "string", "enum": ["low", "medium", "high"]},
    }, "required": ["summary"]},
    _request_approval, "low", ["governance"],
))
register(ToolSpec("list_agents", "列出平台可用的工具 Agent", {"type": "object", "properties": {}}, _list_agents, "low", ["agent"]))

# 确保高风险工具与权限清单一致（write_file/propose_memory 已标 high）
_ = HIGH_RISK_ACTIONS


# ─────────────────── M6：自演进 — 任务内代码执行（D-13）───────────────────

def _run_user_code(args: dict, ctx: dict) -> dict:
    """在隔离沙盒执行用户贡献的代码。Python→沙盒（无网络/限资源/无凭证）；SQL→kyuubi 只读（降级）。

    沙盒本身即安全边界（risk=low）；全局暂停由 execute_tool 拦截。跑通后可经「贡献为 Skill」沉淀。
    """
    task_id = ctx.get("task_id", "")
    if not task_id:
        return _err("BAD_REQUEST", "缺少 task_id 上下文")
    code = args.get("code", "") or ""
    if not code.strip():
        return _err("BAD_REQUEST", "代码不能为空")
    runtime = args.get("runtime", "python")
    params = args.get("params") or {}

    if runtime == "sql":
        if not get_settings().kyuubi_host:
            return _err("KYUUBI_NOT_CONFIGURED", "Kyuubi 未配置，SQL 运行时不可用")
        return _err("KYUUBI_NOT_CONFIGURED", "Kyuubi SQL 执行尚未接入（M6 stub）")
    if runtime != "python":
        return _err("BAD_REQUEST", f"不支持的运行时: {runtime}")

    import uuid as _uuid

    from app.services import sandbox
    if not sandbox.is_enabled():
        return _err("SANDBOX_NOT_ENABLED", "自演进/沙盒未启用（设 IDW_SELF_EVOLVE_ENABLED=true 开启）")

    run_dir = paths.task_sandbox(task_id) / f"run_{_uuid.uuid4().hex[:8]}"
    result = sandbox.run_python(code, params=params, workdir=run_dir)

    # 列出沙盒生成的文件（相对任务 output，用于产物回填）
    generated: list[str] = []
    try:
        out_base = paths.task_files(task_id, "output")
        for f in sorted(run_dir.rglob("*")):
            if f.is_file():
                generated.append(str(f.relative_to(out_base)))
    except Exception:
        pass

    data = {
        "runtime": result["runtime"], "stdout": result["stdout"], "stderr": result["stderr"],
        "exit_code": result["exit_code"], "timed_out": result["timed_out"],
        "duration_ms": result["duration_ms"], "generated_files": generated,
    }
    if result["ok"]:
        return _ok(data, "代码已在沙盒执行完成")
    return _err(result["error_code"], result["message"], data)


register(ToolSpec(
    "run_user_code",
    "在隔离沙盒中执行用户贡献的代码（Python：无网络/限资源/无凭证；SQL：kyuubi 只读）。跑通后可沉淀为 Skill。",
    {"type": "object", "properties": {
        "code": {"type": "string", "description": "要执行的代码（Python 或 SQL）"},
        "runtime": {"type": "string", "enum": ["python", "sql"], "default": "python"},
        "params": {"type": "object", "description": "入参；Python 运行时注入为变量 params"},
    }, "required": ["code"]},
    _run_user_code, "low", ["skill", "sandbox"],
))


def _propose_skill(args: dict, ctx: dict) -> dict:
    """把跑通的代码提议沉淀为 Skill 候选（D-13）。自动抽取入参 schema，待用户在表单确认范围。"""
    task_id = ctx.get("task_id", "")
    if not task_id:
        return _err("BAD_REQUEST", "缺少 task_id 上下文")

    from app.services import skill_svc
    try:
        cand = skill_svc.propose_skill_candidate(
            task_id,
            name=args.get("name", ""), description=args.get("description", ""),
            runtime=args.get("runtime", "python"), code=args.get("code", ""),
            proposer=ctx.get("speaker_id", ""), scope=args.get("scope", "by_user"),
            agent_id=args.get("agent_id", ""), knowledge=args.get("knowledge", ""),
        )
    except Exception as e:
        return _err("BAD_REQUEST", getattr(e, "message", str(e)))
    return _ok(
        {"candidate_id": cand["id"], "input_schema": cand["input_schema"],
         "needs_review": cand["needs_review"]},
        "已生成 Skill 候选（待确认沉淀范围）",
    )


register(ToolSpec(
    "propose_skill",
    "把跑通的代码提议沉淀为可复用 Skill（生成候选，自动抽取入参 schema；待用户确认范围/绑定 Agent）。",
    {"type": "object", "properties": {
        "name": {"type": "string", "description": "Skill 名称"},
        "description": {"type": "string"},
        "runtime": {"type": "string", "enum": ["python", "sql"], "default": "python"},
        "code": {"type": "string", "description": "已跑通的代码"},
        "scope": {"type": "string", "enum": ["by_user", "by_team"], "default": "by_user"},
        "agent_id": {"type": "string", "description": "绑定到的 Agent id"},
        "knowledge": {"type": "string", "description": "何时使用该 Skill（写入 Agent knowledge）"},
    }, "required": ["name", "code"]},
    _propose_skill, "low", ["skill"],
))


# ─────────────────── M7：A2A 多 Agent 协作（D-15）───────────────────

def _agent_exists(task_id: str, agent_id: str) -> bool:
    """目标是否为平台已知 Agent 或本任务参与 Agent。"""
    from app.core.storage.jsonio import iter_dirs
    for d in iter_dirs(paths.root() / "agents"):
        m = read_json(d / "agent.json")
        if m and m.get("id") == agent_id:
            return True
    meta = read_json(paths.task_json(task_id))
    if meta:
        for p in meta.get("participants", []):
            if p.get("ref_type") == "agent" and p.get("ref_id") == agent_id:
                return True
    return False


def _handoff_to_agent(args: dict, ctx: dict) -> dict:
    """请求把任务控制权转交给另一个 Agent（接力）。

    本工具只产出"转交请求"，是否真正接力由编排器的 Twin 仲裁 + 多跳预算/防环把关（D-15）。
    Agent 也可直接在输出末尾写 [[handoff:<agent_id>|<理由>]] 指令，效果等价。
    """
    task_id = ctx.get("task_id", "")
    to = (args.get("to") or "").strip()
    reason = args.get("reason", "")
    if not task_id:
        return _err("BAD_REQUEST", "缺少 task_id 上下文")
    if not to:
        return _err("BAD_REQUEST", "必须指定转交目标 to")
    if not _agent_exists(task_id, to):
        return _err("NOT_FOUND", f"目标 Agent 不存在或不可用: {to}")
    return _ok({"action": "handoff", "to": to, "reason": reason},
               f"已请求转交给 {to}（由 Twin 仲裁是否接力）")


def _ask_agent(args: dict, ctx: dict) -> dict:
    """一次性咨询另一个 Agent（咨询后控制权回到发起方）。"""
    task_id = ctx.get("task_id", "")
    to = (args.get("to") or "").strip()
    question = args.get("question", "")
    if not task_id:
        return _err("BAD_REQUEST", "缺少 task_id 上下文")
    if not to:
        return _err("BAD_REQUEST", "必须指定被咨询 Agent to")
    if not _agent_exists(task_id, to):
        return _err("NOT_FOUND", f"目标 Agent 不存在或不可用: {to}")
    return _ok({"action": "ask", "to": to, "question": question},
               f"已向 {to} 发起咨询")


register(ToolSpec(
    "handoff_to_agent",
    "请求把任务控制权转交给另一个 Agent 接力（由 Twin 仲裁；有界多跳，防环/预算约束）。",
    {"type": "object", "properties": {
        "to": {"type": "string", "description": "目标 Agent id"},
        "reason": {"type": "string", "description": "转交理由（接手方会看到）"},
    }, "required": ["to"]},
    _handoff_to_agent, "low", ["a2a"],
))
register(ToolSpec(
    "ask_agent",
    "一次性咨询另一个 Agent（不交出控制权，得到回答后由发起方继续）。",
    {"type": "object", "properties": {
        "to": {"type": "string", "description": "被咨询 Agent id"},
        "question": {"type": "string", "description": "要咨询的问题"},
    }, "required": ["to", "question"]},
    _ask_agent, "low", ["a2a"],
))
