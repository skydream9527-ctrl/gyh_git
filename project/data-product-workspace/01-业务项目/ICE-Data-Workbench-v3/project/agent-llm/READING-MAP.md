# Agent + LLM — 阅读导航地图

> 把 [agent-llm/](.) 整个目录按 **"先建直觉 → 再学范式 → 然后落工程 → 最后做评测/读论文"** 的顺序梳理成一张图。
>
> - 已有的 [README.md](README.md) 偏「研究范围 + 目录结构」
> - 已有的 [OVERVIEW.md](OVERVIEW.md) 偏「开篇导读 + 心法 + 多条学习路径」
> - 本文是这两者的**索引与阅读顺序**：分 11 个 Part，每 Part 给"解决什么 + 文件清单 + 阅读顺序 + 入门篇推荐"。
>
> 第一次进入这个目录的人，按本文从上到下读即可；老用户当**速查目录**用。

---

## 全景图（一张图先看到底有什么）

```
┌──────────────────────────────────────────────────────────────────────┐
│  Part 0  入口 / 心法           README + OVERVIEW                     │
├──────────────────────────────────────────────────────────────────────┤
│  Part 1  LLM 底层              transformer-gpt-evolution/            │
│                                llm-fundamentals/                     │
├──────────────────────────────────────────────────────────────────────┤
│  Part 2  提示工程              prompting/  +  agents/{cot,tot}       │
├──────────────────────────────────────────────────────────────────────┤
│  Part 3  RAG                   rag/                                  │
├──────────────────────────────────────────────────────────────────────┤
│  Part 4  Agent 核心范式        agents/{react*, loop, memory*}        │
├──────────────────────────────────────────────────────────────────────┤
│  Part 5  工具 / 协议           tools-protocols/  +  mcp-deep-dive/   │
├──────────────────────────────────────────────────────────────────────┤
│  Part 6  多 Agent / 子任务     agents/{multi-agent*, subagent*}      │
├──────────────────────────────────────────────────────────────────────┤
│  Part 7  长任务 Agent / Skills agents/{long-task, skills*, research} │
├──────────────────────────────────────────────────────────────────────┤
│  Part 8  工程化 / 生产         production/                           │
├──────────────────────────────────────────────────────────────────────┤
│  Part 9  评测                  evaluation/  +  agent-evaluation/     │
├──────────────────────────────────────────────────────────────────────┤
│  Part 10 论文 / Talk           papers/                               │
├──────────────────────────────────────────────────────────────────────┤
│  Part 11 面试速通              agents/interview-essentials.md        │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Part 0 · 入口与心法（30 分钟先读）

> 任何人进入这个目录的**第一步**：先建立"为什么 LLM 和 Agent 必须放一起讲""Agent 和 Workflow 的边界"等基本心智。

| 顺序 | 文件 | 读什么 |
|---|---|---|
| 1 | [README.md](README.md) | 8 大研究范围 + 完整目录树（先扫一遍知道"有什么"） |
| 2 | [OVERVIEW.md](OVERVIEW.md) | LLM 是什么 → Agent 是什么 → 四组件抽象 → 五个工程坑 → 四条学习路径 |

**读完应能回答**：
- LLM 和 Agent 的核心差别？
- Agent 的四个核心组件？
- 为什么"能用 Workflow 就别用 Agent"？

---

## Part 1 · LLM 底层（建立"看模型 spec 就能预判性能"的能力）

> 两个目录互补：**时间线视角** vs **主题视角**。Agent 工程师建议先看时间线 1-2 章建直觉，再按需查主题。

### 1A. `transformer-gpt-evolution/` — 时间线视角

> [transformer-gpt-evolution/README.md](transformer-gpt-evolution/README.md)
> 沿"架构演进线 + 模型谱系线"两条线，回答"为什么演进成今天这样"。

| 顺序 | 文件 | 解决什么 |
|---|---|---|
| 1 | [01-transformer-architecture.md](transformer-gpt-evolution/01-transformer-architecture.md) | 2017 原始 Transformer：Self-Attention / Multi-Head / Position Encoding / Encoder-Decoder |
| 2 | [02-architectural-evolution.md](transformer-gpt-evolution/02-architectural-evolution.md) | 9 年间的关键改造（Pre-Norm / RMSNorm / RoPE / SwiGLU / GQA / MoE） |
| 3 | [03-gpt-series-evolution.md](transformer-gpt-evolution/03-gpt-series-evolution.md) | GPT-1 → o3 的 4 个跃迁维度（参数 / 数据 / 对齐 / 推理范式） |
| 4 | [04-frontier-models.md](transformer-gpt-evolution/04-frontier-models.md) | 2026 年第一梯队模型横向对比与选型 |

### 1B. `llm-fundamentals/` — 主题视角

> 不再有 README，按"机制 → 性能 → 训练 → 涌现"四块阅读。

| 顺序 | 文件 | 解决什么 |
|---|---|---|
| 1 | [transformer.md](llm-fundamentals/transformer.md) | 机制直觉：Attention / O(n²) / KV Cache（不抠数学） |
| 2 | [modern-gpt-block.md](llm-fundamentals/modern-gpt-block.md) | Pre-Norm / RMSNorm / RoPE / SwiGLU / GQA 五大改造速查 + 选模型检查表 |
| 3 | [rope-and-positional-encoding.md](llm-fundamentals/rope-and-positional-encoding.md) | RoPE 数学直觉 + 长度外推（PI/NTK/YaRN）+ 5 个工程坑 |
| 4 | [mqa-gqa-and-kv-cache.md](llm-fundamentals/mqa-gqa-and-kv-cache.md) | KV Cache 是性能瓶颈 + 长 context 内存估算公式 |
| 5 | [inference-optimization.md](llm-fundamentals/inference-optimization.md) | 量化 / 投机解码 / Flash Attention / vLLM —— 把单 token 成本砍 5-10× |
| 6 | [training-stages.md](llm-fundamentals/training-stages.md) | Pretrain → SFT → RLHF / DPO 流水线，知道"哪一步给的什么能力" |
| 7 | [scaling-law.md](llm-fundamentals/scaling-law.md) | Scaling Law 与能力涌现：为什么 ChatGPT 是临界点突破 |

**读完应能回答**：原始 Transformer 为什么砍 Encoder？Pre-Norm 为什么取代 Post-Norm？RoPE 比绝对位置编码强在哪？KV Cache 会不会爆显存？MoE 怎么"参数大但激活少"？o1 / R1 引入的"推理时计算"改变了什么？

---

## Part 2 · 提示工程（CoT 家族是"内功"）

> CoT 是 Agent 范式的前置条件——ReAct 之所以成立，是因为 CoT 把"让 LLM 写出推理过程"跑通了。

| 顺序 | 文件 | 解决什么 |
|---|---|---|
| 1 | [prompting/cot-family.md](prompting/cot-family.md) | CoT 家族总览：CoT / Self-Consistency / ToT / Self-Refine / Reflexion / ReAct，**什么时候用哪一个** |
| 2 | [agents/chain-of-thought.md](agents/chain-of-thought.md) | CoT 原理纵深（ReAct 前置）—— 为什么 CoT 有效、prompt 怎么写 |
| 3 | [agents/tree-of-thoughts.md](agents/tree-of-thoughts.md) | ToT 搜索机制：节点/评估/剪枝、四种实现策略、什么时候千万别用 ToT |

> README.md 里规划的 `structured-output.md` / `prompt-caching.md` / `injection-defense.md` 暂未落盘，遇到时跳过。

---

## Part 3 · RAG（检索增强）

> 顺序：先骨架（基础检索），再花活（Self-RAG / CRAG / GraphRAG），最后落地（LangGraph 实现）。

| 顺序 | 文件 | 解决什么 |
|---|---|---|
| 1 | [rag/retrieval-basics.md](rag/retrieval-basics.md) | 分块、向量化、混合检索、rerank、评测——RAG 的"骨架" |
| 2 | [rag/advanced-rag.md](rag/advanced-rag.md) | Self-RAG / CRAG / GraphRAG / Adaptive RAG 的机制和取舍 |
| 3 | [rag/agentic-rag-implementation.md](rag/agentic-rag-implementation.md) | CRAG / Self-RAG 用 LangGraph 写出可跑代码 + 叠加用法 |

---

## Part 4 · Agent 核心范式（从 ReAct 开始）

> 业界 Agent 万变不离 ReAct + 反思 + 记忆这三件事。先看"范式总览"，再看"机制纵深"，再看"循环架构对比"。

### 4A. ReAct 与变体

| 顺序 | 文件 | 解决什么 |
|---|---|---|
| 1 | [agents/react-and-variants.md](agents/react-and-variants.md) | ReAct / Plan-and-Execute / Reflexion / ToT 范式总览 |
| 2 | [agents/react-mechanism-and-strategy.md](agents/react-mechanism-and-strategy.md) | ReAct 机制底层 + 生产级应用策略（含 ice-workbench 接法） |
| 3 | [agents/agent-loop-architectures.md](agents/agent-loop-architectures.md) | 三种循环对比：感知-行动 vs 状态机 vs ReAct |

### 4B. 记忆系统

| 顺序 | 文件 | 解决什么 |
|---|---|---|
| 1 | [agents/memory-systems.md](agents/memory-systems.md) | 记忆分类（短期/长期、Episodic/Semantic/Procedural）+ 工程实现 |
| 2 | [agents/openviking-vs-hindsight.md](agents/openviking-vs-hindsight.md) | 两种主流长期记忆方案对比 + 在 ice-workbench 中的接入 |

---

## Part 5 · 工具与协议（让 LLM 接到现实世界）

> 三层递进：**Function Calling（怎么调）→ Tool 开发（怎么写一个生产可用的工具）→ MCP（怎么跨应用复用）**。

### 5A. tools-protocols/ — 工具协议入门

| 顺序 | 文件 | 解决什么 |
|---|---|---|
| 1 | [tools-protocols/function-calling.md](tools-protocols/function-calling.md) | Function Calling 核心机制 + 各家差异 + 生产级最佳实践 |
| 2 | [tools-protocols/tool-development.md](tools-protocols/tool-development.md) | API 工程师视角：schema 设计 / 参数校验 / 错误处理 |
| 3 | [tools-protocols/mcp.md](tools-protocols/mcp.md) | MCP 入门速查（架构图 + 最小 server 示例） |
| 4 | [tools-protocols/browser-automation.md](tools-protocols/browser-automation.md) | Playwright vs Computer Use vs Browser-Use 分层方案 |

### 5B. mcp-deep-dive/ — MCP 深度专题

> [mcp-deep-dive/README.md](mcp-deep-dive/README.md)
> "Function Calling = 单家厂商内的通话语法；MCP = 跨应用的 USB-C"。

| 顺序 | 文件 | 解决什么 |
|---|---|---|
| 1 | [01-mcp-principles.md](mcp-deep-dive/01-mcp-principles.md) | 协议原理：JSON-RPC / lifecycle / capabilities / transport |
| 2 | [02-using-mcp.md](mcp-deep-dive/02-using-mcp.md) | 客户端/开发者侧挂载 + 常用 server 速查 + 配置陷阱 |
| 3 | [03-developing-mcp-servers.md](mcp-deep-dive/03-developing-mcp-servers.md) | Python/TS SDK 写 server、tool/resource/prompt 设计、鉴权、调试 |
| 4 | [04-industry-landscape.md](mcp-deep-dive/04-industry-landscape.md) | 业界生态、企业方案、安全治理、与 OpenAI Plugins 的边界 |

---

## Part 6 · 多 Agent 与子任务（先看"协作"再看"协调"再看"派子任务"）

| 顺序 | 文件 | 解决什么 |
|---|---|---|
| 1 | [agents/multi-agent-frameworks.md](agents/multi-agent-frameworks.md) | AutoGen / CrewAI / Agents SDK 心智模型 + 5 大反模式 + 单→多 Agent 演进路径 |
| 2 | [agents/multi-agent-coordination.md](agents/multi-agent-coordination.md) | 5 种协商机制 + Anthropic 多 Agent 系统参考 |
| 3 | [agents/subagent-patterns.md](agents/subagent-patterns.md) | Claude Code Task vs CrewAI Crew vs LangGraph Subgraph 本质对比 + State Schema 7 大陷阱 |

---

## Part 7 · 长任务 Agent + Skills（前沿落地）

> 从"理解长任务为什么难" → "Skills 机制" → "搭一个端到端研究 Agent" 三步走。

| 顺序 | 文件 | 解决什么 |
|---|---|---|
| 1 | [agents/long-task-agents.md](agents/long-task-agents.md) | Claude Code / OpenHands / Manus / Devin 设计哲学 + 6 核心策略 + 与 Cursor/Cline/Aider 区别 |
| 2 | [agents/skills-system-design.md](agents/skills-system-design.md) | Skills 最简版 + 动态召回 + LangGraph 接入 + Cline MCP 自定义工具 |
| 3 | [agents/skills-vs-tools.md](agents/skills-vs-tools.md) | Skill 和 Tool 的本质区别（七维度对比 + 协同设计） |
| 4 | [agents/research-agent-architecture.md](agents/research-agent-architecture.md) | 端到端研究 Agent（Claude Code + Manus skill + 自定义 subagent）+ 产品级方案对比 |

---

## Part 8 · 工程化与生产（先认识框架地图，再看 LangGraph 实战）

| 顺序 | 文件 | 解决什么 |
|---|---|---|
| 1 | [production/frameworks-landscape.md](production/frameworks-landscape.md) | 2026 主流框架四类全景：通用编排 / 多 Agent / 垂直 Agent / 协议设施 |
| 2 | [production/frameworks-comparison.md](production/frameworks-comparison.md) | LangChain / LangGraph / LlamaIndex / DSPy / AutoGen / CrewAI 横向对比 + 选型建议 |
| 3 | [production/langgraph-checkpoint-and-hitl.md](production/langgraph-checkpoint-and-hitl.md) | Postgres 表结构 + interrupt() HITL 模式 + 4 个工程坑 |
| 4 | [production/langgraph-research-agent-impl.md](production/langgraph-research-agent-impl.md) | LangGraph 完整可运行代码：骨架 → 状态 → 节点 → subgraph → 主图 → 协商层 → 启动 |
| 5 | [production/latency-optimization.md](production/latency-optimization.md) | 7 个延迟优化杠杆 + 50-70% 降幅组合方案 |
| 6 | [production/observability.md](production/observability.md) | LLM 应用区别于传统系统的观测维度 + 主流工具 + 最小落地路径 |

> README.md 里规划的 `cost-and-latency.md` 暂未落盘。

---

## Part 9 · 评测（两个目录互补）

> **`evaluation/`** 偏专题（LLM-as-Judge、研究 Agent 评测）；**`agent-evaluation/`** 偏方法论体系（4 章完整讲透）。

### 9A. evaluation/ — 评测专题

| 顺序 | 文件 | 解决什么 |
|---|---|---|
| 1 | [evaluation/llm-as-judge.md](evaluation/llm-as-judge.md) | LLM-as-Judge 正确做法 + 常见偏置 + 让它真正可靠 |
| 2 | [evaluation/research-agent-evals.md](evaluation/research-agent-evals.md) | 3 层评测 + 8 种 Judge 偏见 + 6 层防御 + 长期工作流 |

### 9B. agent-evaluation/ — Agent 评测方法论

> [agent-evaluation/README.md](agent-evaluation/README.md)
> 评测分层：端到端 → 阶段 → 组件 → 在线监控。

| 顺序 | 文件 | 解决什么 |
|---|---|---|
| 1 | [01-evaluation-fundamentals.md](agent-evaluation/01-evaluation-fundamentals.md) | 评什么 + Agent 评测与 LLM 评测的本质区别 |
| 2 | [02-evaluation-methods.md](agent-evaluation/02-evaluation-methods.md) | 5 种方法对比：Rule-based / Reference-based / LLM-as-Judge / Human / Online metrics |
| 3 | [03-mainstream-benchmarks.md](agent-evaluation/03-mainstream-benchmarks.md) | 6 类主流 benchmark 全景：通用 / 代码 / 数学 / Agent / 工具调用 / 长上下文 + 多模态 |
| 4 | [04-business-eval-pipeline.md](agent-evaluation/04-business-eval-pipeline.md) | 业务侧落地：黄金集 → CI 集成 → 在线监控 → A/B → 异常回流 |

---

## Part 10 · 论文与 Talk（带反对意见的阅读）

> [papers/README.md](papers/README.md)
> 阅读约定：每篇按"背景 → 核心观点 → 关键论据 → 与本仓库的连接 → 反对意见 → 行动项"展开。

### 10A. 入门顺序（按时间和概念递进）

| 顺序 | 文件 | 一句话 |
|---|---|---|
| 1 | [lilian-weng-llm-agents.md](papers/lilian-weng-llm-agents.md) | Planning / Memory / Tool Use 三组件分类法（2023-06）—— 业界事实词汇 |
| 2 | [react-yao-2022.md](papers/react-yao-2022.md) | ReAct: Thought-Action-Observation 模板 —— 当代 agent loop 的事实标准 |
| 3 | [reflexion-shinn-2023.md](papers/reflexion-shinn-2023.md) | Verbal RL：用自然语言反思代替梯度更新 |
| 4 | [building-effective-agents.md](papers/building-effective-agents.md) | Anthropic 反框架宣言（2024-12）—— 5 种 workflow + 1 agent + ACI |
| 5 | [multi-agent-research-system.md](papers/multi-agent-research-system.md) | Anthropic Multi-Agent Research（2025-06）—— 比单 agent 好 90.2% 但 token 15× |
| 6 | [demystifying-evals-for-ai-agents.md](papers/demystifying-evals-for-ai-agents.md) | Anthropic Agent 评测体系（2026-01）—— 8 步评测路线图 |
| 7 | [harness-engineering-codex.md](papers/harness-engineering-codex.md) | OpenAI Codex Harness Engineering（2026-02）—— 工程师的工作变成"为 agent 设计环境" |

### 10B. 问题导向

- 想搭 agent → ReAct → Building Effective Agents → Reflexion
- 想做评测 → Demystifying Evals → Building Effective Agents（评估部分）
- 想做生产化 → Harness Engineering → Multi-Agent Research System
- 想要分类法 → Lilian Weng → Building Effective Agents

---

## Part 11 · 面试速通

| 文件 | 解决什么 |
|---|---|
| [agents/interview-essentials.md](agents/interview-essentials.md) | 三道高频题（手写 ReAct / MCP 辨析 / 记忆系统设计）的"追问深挖"层级 |

---

## 三种典型场景的快速通道

> 不读完所有内容，只想最快解决眼前问题——按场景选一条线。

### 场景 A：第一次接触 Agent，要给团队做技术分享（≈ 4 小时）
1. [OVERVIEW.md](OVERVIEW.md)
2. [agents/react-and-variants.md](agents/react-and-variants.md)
3. [tools-protocols/function-calling.md](tools-protocols/function-calling.md) + [tools-protocols/mcp.md](tools-protocols/mcp.md)
4. [agents/memory-systems.md](agents/memory-systems.md)
5. [papers/building-effective-agents.md](papers/building-effective-agents.md)

### 场景 B：要搭一个能跑的研究 / 长任务 Agent（≈ 1 天）
1. [agents/long-task-agents.md](agents/long-task-agents.md)
2. [agents/skills-system-design.md](agents/skills-system-design.md)
3. [agents/multi-agent-coordination.md](agents/multi-agent-coordination.md)
4. [agents/research-agent-architecture.md](agents/research-agent-architecture.md)
5. [production/langgraph-research-agent-impl.md](production/langgraph-research-agent-impl.md)
6. [evaluation/research-agent-evals.md](evaluation/research-agent-evals.md)

### 场景 C：选模型 / 调延迟 / 估成本（≈ 半天）
1. [llm-fundamentals/transformer.md](llm-fundamentals/transformer.md)
2. [llm-fundamentals/modern-gpt-block.md](llm-fundamentals/modern-gpt-block.md)
3. [llm-fundamentals/mqa-gqa-and-kv-cache.md](llm-fundamentals/mqa-gqa-and-kv-cache.md)
4. [llm-fundamentals/inference-optimization.md](llm-fundamentals/inference-optimization.md)
5. [transformer-gpt-evolution/04-frontier-models.md](transformer-gpt-evolution/04-frontier-models.md)
6. [production/latency-optimization.md](production/latency-optimization.md)

---

## 与 OVERVIEW.md "四条学习路径" 的对照

> 本文按**目录结构 + 阅读顺序**组织；OVERVIEW.md 第六章按**学习者背景**组织（理论派 / 工程派 / 长任务实战派 / 底层架构派）。两者互补：先用本文找到"目录里有什么"，再用 OVERVIEW.md 选"以什么顺序读最适合你"。

| 学习路径（OVERVIEW.md §六） | 主要落到本文哪几个 Part |
|---|---|
| A. 理论派（数据/算法/研究） | Part 1 → Part 4 → Part 3 → Part 9 → Part 8 |
| B. 工程派（产品/应用开发） | Part 2 → Part 5 → Part 3 → Part 4 → Part 9 → Part 1（回头补） |
| C. 长任务 Agent 实战派 | Part 7 → Part 6 → Part 5 → Part 8 → Part 9 |
| D. LLM 底层架构（性能边界） | Part 1（全部）→ Part 8 §latency-optimization |

---

## 维护说明

- 新增文件后请在对应 Part 的表格里补一行（保持"顺序 / 文件 / 解决什么"三列）。
- 子目录有自己的 README.md 时，**先读子 README** 再读章节文件。
- 如发现某条目仍在 [README.md](README.md) 的"目录结构（建议）"里但 disk 上不存在，标注为"暂未落盘"即可，不要伪造链接。