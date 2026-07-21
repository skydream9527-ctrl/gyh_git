# TokenWisdom 产品 PRD v1

- 日期：2026-06-27
- 项目：TokenWisdom
- 文档类型：产品 PRD
- 当前阶段：概念收敛 / 原型设计 / MVP 定义
- 目标读者：产品、设计、前端、后端、桌面端、移动端、Agent Runtime 开发者
- 关联资料：`2026-06-26-TokenWisdom-产品方案讨论记录.md`、`2026-06-26-TokenWisdom-ICE-Workbench整合分析.md`

## 1. 一句话定位

TokenWisdom 是个人工作者的半自主 AI 分身系统：它长期学习用户的目标、文件、偏好、工作上下文和工具使用方式，并代表用户与外部专业执行 Agent、网页 Agent、平台工具进行协作，帮助用户发现、学习、组合、调用和复盘各类 AI 工具。

更口语化地说：

> TokenWisdom 是我的 AI 分身，专门替我和其他 AI、平台、工具打交道，并把过程、结果和经验沉淀回来。

## 2. 背景与问题

### 2.1 背景

AI 工具和专业 Agent 正在快速分化：用户既要使用通用对话模型，也要使用 Claude Code、Codex、Cursor、数据分析 Agent、浏览器 Agent、PPT Agent、自动化平台等专业执行工具。单个用户面对的是一个越来越复杂的 Agent 生态，而不是单一助手。

### 2.2 用户痛点

| 痛点 | 说明 | 影响 |
|---|---|---|
| 工具太多 | 不同 Agent 能力、入口、上下文格式和限制不同 | 用户难以判断该用哪个工具 |
| 上下文重复 | 每次调用外部 Agent 都要重新说明背景、目标、偏好、文件 | 低效且容易遗漏关键约束 |
| 结果难沉淀 | 工具对话、文件、报告、经验分散在多个平台 | 很难复用历史成果和经验 |
| 自动化风险高 | 代码、文件、邮件、日程、付费调用等动作涉及权限 | 用户需要确认边界和追责机制 |
| 长期代理缺失 | 普通聊天助手不持续观察目标，也不会主动复盘 | 无法形成“越来越懂我”的分身 |

### 2.3 产品机会

TokenWisdom 不直接替代所有专业 Agent，而是成为用户和 Agent 世界之间的个人分身层：理解用户、组织上下文、调度 Agent、请求确认、审计行为、沉淀记忆。

## 3. 产品目标与非目标

### 3.1 产品目标

| 编号 | 目标 | 衡量方式 |
|---|---|---|
| GOAL-001 | 建立用户专属 Wisdom Twin | 完成注册、画像、文件学习、偏好确认 |
| GOAL-002 | 提供清晰的 Workstation 总控台 | 用户能看到运行任务、当前对话任务、最近任务、核心产物 |
| GOAL-003 | 支持具体任务进入 Workspace | 数据分析任务进入 Data Analysis Workspace，普通任务进入 General Workspace |
| GOAL-004 | 支持 User → Twin → Agents 协作 | Twin 可参与其他 Agent 对话，并生成建议、任务包、确认请求 |
| GOAL-005 | 建立权限与审计闭环 | 高风险动作必须用户确认，所有执行动作可追溯 |
| GOAL-006 | 形成可沉淀的记忆和产物 | 文档、报告、Agent Card、Memory Candidate 可管理、确认、复用 |

### 3.2 非目标

| 编号 | 非目标 | 说明 |
|---|---|---|
| NON-001 | 不在首版做完全无人值守执行 | 半自主优先，关键动作由用户确认 |
| NON-002 | 不在首版做企业级团队协作 | 首期面向个人工作者，不做复杂组织权限 |
| NON-003 | 不替代 Claude Code / Codex / Cursor | TokenWisdom 是调度、上下文和权限层，不是全部执行层 |
| NON-004 | 不默认读取全部本机敏感文件 | 本地执行也需要范围、规则、审计和暂停机制 |
| NON-005 | 不一开始覆盖所有生活事务自动化 | 邮件、消息、日程先做建议和审批，逐步开放执行 |

## 4. 目标用户

### 4.1 首期用户

个人工作者、AI 工具重度使用者、独立创业者、产品经理、开发者、研究型创作者、数据分析师。

### 4.2 典型用户画像

| 用户 | 高频任务 | TokenWisdom 价值 |
|---|---|---|
| 产品经理 / 创业者 | 调研、PRD、竞品、路线图、任务推进 | 帮用户组织资料、调用外部 Agent、沉淀产品判断 |
| 开发者 / 自动化玩家 | 用 Claude Code、Codex、Cursor 修改项目 | 生成任务包、限定范围、审计执行、复盘结果 |
| 数据分析师 / 运营 | 查数、归因、报告、定时巡检 | 协调数据 Agent，生成分析视图与报告草稿 |
| 研究型创作者 | 资料收集、知识整理、长文写作 | 建立知识库，复用历史对话和素材 |

## 5. 核心概念

| 概念 | 定义 | 产品表现 |
|---|---|---|
| User | 真实用户，拥有最终确认权 | 账号、设备、权限、确认动作 |
| Wisdom Twin | 用户的数字分身，长期学习用户并代表用户沟通 | 全局右侧对话框、建议区、确认区、管理页 |
| Workstation | 平台最外层主页，用于展示正在运行的内容和核心产物 | 定时任务、当前对话任务、最近任务、核心产物 |
| Workspace | 点击某个任务、文档或 Agent 后进入的具体工作页面 | Data Analysis Workspace / General Workspace |
| Data Analysis Workspace | 数据分析任务工作台，核心展示分析视图和对话窗口 | 指标、图表、结论、分析 Agent 对话 |
| General Workspace | 普通任务工作台，核心展示文档和对话窗口 | PRD、报告、方案、执行对话 |
| Agent / Tool Agent | 外部或平台内专业执行 Agent | Agent Hub、Agent Card、Connector |
| Mission | 可被 Twin 计划、调度、跟踪和复盘的任务 | 一次对话任务、定时任务、长期任务 |
| Artifact | 工作产物 | 报告、文档、代码变更、表格、图表、Agent Card |
| Memory Candidate | 候选记忆，需要用户确认后进入长期记忆 | “用户偏好用表格表达”等 |
| Approval | 用户确认动作 | 写文件、上传上下文、发消息、花钱、固化记忆 |

## 6. 产品原则

1. **User to Agent to Agents**：用户面对自己的 Wisdom Twin，Twin 再面对其他工具 Agent。
2. **Twin 常驻**：右侧 Wisdom Twin 对话框在所有页面长期存在，负责上下文、建议和确认。
3. **Twin 参与而不越权**：Twin 可以讨论、请求、草拟、协调，但高风险动作由用户最终确认。
4. **工作台聚焦产出**：具体 Workspace 核心只展示工作产物与对话窗口，其他状态、文件、Agent、历史对话通过按钮和抽屉隐藏。
5. **Workstation 是总控台**：Workstation 展示运行内容，不承接所有细节操作；点击后进入具体文档或 Workspace。
6. **每次工作都沉淀**：任务结果、经验、偏好、Agent 使用方法都要形成可复用资产。
7. **权限逐步开放**：从观察、建议、代聊，到草拟执行、本机执行、Sovereign Mode 分阶段开启。

## 7. 产品信息架构

```text
TokenWisdom
├── Workstation
│   ├── 定时任务
│   ├── 当前一次对话任务
│   ├── 最近任务
│   └── 核心产物
├── New Mission
│   ├── 任务输入
│   ├── Twin 计划
│   ├── 推荐 Agent
│   └── 权限预览
├── Workspaces
│   ├── Data Analysis Workspace
│   │   ├── 分析视图 / 报告草稿
│   │   ├── 用户 + Twin + Data Agent 对话
│   │   └── 隐藏抽屉：状态 / Agent / 文件 / 对话 / 时间线
│   └── General Workspace
│       ├── 文档 / 方案 / 任务包
│       ├── 用户 + Twin + 执行 Agent 对话
│       └── 隐藏抽屉：状态 / Agent / 文件 / 对话 / 时间线
├── Agent Hub
│   ├── 平台内置工具 Agent
│   ├── 外部专业执行 Agent
│   ├── Agent Card
│   └── Connector / Runtime 状态
├── History
│   ├── 历史任务
│   ├── 执行记录
│   └── 复盘结论
├── Knowledge & Artifacts
│   ├── 历史文档
│   ├── 报告 / 总结
│   ├── 文件学习结果
│   └── Memory Candidate
├── Public Content
│   ├── 公共 Agent Card
│   ├── 公共任务模板
│   └── 公共工作流
├── Twin Manager
│   ├── 分身画像
│   ├── 记忆文件
│   ├── Agent MD 文件
│   ├── API Token 消耗
│   └── 权限策略
└── Approvals & Audit
    ├── 待确认动作
    ├── 权限日志
    ├── 工具调用日志
    └── 成本与风险审计
```

## 8. 核心用户旅程

### 8.1 注册与冷启动

1. 用户注册 TokenWisdom。
2. 系统通过对话建立 Wisdom Twin 初始画像。
3. 用户上传文件或在 Mac App 选择本地文件夹。
4. Twin 生成“我对你的理解”和候选记忆。
5. 用户确认哪些记忆可固化。
6. 用户连接第一个外部 Agent。
7. Twin 冷启动采访外部 Agent，生成 Agent Card。

### 8.2 从 Workstation 进入任务

1. 用户打开 Workstation。
2. 页面展示定时任务、当前对话任务、最近任务、核心产物。
3. 用户点击“DAU 下滑归因分析”。
4. 系统进入 Data Analysis Workspace。
5. 主区域展示分析报告草稿和图表，右侧常驻 Wisdom Twin。
6. 用户确认补查口径或允许调用数据 Agent。
7. Twin 协调 Data Agent 查询并更新报告。
8. 任务完成后沉淀报告、经验和 Memory Candidate。

### 8.3 普通文档任务

1. 用户在 Workstation 点击“TokenWisdom PRD 草稿”。
2. 系统进入 General Workspace。
3. 左侧主区域展示文档正文，右侧工作区展示用户 + Twin + Codex 的对话。
4. Twin 把用户口头需求整理成文档结构。
5. 用户确认后由 Codex / 文档 Agent 生成新版文档。
6. Twin 总结变更、风险和下一步。

### 8.4 外部专业执行 Agent 调用

1. 用户选择 Claude Code / Codex / Cursor。
2. Twin 根据任务生成 Execution Brief。
3. 页面展示可调用范围、文件范围、命令权限、成本预估。
4. 用户确认后 Mac Local Runtime 调用对应本地 Agent。
5. 执行结果回传，包括日志、文件变更、测试结果、失败原因。
6. Twin 总结结果并请求用户采纳或回滚。

## 9. 功能需求

### 9.1 Workstation

| 需求 ID | 需求 | 优先级 | 验收标准 |
|---|---|---|---|
| REQ-WORKSTATION-001 | Workstation 必须作为最外层主页 | P0 | 登录后默认进入，页面标题明确为 Workstation |
| REQ-WORKSTATION-002 | 展示定时任务 | P0 | 可看到任务名称、频率、状态、下一次运行时间、入口 |
| REQ-WORKSTATION-003 | 展示当前一次对话的任务 | P0 | 可看到当前对话派生任务、参与 Agent、待确认项 |
| REQ-WORKSTATION-004 | 展示最近任务 | P0 | 至少展示最近 5 个 Mission，支持进入 Workspace |
| REQ-WORKSTATION-005 | 展示核心产物 | P0 | 报告、文档、总结、Agent Card 可点击打开 |
| REQ-WORKSTATION-006 | 展示总体总结 | P1 | Twin 自动生成今日进展、风险、建议下一步 |

### 9.2 Wisdom Twin 常驻对话框

| 需求 ID | 需求 | 优先级 | 验收标准 |
|---|---|---|---|
| REQ-TWIN-001 | 所有 Web 页面右侧常驻 Wisdom Twin | P0 | 页面切换时对话框不消失，并显示当前页面上下文 |
| REQ-TWIN-002 | Twin 可展示建议 | P0 | 右侧下方有建议卡片，支持继续计划、稍后、生成任务 |
| REQ-TWIN-003 | Twin 可展示待确认动作 | P0 | 高风险动作进入确认卡片，支持确认、修改、拒绝 |
| REQ-TWIN-004 | Twin 可参与其他 Agent 对话 | P0 | Workspace 对话中存在 User、Wisdom Twin、Tool Agent 三方角色 |
| REQ-TWIN-005 | Twin 不可默认最终确认高风险动作 | P0 | 写文件、发消息、付费调用等必须显示用户确认按钮 |

### 9.3 Data Analysis Workspace

| 需求 ID | 需求 | 优先级 | 验收标准 |
|---|---|---|---|
| REQ-DATA-001 | 数据分析工作台核心展示分析产物 | P0 | 主区域展示指标、图表、发现、报告草稿 |
| REQ-DATA-002 | 数据分析工作台核心展示对话窗口 | P0 | 用户、Twin、Data Agent 对话并列或分栏展示 |
| REQ-DATA-003 | 非核心信息通过抽屉隐藏 | P0 | 状态、Agent、文件、历史对话、时间线可通过按钮打开 |
| REQ-DATA-004 | 支持用户确认补查和发布 | P1 | 报告发布或补查数据需要确认卡片 |
| REQ-DATA-005 | 支持结果沉淀为报告与记忆候选 | P1 | 完成后生成 Artifact 和 Memory Candidate |

### 9.4 General Workspace

| 需求 ID | 需求 | 优先级 | 验收标准 |
|---|---|---|---|
| REQ-GENERAL-001 | 普通工作台核心展示文档 | P0 | 主区域展示 PRD、方案、报告、任务包等正文 |
| REQ-GENERAL-002 | 普通工作台核心展示对话窗口 | P0 | 用户、Twin、执行 Agent 对话可见 |
| REQ-GENERAL-003 | 支持文档版本与产物保存 | P1 | 可看到版本号、最后编辑、保存为 Artifact |
| REQ-GENERAL-004 | 支持调用 Codex / Claude Code / Cursor | P1 | 可生成执行任务包并请求用户确认 |

### 9.5 Agent Hub

| 需求 ID | 需求 | 优先级 | 验收标准 |
|---|---|---|---|
| REQ-AGENT-001 | 支持平台内置工具 Agent | P0 | 文件学习、数据分析、浏览器观察等 Agent 有能力卡 |
| REQ-AGENT-002 | 支持外部专业执行 Agent | P0 | Claude Code、Codex、Cursor 可作为首批外部 Agent 展示 |
| REQ-AGENT-003 | 支持 Agent 冷启动采访 | P1 | Twin 可向新 Agent 提问并生成 Agent Card |
| REQ-AGENT-004 | Agent Card 展示能力、输入、输出、风险、最佳用法 | P0 | 每张卡片包含能力、连接状态、权限级别、历史表现 |
| REQ-AGENT-005 | 支持 Connector / Runtime 状态 | P1 | 可看到 API、CLI、浏览器插件、本地 Runtime 是否可用 |

### 9.6 Twin Manager

| 需求 ID | 需求 | 优先级 | 验收标准 |
|---|---|---|---|
| REQ-MANAGER-001 | 管理 Wisdom Twin 画像 | P0 | 可查看目标、偏好、风格、限制、成熟度 |
| REQ-MANAGER-002 | 管理记忆文件和 Memory Candidate | P0 | 可确认、编辑、删除、冻结记忆 |
| REQ-MANAGER-003 | 管理 Agent MD 文件 | P1 | 可查看每个 Agent 的使用说明、约束、历史复盘 |
| REQ-MANAGER-004 | 查看 API Token 和成本消耗 | P0 | 按 Agent、任务、时间展示消耗 |
| REQ-MANAGER-005 | 管理权限策略 | P0 | L0-L5 权限可配置，并有高风险动作例外规则 |

### 9.7 Approvals & Audit

| 需求 ID | 需求 | 优先级 | 验收标准 |
|---|---|---|---|
| REQ-AUDIT-001 | 展示待确认动作 | P0 | 文件写入、上下文上传、命令执行、消息发送、付费调用进入队列 |
| REQ-AUDIT-002 | 记录行动审计 | P0 | 每次工具调用包含时间、发起者、权限、输入摘要、输出摘要 |
| REQ-AUDIT-003 | 支持一键暂停 | P0 | 用户可暂停全部本地执行和外部调用 |
| REQ-AUDIT-004 | 支持失败复盘 | P1 | 失败任务记录 error_type、recoverable、suggested_action |

### 9.8 跨端形态

| 需求 ID | 需求 | 优先级 | 验收标准 |
|---|---|---|---|
| REQ-DEVICE-001 | Web 控制台负责控制和编排 | P0 | 可管理任务、Agent、文件、记忆、审批 |
| REQ-DEVICE-002 | Mac App 负责本地文件和本地执行 | P1 | 可选择文件夹、调用 CLI Agent、同步执行摘要 |
| REQ-DEVICE-003 | Android 负责移动审批和日报 | P2 | 可查看待确认、任务状态和 Twin 日报 |
| REQ-DEVICE-004 | 浏览器插件负责网页观察和网页 Agent 辅助 | P1 | 可保存 AI 对话、识别工具能力、总结使用习惯 |

## 10. 权限模型

| 等级 | 名称 | Twin 可做 | 必须用户确认 |
|---|---|---|---|
| L0 | Observe | 读取用户明确提供的对话和文件摘要 | 任何外部调用 |
| L1 | Suggest | 生成建议、计划、任务拆解 | 执行工具、写文件、上传上下文 |
| L2 | Delegate Draft | 与外部 Agent 草拟对话、生成任务包 | 发送到外部平台、调用付费 API |
| L3 | Request Execution | 请求调用本地 Agent 或平台工具 | 写文件、运行命令、联网、安装依赖 |
| L4 | Bounded Autopilot | 在用户设定边界内自动执行低风险任务 | 高风险操作、越界文件、敏感上下文 |
| L5 | Sovereign Mode | 本机范围内执行长期代理任务 | 删除文件、发消息、提交代码、付费、读取密钥 |

### 10.1 高风险动作清单

- 写入或删除本机文件。
- 运行终端命令。
- 调用 Claude Code / Codex / Cursor 修改项目。
- 上传用户文件或大段上下文到外部服务。
- 发送邮件、消息、评论、日程邀请。
- 产生费用的 API 或平台调用。
- 将候选记忆固化为长期记忆。
- 读取密钥、证书、`.env`、私人文档。

## 11. Agent-to-Agent 协作模型

```text
User
  ↓ 目标、偏好、确认
Wisdom Twin
  ↓ 组织上下文、生成任务包、发起请求、复盘
Agent Room
  ├── Claude Code / Codex / Cursor
  ├── Data Agent / SQL Agent
  ├── Browser Agent
  ├── File & Knowledge Agent
  └── Life Ops Agent
```

### 11.1 Twin 的职责

1. 理解用户目标和边界。
2. 判断适合的 Agent 或工具组合。
3. 生成标准化任务包。
4. 与外部 Agent 对话摸清能力和使用方式。
5. 追踪执行进度和失败原因。
6. 向用户提出确认请求。
7. 总结结果并沉淀记忆。

### 11.2 外部 Agent 的职责

外部 Agent 负责专业执行，例如代码修改、数据查询、网页操作、文件整理、PPT 生成。外部 Agent 不拥有用户最终确认权。

## 12. 数据与对象模型

| 对象 | 关键字段 |
|---|---|
| User | id、name、devices、subscription、global_settings |
| WisdomTwin | id、user_id、name、profile、goals、style、permission_level、maturity_score |
| Mission | id、title、type、status、priority、source、workspace_type、agents、artifacts、approvals |
| Workspace | id、mission_id、type、layout、active_artifact、conversation_id、drawer_state |
| AgentCard | id、name、category、connector_type、capabilities、input_schema、output_schema、risks、best_practices |
| Artifact | id、type、title、source_mission、version、status、content_ref、summary |
| Memory | id、scope、content、confidence、source、created_at、last_verified_at、status |
| Approval | id、risk_level、action_type、requester、summary、payload_ref、status、decided_by |
| AuditEvent | id、actor、action、tool、permission_level、input_summary、output_summary、timestamp |

## 13. MVP 范围

### 13.1 P0 范围

- Web Workstation 首页。
- Data Analysis Workspace 与 General Workspace。
- Wisdom Twin 常驻对话框、建议区、确认区。
- Agent Hub 基础能力卡。
- Knowledge & Artifacts 基础管理。
- Twin Manager 基础画像、记忆、成本、权限管理。
- Approval & Audit 基础队列。
- 首批 Agent：Codex、Claude Code、Cursor、Data Agent、Browser Agent、File Agent。

### 13.2 P1 范围

- Mac Local Runtime 原型。
- 本地文件夹选择与摘要学习。
- Claude Code / Codex / Cursor 本地调用链路。
- 浏览器插件保存 AI 对话。
- Agent 冷启动采访与 Agent Card 自动生成。

### 13.3 P2 范围

- Android 审批端。
- Sovereign Mode 实验模式。
- 公共 Agent Card / 公共任务模板。
- 长期定时 Autopilot Mission。

## 14. 页面级验收标准

| 页面 | 必须包含 |
|---|---|
| Workstation | 定时任务、当前对话任务、最近任务、核心产物、今日总结、右侧 Twin |
| New Mission | 输入任务、推荐路线、Agent 组合、权限预览、确认执行 |
| Data Workspace | 分析报告、指标图表、分析发现、对话窗口、隐藏抽屉、右侧 Twin |
| General Workspace | 文档正文、对话窗口、版本信息、隐藏抽屉、右侧 Twin |
| Agent Hub | Agent Card、连接状态、能力、风险、适用场景、调用入口 |
| History | 历史任务、状态、结果、复盘、可再次打开 |
| Knowledge & Artifacts | 文档、报告、总结、记忆候选、筛选与打开 |
| Public Content | 公共 Agent Card、公共任务模板、公共工作流 |
| Twin Manager | 分身画像、记忆文件、Agent MD、Token 消耗、权限策略 |
| Approvals & Audit | 待确认动作、权限日志、工具调用日志、风险等级 |

## 15. 成功指标

| 指标 | 目标 |
|---|---|
| Activation | 新用户 24 小时内完成分身创建 + 至少 1 个文件学习 + 1 个 Agent 连接 |
| First Mission Success | 首个 Mission 完成率 ≥ 60% |
| Approval Clarity | 用户对确认请求的理解率 ≥ 80% |
| Artifact Reuse | 7 日内历史产物被再次打开或复用比例 ≥ 30% |
| Memory Acceptance | Memory Candidate 被确认比例 ≥ 40% |
| Agent Card Coverage | 已使用 Agent 生成 Agent Card 比例 ≥ 70% |
| Retention | 首批个人工作者 7 日留存 ≥ 35% |

## 16. 风险与缓解

| 风险 | 影响 | 缓解 |
|---|---|---|
| 权限风险 | 分身越权执行或误操作 | 分级权限、确认卡、审计、一键暂停 |
| 隐私风险 | 文件或上下文被错误上传 | Local-first、Secret Boundary、上传前确认 |
| 记忆污染 | 错误偏好被长期固化 | Memory Candidate 先确认，支持编辑和冻结 |
| Agent 失败不透明 | 用户不知道失败原因 | 统一错误结构、失败复盘、建议下一步 |
| 页面过载 | 工作台信息太多 | 核心区聚焦产物和对话，非核心内容抽屉隐藏 |
| 成本不可控 | 多 Agent 调用导致费用飙升 | Token 成本看板、预算、调用前预估 |

## 17. 里程碑建议

| 阶段 | 时间 | 目标 |
|---|---|---|
| M0 | 1 周 | 完成 PRD、信息架构、HTML 原型 |
| M1 | 2-3 周 | Web Workstation + Workspace 静态可交互原型 |
| M2 | 4-6 周 | 后端 Mission / Agent / Artifact / Approval 数据模型 |
| M3 | 6-8 周 | Mac Local Runtime 原型与 Codex / Claude Code 调用 |
| M4 | 8-10 周 | 浏览器插件与 Android 审批 MVP |
| M5 | 10-12 周 | 小范围真实用户闭环验证 |

## 18. 当前待决策问题

1. MVP 是否先以 Web + Mac 为主，Android 仅做审批和日报。
2. Claude Code、Codex、Cursor 的首批接入顺序。
3. Sovereign Mode 是否作为高级实验模式隐藏入口。
4. 文件学习默认本地只存摘要，还是允许用户选择上传原文。
5. Agent Card 是否允许公开分享和导入。
6. Life Ops 首版是否只做提醒和草拟，不做自动发送。

## 19. 本次 HTML 原型交付说明

本次配套 HTML 原型应覆盖实际产品页面：Workstation、新建任务、数据分析工作台、普通工作台、Agent Hub、历史任务、知识与产物、公共内容、数字分身管理、审批与审计。所有页面右侧都应保留 Wisdom Twin 常驻区域，并在具体 Workspace 内体现 User + Wisdom Twin + Tool Agent 的 Agent-to-Agent 对话框架。

