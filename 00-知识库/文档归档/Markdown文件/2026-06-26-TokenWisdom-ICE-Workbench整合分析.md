# TokenWisdom × ICE Workbench 整合分析

- 日期：2026-06-26
- 项目：TokenWisdom
- 参考项目：`/Users/mi/Desktop/ice_workbench_new`
- 原始项目文档：`01-业务项目/TokenWisdom/2026-06-26-TokenWisdom-ICE-Workbench整合分析.md`
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

## 5. 推荐整合路线

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

安卓端不先做完整工作台，优先做分身对话、审批中心、今日汇报、任务状态和记忆确认队列。

## 6. 对 TokenWisdom MVP 的影响

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

## 7. 下一步建议

1. 基于 ICE Workbench 画一版 TokenWisdom IA：页面、导航、对象、路由。
2. 把现有 `Task` 数据结构改写成 `Mission` 数据结构草案。
3. 设计 `Agent Card + Connector + Runtime` 三层模型。
4. 设计 `Wisdom Twin Memory`：全局、空间、Agent、Mission、待确认队列。
5. 设计 Mac Local Runtime 的本地数据目录和云端同步边界。
6. 从 ICE Workbench 前端中挑选可复用组件：Dashboard、Workspace、MessageList、ToolCallCard、PlanApprovalModal、HumanInterventionCard、ExecutionCockpit、AdminAgents、AdminSkills、AdminFiles。

