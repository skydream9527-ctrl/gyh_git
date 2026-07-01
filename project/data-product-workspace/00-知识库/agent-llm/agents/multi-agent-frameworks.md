# 多 Agent 协作框架：AutoGen / CrewAI / Agents SDK

> 本文系统讲清楚三大主流多 Agent 协作框架的**心智模型差异**、**最新进化**（AutoGen 0.4 / CrewAI Flows / Agents SDK Guardrails）、**反模式**和**单 → 多 Agent 演进路径**。
>
> 配套阅读：[subagent-patterns.md](subagent-patterns.md)（Task vs Crew vs Subgraph 的本质对比）、[../production/frameworks-landscape.md](../production/frameworks-landscape.md)（全景定位）。

---

## 一、多 Agent 的本质

### 1. 为什么需要多 Agent？

不是因为"看起来酷"，而是因为**单 Agent 在以下情况会崩**：

- **上下文过长**：一个 Agent 同时背"产品需求 + 代码风格 + API 文档 + 测试规范"，prompt 一塞就糊了
- **角色冲突**：让同一个 Agent 既"激进创造"又"严格审查"，它会两边都做不好
- **能力专精**：检索专家 + 代码专家 + 报告专家，每个用不同模型/不同 prompt 收益更高
- **并行加速**：5 个独立子任务能并行的，串行做就是浪费

### 2. 三种通信模式（最关键的分类）

三大框架本质就是在这三种模式上各押注：

```
模式 A：对话式（Conversation）
  Agent A ⇄ Agent B ⇄ Agent C   全员群聊，看谁该说话
  代表：AutoGen

模式 B：流程式（Pipeline / Crew）
  Manager → Agent A → Agent B → Agent C → 输出
  代表：CrewAI

模式 C：交接式（Handoff）
  Agent A ──handoff──> Agent B ──handoff──> Agent C
  代表：OpenAI Swarm / Agents SDK
```

---

## 二、AutoGen（微软）—— 对话式协作的鼻祖

### 1. 核心抽象

`ConversableAgent` 之间通过**消息**互相对话；`GroupChat` + `GroupChatManager` 决定下一个该谁说话。

### 2. 代码长这样

```python
from autogen import ConversableAgent, GroupChat, GroupChatManager

researcher = ConversableAgent(
    "researcher",
    system_message="你是研究员，负责查资料和分析",
    llm_config={"model": "gpt-4o"},
)

coder = ConversableAgent(
    "coder",
    system_message="你是程序员，根据研究结果写代码",
    llm_config={"model": "claude-sonnet-4-6"},
    code_execution_config={"work_dir": "./sandbox"},  # 自带代码执行!
)

reviewer = ConversableAgent(
    "reviewer",
    system_message="你是审查员，找 bug 和改进点",
    llm_config={"model": "gpt-4o"},
)

group = GroupChat(
    agents=[researcher, coder, reviewer],
    messages=[],
    max_round=20,
)
manager = GroupChatManager(groupchat=group, llm_config=...)

user_proxy.initiate_chat(manager, message="实现 LRU 缓存并测试")
```

### 3. 强项与弱项

**强项**
- **代码执行内建**：`code_execution_config` 直接给 Agent 一个沙箱，**这是 AutoGen 一大杀手锏**
- **对话灵活**：Agent 可以反复 challenge 对方，模拟真实团队 brainstorm
- **多模态**：图像、文件、工具调用都支持
- **微软背书**：v0.4 后架构完全重写（actor 模型），生产级稳定性提升明显

**弱项**
- **流程不可控**：GroupChatManager 内部用 LLM 决定下一个 speaker，**容易跑偏**——谁该接话不是你说了算
- **Token 消耗大**：群聊模式下，每个 Agent 都看到所有历史消息
- **调试困难**：出错时要翻一长串对话日志找问题
- **学习曲线陡**：v0.2 → v0.4 改了一次架构，旧教程都过期了

### 4. AutoGen 0.4：从"对话循环"到"Actor 模型"

#### 为什么要重写？

v0.2 的根本问题：**所有 Agent 在同一个进程里轮流说话**。

```python
# v0.2 的内核大致是这样
GroupChatManager:
  while not done:
      next_speaker = llm.decide(...)   # 一个 LLM call
      msg = next_speaker.respond(...)  # 又一个 LLM call
      group.append(msg)
```

死穴：
- **单点故障**：manager 挂了整个群聊崩
- **无法分布式**：所有 agent 必须在同一台机器
- **难以扩展**：加一个 agent 要改主循环
- **状态混乱**：消息历史是全局共享的，没法做"私聊"

#### v0.4 的核心思想：Actor Model

把每个 Agent 看作独立的 Actor：

```
┌──────────┐       ┌──────────┐       ┌──────────┐
│ Agent A  │ msg→  │  Runtime │ ←msg  │ Agent B  │
│ (Actor)  │       │  (Bus)   │       │ (Actor)  │
└──────────┘       └──────────┘       └──────────┘
   独立状态          消息总线           独立状态
```

每个 Agent：
- **独立的状态和邮箱**
- **只通过消息通信**（不共享内存）
- **可以跑在不同进程/机器上**

#### 三层架构

```
autogen-core      底层 actor runtime + 消息协议
   ↓
autogen-agentchat 对话式 agent 抽象（兼容 v0.2 心智）
   ↓
autogen-ext       第三方扩展（OpenAI/Anthropic/工具/...）
```

**意义**：你可以**只用 core**做底层多 agent 系统（不依赖 agentchat 的对话抽象），也可以**用 agentchat 快速复刻 v0.2 的群聊**。

#### 代码长这样

```python
from autogen_core import (
    AgentId, MessageContext, RoutedAgent,
    SingleThreadedAgentRuntime, message_handler,
)
from dataclasses import dataclass

@dataclass
class TaskMessage:
    content: str

@dataclass
class ResultMessage:
    content: str

class ResearcherAgent(RoutedAgent):
    @message_handler
    async def handle_task(self, msg: TaskMessage, ctx: MessageContext) -> None:
        result = await llm.complete(f"Research: {msg.content}")
        await self.send_message(
            ResultMessage(content=result),
            AgentId("writer", "default"),
        )

class WriterAgent(RoutedAgent):
    @message_handler
    async def handle_result(self, msg: ResultMessage, ctx: MessageContext) -> None:
        report = await llm.complete(f"Write report from: {msg.content}")
        print(report)

runtime = SingleThreadedAgentRuntime()
await ResearcherAgent.register(runtime, "researcher", lambda: ResearcherAgent("R"))
await WriterAgent.register(runtime, "writer", lambda: WriterAgent("W"))
runtime.start()

await runtime.send_message(
    TaskMessage(content="2026 Agent 框架"),
    AgentId("researcher", "default"),
)
```

关键变化：
- `@message_handler` 像 FastAPI 的 route 装饰器，按消息类型路由
- Agent 不再是"对话参与者"，而是**"消息处理器"**
- `SingleThreadedAgentRuntime` 是单进程；要分布式换 `WorkerAgentRuntime` + gRPC

#### 真正的杀手级特性

**a) 分布式 Runtime**

```python
# Host 进程
host = GrpcWorkerAgentRuntimeHost(address="localhost:50051")
host.start()

# Worker 进程 1（跑研究 Agent）
worker1 = GrpcWorkerAgentRuntime(host_address="localhost:50051")
await ResearcherAgent.register(worker1, "researcher", ...)

# Worker 进程 2（跑代码 Agent，单独的沙箱机器）
worker2 = GrpcWorkerAgentRuntime(host_address="localhost:50051")
await CoderAgent.register(worker2, "coder", ...)
```

**Agent 真的可以跨机器**——这是 v0.2 完全做不到的。

**b) Magentic-One**

微软在 v0.4 上构建的开箱即用通用问题解决系统：Orchestrator + WebSurfer + FileSurfer + Coder + Terminal。**不用自己组装**，import 即用。

#### 什么时候用 v0.4

- 真的要**跨进程/跨机器**的多 Agent 系统（沙箱隔离、合规隔离）
- 需要**自定义消息协议**（不只是 LLM 对话）
- 想要**Magentic-One**这种现成的通用 agent

否则，纯应用场景下 LangGraph 更实用。

### 5. 适合 / 不适合

**适合**
- **研究型任务**：探索性的、不知道步骤的
- **代码生成 + 测试 + 调试闭环**：coder 写、executor 跑、reviewer 改，循环到通过
- **复杂推理需要多视角**：辩论式 Agent（pro vs con）

**不适合**
- **生产业务流程**：客服系统、审批流，**别用 AutoGen**，太不可控
- **延迟敏感**：群聊轮次多

### 6. 现状（2026）

AutoGen 现分两个项目：
- **AutoGen 0.4+**（微软主仓库）：actor 模型重写，企业级
- **AG2**（社区 fork，原 AutoGen 团队出走后建立）：更接近原版心智，迭代快

**选型时注意**：很多老教程是 v0.2 的，写法已经废了。

---

## 三、CrewAI —— 流程化角色分工

### 1. 核心抽象

**Crew = Agents + Tasks + Process**

- `Agent`：role + goal + backstory（"你是谁，目标，背景"）
- `Task`：description + expected_output + assigned_agent
- `Process`：sequential（串行）/ hierarchical（带 manager 的层级）

### 2. 代码长这样

```python
from crewai import Agent, Task, Crew, Process

researcher = Agent(
    role="市场研究员",
    goal="找出 2026 年 AI Agent 市场的关键趋势",
    backstory="资深行业分析师，擅长数据挖掘",
    tools=[search_tool, scraper_tool],
    llm=llm_gpt4,
)

writer = Agent(
    role="技术写手",
    goal="把研究结果写成结构化报告",
    backstory="10 年技术写作经验",
    llm=llm_claude,
)

task1 = Task(
    description="调研 AI Agent 框架，重点关注融资和用户增长",
    expected_output="一份包含 5 个关键数据点的清单",
    agent=researcher,
)

task2 = Task(
    description="基于研究清单，写一份 1500 字报告",
    expected_output="Markdown 格式的报告",
    agent=writer,
    context=[task1],  # 显式依赖
)

crew = Crew(
    agents=[researcher, writer],
    tasks=[task1, task2],
    process=Process.sequential,
)

result = crew.kickoff()
```

### 3. 强项与弱项

**强项**
- **上手最快**：role + goal 这种叙事化 prompt 让"组团"非常直觉
- **流程可控**：sequential 模式下，谁先谁后你说了算
- **模板生态丰富**：官方 + 社区一堆现成 crew（市场调研、内容生产、数据分析）
- **YAML 配置**：可以把 Agent/Task 写在 YAML 里，**非工程师也能改**
- **CrewAI Flows**（新功能）：把 Crew 嵌入更大的事件驱动流程，对标 LangGraph

**弱项**
- **role-play 容易过头**：LLM 太"入戏"，会输出"作为资深分析师，我认为..."这种废话
- **状态管理弱**：没有 LangGraph 的 checkpoint，长任务中断不好恢复
- **hierarchical 模式不稳**：manager 调度 agent 的逻辑是 LLM 决定的，跟 AutoGen 一样会跑偏
- **生产化能力弱**：观测、错误恢复、HITL 都不如 LangGraph

### 4. CrewAI Flows：从"流水线"到"事件驱动"

#### 为什么要做 Flows？

经典 Crew（Sequential / Hierarchical）的局限：
- **一次性执行**：crew.kickoff() 跑完就结束，没法长时间运行
- **没有条件分支**：无法"如果 A 失败就走 B"
- **Crew 之间不能编排**：你写了 3 个 Crew，怎么把它们串起来？
- **没有事件**：等不了外部触发

#### Flow 是什么

**Flow = 把 Crew 当作"步骤"，事件驱动地编排起来**。

```python
from crewai.flow.flow import Flow, listen, start, router
from pydantic import BaseModel

class State(BaseModel):
    topic: str = ""
    research: str = ""
    quality_score: int = 0
    final_report: str = ""

class ContentFlow(Flow[State]):

    @start()
    def begin(self):
        self.state.topic = "AI Agent 框架 2026"
        return "started"

    @listen("started")
    def do_research(self, _):
        research_crew = ResearchCrew().crew()
        result = research_crew.kickoff(inputs={"topic": self.state.topic})
        self.state.research = str(result)
        return "research_done"

    @listen("research_done")
    def evaluate_quality(self, _):
        score = llm_judge(self.state.research)
        self.state.quality_score = score
        return "evaluated"

    @router("evaluated")
    def quality_route(self, _):
        if self.state.quality_score >= 8:
            return "write"
        elif self.state.quality_score >= 5:
            return "rewrite"
        else:
            return "redo_research"

    @listen("write")
    def write_report(self, _):
        writer_crew = WriterCrew().crew()
        self.state.final_report = str(
            writer_crew.kickoff(inputs={"research": self.state.research})
        )

    @listen("rewrite")
    def improve_research(self, _):
        ...

    @listen("redo_research")
    def restart(self, _):
        return "started"  # 重新触发研究

flow = ContentFlow()
flow.kickoff()
```

#### 三个核心装饰器

| 装饰器 | 含义 |
|---|---|
| `@start()` | Flow 入口 |
| `@listen("event")` | 监听某个事件，事件触发时执行 |
| `@router("event")` | 监听事件，**返回值决定下一个事件**（条件分支） |

**Flow vs Crew 的关系**：Crew 是"一次协作"，Flow 是"协作之间怎么串"。

#### Crew + Flow 嵌套用法（官方推荐）

```python
class CustomerSupportFlow(Flow[State]):

    @start()
    def receive_ticket(self):
        self.state.ticket = await fetch_from_zendesk()

    @router("receive_ticket")
    def classify(self, _):
        category = classify_with_llm(self.state.ticket)
        return category  # "billing" / "tech" / "general"

    @listen("billing")
    def handle_billing(self, _):
        BillingCrew().crew().kickoff(inputs={"ticket": self.state.ticket})

    @listen("tech")
    def handle_tech(self, _):
        TechCrew().crew().kickoff(inputs={"ticket": self.state.ticket})

    @listen("general")
    def handle_general(self, _):
        GeneralCrew().crew().kickoff(inputs={"ticket": self.state.ticket})
```

**外层 Flow 做路由，内层 Crew 做角色协作**——这是 CrewAI 现在的官方推荐用法。

#### Flows 的局限

- **不如 LangGraph 成熟**：checkpoint、HITL 都是后加的，还不稳
- **状态模型简单**：单个 Pydantic State，不像 LangGraph 有 channel/reducer 那么灵活
- **调试工具少**：出错日志可读性一般

**实战建议**：CrewAI 适合做**业务方能改的 YAML 化流程**；真要工程级流程编排，LangGraph 还是更稳。

### 5. CrewAI Crew 嵌套 Crew 的三种模式

CrewAI 没有原生的"嵌套 Crew"概念，但有三种实战模式。

#### 模式 1：用 Flow 把多个 Crew 串起来（推荐）

见上节"Crew + Flow 嵌套用法"。**这是官方推荐方式**。

#### 模式 2：在一个 Task 里调用另一个 Crew（hack，谨慎）

把"调用另一个 Crew"包装成一个 tool，给某个 agent 用：

```python
from crewai.tools import tool

@tool("call_research_crew")
def call_research_crew(topic: str) -> str:
    """调用研究专家团队对某个 topic 做深入研究"""
    crew = ResearchCrew().crew()
    result = crew.kickoff(inputs={"topic": topic})
    return str(result)

project_manager = Agent(
    role="项目经理",
    goal="协调多个专家团队完成项目",
    tools=[call_research_crew, call_writing_crew, call_review_crew],
)
```

**特点**：
- "manager Crew" 决定调用哪个"子 Crew"
- 类似 Claude Code 的 Task 工具模式
- 但 **LLM 决定调度顺序**——可控性差

**陷阱**：
- Crew kickoff 是阻塞的，工具调用里跑一个完整 Crew，**延迟高、token 高、错误难定位**
- LLM 可能反复调同一个 Crew（成本爆炸）
- **不推荐**用于生产，做 demo 可以

#### 模式 3：Hierarchical Process + Manager Agent（官方但不稳）

```python
crew = Crew(
    agents=[researcher, writer, reviewer],
    tasks=[task1, task2, task3],
    process=Process.hierarchical,
    manager_llm=ChatOpenAI(model="gpt-4o"),
)
```

把每个 Crew 包成一个 "agent"，再用 hierarchical 嵌套：

```python
research_meta_agent = Agent(
    role="Research Team Lead",
    tools=[call_research_crew],
)

writing_meta_agent = Agent(
    role="Writing Team Lead",
    tools=[call_writing_crew],
)

top_crew = Crew(
    agents=[research_meta_agent, writing_meta_agent],
    tasks=[overall_task],
    process=Process.hierarchical,
)
```

**特点**：双层 LLM 调度，成本和不稳定性翻倍。**强烈不推荐**。

#### 三种模式对比

| | Flow + Crew | Crew Tool 模式 | Hierarchical Meta-Crew |
|---|---|---|---|
| 流程控制 | 显式（你写 Flow） | LLM 决定（manager agent） | LLM 决定（manager LLM） |
| 状态管理 | Flow.state（清晰） | 隐式（依赖 prompt 传递） | 隐式 |
| 错误恢复 | Flow 层可以加 | 难 | 难 |
| 推荐度 | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐ |
| 适合场景 | 生产流水线 | demo / 探索 | 几乎不适合 |

#### 实战建议

90% 的"嵌套 Crew"需求，正确解法是：

1. 不要嵌套——拆成多个 Crew + 1 个 Flow 串起来
2. 数据流通过 Flow.state 显式传递
3. 每个 Crew 只关心自己内部的角色协作
4. 复杂分支逻辑写在 Flow 的 `@router`，不要让 Crew 内部的 manager LLM 决策

**判断技巧**：你能不能画出一个"Crew 之间怎么走"的流程图？
- 能画清楚 → 用 Flow + Crew，永远更稳
- 画不清楚 → 你的需求本来就模糊，先想清楚再上 CrewAI

### 6. 适合 / 不适合

**适合**
- **内容生产线**：调研 → 写作 → 审校 → 发布
- **重复性流程任务**：固定模板的报告、固定流程的数据处理
- **演示 / POC**：给老板演示"AI 团队"概念，CrewAI 5 分钟出 demo
- **业务方自助**：让运营/产品同学改 YAML 配 Agent

**不适合**
- **流程会变化、有复杂分支**：用 LangGraph
- **真正的对话式协作**：用 AutoGen
- **核心业务系统**：稳定性和可观测性不够

### 7. 一个真实坑

CrewAI 的 `expected_output` 字段不是强约束——**LLM 经常不按要求输出**。生产里要么用 Pydantic schema 配合 `output_pydantic`，要么用别的框架。

---

## 四、OpenAI Swarm / Agents SDK —— 极简交接

### 1. 历史背景

- **Swarm**（2024）：OpenAI 出的"教育性"轻量框架，**官方说不是生产级**
- **Agents SDK**（2025）：Swarm 升级版，正式发布，加了追踪、guardrails、handoff 强化

现在说"Swarm 心智模型"通常指 **Agents SDK**。

### 2. 核心抽象

只有两个概念：
1. **Agent**：有 instructions 和 tools
2. **Handoff**：Agent 把控制权"交给"另一个 Agent

```python
from agents import Agent, Runner, function_tool

@function_tool
def check_order_status(order_id: str) -> str:
    return f"Order {order_id} is shipped"

billing_agent = Agent(
    name="Billing Agent",
    instructions="处理账单和退款问题",
    tools=[check_order_status],
)

support_agent = Agent(
    name="Support Agent",
    instructions="处理一般客服。账单问题转给 Billing Agent。",
    handoffs=[billing_agent],   # 关键：声明可以交接给谁
)

result = Runner.run_sync(support_agent, "我要退款，订单号 12345")
# support_agent 看到"退款"自动 handoff 给 billing_agent
```

### 3. 强项与弱项

**强项**
- **极简**：核心就 Agent + Handoff 两个概念
- **意图清晰**：每个 Agent 专精一件事，**handoff 是 LLM 看着 instructions 决定的**
- **Tracing 内建**：Agents SDK 自带可视化追踪面板
- **OpenAI 生态原生**：搭配 Realtime API 做语音 Agent 体验最佳
- **Guardrails**：输入/输出校验是一等公民

**弱项**
- **绑定 OpenAI**：Anthropic / Gemini 要走兼容层，不爽
- **能力有限**：没有 LangGraph 的 checkpoint、没有 AutoGen 的代码执行
- **handoff 只能单向**：A 转给 B 后，B 处理完不会自动回 A（需要显式 handoff 回去）
- **不适合复杂协作**：handoff 是"我搞不定，你来"，不是"我们一起讨论"

### 4. Guardrails：把"防护栏"做成一等公民

#### 什么是 Guardrail

不是"prompt 里写'请不要做 X'"——那是 wishful thinking。

**Guardrail = 在 Agent 输入/输出前后，跑一段独立的验证逻辑，违规直接抛 tripwire 中断。**

两类：
- **Input Guardrail**：拦截输入（用户问的不该问 / 试图越权）
- **Output Guardrail**：拦截输出（Agent 答了不该答的 / 格式不对）

#### 代码长这样

```python
from agents import (
    Agent, Runner, GuardrailFunctionOutput,
    InputGuardrailTripwireTriggered,
    input_guardrail, output_guardrail,
)
from pydantic import BaseModel

class HomeworkCheck(BaseModel):
    is_homework: bool
    reasoning: str

# 这是一个"小 agent"专门做检查
homework_detector = Agent(
    name="Homework Detector",
    instructions="判断用户是不是在让你做家庭作业",
    output_type=HomeworkCheck,
)

@input_guardrail
async def homework_guardrail(ctx, agent, user_input):
    result = await Runner.run(homework_detector, user_input)
    return GuardrailFunctionOutput(
        output_info=result.final_output,
        tripwire_triggered=result.final_output.is_homework,
    )

main_agent = Agent(
    name="Tutor",
    instructions="你是一个引导式数学老师，引导思考但不直接给答案",
    input_guardrails=[homework_guardrail],
)

try:
    result = await Runner.run(main_agent, "帮我做这道题：3x+5=20")
except InputGuardrailTripwireTriggered as e:
    print("拦截了:", e.guardrail_result.output.output_info)
```

#### 关键设计点

**a) Guardrail 本身可以是 Agent**

`homework_detector` 就是一个迷你 Agent。**用 LLM 判 LLM**——比正则强大太多。

**b) 并行执行**

```python
main_agent = Agent(
    name="...",
    input_guardrails=[
        homework_guardrail,    # 检查作业
        toxicity_guardrail,    # 检查毒性
        pii_guardrail,         # 检查个人信息
    ],
)
```

**这些 guardrail 并行跑**，任何一个 tripwire 触发就立刻终止主 Agent —— **不等其他检查跑完，省 token**。

**c) Output Guardrail 校验结构和内容**

```python
@output_guardrail
async def no_pii_in_output(ctx, agent, output):
    has_pii = await pii_detector_llm(output)
    return GuardrailFunctionOutput(
        output_info={"detected": has_pii},
        tripwire_triggered=has_pii,
    )
```

#### 实战：典型 Guardrail 组合

**客服 Agent 的标准防护栏**：

| Guardrail | 类型 | 作用 |
|---|---|---|
| Topic relevance | Input | 用户问的是否在产品范围内 |
| Prompt injection detection | Input | 检测"忽略之前指令"这种攻击 |
| PII redaction | Input | 用户发了身份证号要脱敏再进 LLM |
| Off-policy response | Output | Agent 是否给出了违反公司政策的回答 |
| Hallucination check | Output | 关键事实是否能在知识库找到 |
| Format validation | Output | 输出是否符合 schema（用 Pydantic） |

#### 为什么 Guardrail 是一等公民很关键

- **可观测性内建**：每个 guardrail 的判断结果都进 Trace
- **失败模式明确**：tripwire 抛特定异常，业务代码能精确处理
- **不污染主 Agent prompt**：检查逻辑独立，主 Agent 的 instructions 保持简洁

**对比**：CrewAI / AutoGen 没这个一等公民的概念，要自己在工具里塞校验，代码恶心得多。

### 5. 适合 / 不适合

**适合**
- **客服分诊**：通用客服 → 账单 / 技术 / 售后
- **专家路由**：用户问题 → 路由到对应领域专家 Agent
- **简单的多角色对话**：医生 Agent → 转给护士 Agent 做后续

**不适合**
- **需要多个 Agent 同时工作**：handoff 是单线程，一次只有一个 Agent 活跃
- **需要协商 / 辩论**：那是 AutoGen 的活
- **不在 OpenAI 生态**：选 Swarm 没意义

---

## 五、三者对比表

| 维度 | AutoGen | CrewAI | Agents SDK |
|---|---|---|---|
| **协作模式** | 群聊 | 流水线 | 交接 |
| **谁决定下一步** | LLM (manager) | 开发者（task 顺序） | LLM（按 instructions 判断） |
| **代码执行** | ✅ 内建沙箱 | ❌ 需自己接 | ❌ 工具调用 |
| **上手难度** | 高 | **低** | 低 |
| **生产稳定性** | 中（v0.4 改善） | 中 | 高（OpenAI 维护） |
| **可观测性** | 弱 | 弱 | **强**（内建 tracing） |
| **模型自由度** | 高 | 高 | 偏 OpenAI |
| **典型场景** | 研究 / 代码 / 辩论 | 内容生产线 | 客服路由 |
| **代码量（最小可用）** | ~30 行 | ~20 行 | ~15 行 |

---

## 六、实战决策树

```
你的任务是固定流水线吗？
├─ 是 → CrewAI（最快）或 LangGraph（更可控）
└─ 否 → 任务需要多个角色协作完成？
        ├─ 是，且需要"讨论 / 辩论 / 反复迭代" → AutoGen
        ├─ 是，但只是"我搞不定转给你" → Agents SDK
        └─ 否 → 你不需要多 Agent，单 Agent + 多工具就够了
```

---

## 七、五个反模式（什么时候多 Agent 反而更糟）

### 反模式一：用多 Agent 解决"上下文窗口"

**症状**：
> "我们 Agent 的 system prompt 太长了，分成 5 个 Agent 每个 prompt 短一点"

**真相**：

```
拆 → Agent 之间要互相传上下文 → 要么传不全（信息丢失）
                                → 要么传太多（每个 Agent 都收到完整历史，token x N 倍）
```

**核心问题**：多 Agent 不能减少信息总量，**只能改变信息流动方式**。

**正确做法**：
- prompt 太长 → 用 RAG / 工具调用按需加载
- 真要拆 → 拆成"工具"而不是"Agent"（同一个 Agent 用不同工具，上下文统一）

### 反模式二：用多 Agent 解决"质量问题"

**症状**：
> "GPT-4o 答得不够好，让 3 个 Agent 投票！"

**真相**（Anthropic 自己的研究）：

| 方案 | 质量 | 成本 | 延迟 |
|---|---|---|---|
| 1× GPT-4o + CoT | 基准 | 1× | 1× |
| 3× GPT-4o 投票 | +5~10% | 3× | 1× (并行) |
| 1× GPT-4o + Self-consistency (5 samples) | +5~10% | 5× | 1× (并行) |
| 1× Claude Opus + CoT | **+15~25%** | 1.5× | 1× |

**结论**：换更强的模型 > 多 Agent 投票。多 Agent 投票的提升空间，**早就被新一代模型吃掉了**。

**例外**：多 Agent 不同视角（pro vs con 辩论）在**事实核查、复杂推理**上还是有效的——但这是"对抗性多 Agent"，不是"投票多 Agent"。

### 反模式三：用多 Agent 模拟"组织架构"

**症状**：
> "我们要做一个 AI 公司：CEO Agent + CTO Agent + 工程师 Agent + 设计师 Agent..."

**真相**：

人类组织架构的存在是因为**人有认知带宽限制、需要分工**。LLM 没有这些限制。

强行模拟会带来：
- **冗余对话**：CEO 把任务转给 CTO，CTO 转给工程师，每一跳都损耗信息
- **role-play 污染**：模型太"入戏"，输出"作为 CTO，我认为我们应该..."这种废话
- **决策路径变长**：本来一步能答，现在要 5 个 Agent 接力

**实战观察**：MetaGPT 这类"AI 公司"框架做 demo 很惊艳，**真做产品几乎没人用**。

### 反模式四：让 LLM 决定"下一个谁说话"

**症状**：
> "我们用 AutoGen 的 GroupChatManager / CrewAI 的 hierarchical mode"

**真相**：

`manager LLM` 看着所有 agent 的描述，每轮决定下一个谁说。这意味着：
- **每轮多一次 LLM call**：纯路由开销
- **决策不稳定**：同样的状态，可能选 A 也可能选 B
- **死循环风险**：A → B → A → B → ...
- **难调试**：出错时你不知道为什么 manager 选了 A

**正确做法**：
- 流程能写死的写死（CrewAI sequential / LangGraph 显式 edge）
- 必须 LLM 路由的，**用一个明确的"router agent"**，输入是结构化的（不是自由对话历史），输出是 enum（不是自由文本）

### 反模式五：Agent 之间共享"完整对话历史"

**症状**：AutoGen / CrewAI 默认行为——所有 Agent 看到群聊全部消息。

**真相**：
- **token 成本爆炸**：N 个 agent，每轮每个 agent 都要消化完整历史
- **上下文漂移**：早期讨论被覆盖、被歪曲
- **信号噪声比下降**：Agent 看到的是"对话史"，不是"我需要的信息"

**正确做法**：
- **结构化交接**：A 给 B 传一个 schema 化的对象（`{task, context, constraints}`），不是对话历史
- **私有 scratchpad**：每个 Agent 有自己的工作区，主线只传结论
- **summarizer agent**：当历史过长，专门一个 agent 压缩历史给后续 agent 用

---

## 八、从单 Agent 演进到多 Agent 的正确路径

### 阶段 0：单 Agent + 工具

```
[Agent + 5 个工具] ──> 直接干活
```

**80% 的需求到这里就该停**。包括很多人以为需要"多 agent"的需求。

**判断标准**：
- 任务能拆成"调用不同工具"而不是"不同 LLM 上下文"？→ 单 Agent
- 上下文能塞进一个 system prompt + 工具按需加载？→ 单 Agent

### 阶段 1：单 Agent + 子 Agent 作为工具

```
[主 Agent]
    ├─ 工具1
    ├─ 工具2
    └─ 调用[子 Agent]当工具
              └─ 子 Agent 内部有自己的 prompt 和工具，独立 context
```

**这就是 Claude Code 的 Task 工具的模式**（详见 [subagent-patterns.md](subagent-patterns.md)）。

**什么时候升级到这里**：
- 某个子任务需要**独立的长上下文**（比如"读完这 50 个文件做总结"）
- 某个子任务需要**完全不同的 system prompt**（比如"严格 code reviewer"）
- 某个子任务可以**并行**（多个独立检索）

### 阶段 2：固定流水线多 Agent

```
[Agent A] → [Agent B] → [Agent C]
   研究       写作        审校
```

**什么时候升级**：
- 流程**真的固定**，每次都是这几步
- 每一步**职责差异大**（研究 vs 写作 vs 审校的 prompt/模型/工具都不同）
- 中间结果**有价值单独看**（用户想看"研究产出"，不只是"最终报告"）

**框架选择**：CrewAI Sequential / LangGraph 线性 / 自己写都行，差别不大。

### 阶段 3：流程式多 Agent + 状态机

```
        [Router]
       /    |    \
   [A]    [B]    [C]
    |      |      |
    └──→ [Aggregator]
```

**什么时候升级**：
- 需要**条件分支**（不是每次都跑所有 Agent）
- 需要**HITL / Checkpoint**（长任务、可中断）
- 需要**错误恢复**（某个 Agent 失败要重试或走备选）

**框架选择**：**LangGraph**。这是 LangGraph 的核心战场。详见 [../production/langgraph-checkpoint-and-hitl.md](../production/langgraph-checkpoint-and-hitl.md)。

### 阶段 4：对话式 / 协作式多 Agent

```
[Agent A] ⇄ [Agent B] ⇄ [Agent C]
       (互相 challenge / 辩论)
```

**什么时候升级**（很少）：
- 任务本质是**探索性**的，没有固定流程
- 真的需要"对抗"或"辩论"提升质量
- 你能接受**高 token 成本和长延迟**

**框架选择**：AutoGen 0.4。

### 阶段 5：分布式多 Agent

```
机器1: [Agent A]      机器2: [Agent B]
        └──── 消息总线 ────┘
```

**什么时候升级**（极少）：
- **沙箱隔离**（不同 Agent 必须跑在不同环境）
- **合规隔离**（数据不能跨域）
- **资源隔离**（某个 Agent 用大模型 GPU，另一个 CPU 即可）

**框架选择**：AutoGen 0.4 + GrpcWorker，或者直接自己写。

---

## 九、黄金法则总结

> **每升一级，都要先证明上一级真的不够。**

不是"我有钱所以上多 Agent"，是"我证明了单 Agent 真的解决不了这个问题"。

判断你是否真需要多 Agent 的**三个硬指标**：

1. **上下文隔离**：是否真的有信息**不该被其他 Agent 看到**？（隐私、prompt 简洁、防 role-play 污染）
2. **并行加速**：是否有**独立可并行**的子任务？（关键词：独立——有依赖的不算）
3. **专精模型**：是否不同子任务**值得用不同模型/不同 prompt**？（小模型省钱、大模型保质量）

**三个都不满足 → 你不需要多 Agent。**

---

## 十、三个常被忽略的真相

### 真相 1：很多"多 Agent"用单 Agent 就够

工具调用 + 子提示（subagent prompt）+ 路由器，**80% 的"多 Agent"诉求都能用一个 Agent 解决**。先想清楚是不是真的需要多个独立的 LLM 上下文。

### 真相 2：多 Agent 不会让答案更聪明

研究显示：**5 个 GPT-4o Agent 群聊解决问题的能力 ≈ 1 个 GPT-4o 用 CoT**。但 **token 消耗是 5-10 倍**。多 Agent 的价值在于**专精 + 并行 + 上下文隔离**，不在于"集体智慧"。

### 真相 3：生产级多 Agent 系统都自己造

真正跑大规模的（Anthropic 的 Multi-Agent Research、Cognition 的 Devin），**都不用上面这些框架**——他们自己写。框架的价值在于**快速 POC 和中等规模的产品**。

---

## 十一、关键提醒

如果你的实际场景是：
- **多 Agent + 复杂状态 + HITL** → 直接 LangGraph，把每个节点当作"Agent"，比上面三个都更可控
- **单 Agent + 多工具 + 流程清晰** → Pydantic AI，别强行多 Agent
- **真的需要 Agent 互相对话** → 才考虑 AutoGen

---

## 十二、扩展阅读

- [subagent-patterns.md](subagent-patterns.md) —— Claude Code Task / CrewAI Crew / LangGraph Subgraph 三种"派子任务"机制的本质区别
- [../production/langgraph-checkpoint-and-hitl.md](../production/langgraph-checkpoint-and-hitl.md) —— LangGraph 的状态持久化和人工介入
- [../production/frameworks-landscape.md](../production/frameworks-landscape.md) —— 主流 Agent 框架全景
- [react-and-variants.md](react-and-variants.md) —— ReAct / Plan-and-Execute 等基础范式
