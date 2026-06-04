# ReAct: Synergizing Reasoning and Acting in Language Models

> **出处**：arXiv [2210.03629](https://arxiv.org/abs/2210.03629)（ICLR 2023）
> **作者**：Shunyu Yao, Jeffrey Zhao, Dian Yu, Nan Du, Izhak Shafran, Karthik Narasimhan, Yuan Cao
> **发布**：2022-10
> **一句话**：把"**Thought（推理）**"和"**Action（动作）**"在同一个生成轨迹里交错，**不需要训练**就能让 LLM 既推理又用工具——成为后续几乎所有 agent loop 的事实标准。

---

## 〇、核心论断（一段读懂）

- 在 ReAct 之前，**reasoning（如 CoT）** 和 **acting（如 WebGPT 的搜索行为）** 是分离的两条路线。
- ReAct 把它们**统一到一条 prompt 模板**里——LLM 自己生成 `Thought:` 和 `Action:` 交替序列，每次 `Action` 后从环境得到 `Observation`，然后继续 `Thought`。
- **效果惊人**：在 HotpotQA、FEVER、ALFWorld、WebShop 等四类任务上**普遍优于纯推理或纯行动**的 baseline——尤其是**幻觉抑制**——因为推理可以参考刚刚获得的真实观察。
- **ReAct 是当代所有 agent loop 的精神祖先**：Claude Code / OpenHands / LangGraph / 各家 framework 用的都是它的变体。

---

## 一、问题动机

### 1.1 单纯 CoT 的局限

CoT（Chain of Thought）在数学题等任务上有用，但有两类问题：

- **幻觉**：纯生成的 reasoning 没有事实锚点，**编造步骤** / **编造前提**
- **缺乏外部知识**：模型权重中没有的信息，CoT 没法获取

### 1.2 单纯 acting 的局限

WebGPT 这种"边搜边答"的 agent 表现也不错，但：
- **缺反思能力**——不会停下来思考"我现在该问什么"
- **决策被搜索结果淹没**——观察过多但不组织
- **工具序列脆弱**——错一步全错

### 1.3 ReAct 的洞察

> "**Reasoning and acting can synergize.**"
> 推理引导何时行动，行动给推理提供事实锚点。

---

## 二、ReAct 的格式（业界引用最多的部分）

```
Thought 1: I need to search ...
Action 1: Search[X]
Observation 1: <环境返回>
Thought 2: 根据上一步，我应该 ...
Action 2: Lookup[Y]
Observation 2: <环境返回>
...
Thought N: 我已经有足够信息
Action N: Finish[answer]
```

关键设计点：
- **Thought 是自由文本**——可以是 plan、可以是 self-criticism、可以是中间结论
- **Action 是受限语法**——`Search[...]` / `Lookup[...]` / `Finish[...]` 等离散动作 + 自由参数
- **Observation 是环境给的**，不是模型生成的
- **Few-shot prompt** 给几个完整轨迹做示例，模型按格式延续

> 看起来朴素，但**让推理和行动在同一个 token 流里**——这一点是质变。

---

## 三、实验任务与发现

### 3.1 知识密集型任务（HotpotQA, FEVER）

- HotpotQA：多跳问答；FEVER：事实校验
- 工具：`Search[entity]`、`Lookup[keyword in retrieved doc]`、`Finish[answer]`
- 结果：
  - **ReAct 显著超过 Action-only**（无 Thought）
  - 但**单纯 ReAct 略低于 CoT-SC（Self-Consistency）**——CoT-SC 内部知识发挥得很好
  - **混合 ReAct → CoT-SC**（先 ReAct 失败再 fallback CoT-SC，反之亦然）：**最优**

### 3.2 决策任务（ALFWorld, WebShop）

- ALFWorld：家务环境，"把苹果放到桌上"等
- WebShop：模拟电商导航
- 工具：`go to`、`take`、`put`、`open`、`click[link]` 等
- 结果：
  - **ReAct 大幅超越 Act-only baseline 和模仿学习 baseline**
  - 比 imitation learning 训练 10万级别样本的 baseline，**ReAct 仅靠 1-2 个 prompt 例子**就赢
  - 在 ALFWorld 上 ReAct **34%**，纯 Act **仅 25%**；WebShop 上 ReAct **40%**，纯 Act **29%**

### 3.3 关键失败模式

作者诚实列出了 ReAct 的失败模式：
- **推理错误**：Thought 一旦走错，后续 Action 全偏
- **搜索失败**：信息不在搜索结果里 → reasoning 被噪声污染
- **格式错乱**：偶尔不按 `Thought / Action / Observation` 输出（少见但存在）

---

## 四、为什么 ReAct 这么有影响力

### 4.1 它是**零训练**的

不动模型权重，只用 few-shot prompt 即可工作——**任何足够强的 LLM 都能跑**。

### 4.2 它定义了**可解释的 agent loop**

Thought / Action / Observation 这套格式让人**能看见 agent 在想什么**——这是后续所有 transparency 设计的起点。

### 4.3 它**接口友好**

`Action: Search[query]` 和 function calling 一一对应——**模型一开口就出格式良好的工具调用**。Anthropic / OpenAI 后来的 function calling 协议本质就是 ReAct 模板的工程化。

### 4.4 失败时容易诊断

读 transcript 就能看到推理在哪一步走错。这呼应了 [demystifying-evals-for-ai-agents.md](demystifying-evals-for-ai-agents.md) 的"读 transcript 是关键技能"。

---

## 五、ReAct 的"后代"

| 后续工作 | 核心改动 |
|---|---|
| **Reflexion** ([reflexion-shinn-2023.md](reflexion-shinn-2023.md)) | 加一层 self-reflection，跨 episode 记住失败教训 |
| **Tree of Thoughts** | Thought 不再是线性的，**树搜索** |
| **Self-Consistency / CoT-SC** | 多条 Thought 链投票 |
| **Plan-and-Execute** | 先全局 Plan 再 Execute，不是逐步反应 |
| **AutoGPT / BabyAGI** | ReAct + 任务队列 + 长期记忆 |
| **OpenAI Function Calling** | ReAct 的 Action 部分**结构化**（JSON schema） |
| **Anthropic Tool Use** | 和 OpenAI Function Calling 思路一致 |
| **MCP** | ReAct 的 Action 注册中心化、跨 agent 复用 |

> **没有 ReAct，就没有今天的 agent 生态。**

---

## 六、和本仓库现有结论的对照

| 本文论点 | 本仓库已有 |
|---|---|
| ReAct 模板 | [../agents/react-and-variants.md](../agents/react-and-variants.md) ✓ 主战场 |
| ReAct 机制和策略 | [../agents/react-mechanism-and-strategy.md](../agents/react-mechanism-and-strategy.md) ✓ |
| Thought-Action-Observation 三元组 | [../agents/agent-loop-architectures.md](../agents/agent-loop-architectures.md) ✓ |
| Function Calling 是 ReAct 工程化 | [../tools-protocols/function-calling.md](../tools-protocols/function-calling.md) 可加这个历史脉络 |
| CoT vs ReAct 取舍 | [../prompting/cot-family.md](../prompting/cot-family.md) 应加 |
| HotpotQA / FEVER / ALFWorld / WebShop | [../evaluation/benchmarks.md](../evaluation/benchmarks.md) 可补 ALFWorld / WebShop 介绍 |

---

## 七、反对意见与待验证

- **ReAct 在长任务中的弱点**：**累积 token / context 漂移 / 重复劳动**——这些是 [long-task-agents.md](../agents/long-task-agents.md) 的核心命题，ReAct 本身解决不了
- **Few-shot 选择敏感**：示例换一组，效果可能差很多——后续 paper 经常没复现
- **格式脆弱**：模型偶尔脱离格式；现代 function calling 把这部分修了，但代价是失去自由文本的灵活性
- **"Reasoning + Acting" 不一定总是有 synergy**：纯知识题（如数学）CoT 单独更好；纯执行题（如 ALFWorld）Action 占大头
- **没有探索机制**：ReAct 是贪心式的，遇到死胡同不会回溯——后来 ToT、MCTS 才补这一点

---

## 八、行动项

- [ ] 在 [../agents/react-and-variants.md](../agents/react-and-variants.md) 顶部加链接到本论文笔记
- [ ] 在 [../tools-protocols/function-calling.md](../tools-protocols/function-calling.md) 加历史脉络章节："Function Calling = ReAct 的工程化协议化"
- [ ] 在 [../evaluation/benchmarks.md](../evaluation/benchmarks.md) 添加 ALFWorld / WebShop 介绍
- [ ] 在 [../agents/long-task-agents.md](../agents/long-task-agents.md) 显式说明："长任务的 6 失败模式都不是 ReAct 能解决的——这是为什么需要更多机制"

---

## 九、关键引用 / 公式记忆

经典 prompt 片段：
```
You will be given a question, and you should answer it by searching, lookup, or thinking.
You can do the following actions: Search[entity], Lookup[keyword], Finish[answer].
Always start with a Thought before each Action.

Question: <question>
Thought 1: ...
Action 1: ...
Observation 1: ...
```

> 一句话精神：
> **"Reasoning traces help action; observations help reasoning. Mix them."**

ReAct 不是一篇 SOTA 论文，但它**重塑了 agent 的形态**——业界后来所有 agent loop 都是它的变体或扩展。
