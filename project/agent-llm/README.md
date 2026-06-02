# Agent + LLM — 开发与应用（含 LLM 原理与技巧）

> 系统梳理 LLM 底层原理、提示工程、Agent 架构、工具使用、记忆与规划、评测，以及面向真实业务的工程化实践。

## 研究范围

### 1. LLM 原理（自下而上）
- **Transformer 架构**：Attention、位置编码、KV Cache、MoE
- **训练范式**：Pretrain → SFT → RLHF / DPO / GRPO → RLAIF
- **推理优化**：量化、投机解码、Flash Attention、PagedAttention（vLLM）
- **能力涌现**：Scaling Law、Chinchilla、In-Context Learning
- **长上下文**：RoPE 外推、YaRN、滑窗、Ring Attention
- **多模态**：视觉编码器、Audio、统一架构（GPT-4o / Gemini / Claude 3.5 Vision）

### 2. 提示工程（Prompt Engineering）
- 提示结构：System / Role / Few-shot / CoT / Self-Consistency
- 思维链家族：CoT、ToT（Tree of Thoughts）、GoT、Self-Refine、Reflexion
- 结构化输出：JSON Mode、Function Calling、Constrained Decoding
- Prompt Caching（Anthropic / OpenAI）：长 system prompt 重用
- 防御：Prompt Injection、Jailbreak、System Prompt 泄露

### 3. RAG（检索增强生成）
- 检索基础：BM25、Dense Retrieval、Hybrid Search、Reranker
- 分块策略：固定 / 语义 / 层级 / Late Chunking
- Embedding 模型选型：BGE、E5、OpenAI、Voyage
- 进阶：HyDE、Multi-Query、RAG-Fusion、Self-RAG、CRAG、GraphRAG
- 评测：RAGAS、TruLens、Recall@K、Answer Relevance

### 4. Agent 架构
- **基础范式**：ReAct、Plan-and-Execute、Reflexion、AutoGPT
- **多 Agent**：AutoGen、CrewAI、Swarm（OpenAI）、A2A、MetaGPT
- **核心组件**：
  - 规划：任务分解、子目标、Plan-Tree
  - 工具使用：Function Calling、MCP、Code Interpreter
  - 记忆：短期 / 长期、向量记忆、Episodic、Semantic
  - 反思：Self-Critique、Verifier、Reflection
- **设计模式**（Agentic Design Patterns）：
  - Reflection / Tool Use / Planning / Multi-Agent Collaboration
  - 见 [references/agentic-design-patterns.md](../../references/agentic-design-patterns.md)

### 5. 工具协议与生态
- **Function Calling**（OpenAI / Anthropic / Google）
- **MCP（Model Context Protocol）**：标准化工具接入
- **Computer Use / Browser Use**：屏幕级操作
- 沙箱执行：E2B、Code Interpreter、Daytona

### 6. 评测（Eval）
- 离线评测：MMLU、HumanEval、MT-Bench、Chatbot Arena
- LLM-as-Judge：评分一致性、偏置、Pairwise vs Single
- Agent 评测：AgentBench、GAIA、SWE-Bench、WebArena
- 业务评测：黄金集 + 在线 AB（与 [../ab-testing/](../ab-testing/) 联动）

### 7. 工程化与生产
- 框架：LangChain、LlamaIndex、LangGraph、DSPy
- 可观测性：LangSmith、Langfuse、Helicone、Phoenix
- 网关与编排：LiteLLM、Portkey、OpenRouter
- 成本与延迟：Token 成本表、Streaming、批量推理（Batch API）
- 安全：内容审核、Guardrails、PII 脱敏

### 8. 业务场景
- 客服 Agent / 销售 Agent / 数据分析 Agent
- 编码 Agent（Cursor / Copilot / Cline / Claude Code）
- 浏览器 Agent / RPA Agent
- 行业 Agent：金融研报、医疗、法律、教育

## 目录结构（建议）

```
agent-llm/
├── README.md                     ← 本文件
├── llm-fundamentals/             ← LLM 原理
│   ├── transformer.md
│   ├── training-stages.md
│   ├── inference-optimization.md
│   └── scaling-law.md
├── prompting/                    ← 提示工程
│   ├── cot-family.md
│   ├── structured-output.md
│   ├── prompt-caching.md
│   └── injection-defense.md
├── rag/                          ← 检索增强
│   ├── retrieval-basics.md
│   ├── chunking-strategies.md
│   ├── advanced-rag.md
│   ├── agentic-rag-implementation.md  ← CRAG/Self-RAG 落地（LangGraph）
│   └── evaluation.md
├── agents/                       ← Agent 架构
│   ├── react-and-variants.md
│   ├── react-mechanism-and-strategy.md
│   ├── tree-of-thoughts.md
│   ├── agent-loop-architectures.md     ← 感知-行动 vs 状态机 vs ReAct 三种循环
│   ├── multi-agent-frameworks.md       ← AutoGen / CrewAI / Agents SDK 深度
│   ├── multi-agent-coordination.md     ← 5 种协商机制 + Anthropic 多 Agent 参考
│   ├── subagent-patterns.md            ← Task vs Crew vs Subgraph 本质对比
│   ├── long-task-agents.md             ← Claude Code/OpenHands/Manus/Devin + Cursor/Cline/Aider
│   ├── skills-system-design.md         ← Skills + 动态召回 + LangGraph + Cline MCP
│   ├── skills-vs-tools.md              ← Skill 和 Tool 的本质区别
│   ├── research-agent-architecture.md  ← 长任务研究 Agent 架构 + 产品级方案对比
│   ├── memory-systems.md
│   ├── openviking-vs-hindsight.md
│   └── design-patterns.md
├── tools-protocols/              ← 工具协议
│   ├── function-calling.md
│   ├── tool-development.md       ← API 工程师视角：schema 设计 / 参数校验 / 错误处理
│   ├── mcp.md
│   ├── browser-automation.md     ← Playwright vs Computer Use vs Browser-Use
│   └── computer-use.md
├── evaluation/                   ← 评测
│   ├── benchmarks.md
│   ├── llm-as-judge.md
│   ├── research-agent-evals.md   ← 3 层评测 + LLM-as-Judge 偏见防御
│   └── agent-eval.md
├── production/                   ← 工程化
│   ├── frameworks-landscape.md         ← 主流框架四类全景（2026）
│   ├── frameworks-comparison.md        ← LangChain/LangGraph/LlamaIndex 横向对比
│   ├── langgraph-checkpoint-and-hitl.md ← Postgres 表结构 + HITL 落地
│   ├── langgraph-research-agent-impl.md ← LangGraph 完整复刻研究 Agent（可运行代码）
│   ├── latency-optimization.md         ← 7 个延迟优化杠杆 + 50% 降幅组合
│   ├── observability.md
│   └── cost-and-latency.md
├── case-studies/                 ← 业界案例
│   ├── coding-agents.md
│   ├── browser-agents.md
│   └── ...
└── papers/                       ← 论文摘要
```

## 关键参考

- Lilian Weng — LLM Powered Autonomous Agents（OpenAI Blog）
- Andrew Ng — Agentic Design Patterns（DeepLearning.AI 系列）
- Anthropic — Building Effective Agents（2024）
- 本仓库已有：
  - [references/agentic-design-patterns.md](../../references/agentic-design-patterns.md)
  - [references/rag-agent-scenario-analysis.md](../../references/rag-agent-scenario-analysis.md)
  - [knowledge-base/AI-Agent/](../../knowledge-base/AI-Agent/)
  - [knowledge-base/RAG/](../../knowledge-base/RAG/)

## 与本工作区的关联

- 复用 [knowledge-base/AI-Agent/](../../knowledge-base/AI-Agent/)、[knowledge-base/RAG/](../../knowledge-base/RAG/)、[knowledge-base/AI-SKILL/](../../knowledge-base/AI-SKILL/) 已有沉淀
- Agent 评测离线/在线流程与 [../ab-testing/](../ab-testing/) 联动
- 增量评估、归因、个性化策略与 [../causal-inference/](../causal-inference/) 联动
- 实战代码可参考 [project/ice-workbench/](../ice-workbench/) 中的 agents 目录
