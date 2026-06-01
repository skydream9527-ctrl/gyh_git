# Agent + LLM — 开篇导读

> 这是 [agent-llm/](.) 目录的总入口。读完这一篇，你应该能回答：LLM 到底是什么、Agent 在 LLM 之上加了什么、为什么"原理"对 PM/工程师都重要、应该按什么顺序学。

---

## 一、为什么 LLM 和 Agent 要放在一起讲

很多人把 LLM 和 Agent 当成两件事——LLM 是"模型"，Agent 是"应用"。这种划分会让你**看不见两边的关键约束**：

- 不懂 LLM 的人做 Agent → 不知道为什么"链路一长就崩"，也不知道"prompt 缓存"为什么能让成本砍 90%
- 不做 Agent 的人看 LLM → 容易以为只要模型够大问题就解决，忽视真实业务里 80% 的问题在编排层

更准确的说法是：

```
LLM     ←─  原料（语言能力 + 知识 + 推理 + 工具调用接口）
Agent   ←─  把原料组装成一台"会做事"的机器
         ─  规划、调用工具、记忆、反思、错误恢复
```

LLM 是发动机，Agent 是车。学 Agent 不懂 LLM 像不懂发动机调底盘；学 LLM 不做 Agent 像研究发动机却不开车。

---

## 二、LLM 是什么（一句话 + 一段话）

**一句话**：LLM 是一个学会"在巨量文本中预测下一个词"的神经网络，它的所有"能力"都源自这一个看似无聊的目标。

**一段话**：通过在数万亿 token 上预测下一个词，LLM 内部隐式学到了语法、世界知识、推理模式、人类偏好。这些能力**不是显式编程进去的**，而是**涌现出来的（emergent）**——这就是为什么 LLM 让人觉得"像人在说话"，又让人觉得"经常胡说八道"：它本质上不在"理解"，而在"高保真模仿语言分布"。

四个最该懂的 LLM 概念（按重要性）：

| 概念 | 一句话理解 | 为什么重要 |
|---|---|---|
| **Token** | 模型看的不是字符也不是词，是中间粒度的 token | 决定了上下文长度、成本、速度 |
| **上下文窗口** | 模型一次能看的 token 总量 | 决定了"能塞多少东西" |
| **In-Context Learning** | 不更新权重，只靠 prompt 里的例子学新任务 | Agent 的能力来源 |
| **采样温度** | 控制输出确定性的旋钮（0=贪婪，>1=发散） | 决定了"创意 vs 稳定"的取舍 |

详见 `llm-fundamentals/`，先读 [transformer.md](llm-fundamentals/transformer.md)。

---

## 三、Agent 是什么（不是"加了 prompt 的 LLM"）

如果让我用一张图区分 Chatbot、Workflow、Agent：

```
Chatbot:        User → LLM → Reply              (单轮，回答型)
Workflow:       User → [LLM step₁ → tool → LLM step₂ → ...] → Reply
                                                  (流程预先固定)
Agent:          User → ┌─────────────────────────┐
                       │  LLM 决定下一步做什么     │
                       │  ↓                       │
                       │  调工具 / 回答 / 反思     │← 循环 ──┐
                       │  ↓                       │         │
                       │  收到结果 → LLM 再决策   │─────────┘
                       └─────────────────────────┘
                       (流程由 LLM 动态决定)
```

**Agent 的核心特征是"自决策"**：下一步做什么不是流程固定的，而是由 LLM 根据当前状态决定的。

这一点带来了能力，也带来了所有麻烦：

- ✅ 能力：能处理开放式任务、未预见场景
- ❌ 麻烦：链路长 → 错误累积、成本飙升、调试困难、行为不稳定

> Anthropic 在 *Building Effective Agents* 里给出了一个朴素但重要的建议：**能用 Workflow 就别用 Agent**。Agent 是给真正需要"动态决策"的场景的，不是给"想用最新技术"的人的。

---

## 四、Agent 的四个核心组件

任何 Agent 落地都绕不开这四个组件——这也是把整个领域简化成可学习模块的最好抽象：

```
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│   Planning      ←─  把任务拆成可执行的步骤                      │
│   规划          ←─  ReAct, Plan-and-Execute, ToT, Reflexion    │
│                                                                │
│   Tool Use      ←─  把"语言"变成"动作"                          │
│   工具          ←─  Function Calling, MCP, Code Interpreter    │
│                                                                │
│   Memory        ←─  跨步骤、跨会话保持状态                      │
│   记忆          ←─  Short-term (context), Long-term (vector)   │
│                                                                │
│   Reflection    ←─  自检 + 自纠错                               │
│   反思          ←─  Self-Critique, Verifier, Reflexion         │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

业界论文和框架万变不离这四个。新出的"花哨 Agent 名词"基本都能映射回这四件事的某种组合或加强。

详见：
- 规划 → [agents/react-and-variants.md](agents/react-and-variants.md)（范式总览）、[agents/react-mechanism-and-strategy.md](agents/react-mechanism-and-strategy.md)（ReAct 机制纵深）、[agents/tree-of-thoughts.md](agents/tree-of-thoughts.md)（ToT 原理与应用）
- 工具 → [tools-protocols/function-calling.md](tools-protocols/function-calling.md)、[tools-protocols/mcp.md](tools-protocols/mcp.md)
- 记忆 → [agents/memory-systems.md](agents/memory-systems.md)、[agents/openviking-vs-hindsight.md](agents/openviking-vs-hindsight.md)（两种主流长期记忆方案对比 + 在 ice-workbench 中的接入）
- 多 Agent 协作 → [agents/multi-agent-frameworks.md](agents/multi-agent-frameworks.md)（AutoGen / CrewAI / Agents SDK 深度对比 + 五大反模式 + 单→多 Agent 演进路径）
- 多 Agent 协商机制 → [agents/multi-agent-coordination.md](agents/multi-agent-coordination.md)（5 种协商模式 + Anthropic 多 Agent 系统参考）
- 派子任务的三种机制 → [agents/subagent-patterns.md](agents/subagent-patterns.md)（Claude Code Task vs CrewAI Crew vs LangGraph Subgraph 本质区别 + 自定义 subagent 写法 + State Schema 7 大陷阱）
- 长任务 Agent → [agents/long-task-agents.md](agents/long-task-agents.md)（Claude Code / OpenHands / Manus / Devin 设计哲学 + 6 个核心策略 + Cursor/Cline/Aider 对比）
- Skills 系统设计 → [agents/skills-system-design.md](agents/skills-system-design.md)（最简版 + 动态召回 + LangGraph 接入 + Cline MCP 自定义工具）
- 长任务研究 Agent → [agents/research-agent-architecture.md](agents/research-agent-architecture.md)（端到端架构 + Deep Research 产品对比）
- LangGraph 研究 Agent 实现 → [production/langgraph-research-agent-impl.md](production/langgraph-research-agent-impl.md)（完整可运行代码 + 黑板协商）
- Agentic RAG 落地 → [rag/agentic-rag-implementation.md](rag/agentic-rag-implementation.md)（CRAG / Self-RAG 用 LangGraph 写出可跑的代码 + 叠加用法）
- 状态持久化与 HITL → [production/langgraph-checkpoint-and-hitl.md](production/langgraph-checkpoint-and-hitl.md)（Postgres 表结构 + interrupt() 模式 + 4 个工程坑）
- 框架全景定位 → [production/frameworks-landscape.md](production/frameworks-landscape.md)（2026 视角的四类框架分类）
- 浏览器自动化 → [tools-protocols/browser-automation.md](tools-protocols/browser-automation.md)（Playwright vs Computer Use vs Browser-Use 分层方案）
- 研究 Agent 评测 → [evaluation/research-agent-evals.md](evaluation/research-agent-evals.md)（3 层评测 + LLM-as-Judge 8 种偏见 + 6 层防御）

---

## 五、为什么"LLM 原理"对 PM 也重要

很多 PM 觉得 LLM 是黑盒，但你做产品决策时**没有原理感**会反复踩同样的坑：

| 你以为 | 真相 | 影响 |
|---|---|---|
| "上下文给得越多越好" | 上下文越长成本和延迟越高，且模型会"中段失忆"（lost in the middle） | 长 prompt 不一定有效，要切片+检索 |
| "把指令重复多遍模型就能听懂" | 模型对指令的位置和措辞极敏感，更可能产生反效果 | 用结构化 prompt + 例子，不是堆叠口令 |
| "Temperature=0 就完全可复现" | 不一定，多数 API 的浮点累加有非确定性；Mixture of Experts 路由也有抖动 | 别把 LLM 当确定性函数 |
| "GPT-4 比 GPT-3.5 在所有任务上都强" | 不是。简单分类、关键词抽取、特定结构化任务，小模型经常更稳更快更便宜 | 模型选型要按任务做评测，不是按版本号 |
| "RAG 加了就能解决幻觉" | RAG 只解决"知识缺失"。结构混乱、prompt 模糊带来的幻觉它治不了 | RAG 是必要不充分 |
| "Function Calling 就是工具调用，可靠了" | 调对工具是 60-90% 可靠，但参数填错很常见 | 关键工具要做 schema 校验和重试 |

更进一步：**Token 经济学**直接决定产品形态。一个客服 Agent 一天 1 万次会话 × 5 万 token，月成本几十万。哪些能用 prompt cache（Anthropic / OpenAI）、哪些要换小模型、哪些要 fine-tune、哪些干脆不用 LLM——是 PM 必须懂的杠杆。

---

## 六、两条学习路径

不同背景的人切入点不同。选你最像的：

### 路径 A：理论派（数据/算法/研究背景）

```
1. Transformer 原理     →  llm-fundamentals/transformer.md
2. 训练流程             →  [llm-fundamentals/training-stages.md](llm-fundamentals/training-stages.md)
3. Scaling Law / 涌现   →  [llm-fundamentals/scaling-law.md](llm-fundamentals/scaling-law.md)
4. ReAct + 反思         →  agents/react-and-variants.md
5. RAG 与评测           →  rag/, evaluation/
6. 工程框架对比         →  [production/frameworks-comparison.md](production/frameworks-comparison.md)
```

适合：想搞清楚"为什么是这样"的人。

### 路径 B：工程派（产品 / 应用开发背景）

```
1. Prompt 模式          →  [prompting/cot-family.md](prompting/cot-family.md)
2. Function Calling     →  [tools-protocols/function-calling.md](tools-protocols/function-calling.md)
3. RAG 实战             →  [rag/retrieval-basics.md](rag/retrieval-basics.md)
4. ReAct + 设计模式     →  agents/react-and-variants.md
5. 评测与可观测性       →  [evaluation/llm-as-judge.md](evaluation/llm-as-judge.md)、[production/observability.md](production/observability.md)
6. 回头补 Transformer   →  llm-fundamentals/transformer.md
```

适合：想"先做出能用的东西"再回头看原理的人。本工作区大部分日常需求走这条。

### 路径 C：长任务 Agent 实战派（要做产品级研究 Agent / Coding Agent）

```
1. 长任务的本质      →  [agents/long-task-agents.md](agents/long-task-agents.md)（理解 Claude Code/OpenHands/Manus/Devin 的设计差异）
2. 上下文管理三大策略 →  分布式（Task）、文件式（Manus）、摘要式（OpenHands）
3. Skills 机制       →  [agents/skills-system-design.md](agents/skills-system-design.md)（自己造一个 + 动态召回）
4. 多 Agent 协调     →  [agents/multi-agent-coordination.md](agents/multi-agent-coordination.md)（5 种协商机制）
5. 端到端实战         →  [agents/research-agent-architecture.md](agents/research-agent-architecture.md)（用 Claude Code 搭研究 Agent）
6. 工程级实现         →  [production/langgraph-research-agent-impl.md](production/langgraph-research-agent-impl.md)（LangGraph 完整代码）
7. 浏览器能力升级     →  [tools-protocols/browser-automation.md](tools-protocols/browser-automation.md)（Playwright + Computer Use 分层）
8. 评测体系           →  [evaluation/research-agent-evals.md](evaluation/research-agent-evals.md)（3 层评测 + 偏见防御）
```

适合：想用前沿 Agent 能力做产品的人。先看 1-2 建立心智，再按需深入 3-8。

---

## 七、最常见的五个工程坑

放在导读，因为新做 Agent 的团队 80% 在这里栽：

1. **链路太长不收敛**
   - 现象：Agent 跑 8 步 10 步还在转，烧钱不出结果。
   - 原因：没有终止条件 + 没有"我做不到"的退出路径。
   - 解法：硬编码 max_steps；显式 "give up" tool。

2. **prompt 越改越差**
   - 现象：今天加几句明天去几句，效果时好时坏。
   - 原因：没有评测集 → 没有客观对比 → 凭直觉改。
   - 解法：先建 30-50 题黄金集 + LLM-as-Judge，每次改 prompt 跑一遍。

3. **Function Calling 参数错了不知道**
   - 现象：表面上工具被调了，但参数错了导致结果错。
   - 原因：缺 schema 校验 + 缺重试。
   - 解法：Pydantic / Zod 校验 + 自动反馈错误重新生成。

4. **工具数量爆炸**
   - 现象：给了 50 个工具，Agent 经常用错。
   - 原因：上下文里塞太多工具描述 → 模型选错。
   - 解法：动态工具检索（按当前任务召回 5-10 个工具）。

5. **没区分"评测"和"监控"**
   - 现象：上线后发现质量在悄悄下降。
   - 原因：评测只在开发时做，线上没观测。
   - 解法：评测（offline 黄金集）+ 监控（online 真实流量采样 + 用户反馈）双轨。

---

## 八、配套工具与生态速览

| 类型 | 工具 / 协议 |
|---|---|
| 模型提供方 | OpenAI、Anthropic、Google、DeepSeek、Qwen、智谱、月之暗面 |
| 编排框架 | LangChain、LangGraph、LlamaIndex、DSPy、Haystack |
| Agent 框架 | AutoGen、CrewAI、Swarm、LangGraph、Pydantic AI |
| 工具协议 | Function Calling、**MCP**（Model Context Protocol）、A2A |
| 可观测性 | LangSmith、Langfuse、Phoenix（Arize）、Helicone |
| 评测 | RAGAS、TruLens、DeepEval、`promptfoo` |
| 网关 | LiteLLM、Portkey、OpenRouter |
| 代码执行沙箱 | E2B、Daytona、Docker isolation |
| 浏览器 Agent | Playwright + 自研、browser-use、Anthropic Computer Use |

---

## 九、和本工作区其他模块的关联

- **knowledge-base/AI-Agent/**（[../../knowledge-base/AI-Agent/](../../knowledge-base/AI-Agent/)）：现有的 Agent 沉淀
- **knowledge-base/RAG/**（[../../knowledge-base/RAG/](../../knowledge-base/RAG/)）：RAG 专题
- **knowledge-base/AI-SKILL/**（[../../knowledge-base/AI-SKILL/](../../knowledge-base/AI-SKILL/)）：AI 工程技巧
- **references/**：[agentic-design-patterns.md](../../references/agentic-design-patterns.md)、[rag-agent-scenario-analysis.md](../../references/rag-agent-scenario-analysis.md)
- **project/ice-workbench/**：现成的 agents/ 代码库可参照
- **project/understand-anything/**（[../understand-anything/](../understand-anything/)）：把 codebase / 知识库变成知识图谱——多 Agent pipeline 的开源样本
- **project/multica/**（[../multica/](../multica/)）：把 agent 当队友的协作管理层——Multi-Agent + Squad 的生产实现
- **AB 测试 + 因果推断**：LLM 产品的离线/在线评测、增量价值估计——见 [../ab-testing/](../ab-testing/)、[../causal-inference/](../causal-inference/)

---

## 十、心法

如果只能记三句：

1. **能用 Workflow 就别用 Agent**——动态决策的代价很大。
2. **没评测集，所有 prompt 调优都是玄学**——先建集，再改 prompt。
3. **Token 经济学是产品决策**——不是事后优化，是设计阶段就要算的账。

下一步建议：先看 [transformer.md](llm-fundamentals/transformer.md) 建立 LLM 直觉，再看 [react-and-variants.md](agents/react-and-variants.md) 建立 Agent 直觉。两篇加起来一个小时，能让你后续的所有讨论都"接得上"。

---

## 附：2026 主流 Agent 框架四类速览

完整版见 [production/frameworks-landscape.md](production/frameworks-landscape.md)。

```
1. 通用编排框架        LangGraph / Pydantic AI / LlamaIndex Workflows / Semantic Kernel
                      → 自己拼 Agent，框架给抽象和工具

2. 多 Agent 协作       AutoGen / AG2 / CrewAI / OpenAI Agents SDK / MetaGPT
                      → 框架给"多个 Agent 怎么协作"的范式

3. 垂直 / 自主 Agent   Claude Code / Devin / OpenHands / Manus / Browser-Use / Skyvern
                      → 已经是产品形态，给特定场景

4. 协议 / 基础设施     MCP / A2A / LangSmith / Langfuse / Phoenix
                      → 标准 / 协议 / 可观测性
```

**心法**：先确认自己在哪一类，再看类内选哪个。**能用 Workflow 别用 Agent，能用单 Agent 别用多 Agent**。
