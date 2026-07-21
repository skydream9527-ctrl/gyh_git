# TokenWisdom × ICE Workbench 整合分析

- 日期：2026-06-26
- 项目：TokenWisdom
- 参考项目：`/Users/mi/Desktop/ice_workbench_new`
- 阶段：产品方案与原型资产整合
- 状态：初版分析，待继续拆 PRD / IA / 技术方案

## 1. 结论先行

`ice_workbench_new` 可以作为 TokenWisdom 的 **Web 工作台与 Agent 工作空间原型底座**，但不能直接等同于 TokenWisdom。

ICE Workbench 的核心是“AI 数据工作流工作台”，已经具备任务、Agent、Skill、文件、知识库、对话、工具调用、HITL、定时任务、后台管理、用量统计和文件优先存储等完整能力。TokenWisdom 的核心是“个人 AI 分身”，需要在 ICE Workbench 的任务工作台基础上，进一步加入个人画像、长期记忆、外部专业执行 Agent、Mac Local Runtime、Sovereign Mode、跨端授权和 Agent 能力网络。

最适合的整合方式：

> 以 ICE Workbench 的 Web / Backend / Task Workspace 为起点，抽象出 TokenWisdom 的 Twin Mission Control、Mission、Room、Agent Hub、Knowledge Hub、Approval Center 和 Audit Log。

## 2. ICE Workbench 是什么

ICE Workbench v3 是一个面向数据产品场景的 AI 数据工作流工作台。

| 模块 | 当前能力 | 对 TokenWisdom 的价值 |
|---|---|---|
| Web Dashboard | 快速开始、我的任务、公共任务、Agent、Skill、文件、知识库入口 | 可改造成 Twin Mission Control |
| Workspace | 任务会话、文件面板、右侧执行面板、工具调用、HITL、计划确认 | 可改造成 Mission Room / 多方协作空间 |
| Agent 管理 | `agents/{agent_id}/agent.json` 定义 Agent 名称、范式、描述、技能 | 可扩展为 Agent Card / Agent Connector |
| Skill 系统 | `skills/` 目录 + `INDEX.md` + SKILL.md 指令 | 可作为 TokenWisdom Capability Library |
| Task 数据 | `tasks/{task_id}` 文件优先存储，包含 meta、workspace、conversations、files、tool_calls | 可映射为 Mission 数据模型 |
| User 数据 | `users/{user_id}` 包含 profile、settings、notifications、audit、task index | 可扩展为 Wisdom Twin Profile / Memory |
| 文件系统 | input/output/uploaded/imported/public 文件管理 | 可作为 Knowledge Assets 的基础 |
| WebSocket Runtime | 会话流式输出、工具调用、run events | 可用于实时展示分身执行过程 |
| HITL | 任务中的人工介入请求与 resolve 流程 | 可扩展为 Approval Center |
| Scheduled Tasks | 定时任务配置与运行记录 | 可扩展为 Autopilot / 长期代理任务 |
| Admin | Agent、Skill、文件、用户、用量、审计、诊断 | 可作为本地/高级用户控制台参考 |

## 3. 和 TokenWisdom 的关系

ICE Workbench 可以视为 TokenWisdom 的一个垂直版本：它围绕数据分析场景，把 Agent、Skill、文件、任务和对话整合到同一个工作台里。

TokenWisdom 要在此基础上做三层升级：

1. **从任务助手升级为数字分身**：中心对象不只是 Task，而是 Wisdom Twin；任务只是分身行动的一种表现。
2. **从内置领域 Agent 升级为 Agent Network**：不仅有数据分析 Agent，还能配置 Claude Code、Codex、Cursor、浏览器 Agent、文件 Agent、Life Ops Agent。
3. **从 Web 服务执行升级为本地主权执行**：Mac App 内置 Local Runtime，可以访问本机文件、终端、浏览器和专业执行 Agent。

## 4. 对象模型映射

| ICE Workbench 对象 | TokenWisdom 对象 | 迁移说明 |
|---|---|---|
| User | User | 保留账号体系，但增加多端设备、订阅、分身配置 |
| User Profile / Settings | Wisdom Twin Profile | 扩展为用户画像、偏好、目标、表达风格、授权默认值 |
| Task | Mission | Task 偏一次性任务，Mission 强调长期目标、状态、授权和复盘 |
| Workspace | Room / Mission Workspace | Workspace 可拆成工作空间和多方对话房间 |
| Agent | Tool Agent / External Agent / Twin Sub-agent | Agent 需要加连接方式、运行时、权限、能力卡、历史表现 |
| Skill | Capability / Tool Skill | Skill 系统可保留，但需要更丰富 metadata、依赖、互斥和优先级 |
| File | Knowledge Asset | 文件不仅是附件，还要参与长期记忆与知识地图 |
| Experience Card | Memory Candidate / Lesson | 经验卡可改造成待确认记忆与任务复盘沉淀 |
| Tool Call | Action / Tool Invocation | 直接映射到 TokenWisdom Action Audit |
| Run Event | Mission Timeline Event | 可作为分身执行过程可视化基础 |
| HITL Request | Approval Request | 可升级为跨 Web / Android / Mac 的审批中心 |
| Scheduled Task | Autopilot Mission | 可作为长期观察、日报、巡检、复盘任务 |
| Admin Usage | Runtime / Cost Monitor | 可用于 Agent 执行成本与 Token 成本追踪 |

## 5. 可直接借鉴的产品能力

### 5.1 Twin Mission Control

ICE Workbench 的 Dashboard 已经具备快速开始、任务列表、Agent 入口、公共资源、知识库入口。TokenWisdom 可以把它改造成融合式首页：

- 顶部：Twin Status、Safe / Sovereign Mode、Kill Switch
- 第一屏：Today with My Twin
- 第二屏：Mission Queue
- 第三屏：Dev / Knowledge / AI Tools / Life Ops 四大 Hub
- 第四屏：最近 Rooms、外部 Agent 协作记录、待审批事项

### 5.2 Mission Room

ICE Workbench 的 Workspace 已经有 Chat Area、Sidebar、Right Panel、文件面板、工具调用卡、计划确认、HITL。TokenWisdom 可以将其升级为 Mission Room：

- 当前用户 + Wisdom Twin + 外部 Agent 的多方对话空间
- 文件、知识、Agent、工具调用和审计记录在同一上下文中展示
- 支持任务计划、执行过程、阻塞、审批、产出物和复盘

### 5.3 Agent Hub

ICE Workbench 的 `agents/` 目录和 Admin Agent 页面适合作为 Agent Hub 的原型，但 TokenWisdom 需要扩展：

| 现有字段 | 需要新增 |
|---|---|
| id / name / description / paradigm / skills / model | connector_type、runtime、permission_policy、capability_card、risk_level、health、cost、success_rate、best_prompts、failure_modes |

第一批 TokenWisdom 外部专业执行 Agent：Claude Code、Codex、Cursor、Aider、OpenCode。

### 5.4 Knowledge Hub

ICE Workbench 已有 `files/`、公共文件、任务文件、知识库和文件导入机制。TokenWisdom 可以扩展成 Knowledge Hub：

- 用户上传资料、项目文件、本地文件夹索引
- 文件摘要、知识条目、个人事实、偏好提取
- 待确认记忆队列
- 按 Workspace / Mission / Agent 作用域隔离

### 5.5 Approval Center

ICE Workbench 已有 HITL 请求、计划确认、工具失败回灌。TokenWisdom 可以升级为跨端审批中心：

- Web：详细审查任务包、diff、文件和审计
- Android：快速审批、拒绝、补充说明
- Mac：本机敏感操作二次确认

### 5.6 Autopilot / 长期代理任务

ICE Workbench 的 Scheduled Tasks 可作为 Autopilot 起点。TokenWisdom 可以用于：

- 每日分身日报
- 定时整理文件夹
- 定期检查项目状态
- 定时运行 Coding Agent 巡检
- 周复盘与记忆更新

## 6. 可复用的技术资产

| 技术资产 | 当前实现 | TokenWisdom 复用方式 |
|---|---|---|
| FastAPI 后端 | `backend/app` | 可作为 Web API 与 Cloud Orchestrator 基线 |
| React + Vite 前端 | `frontend/src` | 可作为 Web 工作台原型基础 |
| 文件优先存储 | `users/`、`tasks/`、`agents/`、`skills/`、`files/` | 适合 Local-first / 可迁移 / 可审计数据结构 |
| WebSocket 对话 | `/ws/conversations/{conversation_id}` | 支持实时流式执行和工具调用展示 |
| Tool Call 记录 | `tool_calls/*.jsonl` | 可直接用于 Action Audit |
| Run Events | `run_events/*.jsonl` | 可用于 Mission Timeline |
| HITL 请求 | `/tasks/{id}/hitl` | 可升级为 Approval Request |
| 文件导入 / 文件面板 | `/files/*` | 可升级为 Knowledge Asset 管理 |
| Agent Prompt Builder | 分层注入身份、规则、Memory、Task State、Skills、Tools | 可扩展为 Wisdom Twin Prompt Builder |
| Memory 机制 | user memory / agent memory / task state | 可扩展为全局用户记忆、空间记忆、Agent 记忆、任务记忆 |
| Usage / Audit | admin usage、user audit | 可扩展为成本、权限、行为审计中心 |

## 7. 当前项目已暴露的改进点，也适用于 TokenWisdom

`ICE Workbench Agent 改进方向讨论稿` 中的开放问题，对 TokenWisdom 很关键：

| 问题 | 对 TokenWisdom 的影响 | 建议 |
|---|---|---|
| Skill metadata 太薄 | Agent Hub 难以准确选择能力 | Skill / Capability 增加 category、dependencies、priority、mutually_exclusive_with |
| 子 Agent 串行 | 多任务和多 Agent 协作效率低 | 增加并行 spawn / batch execution |
| 子 Agent 失败不透明 | 分身无法判断是否重试、换 Agent、还是问用户 | 返回 files_written、error_type、recoverable、suggested_action |
| 工具错误结构不够 | LLM 只能猜测错误根因 | 统一结构化错误模型 |
| Memory 写入风险 | 可能写入敏感信息、过期规则、冲突偏好 | 增加敏感扫描、去重、created_at、updated_at、last_verified_at |
| Memory 检索朴素 | 长期分身会逐渐记忆膨胀 | 先做时间衰减和 description 检索，中期做语义检索 |
| Retry 缺失 | 临时网络/CLI 错误直接失败 | executor 层按 recoverable 自动重试 |

这些问题如果在 TokenWisdom 初期就抽象好，会比后期补更稳。

## 8. TokenWisdom 的推荐整合路线

### Phase 0：资产复用与概念改名

- `Dashboard` → `Twin Mission Control`
- `Task` → `Mission`
- `Workspace` → `Room / Mission Workspace`
- `Agent` → `Tool Agent / External Agent`
- `Skill` → `Capability`
- `Experience Card` → `Memory Candidate / Lesson`
- `Scheduled Task` → `Autopilot Mission`

### Phase 1：Web 工作台原型

基于 ICE Workbench 前端改造 TokenWisdom Web：

- 首页：分身状态 + Mission Queue + 四大 Hub
- Mission Room：聊天、文件、Agent、工具调用、审批、Timeline
- Agent Hub：内置 Agent + 外部专业执行 Agent 能力卡
- Knowledge Hub：文件、知识库、待确认记忆
- Audit：行为日志、权限日志、工具调用日志

### Phase 2：Twin Core 后端模型

在现有 User / Task / Agent 之外新增或重命名：

- `twin_profile.json`
- `memory/`：global / workspace / agent / mission
- `missions/{mission_id}/`
- `agent_cards/{agent_id}.json`
- `permissions/policies.json`
- `audit/actions/{YYYY-MM}.jsonl`

### Phase 3：Mac Local Runtime

借鉴 ICE Workbench 文件优先与 runtime 记录方式，但新增本机执行层：

- 本地项目绑定
- Claude Code / Codex / Cursor 检测与调用
- 本地文件索引与学习
- 终端命令执行审计
- Secret Boundary
- Kill Switch
- 本机 action log 与云端同步摘要

### Phase 4：Android 审批端

安卓端不先做完整工作台，优先做：

- 分身对话
- 审批中心
- 今日汇报
- 任务状态
- 记忆确认队列

## 9. 需要避免直接照搬的地方

| ICE Workbench 特征 | 为什么不能直接照搬 | TokenWisdom 应该怎么改 |
|---|---|---|
| 面向数据产品工作流 | TokenWisdom 是通用个人分身 | 保留框架，替换业务范式 |
| Task 是中心 | 分身产品中用户画像和长期目标更重要 | Mission 从属于 Wisdom Twin |
| Admin 后台较重 | 个人用户不需要复杂团队管理 | 简化为 Settings / Advanced / Developer Mode |
| Agent 多为内置领域 Agent | TokenWisdom 要接外部专业 Agent | 增加 Agent Connector 与 Agent Card |
| Web 服务执行为主 | TokenWisdom 强依赖 Mac 本地执行 | 加 Local Runtime / Desktop Daemon |
| Memory 粒度偏项目内部 | TokenWisdom 需要长期个人记忆 | 加全局记忆、确认队列、偏好版本化 |

## 10. 对 TokenWisdom MVP 的影响

整合 ICE Workbench 后，TokenWisdom MVP 可以更具体地定义为：

> 一个基于 Web 工作台 + Mac Local Runtime 的个人 AI 分身原型。Web 端承接 Mission、Room、Agent Hub、Knowledge Hub 和审批审计；Mac 端承接本地文件学习和专业执行 Agent 调用；Android 端先做移动审批与分身日报。

MVP 建议优先级：

| 优先级 | 能力 | 来源 / 参考 |
|---|---|---|
| P0 | Web Mission Control | ICE Dashboard 改造 |
| P0 | Mission Room | ICE Workspace 改造 |
| P0 | Agent Hub | ICE agents + Multica Agent Card 思路 |
| P0 | Knowledge Hub | ICE files / kb / memory 改造 |
| P0 | Approval Center | ICE HITL + PlanApproval 改造 |
| P1 | Mac Local Runtime | 新增，借鉴 Multica Local Daemon |
| P1 | Claude Code / Codex / Cursor Connector | 新增 |
| P1 | Action Audit | ICE tool_calls / run_events 扩展 |
| P2 | Android 审批端 | 新增 |
| P2 | Sovereign Mode | 新增高级模式 |

## 11. 下一步建议

1. 基于 ICE Workbench 画一版 TokenWisdom IA：页面、导航、对象、路由。
2. 把现有 `Task` 数据结构改写成 `Mission` 数据结构草案。
3. 设计 `Agent Card + Connector + Runtime` 三层模型。
4. 设计 `Wisdom Twin Memory`：全局、空间、Agent、Mission、待确认队列。
5. 设计 Mac Local Runtime 的本地数据目录和云端同步边界。
6. 从 ICE Workbench 前端中挑选可复用组件：Dashboard、Workspace、MessageList、ToolCallCard、PlanApprovalModal、HumanInterventionCard、ExecutionCockpit、AdminAgents、AdminSkills、AdminFiles。

