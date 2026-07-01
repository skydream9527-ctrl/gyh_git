# PM-AI 协作工作区设计理念

> 来源：pm-workspace-starter / ICE Data Workbench v3 设计沉淀
> 沉淀日期：2026-06-29

---

## 1. 核心设计原则

### 1.1 工作区组织原则

- **文件优先存储（G3）**：文件系统是唯一真相源，SQLite仅作为派生索引
- **任务为原子单位**：以「任务(Task)」为核心工作单元，而非笔记本
- **空间边界显性化**：当前所在团队/项目、记忆归属、产物沉淀层级对用户可见
- **高风险动作确认**：写文件、跑命令、发消息、付费调用、固化记忆、跨空间读取——一律走确认卡
- **每次工作可沉淀**：任务结束有明确的"沉淀经验/产物"出口，可选择沉淀到个人/项目/团队/Agent经验

### 1.2 Agent设计理念

- **Agent是同事，不是工具栏**：Agent在看板上是一等assignee，在对话里是一等发言者，有头像、有身份、有记忆
- **看板是入口，Workspace是现场，Twin是常驻陪伴**：用户在看板看见待推进工作，进入任务在Workspace协作，右侧Twin始终在场
- **核心区只放产出物与对话**：Workspace主区域只展示工作产出物（报告/文档/图表）与对话窗口；状态、文件、Agent、历史、时间线一律抽屉隐藏

---

## 2. 信息架构（IA）

### 2.1 全局导航分组

```text
[Team/Project 切换器]            ← 顶部：当前所在团队 + 项目

Operate（操作）
├── 工作台 Workbench            ← 看板首页（默认页）
├── 新建任务 New Mission
└── 任务看板 Board              ← 全量任务的状态泳道视图

Workspace（进入具体任务后动态出现）
├── 数据分析工作台
└── 通用工作台

Assets（资产）
├── Agent Hub                  ← 工具 Agent + 我的 Twin
├── 知识与产物 Knowledge        ← 文档/报告/总结/记忆
├── 项目空间 Project Space      ← 当前项目的共享文件/知识/产物
└── 团队空间 Team Space         ← 团队级共享

Control（控制）
├── 数字分身管理 Twin Manager
├── 审批与审计 Approvals & Audit
└── 管理后台 Admin             ← admin+ 可见

[右侧常驻] Twin Dock            ← 所有页面右侧常驻，不随页面切换消失
```

### 2.2 权限模型（三条正交轴）

| 轴 | 取值 | 管什么 |
|---|---|---|
| 平台角色 | super_admin / admin / user | 平台级管理能力 |
| 成员角色 | Team(owner/admin/member) · Project(member) | 团队/项目访问、成员管理、共享空间 |
| Twin 权限 | L0 Observe ~ L5 Sovereign | 数字分身自主程度 |

**有效权限 = 平台角色 ∩ 成员资格 ∩ Twin 权限**

---

## 3. Agent体系设计

### 3.1 内置Agent清单

| Agent | 用途 | 状态 |
|---|---|---|
| 通用Agent | 开放任务入口与跨Agent编排 | published |
| 数据分析Agent | 数据分析、NL→SQL、Python分析、报告生成 | published |
| 实验分析Agent | AB显著性检验、指标下钻、放量决策 | published |
| 灰度版本Agent | APP版本灰度发布分析与决策 | published |
| 知识库Agent | 飞书知识空间使用、维护、归档 | published |
| 火山实验分析 | 火山ABtest查询与报告 | published |
| 自建数据分析 | 自建信息流分析 | published |
| 日报推送 | 内容池日报生成、补跑、飞书推送与异常告警 | published |
| 经营洞察Agent | 经营报告与洞察 | coming_soon |
| 波动归因Agent | 指标异动归因 | coming_soon |

### 3.2 Agent目录约定

每个Agent包含：

```text
agents/{agent_id}/
├── agent.json          # 运行时声明：工具白名单 / spawn目标 / feature flags / 展示信息
├── prompt/             # system.md 或 identity.md + sop.md
├── knowledge/          # Agent私有知识库（可选）
├── workflows/          # Agent私有工作流模板（可选）
├── skills/             # Agent私有说明型skill（可选）
└── README.md           # Agent使用说明（可选）
```

### 3.3 agent.json关键字段

| 字段 | 说明 |
|---|---|
| `tools` | 该Agent可见的function tools白名单 |
| `features` | 细粒度开关：todo_write、exit_plan_mode、spawn_subagent、run_background |
| `spawn_targets` | 可派单的子Agent白名单，`["*"]`表示所有已发布Agent |
| `prompt_layout` | `"v3"`使用identity.md/sop.md + 共享片段组装 |
| `permission_mode` | 工具权限策略：default/read_only/confirm_write/confirm_network |
| `max_turns` | 单轮Agent ReAct最大工具轮数上限 |
| `effort` | 推理强度：low/medium/high或正整数 |

---

## 4. 核心用户旅程

### 4.1 主流程：从看板进入任务多方协作

```text
Workbench看见"6.20 DAU下滑归因" → 点击进入/task/:id（数据分析工作台）
  → Workspace顶部"参与者"区显示：我 + Twin（已默认在场）
  → 点"+邀请" → 选择Data Agent加入
  → 空间上下文 = 任务文件 + Data Agent记忆 + Twin记忆
  → 对话区出现三方：我 / Twin / Data Agent
  → Data Agent发起只读查询 → 直接执行，结果回填报告面板
  → Twin建议"补查ANR"新查询 → 生成确认卡
  → 用户确认 → 执行 → 报告更新
  → 任务完成 → Twin生成Memory Candidate（待确认）
```

### 4.2 记忆沉淀流程

```text
Twin Dock"待确认"出现Memory Candidate卡片
  → 用户点开，选择scope：
       · 个人偏好（进我的Twin记忆）
       · 项目共享（进当前Project）
       · 团队共享（进Team）
       · 贡献给该Agent的团队经验（agent_team，需审核）
  → 确认 → 原子晋升到目标空间
```

---

## 5. 后端架构关键设计

### 5.1 文件优先存储G3（核心约束）

- 所有持久化数据在顶级目录：`agents/`、`skills/`、`files/`、`users/{uuid}/`、`tasks/{uuid}/`
- 所有路径解析通过统一paths模块，禁止直接拼接路径
- 多文件写入通过file_transaction（advisory lock + 原子备份+回滚）
- 追加型数据用jsonl而非json，避免锁竞争
- SQLite缓存可随时从文件系统重建

### 5.2 LLM网关路由

| 模型前缀 | 协议 | 端点 |
|---|---|---|
| `ppio/pa/claude-*` | Anthropic native | `/anthropic/v1/messages`（支持tool_use streaming） |
| `azure_openai/*` | OpenAI Responses | `/v1/responses` |
| `vertex_ai/*`/`xiaomi/*` | OpenAI Chat | `/v1/chat/completions` |
| 无`/` | Legacy Anthropic | `ANTHROPIC_BASE_URL` |

### 5.3 工具调用与沙箱

- 5轮有界Tool Calling循环（`MAX_TOOL_ROUNDS=5`，`TOOL_TIMEOUT_SEC=30`）
- 内置工具：now、echo、kyuubi_query、feishu_publish、write_file、execute_python等
- Python沙箱：独立venv，CPU 60s/内存1GB/文件50MB/无网络，每次调用新进程
- 飞行中保护：WS断开不取消任务，显式abort才终止，重复请求返回CONVERSATION_INFLIGHT

### 5.4 认证与角色

- 三级角色：super_admin / admin / user
- 双认证：Aegis米盾（RSA验证）或JWT
- super_admin必须飞书OAuth登录，密码登录返回错误
- 飞书首次登录可自动建号，支持严格白名单模式
- 系统始终保留至少1个super_admin，不能自行降级
