# LLM Powered Autonomous Agents

> **出处**：[Lil'Log](https://lilianweng.github.io/posts/2023-06-23-agent/)
> **作者**：Lilian Weng（OpenAI 应用研究负责人）
> **发布**：2023-06-23
> **一句话**：第一篇被广泛引用、把"LLM-powered agent"做成清晰**三组件分类法（Planning / Memory / Tool Use）**的综述——奠定了之后两年 agent 工程对话的基本词汇。

---

## 〇、核心论断（一段读懂）

- 在这篇之前，AutoGPT、BabyAGI、GPT-Engineer 各有玩法，社区没有共同语言
- Lilian Weng 提出一个**三组件框架**：
  ```
  Planning    ── Subgoal decomposition + Reflection / Self-criticism
  Memory      ── Short-term (in-context) + Long-term (vector store)
  Tool Use    ── 调外部 API 拿模型不知道的信息
  ```
- 这套词汇成了**后续所有 agent 文档的事实标准**——OpenAI / Anthropic / LangChain 的图都是这套。
- 综述风格——不是新方法，**是把已有方法整理成一张图**。

---

## 一、Agent System Overview（核心图）

```
                  ┌──────────────────┐
                  │     Memory       │
                  │  ─ short-term    │
                  │  ─ long-term     │
                  └────────▲─────────┘
                           │
                  ┌────────┴─────────┐
        plan      │       LLM        │      action
        ────────► │   (Agent Brain)  │ ─────────►
                  └────────▲─────────┘
                           │
                  ┌────────┴─────────┐
                  │     Tools        │
                  └──────────────────┘
                           ▲
                           │
                       Planning
                  (subgoal + reflection)
```

LLM 是"大脑"，外挂三件套。所有现代 agent 框架都是这张图的工程化。

---

## 二、组件 1：Planning

### 2.1 Task Decomposition

- **CoT（Chain of Thought）**：让模型 "think step by step"，把大任务分成小步骤
- **Tree of Thoughts**：在每一步生成多个 thought，**树搜索**（BFS / DFS）
- **简单 prompt** 也能做：`"Steps for XYZ.\n1."` / `"What are the subgoals for achieving XYZ?"`
- **LLM+P**：让 LLM 把问题翻译成 PDDL，外部经典规划器解，结果再翻译回自然语言

### 2.2 Self-Reflection

- **ReAct**（[react-yao-2022.md](react-yao-2022.md)）：Reasoning + Acting 在同一轨迹
- **Reflexion**（[reflexion-shinn-2023.md](reflexion-shinn-2023.md)）：跨 episode 用语言反思
- **Chain of Hindsight (CoH)**：把人类反馈历史拼到 prompt，让模型学着自我修正

> 这一节几乎覆盖了 2023 年之前所有 reasoning + agent 的核心工作。

---

## 三、组件 2：Memory

Lilian 把人脑记忆理论拿来做类比：

| 人脑记忆 | LLM agent 类比 |
|---|---|
| Sensory memory（感觉记忆，毫秒级） | LLM 的输入 embedding |
| Short-term memory（短时记忆） | **Context window 内的 in-context learning** |
| Long-term memory（长时记忆） | **外部向量库 + 检索** |
| Explicit memory: episodic / semantic | 工具调用历史 / 知识库 |
| Implicit memory: procedural | 模型权重本身 |

### 关键工程问题：MIPS（Maximum Inner Product Search）

长期记忆要用近似最近邻：
- **LSH**（Locality-Sensitive Hashing）
- **ANNOY**（树结构）
- **HNSW**（基于图）
- **FAISS**（量化）
- **ScaNN**

> 这一节是**当年 RAG 工程的入门必读**。

---

## 四、组件 3：Tool Use

- LLM 学会"调用外部 API"绕过权重不可改的问题
- 关键工作：
  - **MRKL**（Modular Reasoning, Knowledge and Language）：早期 routing 思想——LLM + 多个专家模块
  - **TALM / Toolformer**：训练 LLM 学习 API 调用
  - **HuggingGPT**：LLM 当 controller，调用 HuggingFace 上的多个 model
  - **API-Bank**：评测 LLM 用工具的 benchmark

> 这一节是 OpenAI Function Calling、Anthropic Tool Use 的**思想前哨**——一年后这些就成产品功能了。

---

## 五、案例研究

### 5.1 Scientific Discovery Agent

- **ChemCrow**：化学家 agent，用 17 个化学专用工具规划合成路径
- 比纯 GPT-4 显著好——专家工具是关键

### 5.2 Generative Agents Simulation

- Stanford / Google 的 25 个 agent 模拟小镇
- 每个 agent 有 memory stream + reflection + planning
- 引发"涌现行为"：互相邀请生日派对、传播信息

### 5.3 Proof-of-Concept

- **AutoGPT**：把 task 队列 + memory 接进 GPT-4，让它自己跑
- **GPT-Engineer**：写代码的 agent
- **BabyAGI**：极简任务循环

> 这些是社区的"早期产品级 agent"——也是后来 Manus / Devin / Claude Code 的远祖。

---

## 六、Lilian Weng 总结的"挑战"

文章末尾给了几条**至今依然没解决**的挑战：

1. **有限的 context 长度**——agent 想记住的东西比 context 能装的多
2. **长程规划困难**——LLM 在多步规划中容易漂移
3. **自然语言接口的可靠性**——格式不稳，下游难解析
4. **细节执行不稳**——agent 容易看似在做对的事，实际细节错
5. **学习能力**——如何让 agent 跨任务积累，**至今仍是开放问题**

> **三年后回看，这五条几乎一字未变地仍是 agent 研究的核心命题**——这就是本文的"远见性"。

---

## 七、为什么这篇文章地位特殊

### 7.1 词汇贡献

- "Planning / Memory / Tool Use" 这套切分法**成了行业话术**
- 所有后续教程、综述、SDK 都套这个框架

### 7.2 综述质量

- 引用 50+ 篇当时分散的论文，**第一次整合**
- 既给 conceptual 也给 implementation 提示

### 7.3 时机

- 发布于 ChatGPT plugin 上线、AutoGPT 病毒级传播之后
- 业界正缺一个"权威整理"——Lilian Weng 写出来了

> 截至 2026，这篇仍是被引用最多的 agent 综述博客之一。

---

## 八、和本仓库现有结论的对照

| 本文论点 | 本仓库已有 |
|---|---|
| Planning / Memory / Tool Use 三组件 | [../README.md](../README.md) 第 4 节 ✓ |
| Task decomposition 方法谱系 | [../agents/tree-of-thoughts.md](../agents/tree-of-thoughts.md) ✓ |
| Self-reflection 谱系 | [../agents/react-and-variants.md](../agents/react-and-variants.md) ✓ |
| Short-term / Long-term memory | [../agents/memory-systems.md](../agents/memory-systems.md) ✓ |
| MIPS / 向量检索 | [../rag/retrieval-basics.md](../rag/retrieval-basics.md) ✓ |
| Tool use 工作谱系 | [../tools-protocols/function-calling.md](../tools-protocols/function-calling.md) ✓ |
| ChemCrow / Generative Agents 案例 | **建议新增** [../agents/case-studies-classics.md](../agents/case-studies-classics.md) |
| 5 大未解挑战 | [../agents/long-task-agents.md](../agents/long-task-agents.md) ✓（"6 失败模式"是这一条的延续） |

---

## 九、反对意见与待验证

- **三组件分类**清晰但可能**过度简化**：现代 agent 还需要"planning + execution"分离、"persistent state"独立——三组件不够用
- **"Memory = vector store"** 在多模态 / 结构化记忆出现后偏窄
- **Tool use** 这一节描述偏 2023 早期——MCP 之后协议化讨论缺失（但本文写的时候 MCP 还不存在）
- **5 大挑战** 写得对但**缺解决路径**——这是综述天然的局限
- **case studies 偏 PoC**：AutoGPT / BabyAGI 后来都没真正生产化——更值得讲的是 Cursor / Claude Code 这一代

---

## 十、行动项

- [ ] 在 [../README.md](../README.md) "关键参考" 节明确 link 到本笔记
- [ ] 把 "Planning / Memory / Tool Use" 三组件做成 [../OVERVIEW.md](../OVERVIEW.md) 顶部的"经典分类法"图
- [ ] 在 [../agents/memory-systems.md](../agents/memory-systems.md) 加一节："**人脑类比 vs 工程实现**"——直接借用 Lilian 的对照表
- [ ] 新增 [../agents/case-studies-classics.md](../agents/case-studies-classics.md) 收录 ChemCrow / Generative Agents / AutoGPT 等"远祖案例"
- [ ] 在 [../agents/long-task-agents.md](../agents/long-task-agents.md) 末尾加一节："**Lilian Weng 三年前的 5 大挑战，今天解决了几个？**"

---

## 十一、关键引用

- "**Building agents with LLM as the core controller is a cool concept.**"（开篇就奠定了基调）
- "**LLM functions as the agent's brain, complemented by several key components: Planning, Memory, Tool Use.**"
- "**Self-reflection is a vital aspect that allows autonomous agents to improve iteratively.**"
- "**Finite context length restricts the inclusion of historical information, detailed instructions, API call context, and responses.**"——三年后还是 agent 工程最大单点制约。

> 一句话精神：
> **"LLM 不是 agent 的全部，LLM 是 agent 的大脑——agent 还需要规划、记忆、工具。"**
> 这看似显然，但**第一个把它写下来并系统化**的就是这篇。
