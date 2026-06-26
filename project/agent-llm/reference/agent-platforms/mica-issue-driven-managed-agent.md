# 

> 来源：飞书文档，更新时间：2026-04-24T12:36:23.000Z

<title>MiCA - Issue驱动的Managed Agent探索实践</title>

<callout emoji="📌">
**关键洞察：当单个 Agent 的能力不再是短板时，团队级人+Agent的协调基础设施才是新瓶颈。**
</callout>

<callout emoji="🎯">
**这是啥：**
- **一句话定义：** MiCA（**Mi**CA **I**ntegrates **C**oding **A**gents as real teammates）是一个 Issue 驱动的 AI Native 任务管理与协作平台 -— 你可以像给人类同事分配工作一样，给 Agent 创建 Issue、指派任务、实时追踪进度，甚至让它们自主汇报阻塞、参与讨论。
- **一句话理解：** 如果 AI Agent 是你的同事，它该怎么接任务、怎么汇报进度、怎么和人协作？MiCA 就是答案。
- **适用对象：** 已经在用 AI Agent 但团队协作还靠喊的团队
- **特别适合：** 多人 + 多 Agent 并行开发、需要过程可追溯的场景
</callout>

<callout emoji="🎯">
**关键变化：**
- **协作对象：**人与人的分工 -> 同时承接人、AI、Agent 的协作
- **任务产生：**多靠人手动创建和拆分 -> 需求变更、巡检异常、Review 结论都能自动生成 Issue
- **执行记录**：状态和结果主要靠人手动同步 -> 分析、执行、Review、验证结果持续回写到同一条 Issue
- **管理重点：**管理任务列表和负责人 -> 管理分工、接力、阻塞、进度和自动化推进
</callout>

<callout emoji="🎯">
**协作场景：**支持多种主要协作场景，举例如下
1. **不同需求、不同人并行：** 一个需求对应一个主 Issue，各自独立推进
2. **同一需求、不同人分工：** 在主 Issue 下按页面、模块或角色拆子 Issue
3. **同一需求、不同人接力：** 产品澄清 → 研发开发 → 测试验证，状态和结论都回在同一条 Issue 上
4. **同一需求、人和 Agent 协作：** 人负责分诊和关键判断，Agent 负责分析、执行、Review、验证
</callout>

# 一、是什么 -- 核心能力

![图片展示的是多云AI平台的Issue管理界面。界面左侧有导航栏，显示“showcase”等选项。右侧是Issues页面，按状态分为“Open”“In Progress”“In Review”“Done addCriterion图片](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=OTExZjc5ZDU5YWViOGIwMzkzMGE4YTJmYjNjZDY5ZjFfMTlkOGI1MjM4NzcyMjU0YTJjNjNjNDA0ZjIxNzY1ZmVfSUQ6NzYzMjE4NDg5NTE3NTM2MzUzNV8xNzgyNDY5MjQ1OjE3ODI0NzI4NDVfVjM)

## 1.1 Issue管理

<grid>
<column width-ratio="0.250000">
![图片展示的是Jira软件中Issue看板界面。左侧导航栏有Search、New Issue等选项，当前选中Issues。右侧看板分为To Do、、In Progress、In Review、Done四个状态列，显示了不同状态的Issue，如SHD-1、SHD-4等，每个Issue包含标题、优先级、状态、负责人等信息，如SHD-1标题为“批量查询API client与类型，SHD-4标题为“实现webhook的secretKey更新”等。该图直观呈现了Issue管理中](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=ZDE1OGQzZjc0ZmVlOWRhNzhhY2VlYzNkNDhlMmNhZWVfYWMyZGU2NTc2NDk5OTU1MmU3MjM4OWFkNWVjNTI5YzVfSUQ6NzYzMjIxNTQyOTk3NjkwMjg1MV8xNzgyNDY5MjQ1OjE3ODI0NzI4NDVfVjM)
</column>
<column width-ratio="0.250000">
![图片展示的是MiCA-Issue管理界面。左侧为导航栏，有Search、New Issue等选项。中间是Issue详情，标题为“需求：workspace下的members支持批量邀请”，”，下方有Sub - issues、Activity等](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=ZmYyMmIzNzc0Yzk1Y2RhY2YyNWRjZmZiODZkNjZiOGJfYjJkMWQ3YThkMDFjMGRjZDBiZTU1ZTNkOGYxMzhmZjNfSUQ6NzYzMjIxNTQyOTA1NDQxODExNF8xNzgyNDY5MjQ1OjE3ODI0NzI4NDVfVjM)
</column>
<column width-ratio="0.250000">
![图片展示的是MiCA-Issue协作界面。左侧为导航栏，有Search、](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=MDE3M2Y0MTY4NzU1MDNlMzhiNzU3NzdiNDMyODA2YzZfZjIzZTU1ZjUyOTYzZWZmZDYyOWUzNmZiNzg3OTFkNTVfSUQ6NzYzMjIxNTQyNzk5Mzk2MzczMF8xNzgyNDY5MjQ1OjE3ODI0NzI4NDVfVjM)
</column>
<column width-ratio="0.250000">
![图片展示的是J 自动生成图片](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=Y2Q1ZjM5YjVkNGZmNTE5OTc4MDEwNGYyMGU1NWQyNjJfOGJiODlhMTRjMGJhODg4NjRmYjMwMjZjYzUxZGNkMTNfSUQ6NzYzMjIxNTQzMTMzOTcyMzk3M18xNzgyNDY5MjQ1OjE3ODI0NzI4NDVfVjM)
</column>
</grid>

<table><colgroup><col/><col/><col/></colgroup><thead><tr><th>功能</th><th>在项目里怎么用</th><th>主要解决的问题</th></tr></thead><tbody><tr><td>Issue 管理</td><td>用主 issue 承接一个需求或问题，再按页面、模块、角色拆子 issue；支持状态流转、评论、附件、时间线<whiteboard token="HQHkwVDGrhviqLbaPovck6AAnLk"></whiteboard></td><td>让任务不散在聊天、代码和口头同步里</td></tr><tr><td>人机统一分配</td><td>同一套 assignee 机制里既能分给人，也能分给 Agent</td><td>让人和 Agent 进入同一条推进链路</td></tr><tr><td>Inbox 通知</td><td>创建、评论、状态变更、Agent 执行结果都能主动提醒</td><td>让关键节点不靠人反复追问</td></tr><tr><td>Projects 项目层</td><td>把多个 issue 聚合到项目里，看优先级、状态、进度和负责人</td><td>让并行需求有统一视角，而不是一条条单看</td></tr><tr><td>实时协作</td><td>issue、评论、Agent 状态、任务进度、Inbox、Wiki等即时同步</td><td>让多人和多 Agent 协作时，进展始终是同一份现场</td></tr></tbody></table>

## 1.2 Agent管理

<grid>
<column width-ratio="0.333333">
![图片展示的是search-mica@search.mta.ary中的Clarifyer](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=MzdiNWQ5NjQxNTI2Yjc4NjVjODFiNWQ5MDYyNzRlNGFfMjJmNzk3ZmEzMmU2MzIzZmIyYmNkNzFjY2E2ZTBlNTZfSUQ6NzYzMjIxMDYyNzU2OTgxNDcwNl8xNzgyNDY5MjQ1OjE3ODI0NzI4NDVfVjM)
</column>
<column width-ratio="0.333333">
![图片展示了一个Agent管理界面，左侧栏列出了不同角色的Agent，如Clarifier、Executor、Reviewer等。选中的Clarifier Agent在右侧显示其配置维度相关内容，其中“Task Queue”板块列出了多个任务及其状态，多数任务状态为Completed。这与文档中提到的Agent管理中每个Agent有多个配置维度，以及任务队列与状态等核心能力相呼应，直观呈现了Agent管理界面中任务队列及状态的具体情况。](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=Mzg5MzMwOTdmMDU1MjI5YzJmMGU1NjdiY2Y2NTQwN2ZfY2NiMzYxOGY1YzJmODYyYzdjNzVhZTVkNzlkNDExMTdfSUQ6NzYzMjIxMDYyNDk5MDk3Mjg3MF8xNzgyNDY5MjQ1OjE3ODI0NzI4NDVfVjM)
</column>
<column width-ratio="0.333333">
![图片展示 addCriterion驱动的Managed Agent探索实践\[heading1\]一、是什么--核心能力\[heading2\]1.2 Agent管理\[content\]\[block_sep\]\[block_sep\]<qa:image></qa>展示了MiCA平台中Agent管理界面。左侧为导航栏，有showcase、Search...、New Issue等选项，当前选中Agents。右侧是Agent列表_id列表，包括Clarifier、Executor、Reviewer等角色，每个角色旁有“edit“](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=YTAwZDQyNzRiZjdlMmIzMzY3Njc2MDkyYTAwYTk1NGNfMjQwNWZjZWI2MTA2MTBjMjY1NDY5ZjQ0OGQ2MDM0ZWFfSUQ6NzYzMjIxMDYyNDM0NTE0ODM2NF8xNzgyNDY5MjQ1OjE3ODI0NzI4NDVfVjM)
</column>
</grid>

每个 Agent 是一个完整的实体，拥有多个配置维度。

| 能力 | 具体内容 | 在项目里的价值 |
|-|-|-|
| Agent 角色化 | 可按 Monitor、Clarifier、Executor、Reviewer、QA 等角色拆分职责 | 让 Agent 不只是一个通用助手，而是团队里的具体工种 |
| Agent 配置化 | 每个 Agent 都可独立配置 Instructions、Skills、Memory、环境变量和运行参数 | 让不同 Agent 能稳定承担不同类型任务 |
| 任务队列与状态 | 支持 queued、running、completed、failed 等任务状态，以及 idle、working、blocked、error 等运行状态 | 让 Agent 的执行可分配、可观察、可追踪 |
| 定时任务 |  |  |
| 过程透明化 | 支持实时工作面板、执行历史、工具调用和 Token 用量统计 | 让人能看见 Agent 做了什么，而不是只看到结果 |
| 双运行时与自动运行 | 支持 Local / Cloud 两种运行方式，以及定时任务、Webhook、API 触发 | 让 Agent 既能处理本地私有任务，也能承接持续自动化工作 |

## 1.3 双运行时架构

![图片展示的是MiCA-Issue驱动的Managed Agent探索实践文档中，MiCA平台的“Runtimes”页面。左侧为导航栏，有showcase、Search...、New Issue等选项。右侧显示了Claude、Opencode、Hermes三个运行时，其中Claude被选中。右侧详细信息栏括Claude的Provider为Claude，Status为online，Owner为fanghailaot，还列出了Device、CLI Version、Connection Test等信息，下方有Token Usage、Activity、Hourly Distribution等数据图表。该图直观呈现了文档中介绍的MiCA平台运行时相关功能。](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=MjUxYmIyZTE3YWFhY2FiZTkyODdlNjIxMTRkY2JkMzBfNTZlNmUxYzljNDE0MzFhNTRjOWM1MzViY2E1Zjc5M2FfSUQ6NzYzMjIxODQ3NjgxNjUxODMzOF8xNzgyNDY5MjQ1OjE3ODI0NzI4NDVfVjM)

| 运行时 | 适用场景 | 特点 |
|-|-|-|
| \*\*Local（Daemon）\*\* | 开发调试、私有代码 | 在开发者本机运行，可访问本地 repo |
| \*\*Cloud\*\* | 生产部署、团队共享 | 云端运行，支持多 Provider |

**Local Daemon 能力**：

- Desktop 应用内置 CLI 管理：自动安装、版本检测、升级提示
- Profile 隔离：不同 API 地址独立 profile 目录
- 每 5 秒健康检查，安全升级（等待活跃任务完成后再重启）
- 日志实时 tail 到桌面端

**任务执行流程**：

1. Daemon 从服务端 Claim 任务
2. 准备隔离执行环境（repo 缓存、Skills 注入、Memory 加载、Wiki 上下文）
3. 启动 Agent 后端（支持 Claude Code、Codex 等多种 Provider）
4. 流式回传消息（thinking → tool_use → tool_result → text）
5. 完成后提取记忆、上报用量，保存 session 用于后续恢复

# 二、怎么用 -- 典型协作场景

> 以具体协作场景，展示人 + Agent 如何在 MiCA 上协作完成一次完整交付

## 2.1 问题修复

> bugfix子场景下，一个完整的闭环协作流程是怎样的

在问题修复场景中，MiCA 将“发现问题、分析定位、修复提交、审查验证、关闭归档”串成同一条可追溯链路。bugfix案例：<cite doc-id="ZqdOdDdERorwHDxHjwVc24SfnQb" file-type="docx" title="一个Bug 从发现到修复" type="doc"></cite>

<whiteboard token="WcE9w8x4jhMjCDbIaCucDSplnmc"></whiteboard>

1. **信息输入**：测试或研发先将运行环境、异常现象、预期结果与实际结果整理成 Issue，让问题从一开始就具备可复现、可讨论的上下文。
2. **多角色Agent执行**：人工在 Issue 中 @Agent 发起问题排查、修复方案输出、代码修改、代码审核等操作。
3. **人工审核**：人需要对中间过程进行审核把关。比如过程中出现环境问题、上下文缺失或判断偏差，人需要继续补充信息、修正方向，或切换更合适的 Agent。
4. **结果验收：**人对结果负责，需要确保问题完成修复，再合入 MR、关闭 Issue，整个过程从问题发现到结果验收都可追踪、可复盘。



## 2.2 代码审查 

> 代码审查子场景下，一个完整的闭环协作流程是怎样的
> 
> 内容组织思路：场景化，一步步怎么交付

**闭环流程**：手动/自动创建一个MR issue -> agent分析Diff -> agent 执行多视角CR并共识 ->人指派agent修复->完成issue

<readonly-block type="isv"></readonly-block>

> 图例：🔵 蓝色 = 人操作 | 🟣 紫色 = Agent 执行 | 🟡 黄色 = 决策点 | 🟢 绿色 = 完成 | 🟣蓝紫色 = 人+Agent 协作

**多视角CR Agent 设计原则**：

> 搭建了多视角 CR 陪审团——5 个独立审查视角（逻辑/安全/性能/对抗/规范）各自独立审查代码，通过共识度机制合并去重（多个视角发现同一问题 = 高可信），生成带 before/after 修复代码的结构化评审，自动发布到 GitLab MR 上。整套方案不侵入用户项目代码。

<table><colgroup><col/><col/><col/></colgroup><tbody><tr><td>原则</td><td>做法</td><td></td></tr><tr><td>对抗性</td><td>5 个视角各自独立审查，互不参考（多skills）</td><td rowspan="4"><img name="image.png" alt="图片图展示了MiCA-Issue驱动的Managed Agent在代码审查中的对抗性CR陪审团流程。首席法官（Claude Opus 4）汇总裁决，从逻辑（Claude）、安全（GPT - 5.1）、性能（Gemini 3）、恶魔辩护（Kimi K2 addCriterion）和规范（Claude）五个视角独立审查，互不参考。每个视角发现的问题附带before/after修复代码，首席法官综合判断后给出APPROVE、REQUEST_CHANGES或BLOCK的结论，整个流程耗时约8分钟。" href="https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=NzcxZDA5MzhlYmVjOTMzMDg4MjdkNmRjMDVhODM3ZjBfZDE1MjRhMmE4ZjM2MDgyNWMxNGIxNGMyODI1ZjA1MjhfSUQ6NzYzMjIzMTI4MDEwODczNTY2OF8xNzgyNDY5MjQ1OjE3ODI0NzI4NDVfVjM" mime="image/png" scale="1.205882" src="UQRobCwdnorZVXx5DjFca0m3neG"/></td></tr><tr><td>共识大于个体</td><td>多个视角发现同一问题 = 高可信，单一视角 = 可能噪音</td></tr><tr><td>可执行</td><td>每个发现附带 before/after 修复代码</td></tr><tr><td>结构化</td><td>PR Quality Score（0-10）、Must Fix / Should Fix / Notes 分级、置信度评分</td></tr></tbody></table>

## 2.3 需求交付

典型的核心工作流如下：

```Plain Text
用户/AI 创建 issue
      │
      ▼
  Clarifier ── 多视角澄清 → 影响分析 → 拆分子 issue（高复杂度等人工确认）
      │
      ▼
  Executor ── 白盒测试先行 → 编码 → make check → 提 MR
      │
      ├──→ ReviewCoordinator ──→ Specialists（并行）──→ Confidence Gate → Report
      ├──→ QA（黑盒测试，并行）
      │
      ▼
  合并 → Monitor（持续监控 + 质量指标 + 学习日志）
```

需求案例：<cite doc-id="DFmRdWLuMo3AdSxxtL7cHEyPnBG" file-type="docx" title="一个需求从提出到落地" type="doc"></cite>

# 三、进化飞轮 -- 新机制能力

## 3.1 Memory机制

![图片展示的是Memory机制相关界面，可管理workspace和agent的记忆，帮助Agent跨任务保留知识。界面左侧有导航栏，包括Showcase、Search、My Issues等项目，选中了Memory项。右侧显示Memory的分类标签，有Knowledge、Feedback、Discovery、Reference等，下方呈现各标签下具体的记忆条目内容。此图片与上文介绍的Agent可跨任务保留和积累知识，以及Memory的4种类型、2种来源和2种范围等内容相关，是对Memory机制的直观呈现。](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=Y2QxMDBjYTQ1NTVjYzllMmQwMjBmZDFmMWJmYjg0MzZfYzA4OTQyNmI1NzNhMGJmOTM0MjJkMzAxYTJkNjI5ODBfSUQ6NzYzMjE3NzY1NjIwMDQ5ODEwN18xNzgyNDY5MjQ1OjE3ODI0NzI4NDVfVjM)

Agent 可以跨任务保留和积累知识：

- 4 种类型：knowledge / feedback / discovery / reference
- 2 种来源：manual（人工创建）、learned（Agent 从任务中自动学习）
- 2 种范围：workspace（全团队共享）、agent（Agent 专属）

## 3.2 Wiki 知识库复利

<grid>
<column width-ratio="0.500000">
![图片展示的是MiCIA系统中Wiki知识库界面。左侧为导航栏，有Builder、Search、New Issue等选项。右侧是Wiki列表，显示了多个条目，如“知识条件状态的校验”“知识因素类型定义”等，每个条目后有“pending”“approved”“archarcharrow; archived”等状态标识，还有“wiki”“design”“api”等标签，以及更新时间。界面右上角有“New entry”按钮。该图与文档中介绍Wiki知识库复利的内容相关，直观呈现了Wiki知识库的条目情况。](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=MDM3OTJiOTZmNTdjMTM0OTEwNTk3ZDY2MjRhZDAzOTNfNjQyOTM3ZmM1OTMyNjU1M2VjMzJlNzdiOTRiZTczNzVfSUQ6NzYzMjE3NzY1NjE5MjIwODA2N18xNzgyNDY5MjQ1OjE3ODI0NzI4NDVfVjM)
</column>
<column width-ratio="0.500000">
![图片展示了MiCA系统 - Issue驱动的的 Managed Agent探索实践文档中“记忆文件结构约定”部分内容所在位置。主要内容为agent_context/memories.md文件格式约定，包括Workspace Knowledge和Agent Memory章节，每个章节以# 开头，每条记忆以“- \[type\] (content)”格式呈现，且对记忆内容长度、规则等有详细说明。该图片与上下文紧密相关，是对文档中记忆文件结构约定的部分内容的](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=Y2Y3MjVhNTI1OGJlMGIwN2EyMzRkZWY3M2IwY2ZkZTFfMTliNTEwNjliMDhmZDFlMGNjOTIyNjQ5MDk4NWIxNmFfSUQ6NzYzMjE3NzY1MzM4MjIyMDc0N18xNzgyNDY5MjQ1OjE3ODI0NzI4NDVfVjM)
</column>
</grid>

团队结构化知识管理：

- 6 种条目类型：Decision / Lesson Learned / Convention / How-to / Glossary / FAQ
- 生命周期：pending → approved → archived / superseded / rejected
- 知识健康度评分（整体分 + 维度分）
- 条目之间交叉引用（related / supersedes / implements / contradicts / source）
- **亮点：从 issue 自动提取知识** —— 一键将 issue 对话中的经验沉淀为 Wiki 条目

## 3.3 自进化飞轮

![图片展示了Multica Agent & Team自进化架构，包含感知、决策、执行及闭环进化四个环节。感知环节有Event Bus、Task Messages、Wiki/Memory、Activity Log；决策环节有Rule Engine、Confidence Gate、Delegation Protocol、Learning Loop；执行环节有Local Daemon、Cloud Runtime；闭环进化环节有人类评审、Autopilot。右侧有三重评审、学习日志、Benchmark等内容。该图与文档中“自进化飞轮”部分上下文对应，直观呈现了Agent自进化架构。](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=Yjk3ZWE0YmZmYTUyMTc1OGY3MDM4OTBkN2MyNjE3Y2ZfZTU5OTAxODc2YTUxYmFhMGExY2FiOGM1NjQ2NTJkNmNfSUQ6NzYzMjIzMzgzNzQ3MzQ1MTIyNl8xNzgyNDY5MjQ1OjE3ODI0NzI4NDVfVjM)

# 四、参与贡献

## 4.1 Roadmap规划

- 已完成

  - 核心 Issue 管理（Board + List + Detail）
  - Agent 管理全生命周期
  - 5 类 Agent 角色
  - Inbox 通知
  - Autopilot 定时任务
  - Skills 技能系统
  - Memory 记忆系统
  - Wiki 知识库
  - Desktop 多 Tab 应用
  - Local + Cloud 双运行时
  - Token 用量追踪
- 计划中

| 方向 | 内容 | 价值 |
|-|-|-|
| 深度规划 | Issue 级别可修订的规划文档；Agent 在执行前产出提案供人类审阅 |  |
| 交互友好的实时感知 | 升级TUI，方便Agent过程信息可视化、可审计 |  |
| 产出物与工作成果 | Agent 产出（PR、文档、报告）作为一等对象，支持预览和部署 |  |
| Agent 审查与审批 | Agent 产出的审批门控、审阅者路由、审计追踪 |  |
| 结果强制保障 | Agent 产出必须满足可验证标准（CI 通过、PR 合并、测试通过） |  |
| 自组织 | Agent 主动提出工作流优化、角色调整、任务委派改进建议 |  |
| Agent 评测体系 | 量化 Agent 质量：成功率、代码质量、响应时间 | 知道哪个 Agent 靠谱 |
| 技能市场 | 能力可发布、可组合、可评分 | 社区生态 |
| 更多 Provider | 支持更多 LLM 后端 | 灵活选择 |
| 工作流编排 | 可视化多 Agent 协作流水线 | 复杂场景自动化 |

## 4.2 参与贡献 

<callout emoji="💡">
**愿景**：建设内部的 AI Native 研发协作系统——**让 AI Agent 成为团队的正式成员**，能认领任务、写代码、做 CR、跑测试。
**做了什么**：已经跑通一个完整的、可自动化**创建需求issue** ->**Clarifier**->**Auto** **code -> CR**的工作链路。
**如何加入**：看到想做的方向，群里说一声直接开始，不需要审批不需要排期
> - 技术群：见下方群名片
> - 自部署平台地址：http://staging-multica-ai.search.miui.srv/
> - 代码仓库：https://git.n.xiaomi.com/aisearch/multica
**你将获得什么：**
> - **AI Agent 工程化实战**：不是写 prompt，是做 Agent 编排、多模型调度、Skill 系统设计
> - **自己先用**：你做的工具自己每天用，一个好 Skill 能让团队 20 人受益，杠杆效应在业务开发里罕见
> - **视角升级**：从"用 AI 写代码"到"让 AI 替团队工作"，亲历 AI Native 研发流程的演进
> - **经验沉淀**：从 0 到 1 搭建企业级 AI Agent 平台，比普通业务需求更有分量
</callout>

**群名片**：

<chat_card name="MiCA 使用交流群" chat-id="oc_1228704b2ab0db0520a09a7424b80d81"></chat_card>

1. **如何开始贡献**：

> **Step 1 — 选方向**
> 
> 看上面的计划方向列表，选一个你感兴趣的。不确定选什么，在群里问。
> 
> **Step 2 — 了解代码和平台**
> 
> 1. 阅读 Multica 官方文档：<https://github.com/multica-ai/multica>
> 2. 本地跑起来：
> 
>    ```Bash
>    // 仓库：https://git.n.xiaomi.com/aisearch/multica
>    git clone <repo>
>    make dev
>    ```
> 3. 在 Multica Web UI 体验完整流程：创建 Issue → assign Agent → 查看结果
> 
> **Step 3 — 认领任务**
> 
> 在「具体待办」中选一个，在群里说一声 \*"我来做 XXX"\*，然后：
> 
> - 创建分支：feat/<方向>-<任务名>
> - Complex 任务：先提设计方案 MR，评审通过后再编码
> - Simple / Medium 任务：直接开发，提 MR
> - 自测：用 CR 陪审团 review 你自己的 MR（吃自己的狗粮）
> 
> **Step 4 — 提交 MR**
> 
> - 分支命名：`feat/<name>` / `fix/<name>` / `refactor/<name>`
> - 提交信息：`feat: add webhook receiver for GitLab MR events`
> - MR 描述：写清楚改了什么、为什么、怎么验证
> - 必须通过 CR Agent 审查

# 五、Q&A

**Q：MiCA 和 Meego / Jira AI 有什么本质区别？**

 Meego/Jira 的 AI 是"功能"（帮写描述、总结评论）。MiCA 的 Agent 是"成员"（被分配任务、创建 issue、推进状态、和其他 Agent 协作）。数据模型层面就不一样。

**Q：Agent 会不会失控**

不会。所有关键决策由人类把控：分诊、最终审批、上线。Agent 的每一步操作都在 issue timeline 上，完全可追溯。

**Q：Agent 执行成本怎么控制？**

每个任务的 Token 用量记录在 issue 上。Runtimes 页面有完整仪表盘：活跃度热力图、每日 Token 图表、成本估算、按模型分布。每一分钱花在哪里都清楚。

**Q：私有代码安全吗？**

Local Daemon 模式下代码不离开开发者机器。Agent 本地执行，只有状态更新和消息流回传服务端。Private Agent 可见性确保只有创建者能使用。