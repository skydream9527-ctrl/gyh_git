# ICE-DATA-WORK 材料二 · 技术实现方案与开发 ToDo

- 日期：2026-06-27
- 上级文档：`2026-06-27-ICE-DATA-WORK-设计方案-v1.md`（总纲）
- 关联：材料一（产品/交互）、材料三（Agent 与空间文件区）
- 本文范围：技术栈与架构、仓库结构、数据对象模型、四层空间存储、ContextAssembler、多 Agent 运行时、记忆服务、权限实现、API/路由清单、模块拆解（复用/改造/新建）、分阶段开发 ToDo
- 底座：复用 ICE Data Workbench v3（决策 D-02），在 ICE-DATA-WORK 新仓重组

---

## 1. 技术栈与总体架构

| 层 | 技术 | 来源 |
|---|---|---|
| 后端 | FastAPI + SQLAlchemy + 双认证(JWT/Aegis) | 复用 ICE |
| 前端 | React 18.3 + Vite + TypeScript + Zustand | 复用 ICE |
| 持久化 | **G3 文件优先**（文件系统为真相源）+ SQLite 派生索引 | 复用 ICE |
| 向量检索 | **PostgreSQL + pgvector**（仅存记忆向量索引，可重建） | 新增 |
| LLM | mify 网关（前缀路由 4 协议） | 复用 ICE |
| 执行 | 服务端 ReAct 运行时 + Python 沙盒；本机 daemon（二期 P2-01） | 复用 + 二期 |
| 集成 | Kyuubi / 飞书 / 米盾(Aegis) | 复用 ICE |

```text
┌─────────────┐    ┌──────────────────────────┐    ┌──────────────┐
│ React SPA   │───▶│ FastAPI                   │───▶│ 文件系统(G3) │ ← 真相源
│ (Vite+Zust) │◀──▶│  api/v1 + services        │◀──▶│ users/agents │
└─────────────┘ WS │  ContextAssembler         │    │ teams/tasks  │
                   │  agent_runtime + tool_runner│   └──────────────┘
                   │  memory_svc               │    ┌──────────────┐
                   │  llm_gateway → mify        │───▶│ SQLite index │ ← 派生
                   └──────────────────────────┘    │ pgvector     │ ← 派生(记忆向量)
                                                    └──────────────┘
```

> **G3 不变量**：文件系统是唯一真相源；SQLite 与 pgvector 都是可从文件重建的派生索引（启动时行数不一致则自动重建）。任何与之矛盾的实现都是 bug。

---

## 2. 仓库结构（新仓，从 ICE 演进）

```text
ice-data-work/
├── backend/app/
│   ├── main.py                  # FastAPI + lifespan(seed + scheduler)
│   ├── api/v1/                   # 每资源一个 router
│   ├── services/                 # 业务逻辑（所有 IO 经此层）
│   ├── core/
│   │   ├── storage/              # paths/transaction/jsonio/locks/index（四层空间扩展）
│   │   ├── deps.py aegis.py errors.py
│   │   └── permissions.py        # 新增：三轴权限
│   ├── schemas/  seed/
│   └── tests/
├── frontend/src/                 # pages/components/stores/api/hooks
├── agents/ skills/               # Agent/Skill 定义（团队/平台级共享）
├── teams/                        # 新增：团队/项目共享空间
├── users/ tasks/ files/          # G3 数据目录
└── deploy/ docs/ Makefile deploy.sh docker-compose.yml
```

---

## 3. 数据对象模型

> 文件优先：每个对象有 JSON 落盘位置；SQLite 仅存可查询索引列。下表"存储"列给出落盘路径。

### 3.1 实体与关键字段

| 对象 | 关键字段 | 存储 |
|---|---|---|
| **Team** | id, name, members[(user_id, role: owner/admin/member)], created_at | `teams/{tid}/team.json` |
| **Project** | id, team_id, name, members[(user_id, role: member)], created_at | `teams/{tid}/projects/{pid}/project.json` |
| **User** | id, name, email, feishu_id, auth_role(super_admin/admin/user), team_ids[], default_project_id | `users/{uid}/profile.json` |
| **Twin** | id, user_id, name, profile, goals, style, permission_level(L0-L5), maturity_score | `users/{uid}/twin/twin.json` |
| **Agent** | id, name, category, connector_type, capabilities, input/output_schema, risks, best_practices, prompt_version | `agents/{aid}/agent.json` |
| **Task** | id, **project_id**, title, type(data/general), status(todo/doing/await/done), **participants[]**, assignee, artifacts[], created_by | `tasks/{tid}/task.json` |
| **Participant** | ref_type(user/twin/agent), ref_id, role(owner/collaborator/tool), joined_at, permission_level | `tasks/{tid}/task.json#participants` |
| **Conversation** | id, task_id, turns(*.jsonl), inflight_state | `tasks/{tid}/conversation.jsonl` |
| **Turn** | id, speaker{type,id}, content, tool_calls[], ts | conversation.jsonl 行 |
| **MemoryItem** | id, scope(user/agent_user/agent_team/project/team), owner_ref, content, confidence, source_task, status, embedding_id | `*/memory/*.memory.md`（+pgvector） |
| **MemoryCandidate** | id, task_id, proposed_scope, content, source, status(pending/approved/rejected) | `tasks/{tid}/memory/candidates.jsonl` |
| **Approval** | id, task_id, risk_level, action_type, requester, summary, payload_ref, status, decided_by | `tasks/{tid}/approvals.jsonl` |
| **AuditEvent** | id, actor, action, tool, permission_level, input/output_summary, ts | `*/audit.jsonl` |
| **Grant**（二期 P2-02） | id, visitor_twin_id, host_task_id, scope, granted_by, expires_at, status | `tasks/{tid}/grants.jsonl` |

### 3.2 关系概览

```text
Team 1─* Project 1─* Task 1─* Participant *─1 {User | Twin | Agent}
User 1─1 Twin            Task 1─1 Conversation 1─* Turn
Task 1─* MemoryCandidate ──promote──▶ MemoryItem(scope→目标空间)
Agent 1─* MemoryItem(by-user/{uid} | by-team/{tid})
```

---

## 4. 存储层：四层空间 paths 扩展（G3）

在 ICE 的 `core/storage/paths.py` 基础上新增路径解析器（所有用户/任务/团队数据路径必须经此，禁止内联拼接）：

```python
# 新增/扩展的 paths（示意）
def team_dir(tid): ...                          # teams/{tid}/
def team_shared(tid, kind): ...                 # teams/{tid}/shared/{files|knowledge|memory|artifacts}
def project_dir(tid, pid): ...                  # teams/{tid}/projects/{pid}/
def project_shared(tid, pid, kind): ...
def twin_dir(uid): ...                          # users/{uid}/twin/
def twin_memory(uid, name): ...                 # users/{uid}/twin/memory/{name}.memory.md
def agent_user_memory(aid, uid): ...            # agents/{aid}/memory/by-user/{uid}/usage.memory.md
def agent_team_memory(aid, tid): ...            # agents/{aid}/memory/by-team/{tid}/shared.memory.md
def task_participant_notes(task_id, ref_id): ...# tasks/{tid}/participants/{ref_id}/notes.md
def task_working_memory(task_id): ...           # tasks/{tid}/memory/working.memory.md
def task_candidates(task_id): ...               # tasks/{tid}/memory/candidates.jsonl
```

- 多文件写入仍走 `file_transaction()`（portalocker 咨询锁 + 原子备份回滚）。
- 追加型（conversation/tool_calls/candidates/audit）用 `.jsonl`。
- 记忆晋升 = `file_transaction` 内"从 candidates.jsonl 读 → 写目标 `*.memory.md` → 更新 SQLite/pgvector 索引"，原子完成。

---

## 5. ContextAssembler（多参与者上下文组装，技术内核）

新增服务 `services/context_assembler_svc.py`，替代/包裹 ICE 的 `context_svc.py`。每个对话回合开始时按层组装：

```python
def assemble_context(task, speaker, participants, acting_user) -> Messages:
    layers = []
    # 1) 任务层
    layers += task_system(task)                       # task.json 摘要 + workspace_type
    layers += recent_turns(task) + compaction_summary(task)
    layers += working_memory(task)                    # 全量（小）
    layers += task_file_index(task)                   # 仅索引，不灌内容
    # 2) 参与者层（每个 agent/twin 一份，带来源标注）
    for p in participants:
        layers += agent_md(p)                         # 操作手册，始终注入
        layers += pinned_memory(p)                    # pinned 全量
        layers += retrieve_memory(p, query=task_context, k=K)   # pgvector top-k 切片
        layers += participant_task_notes(task, p)     # 任务级 notes
    # 3) 用户层
    layers += user_global_prefs(acting_user)
    # 4) 团队/项目层
    layers += retrieve_shared(task.project_id, query=task_context, k=K)
    return budget_clamp(layers, max_tokens)           # 超预算时按优先级丢弃低层
```

- **优先级（保留顺序）**：任务 > 参与者 > 用户 > 项目 > 团队（材料一/总纲一致）。
- **访问控制内嵌**：`retrieve_memory(p)` 只检索 `p` 在当前 task/user/team 边界内**有权读**的记忆（见 §8）。
- **检索后端**：v1 用"pinned + agent.md 全量 + 关键词命中"；v1.5 接 pgvector 语义检索 top-k。
- **来源标注**：每段注入带 `[source: agent:DataAgent / scope: by-user]`，便于审计与可解释。
- **缓存**：参与者层按 (participant, memory_version) 缓存，记忆未变则复用。

---

## 6. 多 Agent 对话与运行时

### 6.1 会话模型

- 一个 Task 一条主 Conversation；Turn 带 `speaker{type:user|twin|agent, id}`。
- **轮次路由（v1，Twin 编排）**：用户发言 → Twin 接管，决定本轮由哪个工具 Agent 执行（或自己回应）；`@参与者` 可由用户强制定向。Squad 自动路由留二期（P2-03）。
- 复用 ICE `agent_runtime.run_agent_turn`（有界 ReAct，默认 20 轮，硬顶 50）；扩展为"按 speaker 切换 system/agent.md + 组装上下文"。

### 6.2 WebSocket（扩展 ICE `api/v1/ws.py`）

- 路径不变：`/api/v1/ws/conversations/{cid}?task_id=...`，鉴权沿用 subprotocol bearer。
- 事件协议复用：`text / tool_use_delta / message_done`，**新增 `speaker` 字段**区分发言主体。
- Inflight guard 复用：`(task_id, conv_id)` 单飞；新增"按参与者并行工具"留二期。

### 6.3 工具与沙盒

- 复用 ICE 内置工具集（~23 个）与 `execute_python` 沙盒 venv（pandas/prophet/sklearn…，CPU/内存/网络限制）。
- 新增工具：`read_space_file`（带四层空间访问控制）、`propose_memory`（生成 Memory Candidate）、`request_approval`（HITL）。

---

## 7. 记忆服务 memory_svc（新建）

职责：记忆候选生成、晋升路由、检索、pgvector 索引维护。

| 能力 | 实现 |
|---|---|
| 生成候选 | `propose_memory` 工具 → 写 `tasks/{tid}/memory/candidates.jsonl`（proposed_scope） |
| 晋升 | 审批通过 → `file_transaction`：写目标 `*.memory.md` + 更新 pgvector + SQLite |
| scope 路由 | user_preference / agent_user / agent_team / project / team（见总纲 §4.4） |
| 检索 | 按 (participant, 访问边界) 过滤后 pgvector top-k；v1 降级关键词 |
| 嵌入 | mify 嵌入端点；嵌入失败降级关键词，不阻塞 |

- 复用 ICE 的"经验卡片审批闭环"作为 `agent_team` 晋升的审核实现。
- "贡献给团队"是显式动作：默认只进 `agent_user`，晋升 `agent_team` 需用户主动 + 审核（D-06）。

---

## 8. 权限与治理实现

新增 `core/permissions.py`，三轴合一中间件：

```python
def effective_perms(user, resource) -> Perms:
    platform = user.auth_role                      # super_admin/admin/user
    membership = team_project_role(user, resource) # owner/admin/member/none
    twin_level = user.twin.permission_level         # L0-L5
    return intersect(platform, membership, twin_level)
```

- 资源访问（任务/项目/团队/记忆）先过成员资格 gate，再过 Twin 等级 gate。
- 高风险动作清单（写文件/跑命令/发消息/付费/固化记忆/**跨空间读取**）→ 强制 `request_approval`，复用 ICE `hitl_svc`。
- 审计：所有工具调用 + 跨空间读取写 `audit.jsonl`（复用 ICE event_log/audit）。
- `grant_svc`（二期）：访客 Twin 的 scoped grant 校验；v1 仅留接口 stub。

---

## 9. API / 路由清单

### 9.1 复用 ICE（基本不动）

auth、ws、conversations、agents（改造见下）、skills、files、kb、notifications、scheduled、templates、search、system_config、voice、admin*、guide、usage、sql-audit、audit、diagnostics。

### 9.2 改造

| 路由 | 改造 |
|---|---|
| `POST /tasks` | 必带 `project_id`（缺省落用户个人项目）；支持初始 participants |
| `GET /tasks` | 按成员资格 + project 过滤 |
| `agents/*` | 记忆分区读写（by-user/by-team）；Twin 作为特殊 agent 纳入 |
| `ws` | 事件加 `speaker`；上下文走 ContextAssembler |
| `experience_cards` | 泛化为记忆晋升审核（agent_team） |

### 9.3 新增

| 路由 | 说明 |
|---|---|
| `GET/POST /teams`、`/teams/:id`、`/teams/:id/members` | 团队 CRUD + 成员 |
| `GET/POST /projects`、`/projects/:id`、`/projects/:id/members` | 项目 CRUD + 成员 |
| `GET/POST /tasks/:id/participants` | 邀请/移除参与者（agent/twin/二期他人twin） |
| `GET/PUT /twin` | 我的 Twin 画像/权限等级 |
| `GET /twin/memory`、`POST /twin/memory/:id`（确认/编辑/冻结） | Twin 记忆管理 |
| `GET /memory/candidates`、`POST /memory/promote` | 记忆候选 + 晋升（带 scope） |
| `GET/POST /teams/:tid/projects/:pid/shared/*` | 项目/团队共享文件/知识/产物 |
| `POST /grants`（二期 stub） | 跨用户 Twin 授权 |

---

## 10. 后端模块拆解（复用 / 改造 / 新建）

| 模块 | 处置 | 说明 |
|---|---|---|
| core/storage（paths/transaction/jsonio/locks/index） | **改造** | 加四层空间路径解析（§4） |
| llm_gateway / sandbox / tool_runner / compaction_svc / scheduler_svc | **复用** | 基本不动；tool_runner 加 3 个新工具 |
| auth_svc / aegis / rate_limit / sql_audit / usage_svc / voice | **复用** | voice 仍默认关 |
| feishu / kyuubi 集成 | **复用** | 缺失降级 `*_NOT_CONFIGURED` |
| context_svc | **改造→ context_assembler_svc** | 多参与者分层组装（§5） |
| agent_runtime / ws | **改造** | speaker 切换 + 多参与者 |
| task_svc | **改造** | project_id + participants |
| agents_svc | **改造** | 记忆分区 by-user/by-team |
| experience_card_svc | **改造** | 泛化为记忆晋升审核 |
| hitl_svc / invitation_svc | **改造** | 审批含记忆/跨空间；邀请含参与者 |
| **team_svc / project_svc** | **新建** | 团队/项目 + 共享空间 + 成员 |
| **twin_svc** | **新建** | Twin = 特殊 agent + 特权 |
| **memory_svc** | **新建** | 候选/晋升/检索/pgvector |
| **permissions.py** | **新建** | 三轴权限 |
| **grant_svc** | **新建(stub)** | 二期跨 Twin 授权 |
| **pgvector 适配** | **新建** | 嵌入 + 检索 + 重建 |

---

## 11. 前端模块拆解

| 模块 | 处置 |
|---|---|
| App.tsx 路由、AdminLayout、guards、shell(TopNav/MobileBottomBar) | 复用 + 加团队/项目路由与切换器 |
| pages/dashboard → workbench、pages/workspace、create_task、agent_detail、admin/* | 改造 |
| **pages/board、pages/team、pages/project、pages/twin** | 新建 |
| components/chat（流式对话） | 改造：多 speaker 头像/徽标 + 工具卡 + @定向 |
| components/TwinDock（常驻） | 新建 |
| components/participants（邀请 chips/picker） | 新建 |
| components/memory（候选卡 + 贡献给团队开关） | 新建 |
| stores：authStore、uiStore、+ spaceStore(当前team/project)、+ twinStore | 改造/新建 |

---

## 12. 非功能：测试 / 部署 / 迁移 / 开关

- **测试**：复用 ICE pytest；新增覆盖 ContextAssembler 分层/访问控制、记忆晋升 file_transaction、三轴权限 gate、四层 paths。
- **部署**：复用 `deploy.sh`/Makefile/docker-compose；新增 Postgres+pgvector 服务（compose 加一服务，缺失则记忆降级关键词）。
- **特性开关**（沿用 ICE `ICE_*_ENABLED` 模式）：`IDW_PGVECTOR_ENABLED`、`IDW_TWIN_ENABLED`、`IDW_DAEMON_ENABLED`(二期)、`IDW_CROSS_TWIN_ENABLED`(二期)，默认保守关，灰度开。
- **迁移**：新仓不迁 ICE 运行时数据；保留 G3 目录结构兼容，必要时写 `scripts/migrate_ice_to_idw.py`。

---

## 13. 分阶段开发 ToDo

### M0 · 仓库与底座（1 周）
- [ ] 从 ICE 拉出新仓骨架，去掉 ICE 专有运行时数据，保留 backend/frontend/storage/deploy
- [ ] 接入 Postgres+pgvector（docker-compose + settings + 健康检查 + 降级开关）
- [ ] `core/storage/paths.py` 四层空间路径解析 + 单测
- [ ] `core/permissions.py` 三轴权限骨架 + 单测

### M1 · 团队/项目/Twin 基础（2 周）
- [ ] team_svc / project_svc + `/teams` `/projects` + 成员角色 gate
- [ ] 用户默认"个人项目"自动创建（D-11）
- [ ] twin_svc：Twin = 特殊 agent；`/twin` 画像 + L0-L5
- [ ] 前端：团队/项目切换器、/team /project /twin 页骨架

### M2 · 任务、看板、多参与者会话（2-3 周）
- [ ] task_svc 加 project_id + participants；`/tasks/:id/participants`
- [ ] context_assembler_svc 分层组装（v1 关键词版）+ 访问控制 + 单测
- [ ] ws/agent_runtime 加 speaker；多 Agent 对话
- [ ] 前端：Workbench、Board（状态泳道 + Agent assignee）、Workspace（产出物+多方对话+参与者chips+抽屉）、TwinDock

### M3 · 记忆隔离/复用闭环（2 周）
- [ ] memory_svc：propose_memory / candidates / promote（5 种 scope）
- [ ] Agent 记忆分区 by-user/by-team + "贡献给团队"显式晋升 + 审核
- [ ] hitl_svc 接记忆候选 + 跨空间读取确认
- [ ] pgvector 嵌入 + 语义检索接入 ContextAssembler（v1.5）
- [ ] 前端：记忆候选卡、贡献给团队开关、Twin Manager 记忆管理

### M4 · 治理/资产/管理后台（1-2 周）
- [ ] Approvals & Audit 页 + 一键暂停 + 失败复盘
- [ ] 项目/团队共享空间（文件/知识/产物，按层隔离）
- [ ] Agent Hub/详情（记忆分区展示）、知识与产物（层级筛选）
- [ ] /admin 加团队/项目管理

### M5 · 联调/移动端/验收（1-2 周）
- [ ] 端到端场景（材料一 §5）跑通；pytest + tsc 全绿
- [ ] 移动端：Workbench / Workspace(只读+确认) / Approvals
- [ ] 部署演练（deploy.sh --prod + pgvector）+ 数据热更新不丢

### 二期（记录，不在 v1）
- [ ] P2-01 本机 daemon/Runtime（驱动 Claude Code/Cursor）
- [ ] P2-02 ⭐ 跨用户 Twin 协作（grant_svc 完整 + 多 Twin 同台）
- [ ] P2-03 Squads / P2-04 Autopilots

---

## 14. 关键技术决策记录（TDR）

| 编号 | 决策 | 理由 |
|---|---|---|
| TDR-1 | 记忆走文件(`*.memory.md`)，pgvector 只存可重建的向量索引 | 守 G3 不变量；向量库坏了能重建 |
| TDR-2 | Twin 复用 Agent 运行时（D-08） | 不引入第二套运行时；Twin 与工具 Agent 同循环共存 |
| TDR-3 | 上下文组装内嵌访问控制 | 隔离在"读取点"强制，避免越权注入 |
| TDR-4 | 多 Agent v1 用 Twin 编排路由，Squad 自动路由留二期 | 降复杂度，先跑通三方协作 |
| TDR-5 | 记忆晋升用 file_transaction 原子完成（文件+索引同事务） | 保持索引↔文件一致性 |

---

## 15. 用户贡献驱动的 Skill / Agent 自演进（D-13）

让 Agent 在缺能力时由用户"喂代码"跑通，再蒸馏为可复用 Skill 并绑进 Agent。**大量复用 ICE 现成基建**：Skill CRUD + JSON schema 校验 + 沙盒 test-run、`execute_python` 沙盒、kyuubi + SQL 审计、Agent Prompt 版本/快照/回滚、经验卡片审批闭环。新增的只是"任务内贡献 → 候选 → 晋升/绑定"的串联 + Skill 的 by-user/by-team 分区。

### 15.1 数据对象（新增）

| 对象 | 关键字段 | 存储 |
|---|---|---|
| **Skill** | id, name, desc, runtime(sql/python), input_schema, owner_scope(builtin/team/user), current_version | 团队：`skills/{sid}/skill.json`；个人草稿：`users/{uid}/skills/{sid}/skill.json` |
| **SkillVersion** | n, code_ref, meta(author, source_task), created_at, test_status | `…/{sid}/versions/{n}/{code.(sql\|py), meta.json}` |
| **SkillCandidate** | id, task_id, name, code, input_schema, runtime, proposed_scope(user/team), bind_agent_id, status | `tasks/{tid}/skill_candidates.jsonl` |
| **AgentSkillBinding** | agent_id, skill_id, scope(team/by-user), knowledge(何时用), enabled | `agents/{aid}/agent.json#skills` + `agents/{aid}/bindings/by-user/{uid}/skills.json` |

> Skill 代码落文件（守 G3）；SQLite 仅索引可查询列；版本目录不可变，回滚 = 指 current_version 到旧版或生成新版。

### 15.2 新增工具

| 工具 | 作用 | 安全 |
|---|---|---|
| `run_user_code` | 执行用户在任务中贡献的代码 | python → `execute_python` 沙盒（无网络/限 CPU 内存/无凭证）；sql → kyuubi 只读 + SQL 审计 |
| `propose_skill` | 跑通后生成 SkillCandidate（含抽取的入参 schema） | 写 `tasks/{tid}/skill_candidates.jsonl` |
| `promote_skill` | 审批后晋升：写 Skill 版本 + 绑定 Agent + 版本+1 | `file_transaction` 原子；团队晋升强制沙盒 test-run 通过 + 审核 |

### 15.3 服务（新增 / 改造）

| 模块 | 处置 | 说明 |
|---|---|---|
| `skill_svc`（ICE 已有） | **改造** | 加 by-user 草稿分区、入参 schema 抽取、版本目录、test-run 封装 |
| `skill_evolve_svc` | **新建** | 串联 候选→审核→晋升→绑定 Agent→bump 版本；调用 experience_card 审批闭环做团队门控 |
| `agents_svc` | **改造** | Agent 绑定 Skill（team / by-user）+ knowledge 写入 + 版本/快照/回滚（复用 ICE） |
| `tool_runner`（ICE 已有） | **改造** | 注册 `run_user_code` / `propose_skill` / `promote_skill` |
| `sandbox`（ICE 已有） | **复用** | 用户代码一律在此跑 |

### 15.4 API（新增）

| 路由 | 说明 |
|---|---|
| `POST /tasks/:id/run-code` | 任务内执行贡献代码（沙盒） |
| `GET /tasks/:id/skill-candidates` · `POST /skills/promote` | 候选列表 + 晋升（带 scope + bind_agent） |
| `GET/POST /skills`、`/skills/:id`、`/skills/:id/versions`、`/skills/:id/test-run`、`/skills/:id/rollback` | Skill CRUD + 版本 + 沙盒测试 + 回滚 |
| `POST /agents/:id/skills` | 绑定/解绑 Skill（team / by-user）+ knowledge |

### 15.5 上下文组装的衔接

ContextAssembler 的"参与者层"在注入 Agent 时，除 agent.md + 记忆切片外，**注入该 Agent 对当前用户可见的 Skill 清单 + knowledge**（团队绑定 + 该用户 by-user 绑定），使 Agent "知道自己会哪些活、何时用"。

### 15.6 安全（强约束）

- 用户贡献代码 = **不可信输入**，一律沙盒执行；Python 无网络、限 CPU 60s/内存 1GB、无服务凭证；SQL 只读 + SQL 审计。
- 团队级 Skill 晋升 = **沙盒 test-run 通过 + owner/admin 审核** 双门，缺一不可。
- 个人草稿 Skill 仅本人任务可用，不进他人上下文（隔离同 D-06）。

### 15.7 开发 ToDo（追加到 §13）

#### M6 · Skill/Agent 自演进闭环（2 周，依赖 M3 记忆闭环）
- [ ] `run_user_code` 工具（python 沙盒 / sql kyuubi）+ 任务内执行 UI
- [ ] 入参 schema 抽取 + `propose_skill` → SkillCandidate
- [ ] skill_svc 加 by-user 草稿分区 + 版本目录 + test-run
- [ ] skill_evolve_svc：候选→审核→晋升→绑定 Agent→bump 版本（复用经验卡审批 + Agent 快照/回滚）
- [ ] ContextAssembler 注入 Agent 的可见 Skill 清单 + knowledge
- [ ] 前端：Workspace 贡献代码 + run 工具卡、贡献为 Skill 表单、Agent 详情 Skills 标签（版本/test-run/贡献给团队/回滚）

### 15.8 技术决策记录（追加）

| 编号 | 决策 | 理由 |
|---|---|---|
| TDR-6 | Skill 代码落文件 + 版本目录不可变 | 守 G3；回滚/审计可追溯 |
| TDR-7 | 用户代码只在沙盒跑；团队晋升双门（test-run + 审核） | 不可信输入隔离 + 团队资产质量门控 |
| TDR-8 | 个人草稿 Skill 与团队 Skill 分区（by-user/by-team） | 与记忆模型 D-06 一致，隔离/复用统一心智 |
