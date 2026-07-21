# 主流 Agent 框架全景（2026 视角）

> 本文做"横向地图"：把当前 Agent 生态分成四类，每类挑代表性框架，给出特点和适用场景。深度对比见 [frameworks-comparison.md](frameworks-comparison.md)；多 Agent 协作见 [../agents/multi-agent-frameworks.md](../agents/multi-agent-frameworks.md)。

---

## 一、四类划分

按"定位"分类——选错类别比选错框架更糟。

```
1. 通用编排框架      自己拼 Agent，框架给抽象和工具
2. 多 Agent 协作    框架给"多个 Agent 怎么协作"的范式
3. 垂直 / 自主 Agent 已经是产品形态，给特定场景
4. 协议 / 基础设施   不是框架，是标准 / 可观测性 / 协议
```

每一类解决的问题不同。**先想清楚自己在哪一类，再看里面选哪个。**

---

## 二、第一类：通用编排框架（自己拼 Agent）

| 框架 | 特点 | 适用场景 |
|---|---|---|
| **LangGraph**（LangChain 出品） | 基于图的状态机编排，节点=函数/Agent，边=条件跳转；checkpoint、HITL、流式一等公民 | 需要**确定性流程 + 局部 LLM 决策**的复杂业务流（审批、客服、Multi-step RAG） |
| **LlamaIndex Agents / Workflows** | 事件驱动（Event-based Workflow），强 RAG 基因，索引和查询引擎一等公民 | **以知识检索为核心**的 Agent（文档问答、企业知识库、报告生成） |
| **Pydantic AI** | 类型安全、依赖注入风格，模型无关，输出强校验 | 写**生产级后端 Agent 服务**，对返回结构有严格契约的场景 |
| **Semantic Kernel**（微软） | Plugin/Planner 模式，C#/Python，深度对接 Azure 与 M365 | **企业 .NET / 微软生态**集成 |

### LangGraph vs Pydantic AI vs LlamaIndex Workflows 速选

三者都是"在后端服务里嵌入 Agent 能力"，但**心智模型完全不同**：

| 你的场景 | 选 |
|---|---|
| 流程复杂 + 要中断恢复 + 要人工介入 | **LangGraph** |
| 嵌入现有后端、追求类型安全和可测试性 | **Pydantic AI** |
| 主战场是"对一堆文档做智能问答/分析" | **LlamaIndex Workflows** |
| 三者都不太合身 | 自己写（很多严肃项目最后都这样） |

### 一个常被忽略的点：它们不互斥

常见组合：
- **LlamaIndex 做检索层** + **LangGraph 做编排层** —— 知识密集型业务的黄金组合
- **Pydantic AI 做对外 API 层** + 内部用 LangGraph 跑复杂流程 —— 类型契约 + 流程控制兼得

更细的对比见 [frameworks-comparison.md](frameworks-comparison.md)。

---

## 三、第二类：多 Agent 协作框架

| 框架 | 特点 | 适用场景 |
|---|---|---|
| **AutoGen / AG2**（微软） | 多 Agent 对话式协作（GroupChat、Society of Mind），代码执行内建 | **研究型多角色协作**：研究员+评审+程序员；探索性任务 |
| **CrewAI** | "Role + Task + Crew" 抽象，上手简单，社区模板多 | **流程化角色分工**（市场调研、内容生产线） |
| **OpenAI Agents SDK**（前 Swarm） | 轻量 handoff（Agent 之间转交控制权），官方维护 | OpenAI 生态下**简单的多 Agent 路由**（客服分流、专家分诊） |
| **MetaGPT** | 软件公司隐喻（PM/架构师/工程师），面向代码生成 | **从需求 → 完整代码库**的端到端尝试 |

**关键认识**：多 Agent 协作的本质是**通信模式之争**——对话式（AutoGen）/ 流水线式（CrewAI）/ 交接式（Agents SDK）。三者根据这个心智模型选型，深度展开见 [../agents/multi-agent-frameworks.md](../agents/multi-agent-frameworks.md)。

---

## 四、第三类：垂直 / 自主 Agent（已经是产品形态）

| 框架 | 特点 | 适用场景 |
|---|---|---|
| **Claude Agent SDK / Claude Code** | 工具调用 + 文件系统 + 子 Agent + Skills，长任务实战强 | **编码 / 运维 / 长链路自动化** |
| **Devin / OpenDevin (OpenHands)** | 自主软件工程 Agent，自带浏览器+终端+编辑器 | **端到端代码任务**（issue → PR） |
| **Manus** | 文件式规划（task_plan / findings / progress），强长任务记忆 | **跨小时 / 跨会话的研究与执行类任务** |
| **Browser-Use / Skyvern** | 浏览器自动化为核心，视觉+DOM 双通道 | **网页自动化、爬取、表单流** |

这一类的特点：**不是给你"组装能力"，而是直接给你"已经组装好的 Agent"**——你只要给任务和工具。

---

## 五、第四类：协议 / 基础设施层

| 项 | 特点 | 适用场景 |
|---|---|---|
| **MCP**（Model Context Protocol） | Anthropic 主推的工具/资源标准协议，跨 Agent 复用 | **统一对接外部系统**（数据库、IDE、企业 API） |
| **A2A**（Agent-to-Agent，Google） | Agent 之间通信协议，能力声明 + 任务交接 | **跨厂商 Agent 协作** |
| **LangSmith / Langfuse / Arize Phoenix** | 可观测性、Eval、Trace | 任何 Agent 都需要的**调试与质量监控** |

详见 [../tools-protocols/mcp.md](../tools-protocols/mcp.md) 和 [observability.md](observability.md)。

---

## 六、决策心法

### 三个硬指标决定要不要"上层框架"

1. **流程是否会演化** —— 早期演化快，先用 SDK 直写；模式稳定再框架化
2. **是否需要可观测和恢复** —— 是 → LangGraph；只是单次调用 → SDK 够了
3. **是否团队多人协作** —— 是 → 框架的"统一抽象"价值大；单人 → 抽象成本可能 > 收益

### 反模式

- ❌ "听说 LangChain 火，先用着" —— 强项是集成，不是生产架构
- ❌ "用 AutoGen 做单 Agent" —— 重型不必要
- ❌ "用 CrewAI 做 RAG" —— 不如 LlamaIndex 顺手
- ❌ "选完框架先深度绑定" —— 早期需求会变，先 SDK 直写

### 一句话总结

> **不要从框架开始**。从"能用的最小代码"开始，让真实痛点引导框架选择。

---

## 七、扩展阅读

- [frameworks-comparison.md](frameworks-comparison.md) —— LangChain / LangGraph / LlamaIndex / DSPy 等的深入横向对比
- [../agents/multi-agent-frameworks.md](../agents/multi-agent-frameworks.md) —— AutoGen / CrewAI / Agents SDK 三家的协作模式深度对比
- [../agents/subagent-patterns.md](../agents/subagent-patterns.md) —— Claude Code Task / CrewAI Crew / LangGraph Subgraph 三种"派子任务"机制的本质区别
- [langgraph-checkpoint-and-hitl.md](langgraph-checkpoint-and-hitl.md) —— LangGraph 的 checkpoint 表结构和 HITL 落地
- [../rag/agentic-rag-implementation.md](../rag/agentic-rag-implementation.md) —— CRAG / Self-RAG 的具体实现
