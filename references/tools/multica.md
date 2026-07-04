# Multica

> 让 coding agents 变成**真正的队友**——像分配给同事一样把 issue 分给 agent；agent 自己接活、写代码、报 blocker、更新状态。
>
> 上游：[github.com/multica-ai/multica](https://github.com/multica-ai/multica) · [官网/Cloud](https://multica.ai) · [X](https://x.com/MulticaAI) · MIT License

---

## 一、它解决什么

> "你下一个雇 10 个人——可能不是人。"

传统 AI 编码工具的工作流是：**人开 IDE → 人写 prompt → 人盯着 agent 跑 → 人复制结果**。这个链条的每一步都需要人在场，agent 本质还是工具。

Multica 把这件事翻转过来：

```
传统：       agent 是工具
            ↓
            人发起 → 人监督 → 人收尾

Multica：    agent 是队友
            ↓
            issue 被 assign 给 agent → agent 自动 claim → 自动执行
            → 在 board 上更新状态 → 评论 → 发现 blocker 主动报
```

→ 像 GitHub Issues 那样的**任务系统 + 看板 + 评论流**，但 assignee 既可以是人也可以是 agent。

---

## 二、为什么叫 Multica

**Mul**tiplexed **I**nformation and **C**omputing **A**gent。

致敬 1960 年代的 Multics——那个"分时共享"的开山之作（Unix 是它的简化版）。Multica 打的赌是：**软件团队几十年来一直是单线程的**（一人一任务一上下文），AI agent 改变了这个等式。Multica 把"分时共享"带回，但这次"复用机器"的"用户"既是人也是 agent。

> "团队人少不应该等于团队小。系统对了，2 个工程师 + 一队 agent 能跑得像 20 个人。"

---

## 三、核心特性

| 特性 | 干什么 |
|---|---|
| **Agents as Teammates** | Agent 有 profile，能在看板上、能评论、能开 issue、能主动报 blocker |
| **Squads** | 把多个 agent（或人）组队，由一个 leader agent 路由——`@FrontendTeam` 而不是 `@alice-or-bob-or-carol` |
| **Autonomous Execution** | 全任务生命周期管理（enqueue / claim / start / complete / fail）+ WebSocket 实时进度流 |
| **Autopilots** | 给 agent 排期：cron / webhook / 手动；每次自动开 issue 路由给 agent——日报、周报、定期审计自动跑 |
| **Reusable Skills** | 每个解决方案沉淀成 skill 给全队复用——deployments / migrations / code review 累计 |
| **Unified Runtimes** | 一个 dashboard 管所有计算资源（本地 daemon + 云端 runtime）；自动检测可用 CLI；实时监控 |
| **Multi-Workspace** | workspace 级别隔离——每个 workspace 自己的 agents / issues / settings |

支持的 agent 后端：Claude Code、Codex、GitHub Copilot CLI、OpenClaw、OpenCode、Hermes、Gemini、Pi、Cursor Agent、Kimi、Kiro CLI（vendor-neutral，自托管，跨工具中立）。

---

## 四、架构

```
┌──────────────┐     ┌──────────────┐     ┌──────────────────┐
│   Next.js    │────>│  Go Backend  │────>│   PostgreSQL     │
│   Frontend   │<────│  (Chi + WS)  │<────│   (pgvector)     │
└──────────────┘     └──────┬───────┘     └──────────────────┘
                            │
                     ┌──────┴───────┐
                     │ Agent Daemon │  ← 跑在你机器上
                     └──────────────┘    （Claude Code / Codex / Copilot CLI /
                                            OpenCode / OpenClaw / Hermes / Gemini /
                                            Pi / Cursor Agent / Kimi / Kiro CLI）
```

| Layer | Stack |
|---|---|
| Frontend | **Next.js 16**（App Router） |
| Backend | **Go**（Chi router、sqlc、gorilla/websocket） |
| Database | **PostgreSQL 17 + pgvector** |
| Agent Runtime | 本地 daemon 调用各种 coding agent CLI |

**关键观察**：Multica 自己**不实现 LLM 调用**——它是 agent CLI 的**调度层 + 任务系统 + 看板 UI**。底层执行交给 Claude Code / Codex 等成熟工具。这是它能"vendor-neutral"的根因。

---

## 五、关键概念

### 5.1 Runtime

一个**能执行 agent task 的计算环境**。可以是：
- 本地机器（通过 daemon 暴露）
- 云端实例

每个 runtime 上报"我有哪些 CLI 可用"，Multica 据此决定派活到哪台机器。

### 5.2 Agent

一个**配置实体**——绑定到某个 runtime + 某个 provider（Claude Code / Codex / ...）+ 一个名字。这个名字会出现在 board / 评论 / assignee 选择里，跟人一样。

### 5.3 Issue

一个任务单元。可以 assign 给 human 或 agent。被 assign 给 agent 时，agent 在它绑定的 runtime 上自动 claim → execute → 报告进度。

### 5.4 Squad

**让"路由稳定性"和"团队规模"解耦**：
- 把若干 agent + 人组成一个 squad，指定一个 leader agent
- assign 给 squad 而不是具体成员
- leader 决定具体派给谁
- 团队增减成员不影响外部的 assign 习惯

### 5.5 Autopilot

定时器 + webhook + 手动触发的 trigger。每次触发自动**开 issue 并 assign 给 agent**——把"周期性事项"变成"agent 自动跑"。

---

## 六、快速安装

### macOS / Linux（推荐 Homebrew）

```bash
brew install multica-ai/tap/multica
```

升级：`brew upgrade multica-ai/tap/multica`

### macOS / Linux（脚本）

```bash
curl -fsSL https://raw.githubusercontent.com/multica-ai/multica/main/scripts/install.sh | bash
```

### Windows（PowerShell）

```powershell
irm https://raw.githubusercontent.com/multica-ai/multica/main/scripts/install.ps1 | iex
```

### 一键 setup

```bash
multica setup          # 配置 + 登录 + 启动 daemon（连 Multica Cloud）
```

### 自托管

```bash
curl -fsSL https://raw.githubusercontent.com/multica-ai/multica/main/scripts/install.sh | bash -s -- --with-server
multica setup self-host
```

会从 GHCR 拉官方镜像（默认 latest stable），需要 Docker。详见上游 [SELF_HOSTING.md](https://github.com/multica-ai/multica/blob/main/SELF_HOSTING.md)。

---

## 七、CLI 速查

| 命令 | 干什么 |
|---|---|
| `multica login` | 浏览器登录 |
| `multica daemon start` | 启动本地 agent runtime |
| `multica daemon status` | 看 daemon 状态 |
| `multica setup` | 一键 setup（连 Cloud） |
| `multica setup self-host` | 一键 setup（自托管） |
| `multica workspace list` | 列工作区（当前 `*`） |
| `multica workspace switch <id\|slug>` | 切默认工作区 |
| `multica issue list` | 列 issue |
| `multica issue create` | 开 issue |
| `multica update` | 更新 |

详见上游 [CLI_AND_DAEMON.md](https://github.com/multica-ai/multica/blob/main/CLI_AND_DAEMON.md)。

---

## 八、和本工作区的关系

### 8.1 在 [`pm-workspace-starter/`](../) 整体定位

| 模块 | 角色 |
|---|---|
| [`agent-llm/`](../agent-llm/) | Agent 的**原理**（ReAct、ToT、Memory） |
| [`ice-workbench/`](../ice-workbench/) | 一个**单工作台、对话式**的 Agent 应用 |
| [`understand-anything/`](../understand-anything/) | 把 codebase 变知识图谱（**理解**层） |
| **本目录（multica）** | 把 agent 当**队友**的**协作管理**层（**生产**层） |

ice-workbench 解决的是"**单个用户**和 **N 个 Agent** 一起工作"；Multica 解决的是"**整个团队**（人 + N 个 Agent）一起工作，**任务级别可追踪**"。

二者**不冲突**——可以让 ice-workbench 跑在 Multica 的 runtime 上，作为团队里"专门干数据分析的 agent"。

### 8.2 Multica + ice-workbench：可能的整合方式

#### 用法 A — Multica 调度 ice-workbench Agent

把 ice-workbench 的 [`agents/`](../ice-workbench/agents/)（data-analysis / biz-insight 等）封装成 Multica 的一种"provider"：

```
Multica daemon 检测到本机有 ice-workbench → 注册成可用 agent
↓
团队在 Multica 看板上 assign issue 给 "data-analysis-agent"
↓
Multica 调用 ice-workbench 的 [`bg_task_svc.py`](../ice-workbench/backend/app/services/bg_task_svc.py) 跑后台任务
↓
完成后 ice-workbench 把结果（文件 / 报告）回写 Multica issue
```

→ 把 ice-workbench 从"单个 PM 自己的工作台"升级成"**给整个团队提供数据 agent 服务**"。

#### 用法 B — ice-workbench 复用 Multica 的 Skill 概念

Multica 的 "Reusable Skills" 和 ice-workbench 的 [`skills/`](../ice-workbench/skills/) 在概念上几乎一致——都是"沉淀解决方案给全队复用"。可以做到 **schema 兼容**：

```
ice-workbench skill (JSON schema + sandbox)
        ↕ 双向同步
Multica skill registry
```

#### 用法 C — Autopilot 替代 ice-workbench scheduler

ice-workbench 自己有 scheduler（[`backend/app/services/scheduler_svc.py`](../ice-workbench/backend/app/services/scheduler_svc.py)，每 20s 扫一次）。如果团队级别要做"日报 / 周报 / 定期审计"，Multica 的 Autopilot 是更合适的层——issue 化、可追踪、可看板上看到状态。

### 8.3 和 [`agent-llm/agents/`](../agent-llm/agents/) 对应

Multica 把 [`agent-llm/agents/react-and-variants.md`](../agent-llm/agents/react-and-variants.md) 里一个被反复提及但没人讲清楚的话题落地：

> **"多 Agent 不是更高级的单 Agent，而是用模拟分工解决单 Agent 难解的问题"**

Multica 的 **Squad + Leader** 模式正是 [`react-and-variants.md §8`](../agent-llm/agents/react-and-variants.md) 描述的"角色明确切开"的实现：

```
Manager / Planner / Researcher / Coder / Critic / Tester
        ↓
Multica Squad：每个 agent 一个 profile + provider，leader 路由
```

→ 想看"Multi-Agent 在生产环境怎么落"——Multica 是开源样本里**最完整的一个**。

---

## 九、与传统项目管理工具（Linear / Jira / GitHub Projects）的差异

| 维度 | Linear / Jira | Multica |
|---|---|---|
| Issue assignee | 只能是人 | 人 / agent / squad |
| Agent 集成 | 通过 webhook 旁挂（有限） | agent 是 first-class 实体 |
| 任务执行 | 人手动做 | agent 自动 claim / execute |
| 进度报告 | 人写 comment | agent 自动 stream（WebSocket） |
| Skill 沉淀 | 文档（被动） | reusable skill（主动复用） |
| 周期性任务 | 模板 + 提醒 | autopilot 自动开 issue + 自动派 |

→ Multica 不是"加了 AI 的 Linear"，是**为 human + AI 团队从底设计的协作系统**。

---

## 十、典型使用流（团队视角）

```
□ 1. brew install multica-ai/tap/multica
□ 2. multica setup（连 Cloud 或 self-host）
□ 3. Web app → Settings → Runtimes 验证本机已上线
□ 4. Settings → Agents → New Agent
   • 选 runtime（你的机器）
   • 选 provider（claude / codex / cursor-agent / ...）
   • 起名（"@DataBot" / "@DocsBot"）
□ 5. 团队成员一起 onboard agent 到 squad
□ 6. 在 board 上 assign issue 给 agent / squad
□ 7. 真正高频的事情设 autopilot（cron 每天 9:00 → @DocsBot 写日报）
□ 8. 沉淀 skill 给全队复用
```

---

## 十一、相关链接

- 项目：[github.com/multica-ai/multica](https://github.com/multica-ai/multica)
- 官网 / Cloud：[multica.ai](https://multica.ai)
- 自托管指南：[SELF_HOSTING.md](https://github.com/multica-ai/multica/blob/main/SELF_HOSTING.md)
- CLI 文档：[CLI_AND_DAEMON.md](https://github.com/multica-ai/multica/blob/main/CLI_AND_DAEMON.md)
- 贡献指南：[CONTRIBUTING.md](https://github.com/multica-ai/multica/blob/main/CONTRIBUTING.md)
- iOS 客户端：[apps/mobile/](https://github.com/multica-ai/multica/tree/main/apps/mobile)

### 在本工作区的衔接

- 多 Agent 协作范式：[`../agent-llm/agents/react-and-variants.md`](../agent-llm/agents/react-and-variants.md)
- 单工作台对照：[`../ice-workbench/`](../ice-workbench/)
- 代码理解层（互补）：[`../understand-anything/`](../understand-anything/)
