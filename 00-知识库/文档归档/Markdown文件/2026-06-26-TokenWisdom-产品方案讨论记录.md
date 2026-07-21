# TokenWisdom 产品方案讨论记录

- 日期：2026-06-26
- 项目：TokenWisdom
- 阶段：早期产品方案讨论
- 状态：讨论中，待继续收敛 PRD / 原型 / 技术方案
- 原始项目文档：`01-业务项目/TokenWisdom/2026-06-26-TokenWisdom-产品方案讨论记录.md`
- 记录说明：本文为项目文档的归档副本，沉淀当前对话中的阶段性共识，所有方案均为产品假设，后续需要继续验证。

## 1. 一句话定位

TokenWisdom 是用户的半自主 AI 分身：它长期理解用户目标、偏好、文件、工作上下文和 AI 使用习惯，并能代表用户发现、学习、组合和调用其他专业执行 Agent 与平台工具。

更口语化的表达：

> TokenWisdom 是我的第二个 AI 大脑，专门替我和其他 AI、平台、工具打交道。

## 2. 核心定位

TokenWisdom 不只是 AI 工具管家，而是用户的 AI 分身。

| 类型 | 核心角色 | 价值边界 |
|---|---|---|
| 普通 AI 助手 | 回答用户问题 | 单轮或多轮对话 |
| AI 工具管家 | 帮用户用好工具 | 推荐、教学、调用 |
| AI 工作空间 | 组织任务和协作 | 项目上下文、多方协作、产物沉淀 |
| TokenWisdom AI 分身 | 代表用户与外部 Agent / 平台互动 | 学习用户、替用户沟通、组合外部能力、推进任务 |

核心差异：TokenWisdom 要能持续成长，逐渐知道“用户是谁、想要什么、怎么判断、信任哪些工具、哪些事情可以自动做、哪些事情必须确认”。

## 3. 目标用户

首期目标用户：个人工作者，尤其是 AI 工具重度使用者和专业知识工作者。

| 用户类型 | 高频任务 | 适配度 |
|---|---|---|
| 产品经理 / 独立创业者 | 调研、PRD、竞品、需求、项目推进 | 高 |
| 研究型创作者 | 资料收集、知识整理、写作、发布 | 高 |
| 开发者 / 自动化玩家 | 调用 Claude Code、Codex、Cursor、MCP、自动化工具 | 高 |
| 数据分析师 / 运营 | 查数、分析、报告、自动化推送 | 中高 |

当前讨论中，第一批外部执行 Agent 更偏专业执行型 Agent，例如 Claude Code、Codex、Cursor，而不是泛用聊天工具。

## 4. 产品形态

TokenWisdom 是跨端 AI 分身系统，由后台服务、Web 工作台、Mac App、安卓 App、浏览器插件共同组成。

| 模块 | 角色 |
|---|---|
| 后台服务 | 数字分身核心：记忆、用户画像、权限、任务、Agent 能力库 |
| Web 工作台 | 分身管理中心：目标、记忆、文件、Agent、任务、权限、审计 |
| Mac App | 本地上下文采集与执行端：文件学习、本机执行、Claude Code / Codex / Cursor 调用 |
| 安卓 App | 移动交互与授权端：对话、审批、接收汇报、任务状态查看 |
| 浏览器插件 | AI 工具观察与网页 Agent 协助：保存对话、总结使用习惯、识别工具能力 |

三端分工原则：

> Web 负责控制，Mac 负责采集和执行，安卓负责确认和随身交互。

## 5. 工作空间定义

TokenWisdom 需要一个 Agent 工作空间，不能只做聊天窗口。

> TokenWisdom Workspace 是用户数字分身的长期工作台。它是跨 Web、Mac、安卓同步的个人 AI 作战室，沉淀用户目标、文件、记忆、工具、外部 Agent、任务、授权和所有协作对话。

一个用户可以有：

- 默认个人空间：例如 `My Wisdom`
- 多个项目空间：例如 `找工作`、`创业项目`、`研究报告`、`个人知识库`
- 每个空间拥有独立的记忆、文件、Agent、任务和授权边界

## 6. 工作空间核心区域

| 区域 | 作用 |
|---|---|
| Home | 今日状态、待确认事项、分身建议 |
| Goals | 长期目标、当前项目、优先级 |
| Memory | 用户画像、偏好、规则、风格、禁忌 |
| Files | 上传资料、本地文件索引、知识库 |
| Agents | 外部 Agent / 平台能力卡、连接状态、调用方式 |
| Rooms | 多方对话空间：用户 + TokenWisdom + 外部 Agent |
| Tasks | 任务拆解、执行状态、下一步动作 |
| Audit | 分身做了什么、为什么做、用了哪些权限 |

## 7. 核心对象模型

| 对象 | 含义 | 关键字段 |
|---|---|---|
| User | 真实用户账号 | 身份、订阅、设备、全局设置 |
| Wisdom Twin | 用户的 AI 分身 | 名称、人格、目标、偏好、权限等级、成熟度 |
| Workspace | 分身工作的上下文空间 | 空间目标、成员、文件、Agent、任务、记忆 |
| Room | 多方对话空间 | 用户、分身、外部 Agent、平台、工具、消息记录 |
| Agent Card | 外部 Agent / 平台能力卡 | 能力、输入格式、输出格式、风险、最佳用法 |
| File / Knowledge Item | 用户上传或同步的知识资产 | 来源、摘要、索引状态、权限范围、关联空间 |
| Memory | 长期记忆单元 | 用户偏好、事实、判断规则、风格、置信度、确认状态 |
| Task | 分身推进的工作单元 | 目标、计划、状态、调用过的 Agent、产出、下一步 |
| Permission Policy | 授权策略 | 哪些空间 / 工具 / 动作允许自动执行，哪些必须确认 |
| Audit Log | 行为审计记录 | 谁在何时做了什么、依据什么记忆、用了什么权限 |

关系示意：

```text
User
 └── Wisdom Twin
      ├── Global Memory
      ├── Permission Policies
      └── Workspaces
           ├── Workspace Memory
           ├── Files / Knowledge
           ├── Agent Cards
           ├── Rooms
           │    ├── User
           │    ├── Wisdom Twin
           │    └── External Agents / Tools
           └── Tasks
                ├── Plan
                ├── Agent Calls
                ├── Outputs
                └── Audit Logs
```

## 8. 记忆分层

| 记忆层 | 示例 | 作用 |
|---|---|---|
| 全局用户记忆 | “我偏好先结论后细节” | 跨所有空间生效 |
| 工作空间记忆 | “TokenWisdom 项目定位是 AI 分身” | 只在某项目生效 |
| Agent 使用记忆 | “某 PPT Agent 适合生成大纲，不适合美化” | 帮用户用好工具 |
| 任务过程记忆 | “这次调研用户否定了 B 方案” | 防止重复讨论 |
| 待确认记忆 | “推断用户偏好用表格表达” | 等用户确认后再固化 |

长期交互本质上是分身训练机制，而不是普通聊天功能。

## 9. 完整工作流

```text
注册数字分身
 → 建立初始画像
 → 导入文件和工作上下文
 → 开启插件 / 设备观察
 → 冷启动外部 Agent
 → 创建工作空间和房间
 → 分身提出行动建议
 → 用户授权执行
 → 多 Agent 协作推进
 → 产出结果
 → 用户复盘纠偏
 → 更新分身记忆和能力网络
```

关键阶段：

1. 注册数字分身：对话式建立用户画像，生成“我的分身初始说明书”。
2. 文件学习：上传资料或通过 Mac App 选择本地文件夹，提取事实知识、用户偏好、项目上下文。
3. 插件观察：保存用户使用 AI 工具的过程，学习 prompt 偏好、采纳标准和工具选择习惯。
4. Agent 代聊：用户添加外部 Agent 后，TokenWisdom 自动采访它，生成能力卡。
5. 执行与复盘：创建任务、选择 Agent、创建 Room、授权执行、回收结果、更新记忆。

核心闭环：

> 每次工作都让分身更懂用户，也更懂外部 Agent 世界。

## 10. MVP 边界

当前共识：第一版做“完整闭环的薄版本”，不只做聊天工具，也不一开始追求完全自动。

| 模块 | MVP 要做 | MVP 不做 |
|---|---|---|
| Web 工作台 | 分身首页、工作空间、文件、Agent Card、任务、授权日志 | 复杂团队协作、多角色权限 |
| Mac App | 登录、选择本地文件夹、同步文件摘要、快捷唤起分身、本地 Agent Runner | 深度系统控制的全部自动化能力 |
| 安卓 App | 对话、审批、日报、任务状态查看 | 完整工作台编辑能力 |
| 浏览器插件 | 保存 AI 对话、识别当前工具、总结用户 prompt 偏好 | 全量屏幕录制、自动接管网页 |
| 文件学习 | 上传文件 → 摘要 → 提取记忆 → 用户确认 | 大规模企业知识库治理 |
| Agent 代聊 | 手动添加 Agent 入口 → 冷启动提问 → 生成能力卡 | 任意平台自动登录和自动付费调用 |
| 多方 Room | 用户 + TokenWisdom + 外部 Agent 的对话记录和结论沉淀 | 真正实时跨平台群聊协议 |
| 权限系统 | L0-L3：观察、建议、代聊、草拟执行 | 默认无人值守的高风险执行 |

第一版核心 Demo：

> 用户创建分身 → 上传个人资料 / 项目文件 → 安装插件保存几段 AI 对话 → 添加一个外部 Agent → TokenWisdom 自动采访它 → 生成 Agent Card → 用户创建任务 → 分身推荐怎么组合文件、prompt 和 Agent → 用户确认后执行 → 结果进入复盘 → 分身更新记忆。

## 11. Agent Network 与外部 Agent 接入

TokenWisdom 不直接内置所有能力，而是拥有可扩展的 Agent Network。用户可以给自己的 AI 分身配置平台内置工具 Agent，也可以接入外部 Agent。

| Agent 来源 | 示例 | 接入方式 | TokenWisdom 的角色 |
|---|---|---|---|
| 平台内置工具 Agent | 文件学习 Agent、网页观察 Agent、Prompt 优化 Agent、任务规划 Agent | 平台原生提供 | 直接调用，保证稳定性 |
| 外部通用 Agent | ChatGPT、Claude、Kimi、Gemini、Perplexity | 浏览器插件、API、MCP、手动对话转发 | 代用户沟通、总结、复用 |
| 外部专业 Agent | Claude Code、Codex、Cursor、Devin、数据 Agent、PPT Agent | CLI、API、MCP、本地桥接、网页自动化 | 作为专业执行者参与任务 |

统一抽象：

- Agent Connector：解决“怎么连接它”
- Agent Card：解决“怎么用好它”

## 12. 第一批重点外部 Agent

第一批优先支持专业执行 Agent，尤其是 Coding / IDE / 自动化执行类 Agent。

| Agent 类型 | 示例 | TokenWisdom 的价值 |
|---|---|---|
| Coding CLI Agent | Claude Code、Codex、Aider、OpenCode | 准备需求、限定范围、分派任务、检查结果 |
| IDE Agent | Cursor、Windsurf、Kiro | 生成开发意图、同步上下文、复盘改动 |
| 数据 Agent | SQL Agent、BI Agent、分析 Agent | 提供业务背景、指标口径、验收标准 |
| 自动化 Agent | Browser Agent、RPA Agent、Zapier 类 Agent | 编排动作、管理授权、记录审计 |
| 内容执行 Agent | PPT Agent、文档 Agent、设计 Agent | 提供风格偏好、资料上下文、质量标准 |

对于 Claude Code / Codex / Cursor，TokenWisdom 的价值不是替代它们，而是：

- 判断什么时候该用哪个 Agent
- 自动准备任务上下文、需求文档、代码范围、验收标准
- 调用前做风险提示和授权确认
- 调用后读取结果，做总结、复盘和记忆更新
- 把 Coding Agent 的能力纳入用户长期工作流

## 13. 本地调用执行架构

当前共识：TokenWisdom 更偏“本地调用执行”，不是只生成任务包让用户复制。

Web 工作台负责决策和编排，Mac App 负责本地执行。

```text
Web 工作台
  ↓ 创建任务 / 审批授权
TokenWisdom 后台
  ↓ 下发任务包
Mac App / Local Agent Runner
  ↓ 选择本地项目目录或本机执行范围
Agent Connector
  ↓ 调用 Claude Code / Codex / Cursor / 其他 CLI Agent
本地执行结果
  ↓ 日志、diff、文件、测试结果
TokenWisdom 后台
  ↓ 总结、审计、记忆更新
Web / 安卓端
  ↓ 用户确认采纳
```

Local Agent Runner 需要具备：

| 能力 | 说明 |
|---|---|
| 项目绑定 | 用户选择 repo / 文件夹，明确默认可访问范围 |
| Agent 检测 | 检查本机是否安装 Claude Code、Codex、Cursor CLI / 插件 |
| 任务包执行 | 将 TokenWisdom 生成的任务包传给对应 Agent |
| 结果采集 | 回收 stdout、日志、diff、文件变化、测试结果 |
| 权限控制 | 写文件、跑命令、联网、安装依赖等动作分级确认 |
| 审计同步 | 把执行过程同步到 Workspace 的 Audit Log |

标准化 Execution Brief：

```text
任务目标：
背景上下文：
相关文件：
不可修改范围：
验收标准：
建议执行步骤：
需要运行的检查：
权限限制：
失败时回报格式：
```

## 14. Sovereign Mode / 本地主权分身模式

用户希望高阶形态支持全本机代理权限。建议产品上称为：

> Sovereign Mode / 本地主权分身模式

定义：

> 用户把自己的 Mac 授权给 TokenWisdom 的本地分身，让它可以像用户本人一样读取文件、操作应用、调用命令行 Agent、使用浏览器、管理任务和执行自动化。但所有能力运行在用户本机，受策略、审计、暂停和回滚机制约束。

关键原则：

> 权限可以很大，但行动必须可解释、可暂停、可追责。

全本机权限不是给云端后台，而是给 Mac 本地分身 Runtime。

```text
Web / 安卓端
  → 发起目标、审批、查看进展

TokenWisdom Cloud
  → 记忆、任务、Agent Card、工作空间同步

Mac Local Runtime
  → 全本机代理权限
  → 文件、应用、浏览器、终端、Claude Code、Codex、Cursor、本地自动化
```

配套机制：

| 机制 | 作用 |
|---|---|
| Mission Control | 当前分身正在做什么、下一步要做什么、是否需要确认 |
| Global Kill Switch | 一键暂停所有本机代理行为 |
| Action Audit | 每次读文件、跑命令、调用 Agent、上传上下文都有日志 |
| Risk Classifier | 删除文件、安装依赖、花钱、发消息、提交代码等动作强提醒 |
| Rollback / Snapshot | 对文件修改、代码变更、配置变更尽量支持回滚 |
| Secret Boundary | 默认不读取 `.env`、密钥、证书，除非用户显式授权 |
| Local-first Policy | 敏感文件尽量只在本机处理，上传云端前明确告知 |

## 15. 四大 Agent Hub

Sovereign Mode 下，TokenWisdom 需要支持四类自主任务，但应组织成四个工作域，而不是混成一个万能助手。

| 工作域 | 名称建议 | 解决什么 | 第一版深度 |
|---|---|---|---|
| 代码开发 | Dev Agent Hub | 调用 Claude Code / Codex / Cursor / git / terminal 完成代码任务 | 深做 |
| 文件知识 | Knowledge Agent Hub | 整理本地文件、学习资料、构建个人知识库 | 深做 |
| AI 工具自动化 | AI Tool Agent Hub | 自动使用网页 Agent、平台工具、MCP、API，并总结结果 | 中等 |
| 日常事务 | Life Ops Agent Hub | 邮件、日程、消息、提醒、待办、个人运营 | 浅做 |

共享同一个 Wisdom Twin Core：

```text
Wisdom Twin Core
  ├── 用户画像
  ├── 长期目标
  ├── 偏好与规则
  ├── 授权策略
  ├── 任务记忆
  ├── Agent 能力卡
  └── 审计日志

四个工作域只是不同执行通道：
  Dev / Knowledge / AI Tools / Life Ops
```

## 16. 融合式首页：Twin Mission Control

当前共识：Web 工作台首页采用融合式首页。

> Twin Mission Control / 分身任务中枢

用户每天打开后应该看到：我的 AI 分身现在懂我到什么程度，正在替我做什么，有哪些事情需要我确认，以及我可以把哪些工作交给它。

结构草案：

```text
顶部：当前分身状态
  - 分身名称 / 模式 / 在线状态 / 今日自主等级
  - Safe Mode / Sovereign Mode 开关
  - 一键暂停 Kill Switch

第一屏：Today with My Twin
  - 今天分身学到了什么
  - 正在推进什么
  - 等我确认什么
  - 有什么风险提醒

第二屏：Mission Queue
  - 进行中任务
  - 待授权任务
  - 已完成任务
  - 失败 / 阻塞任务

第三屏：Four Agent Hubs
  - Dev Agent Hub
  - Knowledge Agent Hub
  - AI Tool Agent Hub
  - Life Ops Agent Hub

第四屏：Workspace Rooms
  - 最近工作空间
  - 多 Agent 对话房间
  - 外部 Agent 协作记录

侧栏：长期资产
  - Memory
  - Files
  - Agents
  - Permissions
  - Audit
```

核心卡片：

| 卡片 | 内容 |
|---|---|
| Twin Status | 分身成熟度、记忆数量、已连接 Agent、当前权限等级 |
| Needs Your Approval | 等待用户确认的文件读取、命令执行、外部 Agent 调用、记忆固化 |
| Working Now | 当前正在跑的 Codex / Claude Code / 文件整理 / 网页 Agent 任务 |
| Learned Today | 新学到的用户偏好、工具能力、项目事实 |
| Suggested Missions | 分身主动建议可以推进的事项 |
| Risk Watch | 敏感操作、失败任务、权限异常、可能上传的上下文 |

主输入框建议文案：

> Ask or assign to your Twin...

输入后，TokenWisdom 判断其属于：记忆更新、任务创建、Agent 调用、文件学习、权限变更或工作空间创建。

## 17. 当前待决策问题

1. 首版是否先以 Mac App + Web 工作台为主，安卓 App 做轻量审批端。
2. Claude Code、Codex、Cursor 的具体接入顺序和技术方式。
3. Sovereign Mode 是否首版开放，还是先作为高级实验模式。
4. 文件学习是否默认本地优先，云端只存摘要 / 向量 / 确认后的记忆。
5. Agent Card 是否允许用户编辑、评分和分享。
6. Life Ops 涉及邮件、日程、消息发送，第一版应限制到建议和提醒，还是允许授权执行。

## 18. 下一步建议

建议后续继续沉淀三份文档：

1. `PRD`：产品目标、用户场景、核心功能、非目标、成功指标。
2. `IA / 原型草图`：Web 工作台、Mac App、安卓 App 的页面结构。
3. `技术架构草案`：后台服务、Mac Local Runtime、Agent Connector、权限与审计系统。

## 19. ICE Workbench 整合补充

已查看桌面项目 `/Users/mi/Desktop/ice_workbench_new`，它可以作为 TokenWisdom 的 Web 工作台与 Agent 工作空间原型底座。

整合判断：

- ICE Workbench 的 `Dashboard` 可改造成 TokenWisdom 的 `Twin Mission Control`。
- ICE Workbench 的 `Task / Workspace` 可映射为 TokenWisdom 的 `Mission / Room`。
- ICE Workbench 的 `Agent / Skill` 可扩展为 TokenWisdom 的 `Agent Hub / Capability Library`。
- ICE Workbench 的 `files / kb / memory / experience_cards` 可扩展为 TokenWisdom 的 `Knowledge Hub / Memory Candidate`。
- ICE Workbench 的 `tool_calls / run_events / HITL` 可扩展为 TokenWisdom 的 `Action Audit / Mission Timeline / Approval Center`。
- TokenWisdom 仍需新增 Mac Local Runtime、Claude Code / Codex / Cursor Connector、Sovereign Mode、Android 审批端与个人长期记忆模型。

详细分析见：`01-业务项目/TokenWisdom/2026-06-26-TokenWisdom-ICE-Workbench整合分析.md`。
