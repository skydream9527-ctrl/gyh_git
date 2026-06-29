# ICE-DATA-WORK 开发计划（DEV_PLAN）

- 日期：2026-06-27
- 性质：**任务级完整开发计划**，作为持续开发的 backlog。配套 `PROGRESS.md`（进度记录，同一套任务 ID）。
- 依据：`docs/` 设计方案-v1（决策 D-01~D-14）+ 材料一/二/三 + `docs/prototype/` 原型
- 技术栈：后端 FastAPI + SQLAlchemy + JWT/Aegis；前端 React 18 + Vite + TS + Zustand；存储 G3 文件优先 + SQLite 索引 + pgvector

## 如何使用本文档

1. 每个里程碑拆成带 ID 的任务（`M{n}-T{nn}` / `P2-xx-T{nn}`）；开发时认领任务。
2. 任务完成后到 `PROGRESS.md` 勾掉并记录验证结论与日期。
3. 任务的"关键模块/文件"给出落点；"验收"是完成判据；"依赖"决定先后。
4. §4 工程基线是**贯穿所有任务的恒定规则**，每个任务都要遵守。

## 1. 里程碑与依赖

```text
M0 仓库与地基 ─→ M1 团队/项目/Twin/认证 ─→ M2 任务/看板/多参与者会话 ─→ M3 记忆闭环
                                                                          ├─→ M4 治理/资产/后台
                                                                          └─→ M6 Skill/Agent 自演进
                                                              （M4、M6 可在 M2/M3 完成后并行）
                                                                          └─→ M5 联调/移动端/验收
M7 多 Agent 协作编排 / 任务编排 / Agent 主动性（v1.5 增强，承接并前置 P2-03/P2-04；依赖 M2/M3/M4）
二期：P2-01 本机 Runtime · P2-02 跨用户 Twin · P2-03 Squads · P2-04 Autopilots
```

预估：v1（M0–M6）约 10–12 周；M7（v1.5 增强）约 2–3 周；二期另计。

## 2. 约定

- 任务状态（在 PROGRESS.md 用）：`todo` / `doing` / `done` / `blocked`。
- 模块命名沿用 ICE：服务层 `*_svc.py`；所有文件 IO 走 `services/`，不在 API 层直接读写。
- 前端页面按 `docs/prototype/` 逐页移植，组件命名与原型一致。
- 验收以"可运行 + 测试通过"为准，命令出 0 不等于通过。

## 3. 工程基线（贯穿所有任务，恒定规则）

| 基线 | 要求 |
|---|---|
| G3 不变量 | 文件系统是唯一真相源；SQLite/pgvector 是可重建派生索引；启动时不一致则自动重建 |
| 路径解析 | 一切用户/任务/团队路径走 `core/storage/paths.py`，禁止内联拼接；外部 id 过防穿越 |
| 原子写 | 多文件写入走 `file_transaction`；追加型用 `.jsonl` |
| 错误信封 | 统一 `{code,message,error_code,data}`；服务端 raise `APIError`，不返回 HTTPException |
| 外部 CLI 降级 | kyuubi/feishu/mify 缺失返回 `*_NOT_CONFIGURED`，不阻塞启动 |
| 治理 | 高风险动作（写文件/跑命令/发消息/付费/固化记忆/跨空间读取）必确认 + 审计 |
| 特性开关 | 新机制用 `IDW_*_ENABLED` 灰度，保守默认关 |
| 收口 | 每个里程碑结束：`pytest -q` + `tsc --noEmit` 全绿 |

---

## 4. M0 · 仓库与地基

| ID | 任务 | 关键模块/文件 | 验收 | 依赖 |
|---|---|---|---|---|
| M0-T01 | 项目目录梳理 | `docs/`（设计文档+prototype+参考资料） | 根目录干净，docs 归档 | — |
| M0-T02 | 根配置 | README/Makefile/.env.example/.gitignore/docker-compose | `make` 目标可用 | — |
| M0-T03 | G3 数据目录占位 | agents/skills/teams/users/tasks/files + .gitkeep | 目录存在 | — |
| M0-T04 | 运行配置 | `core/config.py`（DATA_ROOT 自解析） | health 显示 data_root | — |
| M0-T05 | 四层空间路径（keystone） | `core/storage/paths.py` | 单测：结构 + 防穿越 | M0-T04 |
| M0-T06 | 原子写 + 锁 + 事务 | `core/storage/{jsonio,locks,transaction}.py` | file_transaction 回滚可用 | M0-T05 |
| M0-T07 | 错误信封 | `core/errors.py` | 异常→统一信封 | — |
| M0-T08 | 应用入口 | `main.py`（lifespan+异常处理+CORS） | `/api/v1/health` 200 | M0-T04..07 |
| M0-T09 | 路由/服务骨架 | `api/v1/{health,teams}` + `team_svc` + `seed/runner` | `/teams` 返回 seed 团队 | M0-T08 |
| M0-T10 | 前端脚手架 | Vite+React+TS+Zustand + Workbench 自检页 | 前端起、连后端 health | M0-T08 |
| M0-T11 | SQLite 索引层 | `core/storage/index.py` + `scripts/rebuild_index.py` | 启动建/重建索引 | M0-T06 |
| M0-T12 | Postgres+pgvector 接入 | docker-compose + DB 连接 + 降级开关 | 缺省降级、配置则连通 | M0-T02 |
| M0-T13 | 地基验证 | pytest + 启动 e2e | health/teams/paths 测试通过 | M0-T09,T10 |

## 5. M1 · 团队 / 项目 / Twin / 认证

| ID | 任务 | 关键模块/文件 | 验收 | 依赖 |
|---|---|---|---|---|
| M1-T01 | 三轴权限实装 | `core/permissions.py` + `core/deps.py` | gate 生效（平台×成员×Twin） | M0 |
| M1-T02 | 双认证 | `auth_svc` + `core/aegis.py`（飞书 OAuth + JWT + 米盾） | 登录签 token；Aegis 头校验 | M0 |
| M1-T03 | 用户 | `user_svc` + `users/{uid}/profile.json`；登录自动建号 | 首登建 user | M1-T02 |
| M1-T04 | 团队 CRUD | `team_svc` + `/teams`（成员 owner/admin/member） | 建/改团队 + 成员 gate | M1-T01 |
| M1-T05 | 项目 CRUD | `project_svc` + `/projects`（任务归属约束 D-11） | 建/改项目 + 成员 | M1-T04 |
| M1-T06 | 个人项目 | 用户默认"个人项目"自动创建 | 无项目任务落个人项目 | M1-T05 |
| M1-T07 | 一等 Twin | `twin_svc` + `twin.json` + `/twin`（画像+L0-L5） | 建 Twin、改权限等级 | M1-T03 |
| M1-T08 | 索引列 | users/teams/projects 入 SQLite 索引 | 列表走索引、内容走文件 | M0-T11 |
| M1-T09 | 前端认证 | 登录页 + 飞书回调 + authStore 真实化 | 登录跳 Workbench | M1-T02 |
| M1-T10 | 前端空间 | Team/Project 切换器 + /team /project /twin 页 | 切项目、看/改 Twin | M1-T07 |
| M1-T11 | 种子 | admin/测试用户 + Twin 模板 + 内置 Agent（data-analysis 等） | seed 一键就绪 | M1-T03,T07 |
| M1-T12 | 测试 | pytest：权限 gate / 成员资格 / 个人项目 | 全绿 | 本里程碑 |

## 6. M2 · 任务 / 看板 / 多参与者会话（产品主线）✅ 已完成

| ID | 任务 | 关键模块/文件 | 验收 | 状态 |
|---|---|---|---|---|
| M2-T01 | 任务模型 + 状态机 | `task_svc`（project_id+participants+6态 D-14） | 状态流转正确 | ✅ |
| M2-T02 | 任务 API | `/tasks` CRUD + 状态流转 + `/tasks/:id/participants` | 邀请工具Agent/我的Twin | ✅ |
| M2-T03 | 会话 | `conversation_svc`（conversation.jsonl + turn.speaker） | 多 speaker 落盘 | ✅ |
| M2-T04 | 上下文组装 | `context_assembler_svc`（分层 + 访问控制内嵌） | 注入带来源；越权拦截 | ✅ |
| M2-T05 | LLM 网关 | `llm_gateway`（mify 前缀路由 + Anthropic + mock 降级） | 流式事件统一 | ✅ |
| M2-T06 | Agent 运行时 | `agent_runtime`（有界 ReAct + Twin 编排）+ `tool_runner` | speaker 路由 + 落盘 | ✅ |
| M2-T07 | WebSocket | `ws.py`（流式 + speaker + inflight guard + JWT） | 流式三方对话 | ✅ |
| M2-T08 | 内置工具 | now/read_space_file/write_file/kyuubi_query/propose_memory/request_approval/list_agents + 降级 | 工具卡可见 | ✅ |
| M2-T09 | 产物 | `artifact_svc` + 产物 3 态 + 渐进展开列表 + 保存到空间 | 产物▸N→列表→内容 | ✅ |
| M2-T10 | 前端 Workbench | 状态优先卡 + 运行中/待确认/最近 + 统计行 | 状态副行 + 产物入口 | ✅ |
| M2-T11 | 前端 Board | 状态泳道 + assignee + 报错/已暂停 | 指派 Agent、切状态 | ✅ |
| M2-T12 | 前端 Workspace | 产出物面板 + 多方对话 + 参与者chips + 抽屉 | 三方协作现场 | ✅ |
| M2-T13 | 前端 TwinDock + 导航 | 常驻 Dock + 指令驱动导航（D-12） | "带我去看板"切页 | ✅ |
| M2-T14 | 前端 chat 组件 | 多 speaker 头像/徽标 + 工具卡 + 流式光标 | 与原型一致 | ✅ |
| M2-T15 | 测试 | ContextAssembler 分层/访问控制 + 状态机 + 运行时 | pytest 51/51 全绿 | ✅ |

## 7. M3 · 记忆隔离/复用闭环 ✅ 已完成

| ID | 任务 | 关键模块/文件 | 验收 | 状态 |
|---|---|---|---|---|
| M3-T01 | 记忆服务 | `memory_svc`（propose/candidates/promote/reject，5 scope + .memory.md 解析） | 候选→晋升流程 | ✅ |
| M3-T02 | Agent 记忆分区 | by-user/by-team + "贡献给团队"晋升 + 审核(needs_review) | 默认隔离、显式共享 | ✅ |
| M3-T03 | HITL | `hitl_svc`（审批队列 + 记忆候选 + 跨空间确认 + 聚合待确认） | 高风险进队列 | ✅ |
| M3-T04 | 向量检索 | `memory_retrieval`：关键词 top-k + pgvector hook（降级）接 ContextAssembler | 相关切片注入；降级关键词 | ✅ |
| M3-T05 | 经验审批 | 以 hitl_svc 通用审批 + needs_review 实现共享空间晋升门控（替代 experience_card 模块） | 批准后注入 | ✅ |
| M3-T06 | 前端记忆 | memoryStore + MemoryPanel（候选卡 + 贡献给团队开关 + 审批 tab）+ Twin 记忆管理 | 选 scope 晋升 | ✅ |
| M3-T07 | 晋升原子性 | `file_transaction`：候选 + 目标 .memory.md 同事务 | 一致性测试 | ✅ |
| M3-T08 | 测试 | 记忆晋升 5 scope + 隔离/复用矩阵 + 检索 + HITL（pytest 73 全绿） | 全绿 | ✅ |

## 8. M4 · 治理 / 资产 / 后台 ✅ 已完成

| ID | 任务 | 关键模块/文件 | 验收 | 状态 |
|---|---|---|---|---|
| M4-T01 | 审批与审计 | `audit_svc` + 待确认队列 + 权限/工具调用日志 + 跨空间拦截 | 可追溯 | ✅ |
| M4-T02 | 一键暂停 | `control_svc` 全局暂停；runtime + execute_tool 暂停态拒绝 | 暂停生效 | ✅ |
| M4-T03 | 失败复盘 | `error_classifier`（error_type/recoverable/suggested，7 类规则） | 报错结构化 | ✅ |
| M4-T04 | 共享空间 | `shared_svc` 项目/团队 files/knowledge/artifacts + API（按层隔离 + 防穿越） | 成员可见、隔离正确 | ✅ |
| M4-T05 | Agent Hub/详情 | 前端 Agents Hub + AgentDetail（能力 + 记忆分区 D-06 + Skills + agent.md） | 与原型一致 | ✅ |
| M4-T06 | 知识与产物页 | 前端 Knowledge（项目/团队 × files/knowledge/artifacts 层级筛选） | 复用、确认记忆 | ✅ |
| M4-T07 | 管理后台 | `/admin` 概览/用户/团队项目/用量/设置 + admin gate + 角色编辑限 super_admin | admin gate | ✅ |
| M4-T08 | 用量与成本 | `usage_svc`（LLM 单价/月度预算/CSV；mock 计次）；llm done 落账 | 看板+导出 | ✅ |
| M4-T09 | 前端治理/后台 | Approvals 页（待确认+审计+失败复盘+一键暂停）+ Admin(5 tab) + 导航分组 | 与原型一致 | ✅ |

## 9. M5 · 联调 / 移动端 / 验收

| ID | 任务 | 关键模块/文件 | 验收 | 依赖 |
|---|---|---|---|---|
| M5-T01 | 端到端联调 | 材料一 §5 全场景 | 场景跑通 | M1–M4 |
| M5-T02 | 移动端 | Workbench/Workspace(只读+确认)/Approvals | 移动可用 | M2,M4 |
| M5-T03 | 生产部署 | deploy.sh --prod + 单端口伺服 SPA + pgvector | 部署可达 | M0-T12 |
| M5-T04 | 数据热更新 | pack/迁移不丢 users/tasks/.env | 重部署不丢数据 | M5-T03 |
| M5-T05 | 收口 | 全量 pytest + tsc + 健康检查 | 全绿 + 200 | 全部 |

## 10. M6 · Skill / Agent 自演进（D-13，可与 M4 并行）✅ 已完成

| ID | 任务 | 关键模块/文件 | 验收 | 状态 |
|---|---|---|---|---|
| M6-T01 | 任务内执行 | `run_user_code` 工具（python→沙盒 / sql→kyuubi 降级） | 贴码→沙盒跑通 | ✅ |
| M6-T02 | 沙盒 | `sandbox.py` 子进程+限CPU/FSIZE+无网络+去凭证+隔离cwd+墙钟超时 | 安全约束生效 | ✅ |
| M6-T03 | 候选 | 入参 schema 抽取（py params/sql :param）+ `propose_skill` → SkillCandidate | 生成候选 | ✅ |
| M6-T04 | Skill 服务 | `skill_svc`（by-user 草稿立即可用 + 版本目录 + 沙盒 test-run） | 草稿立即可用 | ✅ |
| M6-T05 | 自演进 | `skill_evolve_svc`（候选→审核→晋升双门→绑定Agent+bump→回滚） | 团队晋升双门 | ✅ |
| M6-T06 | 注入 | ContextAssembler `_agent_skills_layer` 注入可见 Skill + knowledge（灰度） | 下次自动会用 | ✅ |
| M6-T07 | 前端 | run 工具卡 + 贡献为 Skill 表单(SkillPanel) + Agent Skills 标签 + skillStore | 与原型一致 | ✅ |
| M6-T08 | 测试 | `test_skills.py` 沙盒安全 + 晋升双门（pytest 117，+25） | 全绿 | ✅ |

## 11. M7 · 多 Agent 协作编排 / 任务编排 / Agent 主动性（v1.5 增强）

> 背景：v1（M0–M6）已跑通"单跳 Twin 编排"的三方协作——用户↔Twin↔单个工具 Agent，每轮只有一个 speaker（材料三 §5.3）。M7 把协作从"单跳"升级为「有界多跳 A2A + 任务计划编排 + 受治理的主动性」：多个 Agent 在同一任务里真正接力、按计划推进、并能主动提议下一步。Squad（多 leader 小队）与完整 Autopilots 仍属二期（P2-03/P2-04）；M7 落地其 v1.5 子集与地基。三块均用特性开关灰度、默认关。

### 11.A Agent ↔ Agent 对话与编排（A2A）

现状 gap：`agent_runtime.resolve_speaker` 每轮只选一个 speaker，Agent A 产出后控制权即回到用户，**没有 Agent→Agent 自动接力**。

| ID | 任务 | 关键模块/文件 | 验收 | 依赖 |
|---|---|---|---|---|
| M7-T01 | 编排器（有界多跳） | `orchestrator_svc`（扩展 `agent_runtime`）：Twin 作 leader，单轮内多跳 A→评估→B…；`max_hops` 默认 3 / 硬顶 6 + 防环（重复/循环检测）+ 总预算（轮数/token/成本） | 多 Agent 一轮内接力且不失控 | M2-T06 |
| M7-T02 | 转交协议 + 工具 | turn 增 `handoff{from,to,reason}`；新增 `handoff_to_agent` / `ask_agent` 工具；Twin 仲裁转交（防 A↔B 死循环，不盲从 Agent 的转交请求） | Agent 可请求转交、Twin 把关 | M7-T01 |
| M7-T03 | 落盘 + 透传 | `conversation_svc` 记录 handoff 链；`ws.py` 透传 handoff 事件（带 speaker） | 转交链可追溯、前端可渲染 | M7-T02 |
| M7-T04 | A2A 上下文 | `context_assembler_svc` 为被转交 Agent 注入"前序 Agent 产出摘要 + 转交理由"，避免重复劳动；访问控制仍按 by-user 不放宽 | 接手 Agent 有上下文且不越权 | M2-T04 |
| M7-T05 | 前端 A2A | 对话流转交卡（A→B）+ 参与者状态实时（忙/等待/完成）+ Twin 编排可视 | 多方接力现场可见 | M7-T03 |

### 11.B 工作空间任务编排（计划 / 步骤 / 推进 / DoD）

现状 gap：任务只有 6 态 + 参与者 + 会话 + 产物，**没有计划/步骤/完成判据**模型（原型卡片副行"现在：kyuubi_query（2/3）"尚无后端支撑）。

| ID | 任务 | 关键模块/文件 | 验收 | 依赖 |
|---|---|---|---|---|
| M7-T06 | 任务计划模型 | `task_svc` + `tasks/{tid}/plan.json`（steps[]：`title/owner_agent/status/result_ref/depends_on`，走 file_transaction）；6 态之上叠加步骤进度 | 步骤可建/推进/查询 | M2-T01 |
| M7-T07 | 计划编排 | Twin 据 `goal` 拆步骤→按 step 指派 Agent→完成推进下一步（由 M7-T01 编排器驱动）；step 失败接 `error_classifier` 建议重试/换 Agent | 计划自动推进、失败可复盘 | M7-T01,M7-T06 |
| M7-T08 | 目标 + DoD | task 增 `goal` + `definition_of_done`；完成判据校验（Twin 自检 + 用户确认）才可置 done | DoD 不满足不许完成 | M7-T06 |
| M7-T09 | 前端计划面板 | Workspace 计划面板（步骤清单 + 当前步 + 进度 + 每步产物入口）；卡片状态副行真实绑定"当前步" | 与原型"现在：X（2/3）"一致 | M7-T06 |

### 11.C Agent 主动性（受治理约束的 proactivity）

现状 gap：运行时纯请求-响应（必须用户发言才触发一轮）；doc01「Twin 主动发言」目前只是 UI 概念，**无后端主动触发机制**。

| ID | 任务 | 关键模块/文件 | 验收 | 依赖 |
|---|---|---|---|---|
| M7-T10 | 回合后主动续接 | 一轮结束后 Twin 评估是否自驱下一步（推进/提议/请求确认），在预算与治理内执行；`IDW_AUTOSTEP_ENABLED` 默认关，高风险仍走 HITL | 开启后能自推进、绝不越权 | M7-T01 |
| M7-T11 | 主动提议队列 | Twin/Agent 主动产出 proposal（下一步/补查/记忆/Skill）进"建议/待确认"队列，**不直接执行**；前端 Twin Dock + 对话流主动卡（对齐 doc01「Twin 主动发言」） | 主动建议可见、可裁决 | M3-T03 |
| M7-T12 | 触发器（Autopilots v1 子集） | `trigger_svc`：手动 / 单次定时(cron) / webhook → 自动建任务并派发；触发同样走治理 + 审计 + 预算；`IDW_TRIGGERS_ENABLED` 默认关 | 触发建任务、全程可审计 | M7-T07 |
| M7-T13 | 巡检/盯盘（可选） | Agent 周期检查指定数据/产物，异常时主动建待确认项（如"DAU 跌破阈值→建归因任务"） | 阈值触发提议 | M7-T12 |
| M7-T14 | 主动性护栏 | 全局速率/预算上限 + 防打扰（静默时段/频次）+ 一键关闭 + 全程审计；防"主动失控" | 护栏生效、可一键停 | M4-T02 |

### 11.D 设计要点 / 新增决策

- **D-15 A2A 编排**：v1.5 仍以 Twin 为唯一 leader（不引入 Agent 对等自由对话），多跳必须**有界 + 防环 + 预算 + 治理**；Squad（多 leader / 小队）仍留 P2-03。
- **D-16 主动性边界**：主动只到"提议 / 请求确认"，**绝不替用户做最终高风险决策**（呼应 agent.md「不可越权边界」）；自驱执行仅限低风险且开关开启，高风险一律进 HITL。
- **D-17 任务计划即真相源**：`plan.json` 走 G3 文件 + `file_transaction`；步骤状态变更落审计。任务级 6 态与步骤级状态正交，卡片副行取"当前步"。
- **特性开关**（默认关，灰度）：`IDW_A2A_ENABLED`（多跳编排）/ `IDW_AUTOSTEP_ENABLED`（回合后自驱）/ `IDW_TRIGGERS_ENABLED`（触发器）。
- **收口**：M7 结束 `pytest -q` + `tsc --noEmit` 全绿；重点测编排防环/预算（M7-T01）、DoD 门控（M7-T08）、主动性护栏与一键停（M7-T14）。

## 12. 二期（v1 后）

| ID | 任务 | 说明 |
|---|---|---|
| P2-01 | 本机 daemon/Runtime | CLI 探测 + 驱动本机 Claude Code/Cursor + 实时监控（= TokenWisdom Mac Local Runtime） |
| P2-02 ⭐ | 跨用户 Twin 协作 | `grant_svc` + scoped grant + 访客 Twin 沙箱 + 记忆回流 + 双方审计 |
| P2-03 | Squads | Agent 小队 + leader 自动路由（在 M7 有界多跳编排之上引入多 leader / 小队） |
| P2-04 | Autopilots | cron/webhook/手动触发自动建任务并派发（在 M7-T12 触发器子集之上做完整调度/编排） |

## 13. 风险与并行建议

- **关键路径**：M0→M1→M2 是主干，必须先稳；M3 紧随其后（记忆是平台内核）。
- **可并行**：M4（治理/后台）与 M6（自演进）可在 M2/M3 完成后并行推进。
- **高风险点**：ContextAssembler 访问控制（M2-T04）、记忆晋升原子性（M3-T07）、沙盒安全（M6-T02）——这三处要重点测试。
- **M7 高风险点**：A2A 编排防环/预算（M7-T01，防多 Agent 互相转交失控）、主动性护栏与一键停（M7-T14，防主动行为打扰/烧钱）、DoD 门控（M7-T08）——M7 三处必须重点测试 + 默认关开关灰度上线。
- **复用优先**：llm_gateway / 沙盒 / kyuubi / 飞书 / Agent 版本回滚 尽量直接搬 ICE，减少重写。
