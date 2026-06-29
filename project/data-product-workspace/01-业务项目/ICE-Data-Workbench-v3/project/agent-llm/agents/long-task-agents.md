# 长任务 Agent：Claude Code / OpenHands / Manus / Devin

> 本文聚焦"跨数十步乃至数百步、跨数小时甚至跨会话"的长任务 Agent。讲清楚它们各自的设计哲学、共性策略、以及和"轻量 Coding Agent"（Cursor / Cline / Aider）的本质区别。
>
> 配套：[skills-system-design.md](skills-system-design.md)（Skills 实现）、[research-agent-architecture.md](research-agent-architecture.md)（端到端研究 Agent）。

---

## 一、长任务的核心命题

### 1. 什么叫"长任务"

不是"任务复杂"，是：
- **跨数十步乃至数百步**：完成一次重构、修一个 bug、写一份研报，需要几十次工具调用
- **跨数小时**：单次任务时长以小时计，不是分钟
- **跨数千 token 决策**：每一步都要看历史、想下一步
- **可能跨会话**：一次没跑完，下次接着跑

**对比**："今天天气怎么样" 是短任务。"把这个 monorepo 从 webpack 迁移到 vite" 是长任务。

### 2. 为什么大多数 Agent 跑不过 10 步

短任务跑得好的 Agent，跑长任务时几乎都会**死在同一些地方**：

| 失败模式 | 现象 | 根因 |
|---|---|---|
| **上下文爆炸** | 跑到第 15 步 token 用完 | 所有中间结果都堆在 context |
| **目标漂移** | 第 20 步开始做和原任务无关的事 | 早期目标被中间细节淹没 |
| **错误累积** | 每步看似对，但叠加起来错 | 没有自检 / 自纠错机制 |
| **死循环** | A 调 B、B 调 A、反复 | 没有终止条件 / 没有"我做不到" |
| **重复劳动** | 已经查过的东西又查 | 没有内部记忆 / 没看 history |
| **工具过载** | 50 个工具，模型选错一半 | 工具描述塞满 context |

**所有"长任务 Agent 框架"本质都在解决这 6 个问题**——只是策略不同。

---

## 二、四家产品级方案的核心矩阵

| | Claude Code | OpenHands (前 OpenDevin) | Manus | Devin |
|---|---|---|---|---|
| **定位** | 编码 / 终端任务 | 通用软件工程 Agent | 通用长任务 Agent | 自主软件工程师 |
| **运行环境** | 用户本机 | Docker 沙箱 | 云端沙箱 | 云端 + IDE |
| **主控** | 单 Agent + Task 子 Agent | 多 Agent 协作 | 单 Agent + 文件计划 | 单 Agent + 内部规划 |
| **上下文管理** | 子 Agent 隔离 + Skill 加载 | Memory + 摘要 | 文件系统当记忆 | 内部 + 浏览器 |
| **工具集** | 精简（Read/Edit/Bash/Task...） | 丰富（含浏览器、代码执行） | 极丰富（含浏览器、文件、终端） | 终端 + 浏览器 + IDE |
| **可见性** | 用户全程可见 | 半透明 | 实时 stream | 几乎黑盒 |
| **是否开源** | SDK 开源，主程序闭源 | ✅ 开源 | ❌ 闭源 | ❌ 闭源 |
| **杀手锏** | Task subagent + Skills + Hooks | 多 agent 协作 + 完全可控 | 文件式记忆 + 长任务持续 | 完全自主 |

---

## 三、Claude Code —— "工具极简 + 子 Agent 隔离"

### 1. 核心设计哲学

Anthropic 自己的话："**Tools, not agents**"。

> 不要堆叠多个对话式 Agent，给一个强 Agent 设计**最小可用、组合性高**的工具集。

### 2. 关键设计

#### 工具集极致精简

Claude Code 的全部核心工具：
```
Read, Edit, Write           — 文件 IO
Bash                        — 终端
Glob, Grep                  — 搜索
Task                        — 派子 Agent
WebFetch, WebSearch         — 网络
TodoWrite                   — 自我规划
NotebookEdit                — Jupyter
```

**对比 LangChain 之类**：动辄 100+ 工具。Claude Code 用 ~12 个核心工具能干几乎所有事。

**为什么这样设计**：
- **Bash 是元工具**：能跑 git / npm / curl / find / sed / awk → 不需要为每个工具单独包一层
- **Read/Edit 是文件操作的最小集**：不需要 RenameFile / CopyFile / DeleteFile
- **工具越少 → context 越省 → 选错率越低**

#### Task 子 Agent —— 长任务的关键

详见 [subagent-patterns.md](subagent-patterns.md)。**核心机制**：

```
主 Agent 的 context：
   ├── 用户原始任务
   ├── 高层规划（TodoWrite）
   ├── 自己做的关键决策
   └── 派 Task → 子 Agent 自己跑 → 只回传结论

子 Agent 的 context（独立、用完即弃）：
   ├── 5 个文件的内容
   ├── 100 次 grep 结果
   ├── 大量中间错误日志
   └── 跑完 → 主 Agent 只看到："找到 8 处使用了 X"
```

**这是 Claude Code 能跑长任务的最重要机制**——把"上下文管理"分布式化。

#### Skills —— 按需加载的长指令

详见 [skills-system-design.md](skills-system-design.md)。

**关键机制**：
- Skill 的 **description 字段一直在 context**（短）
- Skill 的 **正文只在被触发时加载**（长）

#### TodoWrite —— 显式自我规划

为什么 Claude Code 不会"目标漂移"？因为它在 context 里**有一个永远可见的待办列表**：

```
☒ 1. 找到所有用 deprecated API 的地方
☒ 2. 评估替换难度
► 3. 实施替换（处理到 src/api/auth.py）  ← in_progress
☐ 4. 跑测试
☐ 5. 更新文档
```

每完成一项立刻 mark completed，正在做的标 in_progress。**让 Agent "看着自己的待办" 工作** —— 这一招特别简单但极其有效。

#### Hooks —— 用户掌控点

`.claude/settings.json` 里可以配置：
- 每次工具调用前后
- Agent 思考结束时
- 收到通知时

执行任意 shell 命令——**给用户提供"在 Agent 自主运行中插一脚"的能力**，而不破坏自主性。

### 3. 长任务策略总结

```
策略 1：上下文管理 → Task 子 Agent 把详情卸载到子 context
策略 2：目标稳定   → TodoWrite 永远可见的待办清单
策略 3：工具简化   → 12 个核心工具，组合而非堆叠
策略 4：动态加载   → Skills 按触发加载长指令
策略 5：用户掌控   → Hooks 介入点
```

---

## 四、OpenHands —— "多 Agent 协作 + 沙箱执行"

### 1. 核心设计哲学

**完全开源、完全可控、Docker 沙箱里跑**。要解决"如何让 Agent 在隔离环境里安全地跑各种代码"。

### 2. 关键设计

#### Action / Observation 抽象

不是"工具调用"，是 **Action**：
```python
class CmdRunAction:        # 跑一条 shell
class FileEditAction:      # 改文件
class IPythonRunAction:    # 跑 Python
class BrowseURLAction:     # 浏览器
class MessageAction:       # 给用户发消息
class AgentDelegateAction: # 派给另一个 Agent
```

每个 Action 执行后产生 **Observation**（结果）。Agent 的循环就是：
```
观察当前状态 → 决定 Action → 执行 → 拿到 Observation → 继续观察
```

**比 LangChain 的"工具"抽象更接近"操作系统"**——Action 是"操作"，Observation 是"反馈"。

#### 多 Agent 协作

OpenHands 内置多个 Agent：
- **CodeActAgent**：默认主力，写代码 + 执行
- **BrowsingAgent**：纯浏览器
- **PlannerAgent**：规划任务
- **DummyAgent**：测试用

可以通过 `AgentDelegateAction` 派任务给其他 Agent。这个机制和 Claude Code 的 Task 工具类似，**但底层是 actor 模型**——每个 Agent 是独立的 worker。

#### Sandboxed Runtime

所有代码 / 命令都跑在 **Docker 沙箱**里：
- 默认有 Python、Node、git、常用 CLI
- 文件系统隔离
- 网络可配置

#### Memory & Summarization

OpenHands 跑长了会自动**总结历史**：
- 保留最近 N 步的完整 history
- 早期 history 被一个"summarization Agent"压缩成几句话
- 主 Agent 看到"你最近做了 A、B、C；更早做了 [摘要]"

**这是不同于 Claude Code 子 Agent 隔离的另一种思路**——主线压缩，不是分布式。

### 3. 多 Agent 协作的具体配置

#### config.toml

```toml
[core]
workspace_base = "./workspace"
max_iterations = 100
max_budget_per_task = 5.0

# 默认主 Agent
[agent]
name = "CodeActAgent"
memory_enabled = true
memory_max_threads = 3

# 自定义委派 Agent 1：浏览专家
[agents.browsing]
class = "BrowsingAgent"
llm = "llm.cheap"  # 用便宜的 LLM

# 自定义委派 Agent 2：规划专家
[agents.planner]
class = "PlannerAgent"
llm = "llm.main"

[llm.main]
model = "claude-sonnet-4-6"

[llm.cheap]
model = "claude-haiku-4-5"
```

#### 主 Agent 怎么委派

OpenHands 的 `CodeActAgent` 通过特殊 action 委派：

```python
# Agent 在生成代码时输出
<execute_browse>
url: "https://example.com/docs"
task: "Find the API endpoint for user creation"
</execute_browse>
```

OpenHands runtime 看到 `<execute_browse>` → 自动委派给 BrowsingAgent。

#### 自定义委派 Agent

```python
# my_agents/security_agent.py
from openhands.controller.agent import Agent
from openhands.events.action import Action, MessageAction

class SecurityReviewAgent(Agent):
    name = "SecurityReviewAgent"
    sandbox_plugins = []

    def step(self, state) -> Action:
        prompt = self._build_prompt(state)
        response = self.llm.completion(messages=[{"role": "user", "content": prompt}])
        return self._parse_to_action(response)

# my_agents/__init__.py
from openhands.controller.agent import Agent
from .security_agent import SecurityReviewAgent

Agent.register("SecurityReviewAgent", SecurityReviewAgent)
```

主 Agent 的 system prompt 加一段：
```
You can delegate to specialized agents:
- SecurityReviewAgent: for security audits

To delegate, output:
<execute_delegate agent="SecurityReviewAgent" task="..."/>
```

#### 多 Agent 协作的 4 种典型组合

**模式 1：Coding + Browsing（最常用）**
```
CodeActAgent ──delegate──> BrowsingAgent
   ↓                            ↓
   写代码                       查文档/抓数据
```

**模式 2：Planner + Coder**
```
PlannerAgent → 出计划 → CodeActAgent → 执行
```

**模式 3：Coder + Verifier**
```
CodeActAgent → 写完 → VerifierAgent → 跑测试 → 反馈
```

**模式 4：Multi-Coder（并行）**
```
PlannerAgent → 拆成 3 个独立子任务
   ├── CodeActAgent A 做 src/api
   ├── CodeActAgent B 做 src/db
   └── CodeActAgent C 做 src/utils
```

#### 实战陷阱

**陷阱 1：Agent 之间的 LLM 配置混乱** —— BrowsingAgent 用 GPT-4o 浪费，做的是简单 DOM 解析，用 Haiku 就够。要按 Agent 配 LLM。

**陷阱 2：max_iterations 太小** —— 默认 30，多 Agent 协作很容易超。长任务设到 100-200。

**陷阱 3：忽视 sandbox 网络** —— 子 Agent 在 Docker sandbox 里跑，**默认网络受限**。BrowsingAgent 调用外部 URL 会失败。
```toml
[sandbox]
network_mode = "host"  # 或者配白名单
```

### 4. 跟 Claude Code 多 Agent 的实质差异

| | Claude Code | OpenHands |
|---|---|---|
| 委派机制 | Task 工具调用 | AgentDelegateAction |
| 子 Agent 是什么 | 一个新的 LLM session | 一个完整的 Agent 类（有 step 方法） |
| 协议 | 函数调用风格 | actor 消息风格 |
| 自定义难度 | 写一个 .md 文件 | 写一个 Python 类 |
| 隔离强度 | context 隔离 | context + 进程级隔离（Docker） |
| 适合 | 快速定制 | 工程化定制 |

---

## 五、Manus —— "文件即记忆"

### 1. 核心设计哲学

**用文件系统当 Agent 的长期记忆 + 规划工具**。这个思路简单到反直觉，但效果惊人。

### 2. 关键设计：文件式规划

Manus 任务一启动，就在工作目录创建 3 个文件：

```
task_plan.md     ← Agent 自己写的任务计划，分阶段、分子任务
findings.md      ← 跑过程中发现的关键信息（不是日志，是结论）
progress.md      ← 进度跟踪（已完成 / 进行中 / 待办）
```

**关键机制**：
- 每跑一步，Agent **更新这些文件**
- 下一步 Agent 先**读这些文件**了解自己在哪
- 跨会话恢复时，Agent **从这些文件读自己之前在做什么**

### 3. 为什么这个机制强大

#### 上下文管理：把"记忆"从 context 卸载到文件

```
传统 Agent：
   context = [所有历史步骤的完整记录]
   → 长任务必爆

Manus：
   context = [当前步骤 + 文件中的高层规划/进度]
   → 永远不会爆，因为细节都在文件
```

#### 目标稳定：plan 是"显式且持久"的

每次 Agent 都从 task_plan.md 重新对齐目标。**目标漂移变成不可能** —— 因为目标永远写在文件里。

#### 跨会话恢复：天然支持

进程死了？重启读文件就行。**不需要 checkpoint 表，不需要状态机** —— 文件就是状态。

### 4. Claude Code 里复现 Manus（完整方案）

注意 CLAUDE.md 里其实已经装了 `planning-with-files` skill。完整复现的实现见 [research-agent-architecture.md](research-agent-architecture.md)。

#### 加 plan-updater subagent 减负

主 Agent 自己更新这三个文件会消耗主 context。**用专门的 sub-agent 来做**：

```markdown
---
name: plan-updater
description: |
  Updates Manus planning files (task_plan.md, findings.md, progress.md).
  Use when main agent needs to record progress without polluting main context.
tools: Read, Edit, Write
model: haiku
---

You are a plan-state recorder.

When invoked, you receive:
- which file to update (task_plan / findings / progress)
- what change to record

Do ONLY the update. Do not analyze, do not suggest.

For findings.md: APPEND with timestamp + topic + 1-3 sentence finding.
For progress.md: OVERWRITE with current state.
For task_plan.md: EDIT to mark sub-tasks [x].

End with: "UPDATED: <file>"
```

主 Agent 的更新调用变成：
```
Task(subagent_type="plan-updater",
     prompt="Append to findings: discovered that the auth middleware in src/auth/middleware.py is calling deprecated session API")
```

主 context 不会被 markdown 更新细节淹没。

#### 用 hooks 强制更新

`.claude/settings.json`：

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "test -f task_plan.md && test -f progress.md || echo '⚠️  Long task active but progress.md missing — please update it'"
          }
        ]
      }
    ]
  }
}
```

hooks 输出会注入回 Agent，提醒它别忘了更新。

### 5. 复现版 vs Manus 原版

| | Manus 原版 | Claude Code 复刻 |
|---|---|---|
| 文件式记忆 | ✅ | ✅ |
| 跨会话恢复 | ✅ | ✅（重新打开会话即可） |
| 用户可审计 | ✅ | ✅（甚至可以编辑文件干预） |
| 主 Agent 负担 | 中 | **低**（plan-updater 子 agent 减负） |
| 工具体系 | Manus 自家 | **完整 Claude Code 工具链** |
| 可控性 | 黑盒 | **完全可见** |

复刻版本反而比原版更好用——因为你拿到了 Claude Code 的可观测性。

### 6. 局限

- **只适合有"工作目录"概念的任务** —— 纯对话任务（聊天客服）不适用
- **依赖 Agent 严格更新文件** —— 模型不够强会忘了更新
- **不适合多 Agent 并发** —— 文件竞态写入是大坑

---

## 六、Devin —— "完全自主"的尝试

### 1. 核心设计哲学

**给 Agent 一个完整的工作环境**（终端 + 浏览器 + IDE + 网络），让它**像人一样自己做完**。最小化人介入。

### 2. 关键设计（从公开信息和论文反推）

#### 多模态输入

Agent 看到的是**截图**而不是 DOM/AST：
- 浏览器：渲染后的截图（VLM 解析）
- IDE：编辑器界面截图
- 终端：终端输出截图

**为什么这样**：跨工具统一抽象——所有 GUI 都是图。但代价是 token 消耗大、速度慢。

#### 内部规划层（推测）

Devin 应该有一个**专门的 planner**：
- 接到任务先做高层分解
- 执行过程中动态调整
- 失败时自动重试 / 换方案

#### SWE-Bench 优化

Devin 一开始最大卖点是 SWE-Bench 跑分（13.86%）→ 后被超过 → 重新优化。

**注意**：SWE-Bench 跑分和"真实生产体验"差距巨大。跑分高的不一定好用，能商业化的不一定跑分高。

### 3. Devin 的争议

- **Demo 与现实差距**：发布时的 demo 让人惊艳，但用户反馈"做简单事还行，复杂事容易跑歪"
- **价格高**：曾经 $500/月起步
- **黑盒**：用户看不到内部状态，跑歪了不好干预

### 4. 给我们的启发

无论它实际效果如何，**它定义了"长任务 Agent"的产品形态**：
- 工作环境是完整的（不只是 CLI）
- 默认是异步（你交任务，它跑，跑完通知）
- 规划层和执行层分开

---

## 七、长任务 Agent 的 6 个核心策略（提炼）

把上面四家的设计提炼成可复用的"模式"：

### 策略 1：上下文管理（最重要）

三种主流方案：

| 方案 | 代表 | 优势 | 劣势 |
|---|---|---|---|
| **分布式（子 Agent 隔离）** | Claude Code Task | 主 context 永远干净 | 子 Agent 间不能交流 |
| **摘要压缩** | OpenHands | 实现简单 | 摘要会丢信息 |
| **文件卸载** | Manus | 永不爆 + 可审计 | 依赖文件管理纪律 |

**实战推荐**：组合用。Claude Code + planning-with-files skill 就是"分布式 + 文件卸载"。

### 策略 2：显式自我规划

Agent **必须知道自己在哪个阶段**。三种实现：

- **TodoWrite 工具**（Claude Code 风格）：context 内的待办列表
- **task_plan.md 文件**（Manus 风格）：文件系统的计划
- **专门 Planner Agent**（OpenHands / Devin 风格）：独立 Agent 维护计划

**心法**：没有规划机制的长任务 Agent 必跑歪。

### 策略 3：工具集设计

```
反模式：100 个专用工具    → 模型选错一半
正模式：12 个组合工具    → Bash + Read + Edit 已能做大部分事
```

**核心问题**：工具描述都是 context tax。**每多一个工具 → context 多 N 个 token → 选择压力大**。

### 策略 4：失败恢复机制

短任务挂了重跑就行。长任务挂了重跑成本太高，必须能从挂的地方继续：

- **Checkpoint 机制**（LangGraph 风格）
- **文件即状态**（Manus 风格）
- **手动 resume 命令**（Claude Code 风格 —— 用户告诉它继续）

### 策略 5：终止条件

Agent 必须能说"我做不到 / 我做完了 / 我需要帮助"：

- **max_steps 硬上限**：跑超过 N 步强制停（不优雅但保命）
- **预算上限**：花超过 $X token 停
- **显式 give_up 工具**：让 Agent 自己说"我搞不定这个"
- **置信度阈值**：连续 3 步没进展 → 自动停

### 策略 6：人介入点

完全自主跑长任务**不现实**。设计好"人在哪些点能介入"：

- **审批节点**（重要决策前停下等批准）
- **可暂停 / 可恢复**
- **实时可观察**（用户能看到 Agent 在干什么，跑歪能立刻打断）

---

## 八、自己造一个长任务 Agent，从哪开始

### 阶段 1：用 Claude Code 范式（最快）

```
1. 主 Agent：单一强模型 + 精简工具集
2. 上下文管理：派子任务出去（用 LangGraph subgraph 或自己写函数式 Task）
3. 显式规划：在 prompt 里强制让 Agent 维护 todo 列表
4. 终止条件：max_steps + budget 双重保险
```

**适合**：单产品、单场景、用户能持续在线

### 阶段 2：加 Manus 文件机制（长任务）

```
5. 工作目录概念：每个任务一个 dir
6. plan / findings / progress 三件套
7. Agent 启动时强制读这些文件
```

**适合**：跨会话、跨小时的真长任务

### 阶段 3：加 OpenHands 沙箱（不可信代码）

```
8. Docker 沙箱执行所有 shell / 代码
9. 文件 IO 走 sandbox 内
10. 网络白名单
```

**适合**：Agent 会跑用户/Agent 自己生成的代码

### 阶段 4：上 LangGraph 状态机（生产级）

```
11. 把流程画成图，节点 = Agent 决策点
12. Postgres checkpoint 持久化
13. HITL 介入点
14. 可观测性（LangSmith / Langfuse）
```

**适合**：严肃业务、要审计、要 SLA

---

## 九、轻量 Coding Agent vs Claude Code（Cursor / Cline / Aider）

很多人混淆"长任务 Agent" 和"轻量 Coding Agent"。它们是不同物种。

### 同一坐标系

```
                 Cursor      Cline        Aider       Claude Code
─────────────────────────────────────────────────────────────────
形态              IDE        VSCode 插件   终端 CLI    终端 CLI
心智模型          编辑器+AI   IDE 内 Agent  pair coder  通用 Agent
主战场            代码编辑    代码 + 任务   文件级编辑   全栈 + 终端
自主性            低         中            低          高
任务范围          单文件 / 几文件          多文件      整个 repo / 系统
循环              人主导     Agent + 人    Agent 严格  Agent 主导
模型              GPT/Claude多 同左         同左        Claude 为主
```

### Cursor —— "AI-First IDE"

**Cursor = VSCode + 深度集成的 AI**。核心创新是**编辑体验**，不是 Agent 能力。

**关键功能**：
- **Cmd+K**：选中代码 → 自然语言改
- **Composer**：多文件编辑（最像"Agent"的部分）
- **Tab 补全**：极强的下一动作预测
- **Inline Chat**：边写边问

**心智模型**：用户主导，AI 辅助。你点哪 AI 改哪。Composer 模式是后来加的——Cursor 团队也意识到要往 Agent 走。

**强项**：编辑体验最好；多模型自由切换；codebase 索引能跨文件理解。

**弱项**：不擅长长任务（Composer 跑 20 步以上不稳）；没有终端集成；Composer 黑盒。

### Cline（前 Claude Dev）—— "VSCode 内的 Agent"

**Cline = VSCode 插件版的 Claude Code**。把 Agent 体验搬进 IDE。

**关键设计**：
- **Plan / Act 双模式**：Plan 模式讨论方案不动代码，Act 模式执行
- **Diff 全可见**：每个改动都显示 diff，你点 approve
- **支持 MCP**：可以接外部工具（详见 [skills-system-design.md](skills-system-design.md) 里 "Cline 的 MCP 怎么自定义工具"一节）
- **终端集成**：能跑命令，看输出

**心智模型**：Agent 主导执行，用户主导审批。设计哲学是"显式 approval"——每个文件改动都要点同意。

**强项**：完全开源；可见性极强；VSCode 集成好。

**弱项**：Agent 能力比 Claude Code 弱；每步审批拖慢长任务；生态相对小。

### Aider —— "Pair Programmer in Terminal"

**Aider = 终端里的 pair programmer**。最早提出"AI 写代码自动 git commit"的范式。

**关键设计**：
- **极简交互**：终端里你说话，它改代码 + 自动 commit
- **Repo Map**：对整个 repo 建一个轻量索引
- **/add /drop**：手动管理"哪些文件在 AI 视野内"
- **多种编辑模式**：whole / diff / udiff（影响速度和准确性）

**心智模型**：严格的 pair programming。你说一步，它做一步，commit 一次。**几乎没有"自主决策"**。

**强项**：极简极稳；手动控制 context；Git workflow 集成最好（每次改自动 commit，**你可以随时 revert**）。

**弱项**：不是 Agent；不能跑命令；不擅长大任务。

### 本质差别

```
Cursor / Cline / Aider 的核心循环：
   用户 → 描述意图 → AI 改一处代码 → 用户审 → 接着说
   （AI 是"高级补全"）

Claude Code 的核心循环：
   用户 → 给一个目标 → Agent 自己规划 → 调工具 → 看结果 → 自己决定下一步
   （AI 是"自主执行者"）
```

### 关键能力对比

| 能力 | Cursor | Cline | Aider | Claude Code |
|---|---|---|---|---|
| 跑命令 | ❌ | ✅ | ❌ | ✅ |
| 自主多步 | 弱 | 中 | ❌ | **强** |
| 子 Agent | ❌ | ❌ | ❌ | ✅ Task |
| Skills 机制 | ❌ | 部分（MCP） | ❌ | ✅ |
| Hooks | ❌ | ❌ | ❌ | ✅ |
| 跨会话恢复 | ❌ | 部分 | git commit | ✅（用 Manus skill） |
| 工具协议 | 有限 | MCP | ❌ | MCP + 内建 |
| 长任务（>30 步） | ❌ | 弱 | ❌ | ✅ |

### 决策树

```
你的主战场是什么？
│
├─ "我大部分时间在 IDE 里写代码"
│   ├─ 需要"AI 当助手"   → Cursor
│   └─ 需要"Agent 在 IDE 里干活" → Cline
│
├─ "我大部分时间在终端"
│   ├─ 需要"git-friendly 的 pair programming" → Aider
│   └─ 需要"Agent 自主跑长任务" → Claude Code
│
└─ "我需要自定义、要做产品"
    ├─ 想用闭源最强 Agent  → Claude Code（或 Devin）
    └─ 想完全开源可改      → Cline / OpenHands / 自己造
```

### 真相：这些工具不是非此即彼

常见组合：
- **Cursor + Aider**：IDE 里日常写码用 Cursor，git workflow 严格的改动用 Aider commit
- **Cline + Claude Code**：IDE 内任务用 Cline（看着改），跨工具长任务切到 Claude Code
- **Aider + Claude Code**：单文件精细改动用 Aider，整 repo 重构用 Claude Code

实战工作流：**80% 时间 Claude Code，剩下 20% 在 IDE 里 Cursor 做精细编辑**。

---

## 十、最常被忽略的 5 个真相

### 真相 1：模型能力是天花板

再好的工程也救不了不够强的模型。长任务对**指令跟随、长上下文 attention、tool calling 准确性**的要求都极高。

实战：**只有 GPT-4 / Claude Sonnet 4+ / Gemini 2 Pro 级别才能跑长任务**。小模型再加工程也是徒劳。

### 真相 2：可观测性比"自主性"更重要

完全黑盒的"自主 Agent"用户用不下去。**实时 stream + 中间状态可见 + 可暂停可干预** 比"完美自主"重要 100 倍。

Claude Code 之所以好用很大原因是**用户全程能看见**。Devin 之所以争议大是**黑盒**。

### 真相 3：长任务 Agent 不是"少介入" 是"好介入"

理想不是"扔个任务跑一晚上回来收结果"，是：
- Agent 自主推进
- 关键决策点主动问用户
- 用户能随时打断
- 结果可审计

**"介入次数少"是结果，不是目标**。

### 真相 4：上下文管理 > 工具调用

很多人花大力气设计工具，忽视上下文管理。**长任务的瓶颈 90% 在 context，不在工具**。

如果一个长任务 Agent 跑不下去，**先看 context 是怎么管理的，再看工具够不够**。

### 真相 5：开源框架追不上闭源产品

Claude Code、Cursor、Devin 这些产品级 Agent，**核心工程都是闭源的**。开源框架（OpenHands、AutoGen）只能学到"形"，学不到"神"。

**这意味着**：如果你要做严肃产品，**最终都要自己写**。框架只是起点，不是终点。

---

## 十一、决策心法

> **长任务 Agent 的核心不是"让 Agent 更聪明"，是"让 Agent 不那么容易跑歪"**。

判断你是否真需要"长任务 Agent"的三个问题：

1. **任务真的长吗？** —— 一次能完成的别上长任务架构
2. **用户愿意等吗？** —— 不愿等就别做异步 Agent
3. **跑歪的代价大吗？** —— 大就要做强 HITL，小才能自主

---

## 十二、扩展阅读

- [skills-system-design.md](skills-system-design.md) —— Skills 机制深度（最简版 + 动态召回 + LangGraph 接入 + Cline MCP）
- [subagent-patterns.md](subagent-patterns.md) —— Task / Crew / Subgraph 三种"派子任务"机制
- [multi-agent-coordination.md](multi-agent-coordination.md) —— 多 Agent 协调与协商
- [research-agent-architecture.md](research-agent-architecture.md) —— 端到端长任务研究 Agent 实战
- [../production/langgraph-research-agent-impl.md](../production/langgraph-research-agent-impl.md) —— LangGraph 完整复刻代码
