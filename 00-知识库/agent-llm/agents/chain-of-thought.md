# Chain-of-Thought (CoT) 原理与应用策略

> 本文是 [react-and-variants.md](react-and-variants.md) 的**前置篇**——ReAct 之所以成立，是因为 CoT 已经把"让 LLM 写出推理过程"这件事跑通了。把 CoT 讲透才能解释清楚 ReAct / Reflexion / ToT 这些后继范式分别在 CoT 上加了什么。
>
> 阅读路径：本文 → [react-and-variants.md](react-and-variants.md)（看 CoT 怎么演化成 Agent 范式）→ [tree-of-thoughts.md](tree-of-thoughts.md)（看 CoT 怎么升维成树搜索）。

---

## 一、CoT 解决的真问题

2022 年之前，LLM 在数学题、常识推理、多步问答上表现都很差。一个很小的改动改变了这一切：

```
Prompt A（普通）:                       Prompt B（CoT）:
  Q: 罗杰有 5 个网球。                    Q: 罗杰有 5 个网球。
     他买了 2 罐网球，每罐 3 个。            他买了 2 罐网球，每罐 3 个。
     他现在有几个网球？                     他现在有几个网球？
  A: 11                                  A: 罗杰一开始有 5 个。
                                            2 罐 × 每罐 3 个 = 6 个新球。
                                            5 + 6 = 11。
                                            答案是 11。
```

Wei et al. (2022) 在 GSM8K（数学应用题）上测了 PaLM-540B：
- **直接答**：17.9%
- **CoT 提示**：56.9%

CoT 的核心洞察一句话：

> 不是让 LLM "更聪明"，而是**让它把推理过程写出来**——写出来的过程会反过来约束最终答案不会跳跃。

这是后续所有 Agent 范式的起点：ReAct = CoT + 工具，Reflexion = CoT + 自我评估，ToT = CoT + 树搜索。**离开 CoT，没有今天的 Agent**。

---

## 二、为什么"写出来"就有效——三个机制

### 机制 1：把单步预测变成多步预测

LLM 的本质是 next-token prediction。直接答 11，模型需要**在一步内**完成"理解题目 + 数学计算 + 输出"——这超出了 transformer 在单次前向传播里的计算预算。

写出过程后：

```
"罗杰一开始有 5 个" ←  这一句的 token 在被生成时，模型只需要做"提取信息"
"2 × 3 = 6"       ←  这一句被生成时，前面已经有 "5"、"2 罐"、"3 个" 这些
                     token 在上下文里——模型只需要做"乘法"
"5 + 6 = 11"      ←  类似
```

**每一步只解决一个子问题**，每一步都是 LLM 容易做对的事。CoT 等于把"一次推理"分摊成"K 次小推理"。

> 类比：人脑做心算 23×17，不是一步算出来，而是"23×10=230, 23×7=161, 230+161=391"。CoT 在 LLM 上做了同样的事。

### 机制 2：上下文里的 token 互相校验

这是 CoT 最被低估的机制。一旦"5 + 6 = 11"被写到上下文里，下一步要写"答案是 ?" 的时候，模型会**强烈倾向于和上文一致**——因为 LLM 训练目标就是让上下文连贯。

→ **写出来的推理过程，自己变成了下一步推理的约束**。

这一点在 self-consistency（下一节）和 ReAct 里被进一步利用。

### 机制 3：错就错得明显

直接答错没法调试，CoT 答错时你能看到：

```
"罗杰一开始有 5 个。
 2 罐 × 每罐 3 个 = 5 个新球。   ← 这里算错了
 5 + 5 = 10。
 答案是 10。"
```

→ Prompt 工程师能定位"模型在哪一步歪了"，针对性优化。这把 LLM 从黑箱变成了可审查的"推理流程"。

---

## 三、CoT 的 4 类提示形式

CoT 不是一种 prompt，而是一组思路。按照"是否人工提供示例"和"过程的结构化程度"分四类：

```
                  示例多少？
        ┌─────────────────────────┐
   零样本（zero-shot）            少样本（few-shot）
        │                              │
   ┌────┴────┐                    ┌────┴────┐
 自由 CoT   结构化               原始 CoT   ReAct-style
                                              （结构化 + 工具）
```

### 3.1 Zero-shot CoT —— "Let's think step by step"

Kojima et al. (2022) 发现：在问题后加一句 **"Let's think step by step."**，零样本性能就大幅提升。

```
Q: ...问题...
A: Let's think step by step.
   [模型自动接着写出步骤]
```

→ 最便宜、最普适。生产环境里 80% 的"快速接 CoT"都用这个。

### 3.2 Few-shot CoT —— 给几个带步骤的示例

Wei 等人原始 CoT 论文的标准做法。给 3-8 个 (Q, 步骤化 A) 示例，再问真正的问题。

```
Q: 例题 1
A: 步骤 1... 步骤 2... 答案 X。

Q: 例题 2
A: 步骤 1... 步骤 2... 答案 Y。

Q: 真正的问题
A: [模型按相同格式写]
```

→ 比零样本准 5-15 个点，但 prompt 长、贵。**示例选得对不对很影响效果**——这是后来 prompt 工程的一大方向。

### 3.3 Structured CoT —— 把过程切成命名字段

把"步骤"显式拆成结构化字段，强迫模型按格式想：

```
Q: ...
分析：
  - 已知：...
  - 求解：...
  - 用到的公式：...
计算：
  - ...
答案：...
```

→ 适合**有标准解题流程的场景**：数学竞赛题、SQL 推导、合同条款分析。比自由 CoT 稳定。

### 3.4 ReAct-style CoT —— 把"做"嵌入"想"

CoT 的步骤里允许调用工具：

```
Thought: 我需要查 X
Action: search(X)
Observation: ...
Thought: 现在我有了 X，下一步...
```

→ 这是 [react-and-variants.md](react-and-variants.md) 的主题。**ReAct = CoT + Tool Use + Observation 反馈**。CoT 是它的推理骨架。

---

## 四、CoT 的 3 个增强变体

CoT 跑通后，2022-2023 年有一批论文专门改进它的稳定性。

### 变体 1：Self-Consistency（自洽采样）

Wang et al. (2022) 的核心发现：

> CoT 答错的时候，往往是**采样到了不好的推理路径**。同一个问题多次采样（高温度），多数表决，准确率显著上升。

```
1. 问 1 次问题，让模型用 CoT 回答 → 答案 X₁
2. 重复 K 次（K=20-40，温度 0.7）  → 答案 X₂, X₃, ..., X_K
3. 取多数票                       → 最终答案
```

GSM8K 上从 56.9% (CoT) 提升到 74.4% (CoT + self-consistency)。

**业务含义**：

- 任务**对了就值钱、错了代价大**（医疗辅助、法律推理）→ 值得 self-consistency
- 任务**实时**（聊天 / 客服）→ 跑 K 次太慢，不要用
- **答案是开放生成**（写文章）→ 没法多数票，不适用

### 变体 2：Least-to-Most（化大为小）

Zhou et al. (2022)。把"做完整任务"拆成"先想出子问题列表，再一个个解决"：

```
阶段 1（分解）：
  Q: 复杂问题 P
  Prompt: "为了解决 P，需要先回答哪些子问题？列出来。"
  → 子问题 [Q₁, Q₂, ..., Q_n]

阶段 2（依次回答）：
  解 Q₁ → A₁
  把 (Q₁, A₁) 加进上下文，解 Q₂ → A₂
  ...
  最后解 P，已经有了所有 (Q_i, A_i) 作为参考。
```

→ 是 [react-and-variants.md](react-and-variants.md) 里 **Plan-and-Execute 范式的雏形**。Plan-and-Execute = Least-to-Most + 工具调用。

### 变体 3：Self-Refine（自我修正）

Madaan et al. (2023)。让模型先答一次，然后让它自己批评自己的答案，再修正：

```
1. 初次回答 → A₀
2. Critic prompt: "找出 A₀ 里的问题"  → 反馈 F
3. Refiner prompt: "根据反馈 F 改进 A₀" → A₁
4. 重复 2-3 直到 critic 说没问题
```

→ Reflexion 范式的内核。区别：Self-Refine 没有外部反馈源（纯自评），Reflexion 通常有可验证反馈（代码能不能跑、答案对不对）。

---

## 五、CoT 的成本经济学

CoT **不是免费**。每多一个 step，token 都多一倍。

```
直接答:    输入 100 tokens + 输出 5 tokens   ≈ $0.001
CoT:       输入 100 + 输出 200 tokens         ≈ $0.005
Self-consistency (K=20):                     ≈ $0.10
Plan-and-Execute (5 步)：                     ≈ $0.05
ReAct (5 轮)：                                ≈ $0.10
ToT (depth=4, b=5)：                          ≈ $0.30 - $1.00
```

**经验法则**：

- 任务**简单 + 高频**（FAQ 客服）→ 不要 CoT，直接答
- 任务**复杂 + 单次**（数据分析、报告生成）→ 用 CoT
- 任务**正确性极敏感** → 用 CoT + Self-Consistency
- 任务**需要外部信息** → 用 ReAct（CoT + 工具）
- 任务**评估比生成贵** → 用 Plan-and-Execute（Planner 强 + Executor 弱）
- 任务**第一步选错代价巨大** → 用 ToT

→ CoT 是这套阶梯的**第一阶**。生产环境里大约 60% 的 LLM 调用就停在 CoT，并不需要往上爬。

---

## 六、什么时候 CoT 有效，什么时候反而有害

### ✅ CoT 显著有效的 3 类任务

1. **多步推理**——数学题、逻辑题、规划、推断因果。每多一步推理，CoT 的相对增益越大。
2. **可验证的结构化输出**——SQL 生成、代码生成、JSON 抽取。先想再写比直接写错误率低。
3. **需要权衡多因素的判断**——"这个 PR 该 approve 吗？""这个客户该退款吗？"先列因素再下结论比直接判更稳。

### ❌ CoT 反而有害的 3 类任务

1. **简单事实问答**——"北京是哪个国家的首都？"加 CoT 反而让模型东扯西扯。Liu et al. (2024) 在 *To CoT or not to CoT* 里测过：在常识、阅读理解、事实检索任务上，CoT 平均提升只有 1-2 个点，有时还降低。
2. **创意 / 风格类生成**——写诗、写广告语。"先思考再生成"会让产出变得说教、啰嗦、丧失风格。
3. **延迟敏感的实时对话**——CoT 让首 token 慢 3-5 倍。客服 / 语音助手不该用。

### 经验判别

> CoT 的收益，正比于"任务步骤数"，反比于"任务的灵感属性"。
>
> 不知道时的快速判别：**先关掉 CoT 跑 20 个 case，再开 CoT 跑同样 20 个，比 accuracy。差距小于 5% 就别开**。

---

## 七、CoT 的 5 个工程坑

### 坑 1 — 步骤幻觉（合理但错的推理链）

模型常常**写得头头是道但中间一步就错**：

```
"罗杰一开始有 5 个。
 2 罐 × 每罐 3 个 = 5 个新球。   ← 错。但模型继续往下写得很顺。
 5 + 5 = 10。"
```

CoT 不会帮你发现这种错误，反而把它"包装得看起来对"。

**解法**：
- 关键计算步骤交给工具（Python 解释器 / 计算器）→ 这就是为什么 ReAct 比纯 CoT 强
- 用 Self-Consistency 多采样投票，幻觉路径会被多数票稀释

### 坑 2 — 推理冗余 / 啰嗦

模型有时候会写 5 段才到答案，简单题也变贵。

**解法**：
- Few-shot 示例**主动写得简短**，模型会模仿
- 显式约束："Think briefly, in 2-3 sentences."
- 评估时区分"推理 token"和"答案 token"，只看后者的成本

### 坑 3 — 把"先想再写"当成"想了就一定对"

很多团队上线 CoT 后看到 accuracy 涨了 10 个点就以为搞定了，但**剩下 30% 的错误反而更难调**——因为产出看起来更"专业"，错得更隐蔽。

**解法**：
- CoT 上线必须配 **error analysis 流程**，按"错在哪一步"分类
- 比 accuracy 更重要的是 **calibration**——模型自报的置信度和实际正确率是否对齐

### 坑 4 — Few-shot 示例污染

给 3 个示例，模型学到的不只是"步骤化思考"，还有：
- 示例里的写作风格
- 示例里的格式偏好
- 示例里的特定领域偏见

**解法**：
- 示例尽量**和真实 query 同分布**
- 多样化示例（不要 3 个都是同一类问题）
- 大模型用 zero-shot CoT 通常就够，不必硬塞 few-shot

### 坑 5 — 把 CoT 当成 Agent

CoT 只是"让 LLM 写步骤"，**不能调工具、不能纠错、不能反思**。当任务需要外部信息或多轮交互时，应该升级到 ReAct / Reflexion。

→ 一句话区分：**CoT 是单次推理的内部展开，Agent 是多轮交互的外部循环**。

---

## 八、在 [`project/ice-workbench/`](../../ice-workbench/) 里怎么用

下面是 CoT 在生产场景里的最小落地形态——按"任务复杂度"决定上哪一档。

### 档位 1：简单结构化输出（用 Zero-shot CoT）

任务：用户提了一句话需求，要让模型抽成结构化 JSON。

```python
prompt = f"""
用户需求：{user_input}

先简短分析（1-2 句话）这个需求的核心动作和对象，
然后输出 JSON。

分析：
"""
```

→ 让模型先写 1-2 句话再产 JSON，错误率显著下降。**成本只多 50-100 tokens**。

### 档位 2：复杂业务判断（用 Structured CoT）

任务：判断一个 issue 该分给哪个 owner、优先级多高。

```
分析：
  - issue 类型：bug / feature / question
  - 影响面：单用户 / 部分用户 / 全量
  - 紧急度：阻塞 / 不阻塞
推理：
  - 同类历史 issue 的 owner 通常是 ...
  - 影响面 + 紧急度 → 优先级 ...
结论：
  owner = ...
  priority = ...
```

→ Structured CoT 比自由 CoT 在"业务判断"类任务上更稳，因为你**显式定义了思考维度**。

### 档位 3：高价值生成（用 CoT + Self-Consistency）

任务：自动生成发给客户的赔偿方案。

```python
results = []
for _ in range(5):
    r = llm.generate(cot_prompt, temperature=0.7)
    results.append(extract_decision(r))

decision = majority_vote(results)
confidence = max_count / len(results)

if confidence < 0.6:
    escalate_to_human()
```

→ 5 次采样里如果 4 次以上一致，自信地用；不一致就升人审。这个模式是 CoT 在生产环境**最实用的"半自动审批"形态**。

### 档位 4：多步任务（升级到 ReAct）

任务：根据用户问题查多个内部数据源、综合后回答。

→ 这时候 CoT 不够了，因为需要调用工具。直接走 ReAct（见 [react-and-variants.md](react-and-variants.md)）。

---

## 九、CoT 在新一代模型里的演化

2024-2025 年，CoT 不再只是"prompt 技巧"，被两条路径吸进了模型本身。

### 路径 1：模型自带的"思考时间"——OpenAI o1 / o3 系列

o1 把 CoT 从 prompt 层下沉到模型层：

```
传统 CoT:                 o1-style:
  user → prompt(加CoT)     user → 模型内部跑 N 秒"reasoning"
       → LLM → 答案              → 答案
```

模型内部实际上跑了**ToT 风格的多路径搜索 + 自我评估**，但用户只看到"思考了几秒，给出最终答案"。

→ 对工程师的意义：**简单 CoT 任务可以让 o1 自己处理**，不必手写 prompt 模板。但价格是普通模型 5-10 倍。

### 路径 2：Reasoning 蒸馏到普通模型——Claude / DeepSeek-R1 / 文心 X1

把 o1 风格的"长 reasoning trace"作为训练数据，蒸馏到中等规模模型。**这些模型在 zero-shot 下就有很强的 CoT 能力**，不需要再加"Let's think step by step"。

→ 对工程师的意义：**用新模型时不用过度操心 CoT prompt**，但要意识到模型默认在"想"，输出会更长、更慢。

### 工程师该怎么办

1. **把 prompt 模板和模型能力解绑**——不要硬编码 "Let's think step by step"，改成可配置开关。
2. **用基准任务定期重测**——同一个 prompt 在 GPT-4o / Claude 4 / DeepSeek-V3 上 CoT 收益完全不同。
3. **关注 reasoning token 成本**——新模型的 reasoning token 计费是输出 token 的 1-3 倍，账单容易爆。

---

## 十、回到根：CoT 给整个 Agent 领域留下的遗产

CoT 本身的论文已经四年前了，但它的三个核心发现支撑着今天的所有 Agent 架构：

1. **"让模型把过程写出来"是一种通用对齐手段**——后来的 Constitutional AI、RLHF rationale、Tool Use schema 全部继承了这个思路。
2. **token 流可以当指令流用**——ReAct 把这点用到极致：上下文里出现什么，下一步就做什么（见 [react-mechanism-and-strategy.md](react-mechanism-and-strategy.md)）。
3. **"采样多次 + 选最好"是免费的 scaling law**——self-consistency 的思想被 ToT、Reflexion、o1 全部继承。

> 如果只能记一句话：**CoT 不是 prompt trick，是把 LLM 从"答题机器"变成"推理机器"的范式拐点**。后来的所有 Agent 工作，不管叫 ReAct、ToT 还是 o1，本质上都是在 CoT 这一基础上换不同的搜索 / 反馈 / 工具组合。

---

## 附：相关阅读

- [react-and-variants.md](react-and-variants.md) —— CoT 加上工具和反馈环，演化为 ReAct 及其变体。
- [react-mechanism-and-strategy.md](react-mechanism-and-strategy.md) —— ReAct 的 token 流 / prompt 编排细节，CoT 的工程化延伸。
- [tree-of-thoughts.md](tree-of-thoughts.md) —— CoT 升维成树搜索，单线推理变多路径。
- [research-agent-architecture.md](research-agent-architecture.md) —— Plan-and-Execute 在研究型任务里的工程接法（Least-to-Most 的实战版）。