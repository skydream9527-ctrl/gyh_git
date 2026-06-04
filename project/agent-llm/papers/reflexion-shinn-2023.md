# Reflexion: Language Agents with Verbal Reinforcement Learning

> **出处**：arXiv [2303.11366](https://arxiv.org/abs/2303.11366)（NeurIPS 2023）
> **作者**：Noah Shinn, Federico Cassano, Edward Berman, Ashwin Gopinath, Karthik Narasimhan, Shunyu Yao
> **发布**：2023-03（v1）/ 2023-10（最终版）
> **一句话**：不动模型权重——把"失败教训"用**自然语言反思**写成 episodic memory，下一次试错就能避坑——把强化学习的"价值更新"换成 LLM 的"语言更新"。

---

## 〇、核心论断（一段读懂）

- 传统 RL 方法学失败教训需要**梯度更新**——昂贵、危险、对 LLM 几乎不可行
- Reflexion 把"奖励"和"价值更新"全部**用自然语言代替**：
  - 试一次（trial）→ 拿到一个 reward（pass/fail 或评分）
  - **写一段反思（reflection）**：为什么失败、下次怎么做
  - 把反思加入 **episodic memory**
  - **下一次试错时把反思塞进 prompt**——LLM 看见"上次失败原因 + 下次注意事项"
- 在 HumanEval（代码）、AlfWorld（决策）、HotpotQA（推理）三类任务上**显著提升**——比 ReAct + GPT-4 在 HumanEval 上**从 80% 涨到 91%**。

---

## 一、问题动机

### 1.1 ReAct 解决了"推理-行动统一"，但**学不会**

- ReAct 一次是一次——失败就再试一次，**不会因为上次失败而下次更好**
- 同一个错误能犯一百次

### 1.2 真正的 RL 训练 LLM 不现实

- 大模型权重更新成本极高
- 任务 reward 极稀疏（一个 episode 几十步只在末尾打一个分）
- LLM 又是闭源 API → 没办法直接 fine-tune

### 1.3 关键洞察

> **语言本身就可以承载"价值更新"**——把 RL 里的 numerical value update 换成 verbal feedback。

---

## 二、Reflexion 的三模块架构

```
┌──────────────────┐
│   Actor (LLM)    │ ← 用 ReAct 模板执行任务
└──────────────────┘
        ↓ trajectory
┌──────────────────┐
│  Evaluator       │ ← 给一个奖励信号（自动 / LLM-judge / 单元测试）
└──────────────────┘
        ↓ reward
┌──────────────────┐
│ Self-Reflection  │ ← LLM 写一段"为什么失败 + 下次怎么做"
│      (LLM)       │
└──────────────────┘
        ↓ verbal feedback
┌──────────────────┐
│ Episodic Memory  │ ← 累积反思
└──────────────────┘
        ↓ (下一 trial 把反思塞进 prompt)
        ↑
   Actor 下一次试
```

### 关键模块详解

#### Actor
- 一个标准 ReAct agent
- 接收"任务 + 之前的反思 memory"
- 输出 trajectory（thought / action / observation）

#### Evaluator
- 给 trajectory 一个 reward
- 多种来源：
  - **External**：单元测试（HumanEval）/ task success（AlfWorld）
  - **Internal LLM-judge**：用另一个 LLM 评估
- 不要求 reward 密集——**稀疏 binary reward 就够**

#### Self-Reflection LLM
- **输入**：trajectory + reward
- **输出**：一段自然语言反思——核心格式是
  ```
  Reflection: 上一次我尝试了 X，结果是 Y。
  原因可能是 Z。
  下一次应该尝试 W。
  ```
- 这是**整个方法的关键**：反思质量决定一切

#### Episodic Memory
- 简单的 list，**保留最近若干次反思**
- 反思在每次新 trial 开始时被塞入 prompt

---

## 三、三个实验领域

### 3.1 决策任务：AlfWorld

- 任务：家务环境的多步指令执行
- ReAct baseline：73%；**Reflexion + ReAct: 96%**
- 错误类型分布：reasoning errors / hallucinations / planning failures——**反思后大幅减少**

### 3.2 推理任务：HotpotQA

- 任务：多跳问答
- 在 GPT-3.5 + ReAct baseline 基础上提升约 **20% 绝对值**

### 3.3 代码生成：HumanEval / MBPP

- 任务：基于自然语言描述生成 Python 函数
- Evaluator = **跑单元测试**——典型 deterministic grader
- 结果：
  - **GPT-4 + ReAct: 80%**
  - **GPT-4 + Reflexion: 91%**——**新的 SOTA**
- 反思能识别：测试为什么失败、边界条件没考虑、变量名混淆等

---

## 四、为什么 Reflexion 重要

### 4.1 把 RL 的"试错学习"带到了无梯度世界

- 不动模型，只动 prompt
- "学习" = "把上次教训塞进下次 prompt"——**完全发生在 LLM 的 in-context learning 里**

### 4.2 反思的"语言性"是优势

- 数值 reward 不可解释；语言反思**人和 agent 都能读**
- 反思可以**跨任务迁移**——不像数值价值函数高度任务相关

### 4.3 它是 self-improvement 范式的早期里程碑

- 后来的 self-rewarding LLM、Constitutional AI、Tree of Thoughts 部分思想都能追到这里

---

## 五、和 ReAct 的关系

| 维度 | ReAct | Reflexion |
|---|---|---|
| 单次 trial 内部 | Thought-Action-Observation | 同 ReAct |
| 多 trial 之间 | **完全独立** | **跨 trial 用反思 memory** |
| 学习信号 | 无 | 自然语言反思 |
| 是否需要训练 | 否 | 否 |
| 适合场景 | 一次性任务 | 可以重试的任务（评测、代码、AlfWorld） |

> Reflexion = **ReAct + 跨 episode 的语言式价值更新**。

---

## 六、和本仓库现有结论的对照

| 本文论点 | 本仓库已有 |
|---|---|
| Self-reflection 机制 | [../prompting/cot-family.md](../prompting/cot-family.md) ✓（应加 Reflexion 节） |
| Episodic memory | [../agents/memory-systems.md](../agents/memory-systems.md) ✓ |
| Verbal RL = 用语言代替梯度 | **建议新增** [../agents/verbal-rl-and-self-improvement.md](../agents/verbal-rl-and-self-improvement.md) |
| Evaluator 多源（test / LLM-judge / external） | [../evaluation/research-agent-evals.md](../evaluation/research-agent-evals.md) ✓ |
| HumanEval 91% 创纪录 | [../evaluation/benchmarks.md](../evaluation/benchmarks.md) 可补 |
| Reflexion 是后续 self-improvement 的祖师 | [../agents/openviking-vs-hindsight.md](../agents/openviking-vs-hindsight.md) ✓ 同向 |

---

## 七、反对意见与待验证

- **任务必须是"可重试"的**：客服 / 销售 agent 这种"用户已经走了"的场景不适用
- **反思质量天花板 = 模型自身能力**——弱模型反思也是弱反思，**会越反思越偏**
- **反思 token 成本不可忽视**：每次试错多一次 LLM call
- **反思可能 reward hack**：模型反思出"下次要怎么做"但实际上是绕过 evaluator 的漏洞
- **Memory 长度策略**：留多少反思才对？太多 context 爆，太少没记住——文章给的策略相对粗糙
- **AlfWorld 的 73 → 96%** 在某些 reproductions 中难以复现——baseline 设置敏感

---

## 八、行动项

- [ ] 在 [../prompting/cot-family.md](../prompting/cot-family.md) 加一节 **"Reflexion: Verbal RL"**
- [ ] 在 [../agents/memory-systems.md](../agents/memory-systems.md) 补 **Episodic Memory: Reflexion 的最简实现**
- [ ] 新增 [../agents/verbal-rl-and-self-improvement.md](../agents/verbal-rl-and-self-improvement.md)：覆盖 Reflexion → Self-Refine → Self-Reward → Constitutional AI 的进化谱系
- [ ] 在 [../agents/long-task-agents.md](../agents/long-task-agents.md) 加："**Reflexion 处理'同一任务多次试'，但不解决'单次跨数百步'**"——明确边界

---

## 九、关键引用

- "**Reflexion converts binary or scalar feedback from the environment into verbal feedback in the form of a textual summary, which is then added as additional context for the LLM agent in the next episode.**"
- "**This 'verbal reinforcement' helps the agent learn from prior failings to perform better in the future.**"
- "**Self-reflection is most effective when the model can identify the root cause of failure**——这是为什么 reflection 的质量是天花板。"

> 一句话精神：
> **"Don't update weights. Update the prompt."**
