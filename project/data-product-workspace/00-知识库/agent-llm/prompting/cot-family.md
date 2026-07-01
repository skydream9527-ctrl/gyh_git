# Chain-of-Thought 家族：让模型"想清楚"

> CoT（Chain-of-Thought, Wei et al., 2022）是过去 4 年提示工程最重要的发现，也是几乎所有现代 LLM 应用的"内功"。本文梳理 CoT 及其变体（Self-Consistency、ToT、Self-Refine、Reflexion、ReAct），告诉你**什么时候该用哪一个**。

---

## 一、CoT 一句话

> 让模型在给出最终答案前，**显式地写出中间推理步骤**。这一个改动能在数学、逻辑、复杂推理任务上提升 10-50 个百分点。

最经典的例子（Wei et al.）：

```
Q：Roger 有 5 个网球。又买了 2 罐网球，每罐 3 个。现在他有几个？

不用 CoT：A：11
用 CoT：   让我们一步步想：
            Roger 原来有 5 个。
            他又买了 2 罐 × 3 个 = 6 个。
            一共 5 + 6 = 11 个。
            A：11
```

GSM8K（小学数学题集）上：
- GPT-3 175B 直接答：**18%**
- GPT-3 175B 用 CoT：**57%**

> 这是工业界第一次意识到"提示词的形式本身能放大模型能力"。

---

## 二、为什么 CoT 有效（机制视角）

朴素直觉：让模型多算一些 token，相当于"借纸笔做题"。

更严谨的解释：

1. **计算深度**：Transformer 单次前向是固定层数（深度 32-100）。一个数学题需要 5 步推理，而模型层数有限——直接答就是"折叠"了所有步骤，能力受限。CoT 把推理"展开成 token 序列"，让模型可以**任意深度**地推下去。

2. **自我一致性**：写出中间步骤能让后面的 token 看到、引用前面的步骤——形成**软性逻辑约束**。

3. **训练数据反映**：网上的解题文本几乎都是带步骤的。CoT 实际是在召唤训练数据中"做题型"的数据分布。

---

## 三、五种 CoT 触发方式

### 1. Few-shot CoT（原始版）

在 prompt 里给 1-3 个带推理过程的例子：

```
Q1: 苹果 5 个，吃 2 个还剩几个？
A1: 5 - 2 = 3，剩 3 个。

Q2: 教室有 10 张桌子，搬走 3 张又添 5 张，现在几张？
A2: 10 - 3 + 5 = 12，现在 12 张。

Q3: [真实问题]
A3:
```

### 2. Zero-shot CoT（最便宜）

不给例子，直接加一句：

```
[问题]

让我们一步步思考。
```

Kojima et al. (2022) 发现：**只加这一句 zero-shot 也能涨大几十分**——因为模型在 SFT 阶段已经被训过这种触发词。

工业最常用，因为 prompt 简短、稳定。

### 3. 结构化 CoT（生产环境主推）

把推理过程结构化，让模型按字段输出：

```json
{
  "analysis": "用户问的是 ...",
  "key_factors": ["因素1", "因素2"],
  "reasoning": "因此 ...",
  "answer": "..."
}
```

| 优势 | 劣势 |
|---|---|
| 可解析、可审计 | 需要 JSON Mode / 结构化输出支持 |
| 推理过程独立可监控 | prompt 略复杂 |

### 4. CoT + 角色

```
你是一位资深统计学家。请按以下步骤分析：
1. 识别问题类型
2. 选择合适的检验方法
3. 解释结果含义

[问题]
```

适合**领域特定**的推理任务。

### 5. Plan-then-Solve（Wang et al. 2023）

先让模型写"做这题的计划"，再按计划执行：

```
Step 1: 写出解题计划
Step 2: 按计划逐步执行
```

适合**步骤多、容易遗漏**的任务（数学竞赛、长文写作、复杂代码）。

---

## 四、Self-Consistency：让 CoT 更稳

CoT 单次输出有随机性。**Self-Consistency**（Wang et al., 2022）的思路朴素但极有效：

```
1. 用 CoT 跑同一个问题 N 次（temperature > 0）
2. 收集 N 个答案
3. 投票选众数
```

**收益**：GSM8K 准确率从 57% → 74% 这一招就贡献了大头。

**代价**：N 倍 token 成本。

工业落地：
- 关键决策（数学题、SQL 生成）值得 N=5
- 低价值场景不上

---

## 五、Tree of Thoughts（ToT）：从直链到分支

CoT 是单线推理。**ToT**（Yao et al., 2023）扩展成树状：

```
            Root: 问题
               │
        ┌──────┼──────┐
       想法1  想法2  想法3      ← 在每一步生成多个候选
        │       │      │
     ┌──┼─┐  ┌──┼─┐  ┌─┴┐
    1a 1b 1c 2a 2b 2c 3a 3b
     │  ✗  │  ✗  │  │  ✗  │   ← 自我评估，剪掉无望分支
     ↓     ↓     ↓     ↓
    继续展开 ...
```

**关键步骤**：
- **生成（Propose）**：每步多采样
- **评估（Evaluate）**：让 LLM 自己评分（"这条思路有戏吗"）
- **搜索（Search）**：BFS 或 DFS + 剪枝

**适用**：
- 中间状态可评估（数学题、24 点、规划）
- 单线 CoT 走错路代价高
- 能承受 5-10× token 成本

**不适用**：
- 实时对话（太慢）
- 中间步骤没法判好坏

---

## 六、Self-Refine / Reflection：让模型自我修正

**思路**：模型给一版答案 → 自己批评 → 给改进版。

```
Step 1: 直接生成答案 v1
Step 2: 批评 v1 的不足
Step 3: 基于批评生成 v2
Step 4: ... (可循环 N 轮)
```

**何时有效**：

- 答案有客观标准（代码能不能跑、JSON 是否合法）
- 答案有具体改进点（写作改语病、数据分析查异常）

**何时无效**：

- 模型本来就不会的事，反思也想不出新东西
- 简单问题（自我反思反而引入"过度纠正"）

> **Reflexion**（Shinn et al., 2023）是 Self-Refine + 长期记忆——把反思的教训存下来跨轮使用。详见 [../agents/react-and-variants.md](../agents/react-and-variants.md)。

---

## 七、ReAct：CoT + 工具

详见 [../agents/react-and-variants.md](../agents/react-and-variants.md)。

```
Thought（CoT 推理）→ Action（调工具）→ Observation（看结果）→ Thought ...
```

ReAct 把 CoT 从"纯推理"扩展到"推理 + 行动"——是 Agent 的核心范式。

---

## 八、决策树：什么时候用哪种

```
                  任务难度？
              ┌──────┴──────┐
        简单           需要推理
              │             │
              ▼             ▼
         直接 prompt   用 CoT
                              │
                              ▼
                        一致性要求高？
                        ┌────┴────┐
                       是          否
                        │          │
                        ▼          ▼
                 Self-Consistency  普通 CoT
                        │
                        ▼
                  需要多路探索？
                  ┌────┴────┐
                 是          否
                  │          │
                  ▼          ▼
                 ToT      继续
                            │
                            ▼
                      需要纠错？
                      ┌────┴────┐
                     是          否
                      │
                      ▼
                  Self-Refine / Reflexion
                            │
                            ▼
                      需要工具调用？
                      ┌────┴────┐
                     是          否
                      │
                      ▼
                    ReAct
```

---

## 九、CoT 的副作用与陷阱

### 1. 简单问题反而变差
- 经验：分类、关键词抽取等简单任务上，CoT 经常引入幻觉
- 对策：先小数据集 A/B 测试，不要默认开

### 2. 长输出 = 高成本 + 高延迟
- CoT 输出长度通常 3-10×
- 用户能感知首字延迟（TTFT）和总耗时
- 对策：用 streaming、structured output、或对纯 reasoning 部分做后置截断

### 3. 模型"假装"在推理
- 推理过程看起来 plausible，但和最终答案脱节
- 极端情况下答错了，但理由很 confident
- 对策：评测时不只看答案，还要 check 推理一致性

### 4. CoT 暴露给用户的风险
- 模型的"心理活动"可能含偏见、错误结论、敏感推理
- 不要把 CoT 直接展示给最终用户
- 对策：CoT 内部用，用户看的是清洗过的最终答案

### 5. CoT 与多语言
- 用英语 CoT 比中文 CoT 通常推理更准（训练数据偏置）
- 对中文场景关键 prompt：可以让"推理用英文，最终回答用中文"

---

## 十、和模型版本的关系

新模型（GPT-4o、Claude 3.5+、DeepSeek-V3）很多在 SFT / RLHF 阶段已经"内化"了 CoT——有时不显式触发也会自动多想。OpenAI o1 系列更是把"长 CoT 推理"作为产品特性。

含义：
- 显式 CoT 在前沿模型上的边际收益**比一年前小**
- 但是 zero-shot CoT 仍然是"零成本默认"，建议保留
- ToT、Self-Refine 这种重型方案的 ROI 在模型变强后下降

---

## 十一、Checklist

```
□ 1. 我的任务真的需要推理吗（vs 直接回答）？
□ 2. 我用了 CoT 还是默认 prompt？做过 A/B 吗？
□ 3. 输出格式是结构化的（JSON）吗？还是大段自由文本？
□ 4. 关键决策是否上了 Self-Consistency？
□ 5. CoT 内容暴露给用户了吗（如果是，有审查机制吗）？
□ 6. 评测是否同时检查"答案对" + "推理过程合理"？
□ 7. 用的是 zero-shot CoT 还是 few-shot CoT？后者样例是否最新有效？
```

---

## 十二、扩展阅读

- 本目录：（同目录其他 prompting 文档可继续补）
- 相关：[../agents/react-and-variants.md](../agents/react-and-variants.md)、[../evaluation/llm-as-judge.md](../evaluation/llm-as-judge.md)
- Wei et al. (2022) — *Chain-of-Thought Prompting Elicits Reasoning in Large Language Models*（CoT 原始论文）
- Kojima et al. (2022) — *Large Language Models are Zero-Shot Reasoners*（zero-shot CoT）
- Wang et al. (2022) — *Self-Consistency Improves Chain of Thought Reasoning*
- Yao et al. (2023) — *Tree of Thoughts*
- Madaan et al. (2023) — *Self-Refine: Iterative Refinement with Self-Feedback*
- OpenAI o1 / DeepSeek R1 技术报告 — 把"长 CoT"训进模型本体的代表
