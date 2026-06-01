# ReAct 及其变体：Agent 的核心范式

> 本文目标：把 Agent 领域绕不开的几种经典范式（ReAct、Plan-and-Execute、Reflexion、Tree-of-Thoughts）讲清楚，让你看任何"新出的 Agent 框架"都能映射回这几种基本结构，并知道**什么时候该用哪一种**。

---

## 一、为什么 ReAct 是绕不开的起点

ReAct（Reasoning + Acting，Yao et al., 2022, ICLR'23）是把 LLM 从"会聊天的 chatbot"变成"会做事的 Agent"的奠基性论文。它解决了一个简单但关键的问题：

> LLM 单靠"想"（CoT）会胡说，单靠"做"（直接调工具）会乱调，怎么把两者结合起来？

答案是**让 LLM 在每一步交替"想 → 做 → 看结果 → 再想"**。这个简单循环至今是几乎所有 Agent 框架（LangChain Agent、AutoGPT、LangGraph 的默认模式）的内核。

---

## 二、ReAct 的循环

### 一张图

```
┌──────────────────────────────────────────────────────────┐
│                                                          │
│   User 任务                                              │
│       │                                                  │
│       ▼                                                  │
│   ┌─────────────────────────────────────┐               │
│   │  Thought：我现在该做什么？             │  ←──────┐   │
│   │     ↓                                │         │   │
│   │  Action：调用某个工具，参数是 ...     │         │   │
│   │     ↓                                │         │   │
│   │  Observation：工具返回了 ...         │         │   │
│   │     ↓                                │         │   │
│   │  （回到 Thought 继续）                │ ────────┘   │
│   └─────────────────────────────────────┘               │
│       │                                                  │
│       ▼                                                  │
│   Final Answer                                           │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 一段实际 trace

```
Question: 张教授去年发的两篇 AI 顶会论文里，第二作者都来自同一所学校吗？

Thought 1: 我需要先找出张教授去年发的 AI 顶会论文。
Action 1: search_papers(author="张教授", year=2024, venues=["NeurIPS","ICML","ICLR"])
Observation 1: 找到 2 篇：A 论文（NeurIPS）、B 论文（ICML）。

Thought 2: 我需要查这两篇的第二作者。
Action 2: get_paper_authors(paper_id="A")
Observation 2: 第二作者是 李四，机构：清华大学

Thought 3: 再查 B 论文。
Action 3: get_paper_authors(paper_id="B")
Observation 3: 第二作者是 王五，机构：北京大学

Thought 4: 两篇第二作者来自不同学校。
Final Answer: 不是，A 论文的第二作者来自清华大学，B 论文的第二作者来自北京大学。
```

注意几点：
- **Thought 是显式的**——不只是内部状态，而是写出来的（让模型"自我对齐"）
- **Action 是结构化的**——可以被代码解析并执行
- **Observation 是真实的**——是工具实际返回的，不是模型瞎编

---

## 三、ReAct 为什么有效

三个机制叠加：

1. **CoT 让推理更准**：思考的过程会让最终决策更靠谱（CoT 论文已证实）。
2. **工具让幻觉收敛**：不知道的事情不靠记忆瞎编，而是去查、去算。
3. **观察形成反馈环**：上一步的真实结果会修正下一步的推理（不是开盲盒）。

> 一句话：**ReAct = Chain-of-Thought（解决推理）+ Tool Use（解决知识 / 操作）+ 观察反馈（解决稳定性）**。

---

## 四、ReAct 的麻烦

ReAct 不是银弹。三个最常见的工程问题：

### 1. 不收敛（"陷入循环"）
- 现象：跑 8 步、12 步还在转圈调一样的工具
- 根因：没有终止条件、prompt 里"任务定义"模糊
- 解法：硬上限（max_steps=10）+ 让模型有"give_up" / "ask_user" 工具

### 2. 工具选错 / 参数错
- 现象：表面跑得很顺，最终答案错；查日志发现某一步参数填错
- 解法：所有工具加 schema 校验；参数错就把错误反馈给模型重生
- 经验：工具描述写得越具体，错调率越低

### 3. 长链路上下文爆炸
- 现象：第 6 步开始 prompt 变得巨长，性能下降、成本飙升
- 解法：summary 历史 thought（保留摘要）；或换 Plan-and-Execute 范式

---

## 五、变体 1：Plan-and-Execute

ReAct 是"边想边做"，**Plan-and-Execute 是"先想清楚，再一口气做"**。

```
ReAct:               想→做→想→做→想→做  （交错）
Plan-and-Execute:    想想想想→做做做做     （分段）
```

### 流程

```
1. Planner LLM:
     输入任务，输出步骤列表（plan）：
        ① 查论文
        ② 查作者机构
        ③ 比较

2. Executor LLM（可以是更小更便宜的模型）:
     按 plan 一步步执行，每步可以调工具

3. （可选）Replanner:
     执行中发现 plan 有问题，触发重新规划
```

### 何时用 P&E

- 任务**步骤多但前后依赖少**（适合先规划）
- Planner 用强模型 / Executor 用弱模型，**省钱**
- 需要给用户**展示计划再确认**（如客服 Agent、研究 Agent）

### 何时不该用 P&E

- 任务高度**反应式**（每步都依赖上一步真实结果）→ 还是 ReAct 好
- Plan 容易过期 / 错（动态环境）

代表实现：LangChain `PlanAndExecute` 链、ChatGPT 的 "Deep Research"。

---

## 六、变体 2：Reflexion（反思）

Reflexion（Shinn et al., 2023）的核心是给 Agent 加一个"反思官"：

```
┌────────────────────────────────────────────────────┐
│                                                    │
│   尝试执行任务（一轮 ReAct）                       │
│       │                                            │
│       ▼                                            │
│   评估：成功 / 失败？                              │
│       │                                            │
│       ▼                                            │
│   反思（Reflector LLM）:                           │
│      失败原因？这次学到什么？                       │
│       │                                            │
│       ▼                                            │
│   把反思写进"经验记忆" → 下一轮 prompt 中给 Agent │
│       │                                            │
│       └─→ 重新尝试（带着教训）                     │
│                                                    │
└────────────────────────────────────────────────────┘
```

### 何时用反思

- 任务有**可验证的反馈**（代码能不能跑、答案对不对）
- 第一次失败的代价不大，可以多试几次
- 有充足时间预算（多轮反思至少多花 2-3 倍 token）

### 业务意义

- **Coding Agent 的标配**：失败 → 看错误日志 → 反思 → 改代码（Cursor / Cline / SWE-Agent 都用）
- **数据分析 Agent**：跑出来的图不对 → 反思 → 重写 SQL

不太适合的：实时对话（用户不会等你反思 3 轮）。

---

## 七、变体 3：Tree-of-Thoughts（ToT）

ReAct 是单线的"想-做-想-做"。ToT（Yao et al., 2023）扩展成**树状探索**：

```
ReAct:    想₁ → 做₁ → 想₂ → 做₂ → 答案
                 (一条线)

ToT:           想 (根)
              ╱ ╲
           想₁   想₂        ← 同一步生成多个候选思路
          ╱  ╲   ╲
       想₁ₐ 想₁ᵦ 想₂ₐ      ← 每条路继续展开
        ↓    ↓    ↓
       评分 评分 评分          ← 用 LLM 自评 / 投票
        │    │    │
        └─→ 选最优 → 答案
```

### 何时用 ToT

- 任务有**清晰的"中间状态可评估"**（数学题、规划、24 点游戏等）
- 单线推理容易走错路 → 多路探索 + 剪枝有显著收益
- 计算预算不太敏感

### 何时不要用

- 高频对话型 Agent（成本是 ReAct 的 5-10 倍）
- 中间状态难评估（"这一步思路好不好"自评不出来）

ToT 在工程实践上没那么流行，但思想（多路径 + 评估 + 剪枝）影响深远，比如 OpenAI o1 系列的"reasoning"在某种程度上就是 ToT 的进化版。

---

## 八、变体 4：Multi-Agent

多 Agent 不是"更高级的单 Agent"，而是**用模拟分工解决单 Agent 难解的问题**：

```
单 Agent：一个 LLM 同时扮演规划者、执行者、批评者 → 角色容易混
多 Agent：每个 LLM 实例扮演一个固定角色，对话协作

经典分工：
   Manager / Planner
   Researcher
   Coder
   Critic
   Tester
```

代表框架：AutoGen（Microsoft）、CrewAI、Swarm（OpenAI）、MetaGPT。

### 何时用

- 任务**天然涉及不同角色**的协作（写论文、做软件、做研究）
- 单个 Agent prompt 太复杂，拆成多个角色更清晰
- 需要"批评 / 二次审核"机制

### 何时不要用

- 简单任务（多 Agent overhead 大，token 是 N 倍）
- 实时对话型场景（多轮通信延迟堆叠）

---

## 九、决策树：我该用哪个范式

```
                  任务类型？
       ┌──────────────┴──────────────┐
   开放式探索                    流程相对清晰
       │                             │
       ▼                             ▼
   ReAct 起步               能否预先规划完整步骤？
       │                       ┌─────┴─────┐
   是否有可验证反馈？           能           不能
       │                       │             │
   ┌───┴───┐                   ▼             ▼
   有       没有             Plan-and-      ReAct
   ↓        ↓                Execute      
 Reflexion  ReAct            
   ↓
 涉及多角色 / 高并行？
   ┌───┴───┐
   是      否
   ↓       ↓
 Multi-   Reflexion
 Agent    单链
```

---

## 十、把这些范式拼起来用

实战中很少"纯 ReAct"或"纯 P&E"。生产 Agent 通常是**混合体**：

```
Coding Agent（Cursor / Cline 风格）：
  - 外层：Plan-and-Execute（先生成计划）
  - 内层：ReAct（执行单步时探索）
  - 加上：Reflexion（编译 / 测试失败时反思重试）

研究型 Agent（Deep Research）：
  - 外层：Plan-and-Execute
  - 中层：Multi-Agent（搜索员、阅读员、写作员）
  - 内层：ReAct
```

**业界共识**：Agent 不是用一个范式打天下，而是按任务**组合范式**。这也是为什么 LangGraph 这种"显式状态机"框架近两年开始压倒纯 ReAct——它让组合更清晰可控。

---

## 十一、常见认知陷阱

### 1. "ReAct 比 CoT 强"
不一定。**简单事实问题** ReAct 反而更慢更贵更不稳。CoT 在简单推理任务上常常是最优解。

### 2. "Agent 比 Workflow 高级"
完全错。**能用确定性 Workflow 解决的问题就别用 Agent**——Workflow 更便宜、可观测、可调试。
（Anthropic *Building Effective Agents* 的核心建议。）

### 3. "工具越多 Agent 越强"
错。工具数量超过 ~15 个，模型选错率显著上升。要做**动态工具检索**（按当前任务召回相关工具）。

### 4. "Reflexion 只是把失败再跑一遍"
错。Reflexion 的关键是"反思 → 写入记忆 → 下次带着教训"。没有记忆传递的重试就是简单 retry，效果差很多。

### 5. "Multi-Agent 一定优于单 Agent"
不一定。**任务边界模糊的多 Agent 经常退化成"互相打补丁"**。设计前先问：每个 Agent 的责任能否明确切开？切不开就别拆。

---

## 十二、纵深篇（深入到机制 + 应用策略）

本篇是范式总览。深入版分别在：
- [react-mechanism-and-strategy.md](react-mechanism-and-strategy.md) — ReAct 的微观机制（7 步循环 / prompt 模板 / 5 种失败模式）+ 在 ice-workbench 的实战接入
- [tree-of-thoughts.md](tree-of-thoughts.md) — ToT 的搜索机制（4 要素 / 4 种典型配置）+ 成本经济学 + 在 ice-workbench 的"配置 D Hybrid"接法

---

## 十三、扩展阅读

### 必读论文
- ReAct（Yao et al., 2022）—— *ReAct: Synergizing Reasoning and Acting in Language Models*
- Reflexion（Shinn et al., 2023）—— *Reflexion: Language Agents with Verbal Reinforcement Learning*
- ToT（Yao et al., 2023）—— *Tree of Thoughts: Deliberate Problem Solving with Large Language Models*
- Plan-and-Solve（Wang et al., 2023）—— *Plan-and-Solve Prompting*

### 必读博客
- Lilian Weng — *LLM Powered Autonomous Agents*（最系统的总览）
- Anthropic — *Building Effective Agents*（2024，工程视角必读）
- Andrew Ng — *Agentic Design Patterns* 系列（DeepLearning.AI 邮件）

### 框架（按上手难度）
- LangChain / LangGraph
- AutoGen（多 Agent）
- CrewAI（多 Agent，更轻量）
- Pydantic AI（Python 类型友好）

### 本仓库已有
- [references/agentic-design-patterns.md](../../../references/agentic-design-patterns.md)
- [references/rag-agent-scenario-analysis.md](../../../references/rag-agent-scenario-analysis.md)
- [knowledge-base/AI-Agent/](../../../knowledge-base/AI-Agent/)

→ 下一步建议：看完范式后看 [tools-protocols/function-calling.md](../tools-protocols/function-calling.md) 和 [tools-protocols/mcp.md](../tools-protocols/mcp.md)——它们决定 Agent 的"动作能不能落地"。
