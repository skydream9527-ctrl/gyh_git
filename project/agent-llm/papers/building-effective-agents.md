# Building Effective Agents：Anthropic 的"反框架"宣言

> **出处**：Anthropic Engineering Blog [Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)
> **作者**：Erik Schluntz, Barry Zhang
> **发布**：2024-12-19
> **一句话**：和数十个团队合作后 Anthropic 发现，**最成功的 agent 实现都是 simple, composable patterns，不是复杂框架**——少抽象、多直接调 API。

---

## 〇、核心论断（一段读懂）

- "Agent" 本身没有标准定义。Anthropic 把所有变体统称 **agentic systems**，但**严格区分两类**：
  - **Workflow**：LLM 和工具被**预定义代码路径**编排
  - **Agent**：LLM **动态决定自己的过程和工具用法**
- 决策第一原则：**先找最简单的方案，必要时才加复杂度**——很多场景"单次 LLM call + 检索 + few-shot" 就够了，**根本不需要做 agent**。
- 即便要做，**workflow 比 agent 更可预测、更便宜**；只有当任务真的需要灵活性和模型驱动决策、且无法硬编码路径时，再上 agent。
- 框架（LangChain / Strands / Rivet / Vellum）能加速起步，但**抽象层会遮蔽 prompt 和 response，使调试变难**——Anthropic 建议：**直接用 LLM API 起步**，许多模式几行代码就能写。

---

## 一、Workflow vs Agent：核心架构区分

| 维度 | Workflow | Agent |
|---|---|---|
| 控制流 | **预定义的代码路径** | **LLM 动态决定** |
| 可预测性 | 高 | 低 |
| 灵活性 | 低 | 高 |
| 何时用 | 任务定义清晰、步骤可枚举 | 开放问题，无法预测步数 |
| 成本 | 低 | 高（多轮 + 多 tool） |
| 错误风险 | 可控 | 错误会复合 |

> **Anthropic 的强观点**：大多数生产场景应当用 workflow，agent 只在 workflow 撑不住时才上场。

---

## 二、基础构件：The Augmented LLM

所有 agentic system 的最小单元是 **augmented LLM**——一个加了**检索 / 工具 / 记忆**的 LLM。

```
        ┌────────────────────────┐
        │     Augmented LLM       │
        │   ┌──────────────┐     │
        │   │     LLM      │     │
        │   └──────────────┘     │
        │   Retrieval | Tools |  │
        │   Memory             │
        └────────────────────────┘
```

要点：
- 现代模型可以**主动**用这些能力——自己生成查询、选合适的工具、决定保留什么
- 实现重点：**为你的 use case 量身定制 + 给 LLM 一个清晰、文档良好的接口**
- **MCP（Model Context Protocol）** 是一种通用接入方式，让 LLM 能用第三方工具生态

---

## 三、五种 Workflow 模式（按复杂度递增）

### 3.1 Prompt Chaining（提示链）

```
Input → LLM₁ → Gate（程序检查）→ LLM₂ → Output
```

- **何时用**：任务能干净地拆成固定子步骤
- **取舍**：用更长延迟换更高准确度
- **例**：营销文案生成 → 翻译；先写大纲再判定大纲合规再写正文

### 3.2 Routing（路由）

```
            ┌→ Specialist A
Input → Router(LLM 或分类器) → Specialist B
            └→ Specialist C
```

- **何时用**：任务有明显类别，分别优化更好；分类本身可靠
- **例**：客服问询（一般咨询 / 退款 / 技术支持）→ 不同下游处理；简单问题给 Haiku，难问题给 Sonnet

### 3.3 Parallelization（并行化）

两种变体：
- **Sectioning**：拆成独立子任务并行跑
- **Voting**：相同任务跑多次取共识

- **何时用**：可并行加速、或多视角提升置信度
- **例**：
  - **Sectioning**：一个 LLM 做内容生成、另一个并行跑 guardrail 检查
  - **Voting**：多 prompt 审查代码漏洞，任一发现就报警；评估内容是否不当，多 vote 取阈值

### 3.4 Orchestrator-Workers（编排器-工人）

```
                ┌→ Worker LLM₁
Lead LLM ─┼→ Worker LLM₂   →  Lead LLM 综合
                └→ Worker LLM₃
```

和 Parallelization 看起来像，**关键差异**：**子任务由 lead 动态决定，不是预先定义**。

- **何时用**：无法预知子任务数量与性质（如"修复涉及多文件的复杂 bug"）
- **例**：编码产品对多文件做修改；研究任务从多源采集

### 3.5 Evaluator-Optimizer（评估-优化循环）

```
Input → Generator LLM → Output ─┐
              ↑                  ↓
       Evaluator LLM ←───── Critique
```

- **何时用**：有清晰评估标准 + 迭代精修能带来可量化改进
- **两个适配信号**：
  1. 人写 feedback 能明显改进 LLM 输出
  2. LLM 本身能给出有用 feedback
- **例**：文学翻译（细微之处第一遍抓不到）；复杂搜索任务

---

## 四、Agent：什么时候**真的**需要

Anthropic 的 agent 定义带几个**关键特征**：

1. **从用户指令或交互讨论**开始
2. **任务清晰后独立规划和执行**——必要时回头问人
3. **执行中从环境获取 ground truth**（tool 结果、代码执行结果）评估自己进度
4. **在 checkpoint 或卡住时暂停求人**
5. **达成 / 触发停止条件**（最大迭代数等）才结束

**何时用 agent**：
- 开放问题，**步数不可预测**，**无法硬编码路径**
- 你对模型决策有"一定信任"
- **可信任的环境** + **足够大的扩展价值**

**风险**：
- 自治 → 高成本
- 错误会复合
- 必须在沙箱里大量测试 + 加 guardrail

**例**：解决 SWE-bench 任务的 coding agent；computer use 参考实现

> Agent 在结构上很简单——通常就是**LLM 在循环里基于环境反馈用工具**。所以**工具集和工具文档的设计才是关键**。

---

## 五、组合与定制

这 5 种构件**不是教条**——是 Anthropic 见过的常见模式，可任意组合。
- 一个客服 agent 可能是：Routing → Tool Use（augmented LLM）→ 必要时 Orchestrator-Workers
- **关键**：测量性能，迭代实现；只在能**显示改进**时才加复杂度

---

## 六、三条核心原则（最重要）

1. **Maintain simplicity in your agent's design** — 保持简单
2. **Prioritize transparency by explicitly showing the agent's planning steps** — 显式展示 agent 的规划步骤
3. **Carefully craft your agent-computer interface (ACI)** — 通过详尽的 tool 文档和测试精心设计 ACI

> 类比 HCI（Human-Computer Interface），**ACI（Agent-Computer Interface）** 是这篇 blog 的关键术语。

---

## 七、ACI：Agent-Computer Interface（被业界引用最多的概念）

Anthropic 把"工具设计"提升到了**接口设计**的高度。和 HCI 一样的级别：

- 工具描述 = 工具 UX
- 参数命名 = 工具 affordance
- 错误信息 = 工具反馈

> 这条与 [harness-engineering-codex.md](harness-engineering-codex.md) 的 "linter error doubles as instruction" 直接同源——Codex 团队是这个想法的极端工程化。

---

## 八、和本仓库现有结论的对照

| 本文论点 | 本仓库已有 |
|---|---|
| Workflow vs Agent 严格区分 | [../agents/agent-loop-architectures.md](../agents/agent-loop-architectures.md) ✓ |
| 5 种构件模式 | [../agents/react-and-variants.md](../agents/react-and-variants.md)、[../agents/multi-agent-frameworks.md](../agents/multi-agent-frameworks.md) ✓ |
| ACI 概念 | [../tools-protocols/tool-development.md](../tools-protocols/tool-development.md) ✓（"API 工程师视角"），可补 ACI 命名 |
| 反对过度抽象 | [../production/frameworks-comparison.md](../production/frameworks-comparison.md) ✓ |
| Augmented LLM 概念 | [../agents/agent-loop-architectures.md](../agents/agent-loop-architectures.md) 可加 |
| Evaluator-Optimizer | [../agents/react-and-variants.md](../agents/react-and-variants.md)（Reflexion / Self-Refine 同源） ✓ |

---

## 九、反对意见与待验证

- **"先 workflow 后 agent"** 在多 agent 系统中已被自家 [../papers/multi-agent-research-system.md](multi-agent-research-system.md) 部分修订——研究类任务上 multi-agent 显著超过 single-agent。
- **5 种模式是否完备**？很多团队加了 **Plan-and-Execute / ToT / Reflexion** 等高级 agent loop，本文都没单列。
- **反框架立场**有路径依赖——Anthropic 自家 SDK 也在不断加抽象（Claude Agent SDK）。
- **"几行代码"** 是简化叙述：真实场景里 retry / 鉴权 / 流式 / 错误恢复 / observability 加起来不少。
- **ACI 没有给具体准则**：什么样的 schema 是好的、怎么评工具描述质量——本文是宣言，不是 cookbook。

---

## 十、行动项

- [ ] 在 [../README.md](../README.md) 第 4 节"Agent 架构"加一行链接：**Workflow vs Agent: Anthropic 的边界**
- [ ] 在 [../tools-protocols/tool-development.md](../tools-protocols/tool-development.md) 顶部加 **ACI 概念**章节
- [ ] 在 [../agents/agent-loop-architectures.md](../agents/agent-loop-architectures.md) 加一节 **Augmented LLM = agentic system 的最小单元**
- [ ] 把 5 种构件做成可视化（`.planning/templates/AGENTIC-PATTERNS.md`），供后续团队复用

---

## 十一、关键引用

- "**The most successful implementations weren't using complex frameworks or specialized libraries. Instead, they were building with simple, composable patterns.**"
- "**Find the simplest solution possible, and only increase complexity when needed.**"
- "**Frameworks make it tempting to add complexity when a simpler setup would suffice.**"
- "**Agents are typically just LLMs using tools based on environmental feedback in a loop.**"
- "**Maintain simplicity. Prioritize transparency. Carefully craft your ACI.**"

> 整篇宣言的总结：
> **Agent 不是工程奇迹，agent 是反复迭代的简单循环 + 优秀的工具接口。**
