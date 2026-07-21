# Agent 评测：方法论与主流方案

> 评测是 Agent 工程中**最容易被低估、又最决定迭代速度**的一环。Prompt 调一调跑两个 demo 看着不错就上线，迟早翻车——只有把评测做成**可重复、可对比、可量化**的流水线，才能从"玄学调参"变"工程化优化"。
>
> 本目录系统讲清楚：**评测什么 → 怎么评 → 用什么 benchmark → 怎么落到自己业务**。

---

## 阅读顺序

| 顺序 | 文件 | 解决什么问题 |
|---|---|---|
| 1 | [01-evaluation-fundamentals.md](01-evaluation-fundamentals.md) | 评什么、为什么必须建评测集、Agent 评测与 LLM 评测的本质区别 |
| 2 | [02-evaluation-methods.md](02-evaluation-methods.md) | 5 种主流评测方法：rule-based / reference-based / LLM-as-judge / human / online | 
| 3 | [03-mainstream-benchmarks.md](03-mainstream-benchmarks.md) | 公开 benchmark 全景：通用 LLM / 代码 / 数学 / Agent / 长上下文 / 多模态 |
| 4 | [04-business-eval-pipeline.md](04-business-eval-pipeline.md) | 业务侧实操：黄金集构造、CI 集成、在线监控、A/B 设计 |

---

## 关键问题清单（读完应能回答）

- "Agent 评测" 和 "LLM 评测"差在哪？为什么不能只看 MMLU？
- LLM-as-Judge 有哪些**已知偏见**？怎么防御？
- AgentBench / GAIA / SWE-Bench / WebArena / τ-bench 各自评什么、分数怎么读？
- Tool-use 的评测维度有哪些？只看"答对没"够不够？
- 业务侧黄金集多大才够？怎么造、怎么维护？
- 离线评测 + 在线 A/B 怎么衔接？
- 怎么避开"过拟合 benchmark" / "数据污染"？

---

## 与本仓库其它资料的关系

| 资料 | 关系 |
|---|---|
| [./llm-as-judge.md](./llm-as-judge.md) | LLM-as-Judge 基础（原 `evaluation/` 已并入本目录）。本目录 02 章会引用。 |
| [./research-agent-evals.md](./research-agent-evals.md) | 研究 Agent 三层评测（Anthropic 风格）。本目录 01 章会复用三层结构。 |
| [../papers/demystifying-evals-for-ai-agents.md](../papers/demystifying-evals-for-ai-agents.md) | Anthropic 官方方法论。本目录的"方法论灵感"很多来自这里。 |
| [../../ab-testing/](../../ab-testing/) | 业务侧在线 A/B 框架。04 章会衔接。 |

---

## 评测分层框架（贯穿本目录）

```
┌────────────────────────────────────────────────────────────┐
│                                                            │
│  Layer 1  端到端评测      最终输出/任务成功率（业务指标）    │
│             ▲                                              │
│             │                                              │
│  Layer 2  阶段评测        每个 step 的产出（plan/工具调用） │
│             ▲                                              │
│             │                                              │
│  Layer 3  组件评测        单 prompt / 单工具能力             │
│             ▲                                              │
│             │                                              │
│  Layer 4  在线监控        生产流量上的成功率/延迟/反馈       │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

每一层目的不同，工具不同，**缺一不可**。

---

## 关键参考

- Anthropic — *Demystifying Evals for AI Agents*（2026.01）
- OpenAI Evals 框架（github.com/openai/evals）
- Berkeley Function Calling Leaderboard（BFCL）
- AgentBench（清华 KEG, 2023）
- GAIA（Mialon et al., 2023）
- SWE-Bench / SWE-Bench Verified（Princeton, 2024）
- WebArena（CMU, 2023）/ VisualWebArena（2024）
- τ-bench（Sierra, 2024）— Tool-Agent-User benchmark
- RAGAS / TruLens（RAG 评测）
- *AI Engineering* by Chip Huyen — 第 4 章评测方法
