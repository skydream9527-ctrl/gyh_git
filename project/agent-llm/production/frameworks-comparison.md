# LLM/Agent 框架对比

> 选错框架可能让你多写一倍代码、多花两倍精力调试。本文对当前主流框架（LangChain、LangGraph、LlamaIndex、DSPy、AutoGen、CrewAI、Pydantic AI、Haystack）做横向对比，给出按场景的选型建议。

---

## 一、为什么不能"哪个流行用哪个"

LLM 框架领域的特殊之处：

- **演化极快**：2023 年的"标准"到 2025 年可能已经被替代
- **抽象层级差异大**：从"几个工具函数"到"完整 ReAct 引擎"应有尽有
- **锁定成本不一**：有的轻量易换，有的深度耦合（替换=重写）
- **各有真实痛点**：有的擅长 RAG、有的擅长多 Agent、有的擅长生产可观测

**选型五维度**：

```
1. 抽象层级    — 高层（写得快） vs 低层（控制力强）
2. 任务类型    — RAG / Agent / Workflow / 多 Agent 协作
3. 生产成熟度  — 可观测、错误恢复、生产部署
4. 团队偏好    — Python / TS / 企业 / 创业
5. 锁定成本    — 换框架要重写多少
```

---

## 二、主流框架快览

| 框架 | 维护方 | 主擅长 | 抽象层级 | 生产成熟度 |
|---|---|---|---|---|
| **LangChain** | LangChain Inc. | 通用 / 集成多 | 中 | 中（早期 API 有历史包袱） |
| **LangGraph** | LangChain Inc. | 状态机式 Agent | 中-低 | 高（生产首选） |
| **LlamaIndex** | LlamaIndex Inc. | RAG / 数据接入 | 中 | 高（RAG 场景） |
| **DSPy** | Stanford / Databricks | 声明式编程 + 优化 | 高 | 中（仍偏研究） |
| **AutoGen** | Microsoft | 多 Agent 对话 | 中 | 中 |
| **CrewAI** | 独立创业 | 多 Agent 角色协作 | 高 | 中（增长快） |
| **Pydantic AI** | Pydantic 团队 | 类型友好 + 简洁 | 中 | 中（新但口碑好） |
| **Haystack** | deepset | 企业级 RAG / Pipeline | 中 | 高（欧洲生态） |
| **Semantic Kernel** | Microsoft | .NET / 企业 / Agent | 中 | 高（.NET 生态） |
| **Letta** (MemGPT) | Letta | 有状态 Agent + 记忆 | 中 | 中 |

---

## 三、按任务匹配

### 1. RAG 应用为主

```
小项目 / 快速原型     → LlamaIndex（RAG 抽象最完整）
生产 / 复杂流水线     → Haystack 或 LlamaIndex + 自研
企业 .NET 栈          → Semantic Kernel
```

**为什么不是 LangChain？** LangChain 的 RAG 抽象有，但不如 LlamaIndex 系统；它的强项在"集成 + 工具" 而非纯 RAG。

### 2. 单 Agent + 工具调用

```
简单 / 类型友好       → Pydantic AI
复杂状态 / 生产       → LangGraph
研究 / 优化型         → DSPy
基础不想多依赖         → 直接 OpenAI / Anthropic SDK
```

### 3. 多 Agent 协作

```
对话式（Manager + 专家）  → AutoGen
角色扮演 + 工作流         → CrewAI
状态机式（确定性强）      → LangGraph 多节点
```

### 4. Workflow（确定性流程，非 Agent）

```
直接用 SDK + Pydantic    → 最简单
LangGraph 走 deterministic 模式
```

> Anthropic 的 *Building Effective Agents* 反复提醒：**能用 Workflow 别用 Agent**。多数生产场景是 Workflow 加少量动态决策。

### 5. Coding Agent

```
框架几乎全部不合适。
Coding Agent 的最佳实践是直接用 LLM SDK + Function Calling +
显式状态机（Cursor / Cline / Claude Code 的内核都是自研）
```

---

## 四、深入对比：LangChain vs LangGraph

很多人混淆这两个。

### LangChain（2022-）
- 起源：Chain 抽象（一个个组件串联）
- 特点：API 演化快，历史包袱重；社区集成最广
- 现状：**保留维护**，但官方推荐生产用 LangGraph

### LangGraph（2024-）
- 起源：从 LangChain 抽离，专注"状态图 Agent"
- 抽象：节点 + 边 + 状态对象（Pydantic）
- 特点：可控、可恢复、可观测
- 是 **LangChain 团队对自己 v1 抽象问题的反思之作**

```python
# LangGraph 心智模型
from langgraph.graph import StateGraph

graph = StateGraph(State)
graph.add_node("planner", plan_fn)
graph.add_node("executor", exec_fn)
graph.add_edge("planner", "executor")
graph.add_conditional_edges("executor", should_continue, {True: "planner", False: END})
app = graph.compile()
```

> **如果今天开始建生产 Agent，应该看 LangGraph 不是 LangChain。**

---

## 五、DSPy 的特殊性

DSPy 是个"另类"——它把 LLM 应用看成**程序**，prompt 是程序参数：

```python
import dspy

class GenerateAnswer(dspy.Signature):
    """根据上下文回答"""
    context = dspy.InputField()
    question = dspy.InputField()
    answer = dspy.OutputField()

# 不写 prompt，写"签名"
qa = dspy.ChainOfThought(GenerateAnswer)

# 用 trainset 自动优化 prompt（zero-shot / few-shot 自动选）
optimizer = dspy.BootstrapFewShot(metric=my_metric)
optimized_qa = optimizer.compile(qa, trainset=examples)
```

**优势**：
- 不手写 prompt（系统帮你优化）
- 可被"编译" + 评测驱动迭代
- 切换模型不用重调 prompt

**劣势**：
- 学习曲线高
- 工程化稍慢，社区还在长

→ 适合**有评测集 + 团队接受新范式**的场景。前沿研究 / 严肃产品越来越多人尝试。

---

## 六、多 Agent 框架细分

### AutoGen（Microsoft, 2023-）
- 心智模型：**Agent 是会发消息的对象**
- 强项：多 Agent 对话编排灵活
- 适合：研究、复杂多角色任务

```python
manager = AssistantAgent(name="manager")
coder = AssistantAgent(name="coder")
critic = AssistantAgent(name="critic")
chat = GroupChat(agents=[manager, coder, critic])
```

### CrewAI（2024-）
- 心智模型：**任务 + 角色 + 工作流**（更"扁平 / 结构化"）
- 强项：上手最快，"角色卡"叙事清晰
- 适合：内容生产、研究 Agent、营销 Agent

```python
researcher = Agent(role='Researcher', goal='...', backstory='...')
writer = Agent(role='Writer', ...)
crew = Crew(agents=[...], tasks=[...])
```

### Swarm（OpenAI, 2024）
- 极简实验性多 Agent 框架
- 后续被 Microsoft AutoGen / 其他取代为主流
- 思想（Routine + Handoff）影响其他框架

---

## 七、生产成熟度对比

不是所有框架都能上生产。生产维度：

| 维度 | LangGraph | LlamaIndex | Pydantic AI | DSPy | CrewAI |
|---|---|---|---|---|---|
| **可观测性** | ⭐⭐⭐⭐⭐（LangSmith） | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ |
| **错误恢复** | ⭐⭐⭐⭐（checkpoint） | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ |
| **流式输出** | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ |
| **类型安全** | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| **长时任务 / 中断恢复** | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ |
| **多语言 SDK** | Python + JS | Python + TS | Python | Python | Python |

> **生产首选目前是 LangGraph + LangSmith**——并非完美但相对最成熟。

---

## 八、选型决策树

```
                 你的项目规模？
        ┌────────────┴────────────┐
    原型 / 周末项目              生产 / 长期维护
        │                              │
        ▼                              ▼
   直接用 SDK +                  目标场景？
   ┌─ Pydantic AI（Agent）       ┌──────┴──────┐
   ├─ LlamaIndex（RAG）       RAG 主导    Agent 主导
   └─ LangChain (跨工具集成)    │              │
                                 ▼              ▼
                              LlamaIndex     LangGraph
                              （+自研逻辑）    + LangSmith
                                              │
                                              多 Agent？
                                              ┌─┴─┐
                                             是    否
                                              │    │
                                              ▼    ▼
                                            CrewAI/  LangGraph
                                            AutoGen  单链
```

---

## 九、避免的错误选型

### 1. "听说 LangChain 火，先用着"
- LangChain 的强项在"快速集成 100 种工具" 而非"生产架构"
- 单纯调 OpenAI / Anthropic 不需要 LangChain
- 上生产前评估 LangGraph

### 2. 用框架做"框架擅长的事"以外的事
- AutoGen 用来做单 Agent → 重型
- CrewAI 用来做 RAG → 没有 LlamaIndex 顺手
- 选错框架不止慢，还会带来"以为该这么做"的认知偏差

### 3. 太早绑定深度框架
- 早期产品形态会变
- 抽象层 = 重构成本
- 先用 SDK 直写，明确 pattern 后再框架化

### 4. 跟风新框架但没评测
- "X 框架号称比 LangChain 强 30%" → 在哪个任务上？哪个指标？
- 没评测集的选型就是 vibe-driven

### 5. 忽略"不用框架"这个选项
- 200 行 Python 写明确的 ReAct 循环往往最快
- 框架适合**重复模式**多的项目

---

## 十、推荐的"轻量起步路径"

```
Week 1-2:
  直接 OpenAI / Anthropic SDK + Pydantic
  写最小可用版

Week 3-4:
  评估"哪些代码在重复"
  如果重复模式集中在 RAG → 引入 LlamaIndex
  如果重复模式集中在 Agent 状态 → 引入 LangGraph

Month 2+:
  上 LangSmith / Langfuse 做 observability
  补 evaluation 黄金集
  评估是否需要多 Agent / DSPy 等更高层抽象
```

> **不要从框架开始**。从"能用的最小代码"开始，让真实痛点引导框架选择。

---

## 十一、Checklist

```
□ 1. 我清楚目标场景是 RAG / 单 Agent / 多 Agent / Workflow？
□ 2. 我评估了"不用框架"的方案吗？
□ 3. 我选的框架对应的"主擅长"和我场景匹配吗？
□ 4. 框架的可观测性 / 错误恢复方案够生产用吗？
□ 5. 团队成员的语言栈和框架支持一致吗？
□ 6. 框架活跃度（GitHub star、PR 频率、issue 响应）健康吗？
□ 7. 锁定程度高吗？将来换框架成本如何？
□ 8. 是否给了"原型 → 生产"的迭代空间？
```

---

## 十二、扩展阅读

- 本目录：[observability.md](observability.md)、[../evaluation/llm-as-judge.md](../evaluation/llm-as-judge.md)
- 相关：[../agents/react-and-variants.md](../agents/react-and-variants.md)、[../tools-protocols/function-calling.md](../tools-protocols/function-calling.md)
- LangGraph 官方文档：https://langchain-ai.github.io/langgraph/
- LlamaIndex 文档：https://docs.llamaindex.ai
- DSPy 文档：https://dspy-docs.vercel.app
- CrewAI 文档：https://docs.crewai.com
- AutoGen 文档：https://microsoft.github.io/autogen/
- Anthropic — *Building Effective Agents*（2024）
- 各框架的"生产案例" GitHub 仓库
