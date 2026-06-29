# ICE-DATA-WORK 平台设计方案 v1

- 日期：2026-06-27
- 文档类型：新一代平台总体设计（功能 + 实现方案）
- 状态：设计对齐中（核心决策已锁定，空间/记忆模型已定稿）
- 参考资料：
  - ICE Data Workbench v3（现状底座，FastAPI + React + G3 文件优先存储）
  - TokenWisdom 产品 PRD v1（User → Twin → Agents 提案）
  - Multica（agents-as-teammates 看板 + Squads + Runtimes + Autopilots）

---

## 0. 文档地图

本项目文档分为「总纲 + 三份核心材料 + 原型 + 参考资料」：

| 文档 | 内容 |
|---|---|
| **本文件** `…设计方案-v1.md` | **总纲**：北极星、已锁决策(D-01~D-12)、核心概念、四层空间与记忆模型、权限治理、分期计划、技术栈复用 |
| `…01-产品功能与交互设计.md` | **材料一·产品**：IA、用户旅程、看板、Workspace、Twin Dock、各页交互规格、角色权限 |
| `…02-技术实现方案与开发ToDo.md` | **材料二·技术**：数据模型、API/路由、模块拆解、ContextAssembler、四层空间 paths、开发 ToDo |
| `…03-Agent与空间文件区设计.md` | **材料三·Agent与空间**：Twin/工具 Agent 定义、agent.md/记忆格式、多参与者协作、四层空间文件区、记忆晋升 |
| `design/` | 可点击 HTML 原型（15 页 + 共享 app.css/shell.js），双击 `design/index.html` 浏览 |
| `参考资料/` | TokenWisdom PRD / 原型 / 参考页分析（历史溯源，已归档） |

---

## 1. 北极星

> **ICE-DATA-WORK = 一个让人和 AI Agent 共享"数据/工作任务看板"的团队工作台。**
> 每个任务进入一个 Workspace，里面是流式的多 Agent 协作对话（继承 ICE）；Agent 编成 Squad、跑在 Runtime 上；每个用户拥有一个一等公民的数字分身（Twin），负责上下文、记忆、权限与信任治理（继承 TokenWisdom）。数据分析是旗舰垂类，底座是通用的。

三个来源的融合：

| 维度 | ICE Workbench（底座） | TokenWisdom（提案） | Multica（参考） | ICE-DATA-WORK 取舍 |
|---|---|---|---|---|
| 组织模型 | 任务 + 对话 | Workstation/Workspace | 看板 + Squads | 看板为骨架，任务进 Workspace |
| 主体关系 | 用户 → Agent | 用户 → Twin → Agents | 人 + Agent 同事 | 三者融合 |
| 执行 | 服务端 + 沙盒 | Mac Local Runtime（P1） | daemon/runtime | v1 服务端；二期加本地 daemon |
| 治理 | HITL + 审计 | L0-L5 权限 + Twin | 轻 | HITL + L0-L5 + Twin |
| 存储 | G3 文件优先 | 记忆文件 | Postgres + pgvector | G3 为主，pgvector 补向量检索 |
| 强项 | 数据分析垂类 | 个人分身 | 通用编码 Agent 团队 | 数据分析做旗舰，底座通用 |

---

## 2. 已锁定决策

| 编号 | 决策点 | 结论 |
|---|---|---|
| D-01 | 单人 vs 团队 | **团队**。看板/Squad/多 Agent 协作以多主体为前提 |
| D-02 | 技术栈与建设方式 | **沿用 Python(FastAPI) + React**，在 ICE-DATA-WORK 新仓重组；复用 G3 存储、数据 Agent、Python 沙盒 |
| D-03 | Multica daemon/runtime 模型 | **要，但放二期**。用于驱动本机 Claude Code / Cursor（= TokenWisdom 的 Mac Local Runtime） |
| D-04 | 面向谁 | **小米内部**。保留飞书 OAuth / Kyuubi / 米盾(Aegis) 集成 |
| D-05 | Twin 是否一等公民 | **是，v1 就上**。Twin 是平台核心角色，不是附属 |
| D-06 | Agent 情景记忆隔离粒度 | **定义/技能团队共享 + 情景记忆按用户分区 + 显式『贡献给团队』才晋升为共享** |
| D-07 | 团队/项目级空间 | **要**。新增团队/项目共享空间；公共文件/知识/产物按项目或团队隔离 |
| D-08 | Twin 实现形态 | **复用 Agent 抽象**：Twin = 用户私有 Agent + 特权（协调其他 Agent、发起 Approval、读写用户空间），不引入第二套运行时 |
| D-09 | 看板最小形态 | v1 = **状态泳道（待办/进行中/待确认/已完成）+ Agent 一等 assignee + 认领/指派/状态流转**；拖拽美化、swimlane、自定义列留后 |
| D-10 | Team/Project 与角色 | **三条正交权限轴**：平台角色(super_admin/admin/user) × 成员角色(Team owner/admin/member、Project member) × Twin 权限(L0-L5)；有效权限取交集 |
| D-11 | 任务归属 | **每个任务恰好属于一个 Project**；未挂项目的任务进用户默认"个人项目"；v1 不做跨项目任务 |
| D-12 | Twin 导航感知与控制 | Twin **感知**左侧 tab/页面切换（当前页面上下文实时进入 Twin），且可**被指令驱动切换**（如"带我去看板"→ Twin 调 `navigate` 跳转）。导航是 Twin 的一类一等能力 |
| D-13 | 用户贡献驱动的 Skill/Agent 自演进 | 任务中用户可提供代码/内容，Agent 经沙盒执行（`run_user_code`）；跑通后蒸馏为 **Skill**（可复用可执行 + 入参 schema + 版本）+ 绑定进 **Agent**（学会何时用）+ 沉淀 **Memory**。沿用 D-06：个人草稿 Skill 立即可用、显式"贡献给团队"需沙盒通过 + 审核；版本化可回滚 |
| D-14 | 展示模型（状态优先） | 卡片以**状态**为主角。任务 6 态：待办/执行中/待确认/已完成/报错/已暂停（报错卡给重试+查看日志+结构化建议）。Agent 展示三件套：当前状态(空闲/工作中/等待确认/报错/未连接) + 核心能力(一句) + 正在执行的工作。产物 3 态：草稿/已确认/已发布，且**渐进展开**（卡片只给数量入口 → 列表 → 内容） |

---

## 3. 核心概念与角色

| 概念 | 定义 |
|---|---|
| User | 真实用户，拥有最终确认权与自己 Twin 的所有权 |
| Team / Project | 共享单元。Team 为组织级，Project 为团队内项目级；任务归属于某 Project。共享文件/知识/产物按 Team 或 Project 隔离 |
| Twin（数字分身） | 用户的一等公民分身，是一种**特殊的、用户私有的 Agent**。长期学习用户、维护上下文、协调工具 Agent、请求确认；感知页面上下文并可被指令驱动导航（D-12） |
| Tool Agent | 平台/团队级专业执行 Agent（数据分析、AB 实验、波动归因、编码 Agent 等） |
| Squad | 由一个 leader Agent 领衔的 Agent 小队；任务可派给 Squad，由 leader 路由 |
| Task / Mission | 看板上的工作项，可被人或 Agent 认领、推进、复盘 |
| Workspace | 进入某个 Task 后的工作页（数据分析 / 通用两类） |
| Runtime | 执行环境：v1 为服务端运行时；二期加本机 daemon |
| Memory Candidate | 候选记忆，经用户/管理员确认后晋升进对应空间 |
| Approval | 高风险动作与记忆固化的确认动作（HITL + L0-L5） |

---

## 4. 空间与记忆模型（平台技术核心）

用户要求：文档/记忆空间分三层主体空间 —— **任务级、Agent 空间、用户空间**，并要做好**隔离**与**复用**；在此之上再加一层 **团队/项目共享空间**（D-07），承载团队/项目级的共享文件、知识与产物。

> 关键场景（用户原话复述）：我邀请一个工具 Agent 进入任务，我的 Twin 也加入。此时这个工作空间里应同时带有**那个工具 Agent 的记忆** + **Twin 的记忆** + **当前工作空间独立的文件空间**。

### 4.1 空间层级定义

> 三层主体空间（任务 / Agent / 用户）+ 一层共享空间（团队/项目）。

| 层级 | 归属 | 内容 | 生命周期 | 隔离边界 |
|---|---|---|---|---|
| **任务空间** | Task | 对话、工具调用、任务文件(input/output)、任务工作记忆、记忆候选 | 与任务同生命周期 | 仅任务参与者可读，不跨任务泄漏 |
| **Agent 空间** | Tool Agent | agent.md 操作手册、技能、知识库、使用经验记忆 | 与 Agent 同生命周期，跨任务复用 | 定义/技能团队共享；情景记忆按用户分区（D-06） |
| **用户空间** | User（含其 Twin） | Twin 画像、用户长期记忆、偏好、决策、跨任务知识、个人产物 | 与用户同生命周期 | 默认仅本人 + 本人 Twin 可读；他人不可读（二期授权例外） |
| **团队/项目空间** | Team / Project | 共享文件、共享知识、团队晋升的共享经验、共享产物 | 与团队/项目同生命周期 | 仅团队/项目成员可读；按 Team 或 Project 隔离 |

### 4.2 文件系统布局（扩展 ICE 的 G3 文件优先存储）

```text
users/{user_id}/
  profile.json
  twin/                          # Twin = 用户私有的一等 Agent
    twin.json                    # 画像、目标、风格、权限等级、成熟度
    agent.md                     # Twin 操作说明
    memory/
      preferences.memory.md      # 用户偏好（晋升后）
      decisions.memory.md        # 关键决策
      project-context.memory.md  # 项目上下文
      pinned.memory.md           # 始终注入的高优先记忆
  memory/                        # 用户级跨任务共享记忆（与 Twin 记忆区分）
  artifacts/                     # 晋升为用户所有的产物
  bindings/                      # 用户对工具 Agent 的连接/配置（非 Agent 本体）

agents/{agent_id}/               # 工具 Agent（团队/平台级共享定义）
  agent.json
  agent.md                       # 操作手册（始终注入）
  skills/  knowledge/
  memory/
    by-user/{user_id}/           # 按用户分区的情景记忆（默认隔离，D-06）
      usage.memory.md
    by-team/{team_id}/           # 显式"贡献给团队"晋升后的共享经验（按团队隔离）
      shared.memory.md

teams/{team_id}/                 # 团队/项目共享空间（D-07）
  team.json                      # 成员、角色
  shared/                        # 团队级共享：files / knowledge / artifacts / memory
  projects/{project_id}/
    project.json                 # 项目成员、设置
    shared/
      files/                     # 项目级公共文件（按项目隔离）
      knowledge/                 # 项目共享知识
      memory/shared.memory.md    # 项目晋升上来的共享经验
      artifacts/

tasks/{task_id}/
  task.json                      # 标题/类型/状态/participants/workspace_type/project_id
  conversation.jsonl
  tool_calls.jsonl
  files/{input,output}/          # 任务独立文件空间
  memory/
    working.memory.md            # 任务工作记忆/草稿（自动写，无需审批）
    candidates.jsonl             # 本任务产生的记忆候选，审批后路由晋升
  participants/                  # 参与者在本任务内的任务级记忆叠加层
    {agent_id}/notes.md          # 该工具 Agent 在本任务学到/用到的（任务级）
    {twin_id}/notes.md           # 该 Twin 在本任务内的笔记（任务级）
```

### 4.3 读：上下文组装（Context Assembly）= 分层叠加

当某个任务里有参与者 `[Twin_A, DataAgent]` 时，一次对话回合的上下文由 `ContextAssembler` 服务按层组装：

```text
组装后的上下文（带来源标注，是"并集 + 归属"，不是简单覆盖）
├── 任务层：task.json + 近期对话(+compaction 摘要) + working.memory + 任务文件索引
├── 参与者层（每个 Agent/Twin 一份）
│   ├── DataAgent：agent.md + 其 Agent 空间记忆相关切片(本用户分区 + 本团队共享) + 任务级 notes
│   └── Twin_A   ：twin.json + 用户空间记忆相关切片(pinned 全量) + Twin 的任务级 notes
├── 用户层：当前操作用户的全局适用偏好
└── 团队/项目层：任务所属 Project/Team 的共享知识与记忆相关切片
```

- **优先级**：任务级 > 参与者空间 > 用户 > 项目 > 团队（越具体越优先），但记忆是"叠加 + 标注来源"，不是配置覆盖。
- **检索策略**：v1 先做"pinned/agent.md 全量注入 + 关键词命中"；v1.5 用 pgvector 对 `*.memory.md` 做语义检索，只注入相关切片，控制 token。

### 4.4 写：记忆形成与晋升（Memory Routing）

```text
任务进行中产生的认知
├── 临时/过程性 → 写入任务层(working.memory / participants/*/notes)  [自动，无需审批]
└── 值得长期保留 → 生成 Memory Candidate 写入 tasks/{id}/memory/candidates.jsonl
                    （带 proposed_scope：user_preference | agent_user | agent_team | project | team）
                         ↓ 用户/管理员审批（HITL + L0-L5 门控）
                    晋升(file_transaction 原子移动)到目标空间：
                      · user_preference → users/{uid}/twin/memory/preferences.memory.md
                      · agent_user      → agents/{aid}/memory/by-user/{uid}/usage.memory.md（本人分区，低风险）
                      · agent_team ⭐    → agents/{aid}/memory/by-team/{tid}/shared.memory.md（"贡献给团队"，需审核）
                      · project         → teams/{tid}/projects/{pid}/shared/memory/shared.memory.md
                      · team            → teams/{tid}/shared/memory/...
```

复用 ICE 已有的"经验卡片审批闭环"+ TokenWisdom 的"Memory Candidate"概念。**「贡献给团队」是显式动作**：Agent 情景记忆默认只进本人分区(`agent_user`)，只有用户主动选择并经审核才晋升为团队共享(`agent_team`)（D-06）。

### 4.5 隔离 / 复用矩阵

| 读取方 → 资源 | 任务文件 | 该用户 Twin 记忆 | Agent 按用户情景记忆 | Agent 团队共享经验 | 项目/团队共享空间 |
|---|---|---|---|---|---|
| 任务参与者（本人） | ✅ 读写 | ✅（本人 Twin） | ✅（自己分区） | ✅ 读 | ✅（所属项目/团队） |
| 同团队其他用户 | ❌（非参与者） | ❌ | ❌（仅本人分区） | ✅ 读 | ✅（同团队/项目） |
| 其他团队用户 | ❌ | ❌ | ❌ | ❌（仅本团队分区） | ❌ |
| 其他用户的 Twin | ❌ | ❌（二期授权例外） | ❌ | ✅（同团队） | ✅（同团队/项目） |
| 平台管理员 | 审计可见 | ❌ 内容隔离 | 审计可见 | ✅ 管理 | ✅ 管理 |

**隔离保证**：任务文件不跨任务；用户 Twin 记忆不被他人/他人 Twin 读取（二期授权例外）；Agent 私有情景记忆默认按用户分区；团队共享经验按团队隔离；项目/团队共享空间按 Team/Project 边界隔离。
**复用保证**：Agent 定义/技能团队共享；Twin 记忆随用户跨其所有任务；优秀产物可从任务级晋升到用户 / Agent团队 / 项目 / 团队空间。

---

## 5. 权限与治理

- 沿用 TokenWisdom 的 **L0-L5 权限分级** + ICE 的 **HITL 人工介入 + 审计**。
- 高风险动作（写本机文件、跑命令、发消息、付费调用、固化记忆、跨空间读取）必须用户确认。
- 所有工具调用进审计：时间、发起者、权限等级、输入/输出摘要。
- 一键暂停全部执行。

---

## 6. 分期计划

### 6.1 v1（服务端团队工作台 + 一等 Twin）

- 团队看板（任务/Mission，Agent 作为一等 assignee）
- Workspace（数据分析 / 通用两类）+ 流式多 Agent 对话
- **一等 Twin**：常驻、维护上下文、协调工具 Agent、请求确认、感知与控制导航（D-12）
- **三层主体空间 + 团队/项目共享空间 + 记忆隔离/复用模型**（本文件 §4）
- 复用 ICE：G3 存储、数据 Agent、Python 沙盒、Kyuubi/飞书/米盾、LLM 网关
- HITL + L0-L5 权限 + 审计
- pgvector 记忆检索（v1.5）

### 6.2 二期（重点记录）

| 编号 | 功能 | 说明 |
|---|---|---|
| **P2-01** | **本机 daemon / Runtime 模型** | 参照 Multica：本机 daemon 自动探测并驱动 Claude Code / Codex / Cursor 等 CLI；服务端继续跑数据 Agent。即 TokenWisdom 的 Mac Local Runtime |
| **P2-02 ⭐** | **跨用户 Twin 协作（重磅）** | 用户可邀请**其他用户的数字分身**进入同一工作空间协作；**只要该 Twin 的管理员授权认可**即可。空间内将出现多个 Twin + 工具 Agent 同台对话。这是对 TokenWisdom "Agent Room" 和 Multica "Squad" 的跨用户扩展 |
| P2-03 | Squads | Agent 小队 + leader 路由 |
| P2-04 | Autopilots | cron/webhook/手动触发自动建任务并派发 |

#### P2-02 跨用户 Twin 协作 — 已知设计要点（待二期细化）

- **授权链**：访客 Twin 的 owner/管理员发放 **scoped grant**（限定哪个任务、可读什么、只读宿主空间、有效期、可撤销）。
- **沙箱**：访客 Twin 按**其自身 owner 的权限等级**行动，但被限制在宿主任务空间内；不能写宿主的用户/Agent 空间，只能写任务空间，且贡献带来源标注。
- **记忆回流**：访客 Twin 的记忆形成回流到**它自己 owner 的空间**，受其 owner 审批。
- **审计**：跨用户参与全程审计，双方可见。

---

## 7. 技术栈与复用清单

| 能力 | 来源 | 复用方式 |
|---|---|---|
| 后端框架 | ICE | FastAPI + SQLAlchemy + 双认证(JWT/Aegis) |
| 前端框架 | ICE | React 18.3 + Vite + TS + Zustand |
| 文件优先存储 G3 | ICE | paths / file_transaction / portalocker / jsonl，扩展四层空间布局 |
| Agent Runtime | ICE | 有界 ReAct 循环 + tool_runner，扩展多参与者上下文组装 |
| Python 沙盒 | ICE | execute_python 沙盒 venv（pandas/prophet/sklearn…） |
| LLM 网关 | ICE | mify 前缀路由 4 协议 |
| 集成 | ICE | Kyuubi / 飞书 / 米盾 |
| 向量检索 | 新增 | PostgreSQL + pgvector（记忆语义检索） |
| 看板 / Squad / Runtime 模型 | Multica | 概念参考，Python 重新实现 |
| Twin / 权限分级 | TokenWisdom | 一等 Twin + L0-L5 |

---

## 8. 已解决的关键设计问题

§2 的 D-08~D-11 由以下四问收敛而来（均已确认）：

1. **Twin 实现形态** → D-08：复用 Agent 抽象（Twin = 用户私有 Agent + 特权）。
2. **看板最小形态** → D-09：状态泳道 + Agent 一等 assignee，砍掉拖拽美化。
3. **Team/Project 与角色模型** → D-10：三条正交权限轴，有效权限取交集。
4. **任务与项目归属** → D-11：每任务恰属一个 Project，默认有"个人项目"。

D-12（Twin 导航感知与控制）为本轮新增。更细的落地（字段级、交互级、文件区级）在三份核心材料与 `design/` 原型中展开。
