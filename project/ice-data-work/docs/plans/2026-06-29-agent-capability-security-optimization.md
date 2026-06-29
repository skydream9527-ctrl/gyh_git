# Agent Capability & Security Optimization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将本项目从“单轮 Twin 编排 + 基础治理 + Skill 自演进雏形”升级为“安全边界可上线、A2A 可追溯、主动性受控、自进化可评价”的 Agent 工作台。

**Architecture:** 先收紧安全与授权边界，再灰度打开 A2A / Autostep / Triggers。所有高风险动作统一走权限门、HITL、审计和预算护栏；所有新能力默认关闭，通过 `IDW_*_ENABLED` 特性开关逐步放量。

**Tech Stack:** FastAPI + Pydantic + G3 文件优先存储 + React 18/Vite/Zustand + pytest + TypeScript。

---

## 0. 背景与当前扫描结论

本方案基于 2026-06-29 项目扫描结果，覆盖四个方向：安全性、Agent 主动性、Agent 自进化、Agent-to-Agent 对话协作。

### 0.1 已具备基础

- **三轴权限雏形**：`backend/app/core/permissions.py` 定义平台角色、成员角色、Twin L0-L5、高风险动作清单。
- **HITL 与审计雏形**：`backend/app/services/hitl_svc.py`、`backend/app/services/audit_svc.py` 已能记录审批和审计。
- **Skill 自演进雏形**：`backend/app/services/tools/registry.py` 提供 `run_user_code` / `propose_skill`；`backend/app/services/skill_svc.py`、`backend/app/services/skill_evolve_svc.py` 支持候选、草稿、test-run、团队晋升、绑定、回滚。
- **A2A 纯逻辑骨架**：`backend/app/services/orchestrator_svc.py` 已有 handoff/ask 指令解析、防环与 hop budget 逻辑。
- **M7 路线已定义**：`DEV_PLAN.md` 已明确 A2A、任务计划、主动性护栏、触发器等任务。

### 0.2 关键缺口

- **资源访问授权不完整**：多个任务/产物/记忆/审批/WS 路由只验证登录，未验证任务参与者或团队/项目成员。
- **HITL 裁决边界不足**：审批项裁决未绑定 eligible approvers，审批通过与真实执行动作之间缺少强绑定。
- **生产安全基线不足**：默认 JWT secret、默认 admin/test 账号、Aegis header 信任、错误回显、WS token URL、localStorage token 都需要生产加固。
- **沙盒仍是软沙盒**：进程级限制能挡常规误操作，但不能作为生产级不可信代码边界。
- **Agent 主动性未落地**：当前运行时仍是用户触发的一问一答，没有主动 proposal queue / autostep / triggers。
- **A2A 未接入 runtime**：`orchestrator_svc.py` 未接入 `agent_runtime.py`、`conversation_svc.py`、`ws.py` 和前端转交卡。
- **自进化缺评价闭环**：Skill 缺少 run evidence、测试用例资产、风险评分、调用成功率、采纳/回滚反馈。

---

## 1. 优化原则

1. **安全先于智能**：P0 安全缺口未收口前，不打开 `IDW_A2A_ENABLED`、`IDW_AUTOSTEP_ENABLED`、`IDW_TRIGGERS_ENABLED`。
2. **默认关闭，灰度开启**：所有自动化、主动性、跨 Agent 行为默认关。
3. **高风险永远 HITL**：写文件、跑命令、付费、固化记忆、跨空间读取、团队资产晋升必须审批。
4. **先过滤再检索**：ContextAssembler 保持“访问边界先过滤，相关性后排序”。
5. **可追溯优先**：A2A 转交、主动建议、Skill 晋升、触发器建任务都必须有审计记录。
6. **TDD 优先**：权限、HITL、沙盒、A2A 防环、预算护栏、DoD 门控都先写失败测试。

---

## 2. Phase 0 — 安全与治理硬化（P0，必须先做）

### Task 1: 建立统一资源访问 Guard

**Files:**
- Modify: `backend/app/core/deps.py`
- Modify: `backend/app/core/permissions.py`
- Test: `backend/tests/test_auth.py`
- Test: `backend/tests/test_tasks.py`

**Step 1: Write failing tests**

新增测试覆盖：

```python
def test_non_participant_cannot_read_task(client, alice_token, bob_task):
    r = client.get(f"/api/v1/tasks/{bob_task['id']}", headers={"Authorization": f"Bearer {alice_token}"})
    assert r.status_code == 403


def test_team_non_member_cannot_read_project(client, user_token):
    r = client.get("/api/v1/teams/t_growth/projects/p_growth", headers={"Authorization": f"Bearer {user_token}"})
    assert r.status_code == 403
```

**Step 2: Run tests to verify failure**

Run:

```bash
cd backend && . .venv/bin/activate && pytest -q tests/test_auth.py tests/test_tasks.py
```

Expected: new tests fail because current routes only require `get_current_user`.

**Step 3: Implement guard helpers**

Add helpers in `backend/app/core/deps.py`:

```python
def require_task_access(path_param: str = "task_id", min_role: str = "reader") -> Callable:
    """Require current user to be task participant or platform admin."""


def require_team_access(path_param: str = "team_id", min_role: str = MemberRole.MEMBER) -> Callable:
    """Require current user to be team member or platform admin."""


def require_project_access(team_param: str = "team_id", project_param: str = "project_id", min_role: str = MemberRole.MEMBER) -> Callable:
    """Require current user to be project/team member or platform admin."""
```

Implementation notes:

- Platform `super_admin` / `admin` may pass, but content-isolation endpoints should explicitly decide whether admin sees content or only audit.
- Task access passes if user is a `user` participant, task creator, or platform admin.
- Project access checks project members first, then team members.
- Invalid resource IDs return 404/403 without leaking unrelated content.

**Step 4: Run tests to verify pass**

Run:

```bash
cd backend && . .venv/bin/activate && pytest -q tests/test_auth.py tests/test_tasks.py
```

Expected: all existing and new tests pass.

**Step 5: Commit**

```bash
git add backend/app/core/deps.py backend/app/core/permissions.py backend/tests/test_auth.py backend/tests/test_tasks.py
git commit -m "security: add unified resource access guards"
```

---

### Task 2: 全路由接入任务/团队/项目访问控制

**Files:**
- Modify: `backend/app/api/v1/tasks.py`
- Modify: `backend/app/api/v1/ws.py`
- Modify: `backend/app/api/v1/artifacts.py`
- Modify: `backend/app/api/v1/memory.py`
- Modify: `backend/app/api/v1/skills.py`
- Modify: `backend/app/api/v1/governance.py`
- Modify: `backend/app/api/v1/teams.py`
- Modify: `backend/app/api/v1/projects.py`
- Test: `backend/tests/test_auth.py`
- Test: `backend/tests/test_tasks.py`
- Test: `backend/tests/test_memory.py`
- Test: `backend/tests/test_skills.py`

**Step 1: Write failing tests**

覆盖以下越权场景：

- 非任务参与者不能读/改任务。
- 非任务参与者不能打开 WS。
- 非任务参与者不能读/写 artifact。
- 非任务参与者不能列 memory/skill candidates。
- 非团队成员不能列团队项目、读取项目详情、读取团队共享 Skill。
- 非任务参与者不能读取任务审计和审批。

**Step 2: Run tests to verify failure**

Run:

```bash
cd backend && . .venv/bin/activate && pytest -q tests/test_auth.py tests/test_tasks.py tests/test_memory.py tests/test_skills.py
```

Expected: new authorization tests fail.

**Step 3: Apply route dependencies**

Examples:

```python
@router.get("/{task_id}")
def get_task(task_id: str, user: dict = Depends(require_task_access("task_id"))) -> dict:
    return ok(task_svc.get_task(task_id))
```

```python
@approvals_router.post("/decide")
def decide(body: DecideReq, user: dict = Depends(get_current_user)) -> dict:
    task_access_guard(body.task_id, user)
    approval_decision_guard(body.task_id, body.approval_id, user)
    return ok(hitl_svc.decide(...))
```

For WS:

```python
uid = _auth_ws(token)
if uid is None or not task_svc.can_user_access_task(task_id, uid):
    await websocket.close(code=4403)
    return
```

**Step 4: Run route tests**

Run:

```bash
cd backend && . .venv/bin/activate && pytest -q
```

Expected: all backend tests pass.

**Step 5: Commit**

```bash
git add backend/app/api/v1 backend/tests
git commit -m "security: enforce resource access across api routes"
```

---

### Task 3: 强化 HITL 审批资格与动作绑定

**Files:**
- Modify: `backend/app/services/hitl_svc.py`
- Modify: `backend/app/api/v1/memory.py`
- Modify: `backend/app/api/v1/skills.py`
- Modify: `backend/app/services/agent_runtime.py`
- Test: `backend/tests/test_memory.py`
- Test: `backend/tests/test_skills.py`
- Test: `backend/tests/test_governance.py`

**Step 1: Write failing tests**

```python
def test_only_eligible_approver_can_decide(client, member_token, approval):
    r = client.post("/api/v1/approvals/decide", json={
        "task_id": approval["task_id"],
        "approval_id": approval["id"],
        "approved": True,
    }, headers={"Authorization": f"Bearer {member_token}"})
    assert r.status_code == 403
```

**Step 2: Run tests to verify failure**

Run:

```bash
cd backend && . .venv/bin/activate && pytest -q tests/test_memory.py tests/test_skills.py tests/test_governance.py
```

Expected: new tests fail because `hitl_svc.decide()` does not validate approver eligibility.

**Step 3: Add approval metadata**

Extend approval record:

```python
{
  "action_type": "write_file|persist_memory|skill_promote|cross_space_read",
  "resource_ref": {...},
  "eligible_approvers": [{"type": "user", "id": "..."}, {"type": "role", "role": "owner"}],
  "payload_hash": "sha256:...",
  "expires_at": "..."
}
```

**Step 4: Bind approval to execution**

Rules:

- `write_file` approved payload must match `tool_name + args hash`.
- `memory.promote` must verify the approval action and target scope.
- `skill.promote` must verify `test_passed` and approval payload.
- Already decided or expired approvals cannot execute.

**Step 5: Run tests**

Run:

```bash
cd backend && . .venv/bin/activate && pytest -q tests/test_memory.py tests/test_skills.py tests/test_governance.py
```

Expected: all pass.

**Step 6: Commit**

```bash
git add backend/app/services/hitl_svc.py backend/app/api/v1/memory.py backend/app/api/v1/skills.py backend/app/services/agent_runtime.py backend/tests
git commit -m "security: bind hitl approvals to eligible actions"
```

---

### Task 4: 生产安全基线

**Files:**
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/core/security.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/seed/runner.py`
- Modify: `frontend/src/pages/Login.tsx`
- Modify: `frontend/src/hooks/useTaskSocket.ts`
- Test: `backend/tests/test_auth.py`
- Test: `backend/tests/test_governance.py`

**Step 1: Write failing tests**

Cover:

- Production rejects `IDW_SECRET_KEY=dev-insecure-change-me`.
- Production does not seed default `admin/admin123` and `test/test123` unless explicitly enabled.
- Unhandled exception response does not leak raw exception text in production.
- Aegis header is ignored/fails closed unless configured.

**Step 2: Implement config flags**

Add settings:

```python
self.env = os.environ.get("IDW_ENV", "development")
self.seed_demo_users = _truthy(os.environ.get("IDW_SEED_DEMO_USERS", "true" if self.env != "production" else "false"))
self.trust_aegis_header = _truthy(os.environ.get("IDW_TRUST_AEGIS_HEADER"))
self.ws_ticket_ttl_sec = int(os.environ.get("IDW_WS_TICKET_TTL_SEC", "60"))
```

**Step 3: Fail fast in production**

```python
if self.env == "production" and self.secret_key == "dev-insecure-change-me":
    raise RuntimeError("IDW_SECRET_KEY must be configured in production")
```

**Step 4: Add security headers**

In `backend/app/main.py`, add middleware/headers for:

- `Strict-Transport-Security`
- `X-Content-Type-Options`
- `X-Frame-Options`
- `Referrer-Policy`
- `Permissions-Policy`
- conservative `Content-Security-Policy`

**Step 5: Replace WS token URL with short-lived ticket**

Add endpoint:

```text
POST /api/v1/ws-ticket
```

Frontend flow:

1. HTTP request with Authorization header gets one-time ticket.
2. WS connects with `?ticket=...`.
3. Backend validates ticket and task access.

**Step 6: Run tests**

Run:

```bash
cd backend && . .venv/bin/activate && pytest -q tests/test_auth.py tests/test_governance.py
cd frontend && npm run build
```

Expected: backend tests pass and frontend build succeeds.

**Step 7: Commit**

```bash
git add backend/app/core/config.py backend/app/core/security.py backend/app/main.py backend/app/seed/runner.py frontend/src/pages/Login.tsx frontend/src/hooks/useTaskSocket.ts backend/tests
git commit -m "security: add production hardening baseline"
```

---

### Task 5: 路径安全与沙盒生产边界

**Files:**
- Modify: `backend/app/core/storage/paths.py`
- Modify: `backend/app/services/artifact_svc.py`
- Modify: `backend/app/services/shared_svc.py`
- Modify: `backend/app/services/tools/registry.py`
- Modify: `backend/app/services/sandbox.py`
- Modify: `docker-compose.yml`
- Test: `backend/tests/test_paths.py`
- Test: `backend/tests/test_tasks.py`
- Test: `backend/tests/test_skills.py`

**Step 1: Write failing path traversal tests**

```python
def test_artifact_filename_cannot_escape_task_output():
    with pytest.raises(APIError):
        artifact_svc.create_artifact("t1", title="x", filename="../../pwned.md", content="x")
```

**Step 2: Add central safe path helper**

In `paths.py`:

```python
def safe_child(base: Path, rel: str, *, field: str = "path") -> Path:
    if not rel or rel.startswith("/"):
        raise ValueError(f"非法 {field}: {rel!r}")
    target = (base / rel).resolve()
    base_resolved = base.resolve()
    if base_resolved not in target.parents and target != base_resolved:
        raise ValueError(f"非法 {field}: {rel!r}")
    return target
```

**Step 3: Replace ad-hoc checks**

Replace string checks like `".." in name` with `paths.safe_child(base, name)`.

**Step 4: Add sandbox production note and container profile**

Add docker hardening for app/sandbox worker:

```yaml
security_opt:
  - no-new-privileges:true
cap_drop:
  - ALL
read_only: true
pids_limit: 128
mem_limit: 1g
```

If app and sandbox remain same container, document this as interim and add a follow-up for separate sandbox worker.

**Step 5: Run tests**

Run:

```bash
cd backend && . .venv/bin/activate && pytest -q tests/test_paths.py tests/test_tasks.py tests/test_skills.py
```

Expected: path traversal and sandbox tests pass.

**Step 6: Commit**

```bash
git add backend/app/core/storage/paths.py backend/app/services/artifact_svc.py backend/app/services/shared_svc.py backend/app/services/tools/registry.py backend/app/services/sandbox.py docker-compose.yml backend/tests
git commit -m "security: harden file paths and sandbox boundaries"
```

---

## 3. Phase 1 — Skill / Agent 自进化增强

### Task 6: Skill 运行证据链

**Files:**
- Modify: `backend/app/services/tools/registry.py`
- Modify: `backend/app/services/skill_svc.py`
- Modify: `backend/app/services/skill_evolve_svc.py`
- Modify: `backend/app/core/storage/paths.py`
- Modify: `frontend/src/components/SkillPanel.tsx`
- Modify: `frontend/src/stores/skillStore.ts`
- Test: `backend/tests/test_skills.py`

**Step 1: Write failing tests**

Cover:

- `propose_skill` requires a valid `run_id` from a successful `run_user_code`.
- Candidate stores run evidence: `stdout`, `stderr`, `exit_code`, `duration_ms`, `params`, `code_hash`.
- Modified code cannot reuse old evidence hash.

**Step 2: Persist sandbox run evidence**

Add path:

```text
tasks/{tid}/sandbox_runs.jsonl
```

Each run record:

```json
{
  "id": "run_xxx",
  "runtime": "python",
  "code_hash": "sha256:...",
  "params_hash": "sha256:...",
  "ok": true,
  "stdout": "...",
  "stderr": "...",
  "duration_ms": 123,
  "generated_files": [],
  "ts": "..."
}
```

**Step 3: Bind candidate to evidence**

`propose_skill_candidate()` should store:

```json
"evidence": {
  "run_id": "run_xxx",
  "code_hash": "sha256:...",
  "params_hash": "sha256:..."
}
```

**Step 4: Update UI**

Skill candidate card displays:

- last successful run id
- test status
- sample params
- stdout/stderr preview
- code hash

**Step 5: Run tests**

Run:

```bash
cd backend && . .venv/bin/activate && pytest -q tests/test_skills.py
cd frontend && npm run build
```

Expected: tests and build pass.

**Step 6: Commit**

```bash
git add backend/app/services/tools/registry.py backend/app/services/skill_svc.py backend/app/services/skill_evolve_svc.py backend/app/core/storage/paths.py frontend/src/components/SkillPanel.tsx frontend/src/stores/skillStore.ts backend/tests/test_skills.py
git commit -m "feat: add skill run evidence chain"
```

---

### Task 7: Skill 测试资产、风险评分与评价闭环

**Files:**
- Modify: `backend/app/services/skill_svc.py`
- Modify: `backend/app/services/skill_evolve_svc.py`
- Create: `backend/app/services/skill_eval_svc.py`
- Modify: `backend/app/api/v1/skills.py`
- Modify: `frontend/src/components/SkillPanel.tsx`
- Test: `backend/tests/test_skills.py`

**Step 1: Write failing tests**

Cover:

- Skill can store multiple test cases.
- Team promotion fails if required tests fail.
- Risk score is persisted and shown.
- Invocation result updates success/failure metrics.

**Step 2: Add test cases storage**

Use:

```text
users/{uid}/skills/{sid}/tests/cases.json
skills/{sid}/tests/cases.json
```

Case format:

```json
{
  "id": "case_001",
  "name": "happy path",
  "params": {"xs": [1, 2, 3]},
  "expect": {"stdout_contains": "6", "exit_code": 0}
}
```

**Step 3: Add risk scoring**

Initial simple rules:

- `runtime=sql` and non-readonly keyword → high risk.
- Python imports `subprocess`, `os`, `socket`, `requests` → high risk unless explicitly allowed.
- File writes outside sandbox → block.
- Network intent → block in sandbox and mark high risk.

**Step 4: Add eval log**

Use:

```text
skills/{sid}/eval.jsonl
users/{uid}/skills/{sid}/eval.jsonl
```

Record:

```json
{"ts":"...","event":"invoke|test|rollback|promote","ok":true,"latency_ms":123,"user_feedback":"accepted|rejected|edited"}
```

**Step 5: Run tests**

Run:

```bash
cd backend && . .venv/bin/activate && pytest -q tests/test_skills.py
```

Expected: all Skill tests pass.

**Step 6: Commit**

```bash
git add backend/app/services/skill_svc.py backend/app/services/skill_evolve_svc.py backend/app/services/skill_eval_svc.py backend/app/api/v1/skills.py frontend/src/components/SkillPanel.tsx backend/tests/test_skills.py
git commit -m "feat: add skill tests risk scoring and eval loop"
```

---

## 4. Phase 2 — Agent-to-Agent 对话协作

### Task 8: 接入有界多跳 A2A 编排器

**Files:**
- Modify: `backend/app/services/agent_runtime.py`
- Modify: `backend/app/services/orchestrator_svc.py`
- Modify: `backend/app/services/conversation_svc.py`
- Modify: `backend/app/services/context_assembler_svc.py`
- Modify: `backend/app/api/v1/ws.py`
- Modify: `backend/app/services/tools/registry.py`
- Test: `backend/tests/test_tasks.py`
- Create: `backend/tests/test_orchestrator.py`

**Step 1: Write failing tests**

Cover:

- `[[handoff:data-analysis|reason]]` produces a handoff event when A2A is enabled.
- A↔B loop is rejected.
- Hop budget stops after max hops.
- A2A disabled strips directive and does not continue.

**Step 2: Add feature flag gate**

Use existing config:

```python
if not get_settings().a2a_enabled:
    # current single-speaker behavior
```

**Step 3: Add tool specs**

Register controlled tools:

```python
handoff_to_agent(agent_id, reason)
ask_agent(agent_id, question)
```

These tools do not execute directly. They create a request for Twin/orchestrator arbitration.

**Step 4: Extend conversation turn schema**

Add optional:

```json
"handoff": {"from": "agent-a", "to": "agent-b", "reason": "...", "honored": true}
```

**Step 5: Extend WS events**

Emit:

```json
{"type":"handoff","from":{...},"to":{...},"reason":"...","speaker":{...}}
```

**Step 6: Run tests**

Run:

```bash
cd backend && . .venv/bin/activate && pytest -q tests/test_orchestrator.py tests/test_tasks.py
```

Expected: A2A tests pass.

**Step 7: Commit**

```bash
git add backend/app/services/agent_runtime.py backend/app/services/orchestrator_svc.py backend/app/services/conversation_svc.py backend/app/services/context_assembler_svc.py backend/app/api/v1/ws.py backend/app/services/tools/registry.py backend/tests/test_orchestrator.py backend/tests/test_tasks.py
git commit -m "feat: connect bounded a2a orchestrator"
```

---

### Task 9: A2A 前端转交卡与参与者状态

**Files:**
- Modify: `frontend/src/hooks/useTaskSocket.ts`
- Modify: `frontend/src/components/Chat.tsx`
- Modify: `frontend/src/pages/Workspace.tsx`
- Modify: `frontend/src/stores/taskStore.ts`

**Step 1: Add types**

Extend `WsEvent` with:

```ts
interface HandoffEvent {
  type: "handoff";
  from: Speaker;
  to: Speaker;
  reason: string;
  honored: boolean;
}
```

**Step 2: Render handoff card**

Chat should render:

```text
Twin 编排：data-analysis → report-writer
原因：需要把分析结果整理成报告
```

**Step 3: Add participant status**

Statuses:

- `idle`
- `thinking`
- `waiting`
- `done`
- `blocked`

**Step 4: Build frontend**

Run:

```bash
cd frontend && npm run build
```

Expected: build passes.

**Step 5: Commit**

```bash
git add frontend/src/hooks/useTaskSocket.ts frontend/src/components/Chat.tsx frontend/src/pages/Workspace.tsx frontend/src/stores/taskStore.ts
git commit -m "feat: render a2a handoffs in workspace"
```

---

## 5. Phase 3 — 任务计划、DoD 与主动性

### Task 10: `plan.json` 任务计划模型与 DoD 门控

**Files:**
- Modify: `backend/app/core/storage/paths.py`
- Modify: `backend/app/services/task_svc.py`
- Modify: `backend/app/api/v1/tasks.py`
- Modify: `backend/app/services/audit_svc.py`
- Modify: `frontend/src/pages/Workspace.tsx`
- Modify: `frontend/src/stores/taskStore.ts`
- Test: `backend/tests/test_tasks.py`

**Step 1: Write failing tests**

Cover:

- Create/read/update plan steps.
- Step status transition is audited.
- Task cannot become `done` if DoD check fails.
- Task can become `done` after user confirms DoD.

**Step 2: Add path**

```python
def task_plan(task_id: str) -> Path:
    return task_dir(task_id) / "plan.json"
```

**Step 3: Add plan schema**

```json
{
  "goal": "...",
  "definition_of_done": ["..."],
  "steps": [
    {"id":"step_1","title":"...","owner_agent":"data-analysis","status":"todo","depends_on":[],"result_ref":""}
  ]
}
```

**Step 4: Add APIs**

```text
GET /api/v1/tasks/{task_id}/plan
PUT /api/v1/tasks/{task_id}/plan
POST /api/v1/tasks/{task_id}/plan/steps/{step_id}/status
POST /api/v1/tasks/{task_id}/dod/confirm
```

**Step 5: Frontend plan panel**

Workspace shows:

- goal
- DoD checklist
- current step
- step owner Agent
- result artifact link

**Step 6: Run tests/build**

Run:

```bash
cd backend && . .venv/bin/activate && pytest -q tests/test_tasks.py
cd frontend && npm run build
```

Expected: pass.

**Step 7: Commit**

```bash
git add backend/app/core/storage/paths.py backend/app/services/task_svc.py backend/app/api/v1/tasks.py backend/app/services/audit_svc.py frontend/src/pages/Workspace.tsx frontend/src/stores/taskStore.ts backend/tests/test_tasks.py
git commit -m "feat: add task plan and dod gate"
```

---

### Task 11: 主动建议队列（Proposal Queue）

**Files:**
- Create: `backend/app/services/proposal_svc.py`
- Modify: `backend/app/core/storage/paths.py`
- Modify: `backend/app/api/v1/governance.py`
- Modify: `backend/app/services/agent_runtime.py`
- Modify: `frontend/src/components/TwinDock.tsx`
- Modify: `frontend/src/pages/Approvals.tsx`
- Test: `backend/tests/test_governance.py`

**Step 1: Write failing tests**

Cover:

- Agent/Twin can create low-risk proposal after a turn.
- Proposal is visible to task participant.
- Proposal approval creates an auditable follow-up action.
- Proposal rejection keeps trace.

**Step 2: Add storage**

```text
tasks/{tid}/proposals.jsonl
```

Proposal format:

```json
{
  "id": "prop_xxx",
  "type": "next_step|investigate|memory|skill|artifact",
  "summary": "...",
  "risk_level": "low|medium|high",
  "payload": {},
  "status": "pending|approved|rejected|executed",
  "created_by": "twin-admin",
  "ts": "..."
}
```

**Step 3: Add APIs**

```text
GET /api/v1/tasks/{task_id}/proposals
POST /api/v1/tasks/{task_id}/proposals
POST /api/v1/tasks/{task_id}/proposals/{proposal_id}/decide
```

**Step 4: Integrate runtime**

At turn end, if proposal exists in model output/tool request:

- low-risk: proposal queue only, no auto execution unless `IDW_AUTOSTEP_ENABLED`.
- medium/high-risk: create HITL approval.

**Step 5: Run tests/build**

Run:

```bash
cd backend && . .venv/bin/activate && pytest -q tests/test_governance.py
cd frontend && npm run build
```

Expected: pass.

**Step 6: Commit**

```bash
git add backend/app/services/proposal_svc.py backend/app/core/storage/paths.py backend/app/api/v1/governance.py backend/app/services/agent_runtime.py frontend/src/components/TwinDock.tsx frontend/src/pages/Approvals.tsx backend/tests/test_governance.py
git commit -m "feat: add governed proposal queue"
```

---

### Task 12: Autostep 与 Triggers v1 子集

**Files:**
- Create: `backend/app/services/autostep_svc.py`
- Create: `backend/app/services/trigger_svc.py`
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/services/control_svc.py`
- Modify: `backend/app/services/usage_svc.py`
- Modify: `backend/app/services/task_svc.py`
- Modify: `backend/app/api/v1/governance.py`
- Modify: `backend/app/api/v1/tasks.py`
- Test: `backend/tests/test_governance.py`
- Test: `backend/tests/test_tasks.py`

**Step 1: Write failing tests**

Cover:

- Autostep disabled by default.
- Autostep refuses high-risk action and creates HITL instead.
- Daily cap blocks excessive proactive actions.
- Global pause stops autostep and triggers.
- Trigger creates task with audit record.

**Step 2: Add autostep guard**

Guard checks:

- `IDW_AUTOSTEP_ENABLED=true`
- global pause false
- task active
- daily cap not exceeded
- monthly budget not exceeded
- action risk is low
- task DoD not already complete

**Step 3: Add trigger model**

```text
.cache/triggers.jsonl
```

Trigger format:

```json
{
  "id":"trg_xxx",
  "type":"manual|once|webhook",
  "enabled":true,
  "task_template": {"title":"...","project_id":"...","participants":[]},
  "created_by":"...",
  "ts":"..."
}
```

**Step 4: Add APIs**

```text
POST /api/v1/triggers
GET /api/v1/triggers
POST /api/v1/triggers/{trigger_id}/fire
```

**Step 5: Run tests**

Run:

```bash
cd backend && . .venv/bin/activate && pytest -q tests/test_governance.py tests/test_tasks.py
```

Expected: pass.

**Step 6: Commit**

```bash
git add backend/app/services/autostep_svc.py backend/app/services/trigger_svc.py backend/app/core/config.py backend/app/services/control_svc.py backend/app/services/usage_svc.py backend/app/services/task_svc.py backend/app/api/v1/governance.py backend/app/api/v1/tasks.py backend/tests/test_governance.py backend/tests/test_tasks.py
git commit -m "feat: add governed autostep and triggers"
```

---

## 6. Verification Matrix

| Area | Required Checks | Commands |
|---|---|---|
| AuthZ | 非成员无法读任务/项目/产物/审批 | `cd backend && . .venv/bin/activate && pytest -q tests/test_auth.py tests/test_tasks.py` |
| HITL | 非 eligible approver 不能裁决；payload hash 必须匹配 | `cd backend && . .venv/bin/activate && pytest -q tests/test_memory.py tests/test_governance.py` |
| Sandbox | 路径逃逸失败；无网络；超时 kill；证据链落盘 | `cd backend && . .venv/bin/activate && pytest -q tests/test_paths.py tests/test_skills.py` |
| Skill Evolution | test cases、risk score、eval log、rollback | `cd backend && . .venv/bin/activate && pytest -q tests/test_skills.py` |
| A2A | 防环、预算、handoff 落盘、WS 事件 | `cd backend && . .venv/bin/activate && pytest -q tests/test_orchestrator.py tests/test_tasks.py` |
| Proactivity | proposal queue、autostep cap、pause gate、trigger audit | `cd backend && . .venv/bin/activate && pytest -q tests/test_governance.py` |
| Frontend | TypeScript + Vite build | `cd frontend && npm run build` |
| Full Gate | 全量后端测试 | `cd backend && . .venv/bin/activate && pytest -q` |

---

## 7. Rollout Plan

### 7.1 Feature Flags

Keep defaults conservative:

```env
IDW_A2A_ENABLED=false
IDW_AUTOSTEP_ENABLED=false
IDW_TRIGGERS_ENABLED=false
IDW_SELF_EVOLVE_ENABLED=false
IDW_ENV=development
```

Production rollout order:

1. Enable security guards with no feature flag.
2. Enable `IDW_SELF_EVOLVE_ENABLED=true` for internal users only.
3. Enable `IDW_A2A_ENABLED=true` on selected team/project.
4. Enable `IDW_AUTOSTEP_ENABLED=true` after proposal queue has one week of stable audit data.
5. Enable `IDW_TRIGGERS_ENABLED=true` only for manual/once triggers first; webhook later.

### 7.2 Observability

Add dashboard metrics:

- task unauthorized attempts
- approvals pending/approved/rejected
- high-risk tool blocked count
- A2A handoff count and loop-block count
- autostep attempts/blocked/executed
- Skill test pass rate
- Skill rollback count
- LLM budget usage

### 7.3 Audit Requirements

Every major action writes audit:

- `resource_access_denied`
- `approval_created`
- `approval_decided`
- `tool_call`
- `skill_materialize`
- `skill_promote`
- `skill_rollback`
- `handoff_requested`
- `handoff_honored`
- `handoff_blocked`
- `proposal_created`
- `proposal_decided`
- `autostep_executed`
- `trigger_fired`

---

## 8. Suggested Sprint Breakdown

### Sprint 1 — 安全收口

- Task 1: Unified resource guards
- Task 2: Route guard sweep
- Task 3: HITL action binding
- Task 4: Production security baseline
- Task 5: Path/sandbox hardening

Exit criteria:

- All P0 authorization tests pass.
- No route with sensitive data only depends on `get_current_user`.
- Production rejects default secret and default demo users.

### Sprint 2 — 自进化可信化

- Task 6: Skill evidence chain
- Task 7: Skill tests/risk/eval

Exit criteria:

- Team Skill promotion requires evidence + test pass + eligible approval.
- Skill can be rolled back and eval log explains why.

### Sprint 3 — A2A v1.5

- Task 8: Runtime A2A
- Task 9: Frontend handoff cards

Exit criteria:

- A2A can be enabled per environment.
- Handoff chain is visible and auditable.
- Loop and budget guard tests pass.

### Sprint 4 — Proactivity v1

- Task 10: Plan + DoD
- Task 11: Proposal queue
- Task 12: Autostep + triggers

Exit criteria:

- Agents can propose but not silently execute high-risk actions.
- Autostep obeys pause, budget and daily cap.
- Trigger-created tasks are fully auditable.

---

## 9. Open Decisions

1. **Admin content visibility**：平台 admin 是否可读用户/任务内容，还是只能读审计与元数据？建议默认“内容隔离，审计可见”。
2. **Sandbox deployment model**：是否拆出独立 sandbox worker/container？建议生产必须拆分。
3. **A2A scope**：v1.5 是否允许 auto-join 非参与 Agent？建议默认不允许，必须用户或 Twin 明示添加。
4. **Autostep execution boundary**：低风险定义是否只包含读取、总结、生成 proposal？建议第一版不允许任何写入。
5. **Skill team ownership**：团队 Skill 是否归 team，还是归 project？建议归 team，project 可绑定引用。

---

## 10. Handoff Notes

- 先执行 Sprint 1，不要直接做 A2A 或主动性。
- 每个 Task 按 TDD 执行：先失败测试，再最小实现，再全量相关测试。
- 每个 Sprint 结束更新：`PROGRESS.md`、`DEV_PLAN.md`、`.planning/audit/runs/<run-id>/`。
- 任何涉及默认账号、密钥、Aegis、WS 票据、沙盒容器的改动都需要安全复核。
