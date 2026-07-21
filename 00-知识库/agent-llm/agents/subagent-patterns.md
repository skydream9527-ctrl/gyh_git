# 派子任务的三种机制：Task vs Crew vs Subgraph

> Claude Code 的 Task 工具、CrewAI 的 Crew、LangGraph 的 Subgraph——三者看起来都是"在主流程里嵌一个子流程"，但**心智模型完全不同**。本文剖析它们的本质差异、各自的杀手级场景、以及落地时的关键陷阱。

---

## 一、把三者放在同一坐标系下

```
                                  Task 工具         Crew                Subgraph
                                  (Claude Code)    (CrewAI)            (LangGraph)
─────────────────────────────────────────────────────────────────────────────────
本质                              函数调用          独立工作单元         嵌入式状态机
心智模型                          "派外援"          "整组团队干活"       "内部子流程"
状态                              无（fire-forget）  内部状态，外部不可见  与父图共享 state
返回                              文本结果          文本/结构化结果      完整 state 更新
父级控制                          只能等结果        只能等结果           可中断、可介入
关系                              主从              黑盒外包             嵌套合作
```

**一句话总结**：
- **Task** = "派一个**临时工**去办件事，回来交一份报告"
- **Crew** = "外包给一个**独立团队**，他们内部怎么干你不管，最后给你交付物"
- **Subgraph** = "在你的**家里**开一间子工作室，状态和你共享，你随时能进去打断"

---

## 二、Claude Code 的 Task 工具 —— "函数调用式 Agent"

### 1. 它到底是什么

**一个工具调用**。主 Agent 调用 Task 工具，参数是 `{description, prompt, subagent_type}`，返回值是子 Agent 跑完后的最终文本。

```
主 Agent
   └─ Task(prompt="找出所有用了 deprecated API 的地方")
              ↓
       子 Agent（全新 context，独立 LLM session）
       工作 5-50 步
              ↓
       返回：一段文本结果
```

### 2. 关键特征

**a) 完全隔离的上下文**
- 子 Agent 的 system prompt、工具集、历史**完全独立**
- 主 Agent 看不到子 Agent 内部的中间步骤
- 子 Agent 也看不到主 Agent 的历史

**b) 单向通信**
- 输入：一次性 prompt
- 输出：一次性文本
- **中途没有任何交互**——主 Agent 派出去就只能等

**c) 子 Agent 类型可选**
- `general-purpose`：通用
- `Explore`：只读搜索（轻量、便宜）
- `Plan`：规划专家
- 各种自定义专家

**d) 没有持久状态**
- Task 跑完就结束，**所有中间状态丢失**
- 主 Agent 只拿到最终结论
- 想"再追问一次"？只能再开一个新 Task

### 3. 心智模型：派遣外援

就像你让一个实习生去查资料：
- 你告诉他要查什么（prompt）
- 你不关心他怎么查（独立 context）
- 你只要一份报告（返回文本）
- 报告交完，他就走了（无状态）

### 4. 为什么这个设计能跑长任务

**核心洞察**：主 Agent 的上下文是稀缺资源。

如果主 Agent 自己去读 50 个文件，**上下文会被中间过程撑爆**——文件内容、grep 结果、错误日志全都涌进来。

派一个 Task 出去，**只有最终结论回到主 Agent**：
```
主 Agent context:
  - 用户原始问题
  - "我派了 Task 去查"
  - Task 返回："找到 8 处使用了 X，分别在 a.py:10, b.py:20..."

中间那 50 个文件的内容、几百次 grep？全都在子 Agent 的 context 里，
子 Agent 一结束就被丢弃。
```

**这是 Claude Code 能跑跨小时长任务的根本原因。**

### 5. 自定义 subagent_type：定义自己的专家

`general-purpose` / `Explore` / `Plan` 这些**不是 hardcode 的**——它们是配置出来的，你也能配。

#### Agent 定义文件

放在 `.claude/agents/<name>.md` 或 `~/.claude/agents/<name>.md`：

```markdown
---
name: db-migration-reviewer
description: Reviews database migration files for safety. Use when user asks to review schema changes, migrations, or DDL files.
tools: Read, Grep, Glob, Bash
model: opus
---

You are a database migration safety reviewer.

When invoked, you will be given a path to a migration file or directory.

Your responsibilities:
1. Read the migration file(s)
2. Identify operations that are unsafe under concurrent writes:
   - Adding NOT NULL columns to large tables without defaults
   - Dropping indexes during traffic
   - Renaming columns (breaks live readers)
   - ALTER TABLE on tables > 10M rows without batching
3. For each issue, report:
   - File and line number
   - Severity (critical / high / medium / low)
   - Concrete remediation suggestion
4. Output a structured markdown report

Do NOT modify any files. Read-only review.
End with: "REVIEW COMPLETE: <N> critical, <M> high, ..."
```

#### 字段的关键意义

**`name`（必填）**：调用时的 `subagent_type` 值。**kebab-case，全局唯一**。

**`description`（最关键，决定调度质量）**

主 Agent 看到的"这个专家是干什么的"。**主 Agent 用 description 决定要不要派他**——写得不好，主 Agent 永远不会调你。

好 description 三要素：
- **能力**：能做什么
- **触发条件**：什么时候该用
- **边界**：什么时候**不该**用（避免抢活）

反例：
> "A helpful agent for code tasks."

正例：
> "Reviews database migration files for safety. Use when user asks to review schema changes, migrations, or DDL files. Do NOT use for general code review (use code-reviewer agent instead)."

**`tools`（可选，但用好它能省巨多 token）**

如果不写，子 Agent 继承所有工具。但你应该**显式裁剪**：

```yaml
tools: Read, Grep, Glob              # 只读分析专家
tools: Read, Edit, Write, Bash       # 可改代码的专家
tools: WebFetch, WebSearch           # 网络搜索专家
```

**为什么裁剪很重要**：
1. 工具列表也占 system prompt token——5 个工具的子 Agent 比 25 个工具的快和便宜
2. **限制能力 = 防止跑偏**——只读 Agent 永远不会意外修改文件

**`model`（可选）**

不写继承父级。**这是性价比杠杆**：

```yaml
model: haiku    # 简单分类、提取、格式化任务
model: sonnet   # 大部分通用任务
model: opus     # 复杂推理、关键审查
```

实战：让 grader / classifier / extractor 类专家用 haiku，**成本降 10 倍，质量几乎不变**。

#### System Prompt 部分的写法心法

frontmatter 之后的 markdown 是子 Agent 的 system prompt。**和主 Agent 的 prompt 写法不同**——它是一个"工具被调用时的执行说明书"。

**5 个高质量 system prompt 的模式**：

**模式 1：明确单一职责**
```
You are X. You ONLY do Y. If asked to do Z, say "out of scope".
```

**模式 2：明确输入契约**
```
When invoked, you will be given:
- A file path (string)
- An optional severity threshold (one of: critical/high/medium)
```

**模式 3：明确输出契约（极重要）**
```
End with a structured summary block:
---
SUMMARY:
- Issues found: <N>
- Severity breakdown: <crit>/<high>/<med>/<low>
- Recommended action: <text>
---
```

子 Agent 返回的是文本，主 Agent 要解析。**没有结构化结尾，主 Agent 经常误解结果**。

**模式 4：明确禁止行为**
```
Do NOT:
- Modify any files (read-only)
- Spawn additional Task subagents
- Make external network calls
- Continue if input file > 10MB (report error and stop)
```

子 Agent 也能调 Task 工具——**禁止递归是常见安全要求**。

**模式 5：明确终止条件**
```
Stop when ANY of:
- All files in the target directory have been reviewed
- 50 issues have been logged (avoid runaway)
- A critical structural error is found (report and abort)
```

#### 实战案例：典型自定义专家组合

**a) `code-reviewer`**
```yaml
tools: Read, Grep, Bash
model: sonnet
```
找 bug、风格问题、安全漏洞。Bash 给它跑 linter。

**b) `security-auditor`**
```yaml
tools: Read, Grep, Glob, Bash, WebFetch
model: opus
```
模型用 opus（高质量），WebFetch 让它查 CVE 数据库。

**c) `test-writer`**
```yaml
tools: Read, Edit, Write, Bash
model: sonnet
```
能写测试、能跑测试看通不通过。

**d) `incident-investigator`**
```yaml
tools: Read, Grep, Bash
model: opus
```
读日志、跑 diagnostic 命令、给假设。**禁止 Edit/Write**——只调查不动手。

**e) `summarizer-cheap`**
```yaml
tools: Read
model: haiku
```
只做总结，便宜。主 Agent 派几十个并行总结，成本可控。

#### 调度行为的几个隐藏机制

**a) 主 Agent 是看 description 选 agent 的**

如果你定义了三个 agent，description 都很模糊，主 Agent 会随机选一个或者全用 `general-purpose`。**description 是排序信号**。

**b) 子 Agent 不能看到对话历史**

子 Agent 收到的只有 prompt 字段。主 Agent 必须在 prompt 里**自包含所有必要上下文**——文件路径、约束、之前发现的内容。

> "Brief the agent like a smart colleague who just walked into the room."（系统 prompt 原话）

**c) 并行 Task 是一个 message 里多个 Task 调用**

```
主 Agent 一次输出多个 Task 工具调用 → 并行执行
主 Agent 输出一个 Task → 等结果 → 输出下一个 Task → 串行
```

**性能差异巨大**——独立子任务**永远要并行调度**。

### 6. 局限

- **不能交互**：派出去就只能等
- **不能 streaming 干预**：子 Agent 跑歪了你也不知道
- **不适合需要往返讨论的场景**

---

## 三、CrewAI 的 Crew —— "独立工作单元"

### 1. 它到底是什么

一个 `Crew` 是 **agents + tasks + process** 的打包。`crew.kickoff()` 是一次完整的执行。

```python
crew = Crew(
    agents=[researcher, writer, reviewer],
    tasks=[task1, task2, task3],
    process=Process.sequential,
)
result = crew.kickoff(inputs={"topic": "AI Agent"})
```

### 2. 在 Flow 里的角色

```python
class MyFlow(Flow[State]):
    @listen("start")
    def do_research(self, _):
        # 一个 Crew 作为一个 Flow 步骤
        research = ResearchCrew().crew().kickoff(inputs={...})
        self.state.research = str(research)
```

### 3. 关键特征

**a) 内部黑盒**
- Crew 内部的 agents 怎么协作，外部完全看不到
- 你能控制的只有 inputs 和 outputs
- task 之间的中间结果在 Crew 内部传递

**b) 独立的"团队语境"**
- 每个 agent 有 role / goal / backstory
- agents 之间的协作语境是 Crew 内部的
- 出了 Crew，这些都不存在

**c) 一次性执行**
- `kickoff()` 是阻塞的
- 中途不能介入
- 没有 checkpoint（Flows 层有，但 Crew 本身没有）

**d) 强叙事化**
- "你是资深市场分析师，10 年经验..."
- task description 是自然语言
- **不强调状态和数据流，强调角色和目标**

### 4. 心智模型：外包独立团队

就像你把一个项目外包给广告公司：
- 你给需求（inputs）
- 他们内部 PM、文案、设计师怎么协作你不管（黑盒）
- 你拿到交付物（outputs）
- 中途想插话？不行，等他们交稿

### 5. Crew vs Task 工具

表面相似（都是黑盒外包），本质区别：

| | Task 工具 | Crew |
|---|---|---|
| 内部是 | **一个** Agent | **多个** Agent |
| 协作语境 | 无（单飞） | 有（role-play 团队） |
| 复用性 | prompt 即定义 | 类化、可配置、可复用 |
| 适合任务 | 单点深挖 | 需要多角色协作的产出 |

**Task = 派一个外援**
**Crew = 外包一支团队**

---

## 四、LangGraph 的 Subgraph —— "嵌入式状态机"

### 1. 它到底是什么

**一个 graph 嵌进另一个 graph 的某个节点**。

```python
# 子图
subgraph_builder = StateGraph(SubState)
subgraph_builder.add_node("step1", ...)
subgraph_builder.add_node("step2", ...)
subgraph = subgraph_builder.compile()

# 父图
parent = StateGraph(ParentState)
parent.add_node("preprocess", preprocess)
parent.add_node("complex_logic", subgraph)  # 子图当作节点
parent.add_node("postprocess", postprocess)
```

### 2. 关键特征

#### a) 状态可以共享

**模式 1：共享 schema**（state 字段相同/有交集）
```python
class ParentState(TypedDict):
    messages: list
    user: str

class SubState(TypedDict):
    messages: list  # 共享！
```

子图执行时，`messages` 字段是和父图同一份；子图修改了，父图能看到。

**模式 2：独立 schema + 显式映射**
```python
def call_subgraph(state: ParentState):
    sub_input = {"query": state["messages"][-1]}
    sub_result = subgraph.invoke(sub_input)
    return {"messages": state["messages"] + [sub_result["answer"]]}

parent.add_node("subcall", call_subgraph)
```

#### b) Checkpoint 透传

父图的 checkpointer **同时管理子图的状态**。子图中断，父图也能从中断点恢复。

```
checkpoint 表里：
  thread_id     | checkpoint_ns       | step
  task-001      | ""                  | parent step 3
  task-001      | "subgraph:abc"      | subgraph step 5  ← 子图状态
```

`checkpoint_ns` 字段就是用来区分子图命名空间的。

#### c) HITL 可以发生在子图内部

子图里某个节点 `interrupt()` —— 父图也会暂停。从父图的角度看：
```python
result = parent.invoke({...}, config=config)
# result.__interrupt__ 包含子图里抛出的 interrupt
# 父图状态停在"调用子图"的那个节点
```

恢复时：
```python
parent.invoke(Command(resume=...), config=config)
# 子图从内部断点继续
```

#### d) 可以反复进入子图

子图不是"一次性外包"，**它是父图流程的一部分**：
- 可以被循环调用
- 可以被条件分支跳过
- 可以多个父图节点都调用同一个子图

### 3. 心智模型：嵌套的工作室

就像在你的工厂里，**专门划出一片车间**做某道工序：
- 共享同一个仓库（state）
- 你随时可以走进去看（checkpoint 可见）
- 工序中途要审批？暂停整条线，等你批了继续（HITL）
- 这道工序可以多次走（循环调用）

### 4. State Schema 设计的 7 大陷阱

这是真正会让生产事故发生的地方。

#### 陷阱 1：State 字段名冲突（最常见）

**问题场景**：

父图和子图都有 `messages` 字段，但**含义不同**。

```python
class ParentState(TypedDict):
    messages: Annotated[list, add]  # 用户对话历史

class SubState(TypedDict):
    messages: Annotated[list, add]  # 子任务内部的工具调用消息
```

子图直接当节点用：
```python
parent.add_node("subtask", subgraph)
```

LangGraph 看到字段名相同，**自动透传**——子图把内部工具消息塞进了用户对话历史。**用户聊天记录被污染**。

**正确做法**：

要么**改名**：
```python
class SubState(TypedDict):
    sub_messages: Annotated[list, add]  # 完全独立的字段
```

要么**用包装函数**显式映射：
```python
def call_sub(state: ParentState):
    sub_input = {"messages": [state["messages"][-1]]}  # 只传最后一条
    sub_result = subgraph.invoke(sub_input)
    return {"answer": sub_result["final_answer"]}  # 只取需要的输出

parent.add_node("subtask", call_sub)
```

**经验**：**默认用包装函数**，除非你 100% 确定要共享。直接当节点透传是隐式契约，太脆弱。

#### 陷阱 2：Reducer 选错

State 字段的 Reducer 决定**多次写入怎么合并**：

```python
from operator import add
from typing import Annotated

class State(TypedDict):
    messages: Annotated[list, add]      # 累积（追加）
    user_id: str                         # 默认（覆盖）
    counter: Annotated[int, lambda a,b: a+b]  # 累加
```

**子图里的 Reducer 行为不直观**：

子图执行完，把整个 SubState 返回给父图。如果父图字段是"覆盖"reducer，**子图算的累积值会被替换为子图的值**。

```python
# 父图状态: counter=5
# 子图执行：内部把 counter 改成 3
# 子图返回后，父图 counter = 3 还是 8？
```

如果两边都是 `add`：父图 counter = 5+3 = 8
如果父图是默认覆盖：父图 counter = 3

**子图里的 reducer 优先级要和父图一致**——否则计数器、消息列表会出现幽灵 bug。

**经验**：写个测试，故意让父子图在同一字段上各 +1，断言最终值是 2。

#### 陷阱 3：`add_messages` reducer 的去重幻觉

```python
from langgraph.graph.message import add_messages

class State(TypedDict):
    messages: Annotated[list, add_messages]
```

`add_messages` 比 `operator.add` 智能：**根据 message id 去重 / 替换**。

**陷阱**：子图里生成的 message 没有显式 id → LangGraph 自动生成 → 父图收到时被当作新 message 追加，**没有去重效果**。

```python
# 你以为：子图返回相同 id 的 message → 替换
# 实际：子图每次跑都生成新 id → 全追加 → messages 列表无限增长
```

**正确做法**：在子图节点里**显式设置 message id**：

```python
def sub_node(state):
    msg = AIMessage(content="...", id="sub-step-1")  # 固定 id
    return {"messages": [msg]}
```

或者**在父图入口清理**：

```python
def reset_node(state):
    return {"messages": [m for m in state["messages"] if not m.id.startswith("sub-")]}
```

#### 陷阱 4：Checkpoint Namespace 没规划

子图的 checkpoint 落在 `checkpoint_ns = "subgraph_name:task_id"` 下。

**问题**：

```python
# 同一个 thread 跑两次同名 subgraph
parent.invoke(..., config={"configurable": {"thread_id": "t1"}})
# 第一次：checkpoint_ns = "audit_sub:abc"
# 第二次：checkpoint_ns = "audit_sub:def" ← 不同的 task_id

# 但你想"恢复第一次的执行"...
# 怎么知道 task_id 是 abc 还是 def？
```

LangGraph 会自动管理这个，**但当你想 time travel 或手动恢复时**，namespace 字符串就成了关键。

**正确做法**：

a) 不要在多个父图分支里调用同一个子图 instance（除非你接受它们独立追踪）
b) 需要追踪时，用 `state.get_state_history(config, subgraphs=True)` 拿全部历史
c) 复杂场景：把 task_id 持久化到业务表，关联起来

#### 陷阱 5：子图里的 `interrupt()` 让父图状态半挂

子图 step 3 抛 interrupt，整个执行暂停。父图看到的状态：
- 父图节点"call_sub"还在 running
- 子图状态在中间
- **父图其他字段没更新**

**陷阱**：你以为父图 `state.values["sub_result"]` 已经被填了——没有，因为子图没跑完。

**判断技巧**：拿到 state 后看 `state.next`：
```python
state = app.get_state(config)
print(state.next)  # ('subtask',) 表示卡在这个节点
print(state.tasks)  # 看具体 task 的 interrupt 信息
```

**不要假设字段已被更新**——只有跑完的节点才更新父 state。

#### 陷阱 6：循环引用 / 大对象 State

子图里把整个 DataFrame、整个文件内容塞进 state：

```python
class SubState(TypedDict):
    raw_data: pd.DataFrame  # 100MB
    embeddings: np.ndarray  # 50MB
```

**后果**：
- Postgres checkpoint 表每个节点写一次 = 灾难
- 父图字段如果共享，主 thread 也膨胀
- 序列化失败（DataFrame 默认不可 pickle 安全）

**正确做法**：

State 里只放**引用**：
```python
class SubState(TypedDict):
    data_uri: str        # s3://... 或 redis://...
    embeddings_key: str
```

数据存对象存储 / Redis，state 只存 ID。

#### 陷阱 7：State Schema 的"局部覆盖"误解

LangGraph 的节点返回值是**部分更新**，不是完整 state：

```python
def my_node(state):
    return {"answer": "hello"}  # 只更新 answer 字段
    # 其他字段不变（除非 reducer 让它们变）
```

**子图里很多人以为**："我返回完整 SubState 字典 = 替换整个 state"——错。返回的还是**部分更新**，按 reducer 合并。

**特别坑**：

```python
class SubState(TypedDict):
    items: list  # 默认覆盖 reducer

def sub_node(state):
    new_items = process(state["items"])
    return {"items": new_items}  # 你以为：替换
```

如果 items 字段的 reducer 是 `add`（继承自父图），new_items 会被**追加**而不是**替换**——结果列表越跑越长。

**正确做法**：每个字段的 reducer **必须显式声明**，不要依赖默认行为。设计 SubState 时**画一张表**：

| 字段 | 类型 | Reducer | 与父图关系 |
|---|---|---|---|
| messages | list | add_messages | 共享 |
| temp_data | dict | 覆盖 | 子图私有 |
| counter | int | add | 共享累加 |

### 5. State Schema 设计 5 步法

```
1. 列出子图需要读取的父图字段 → 决定哪些字段必须存在于 SubState
2. 列出子图需要写回父图的字段 → 决定哪些字段必须有匹配的 reducer
3. 列出子图私有字段 → 起独立的名字，避免冲突
4. 大对象 → 全部改为引用（URI/key）
5. 写测试：故意让父子图同时写一个共享字段，验证最终值符合预期
```

### 6. Subgraph vs Task / Crew

| | Task 工具 | Crew | Subgraph |
|---|---|---|---|
| 上下文 | 完全隔离 | 边界可见（inputs/outputs） | 可以共享 state |
| 中断 | 不能 | 不能 | 内部可以 interrupt |
| 状态 | 无 | 内部黑盒 | 有，可持久化 |
| 主级介入 | 不能 | 不能 | 可以 HITL 进入子图 |
| 适合 | 一次性深挖 | 角色协作 | 复杂业务流的模块化 |

---

## 五、最关键的差异：信息流模型

```
Task 工具：
   主 → [一段 prompt] → 子
   主 ← [一段文本]   ← 子
   信息流：单次往返，文本接口

Crew：
   外部 → {inputs dict} → Crew 内部
   外部 ← {output}      ← Crew 内部
   信息流：单次往返，结构化但黑盒

Subgraph：
   父图 ⇄ State 共享/映射 ⇄ 子图
   父图 ⇄ Checkpoint 共享 ⇄ 子图
   父图 ⇄ Interrupt 透传 ⇄ 子图
   信息流：持续双向，状态级耦合
```

这个差异决定了它们的根本能力边界。

---

## 六、用一个具体场景看三者怎么写

**场景**：用户问"分析一下我们 repo 的代码质量"。流程是：扫描代码 → 评估 → 出报告。

### Task 工具风格（Claude Code）

```
主 Agent 决定：
  1. Task("Explore 子 Agent: 列出所有源文件，识别核心模块")
       → 返回："核心模块在 src/api, src/db, src/utils"
  2. Task("代码审查子 Agent: 扫描 src/api 的代码质量问题")
       → 返回："发现 12 个问题：..."
  3. Task("代码审查子 Agent: 扫描 src/db ...")
       → 返回："发现 5 个问题：..."
  4. 主 Agent 自己整合写报告
```

**特点**：主 Agent 自己当协调者，每次派一个 Task 去深挖。**简单、直接、上下文友好**。

### Crew 风格（CrewAI）

```python
class CodeQualityCrew:
    scanner = Agent(role="代码扫描员", goal="找出代码气味", ...)
    auditor = Agent(role="代码审查专家", goal="评估严重性", ...)
    reporter = Agent(role="技术写手", goal="写可读报告", ...)

    task1 = Task(description="扫描 repo", agent=scanner)
    task2 = Task(description="审查问题", agent=auditor, context=[task1])
    task3 = Task(description="出报告", agent=reporter, context=[task2])

    crew = Crew(agents=[...], tasks=[...], process=Process.sequential)

result = CodeQualityCrew().crew().kickoff(inputs={"repo": "..."})
```

**特点**：**职责分明、模板化**。但中途不能介入，跑歪了只能重来。

### Subgraph 风格（LangGraph）

```python
class State(TypedDict):
    files: list
    issues: list
    severity: dict
    report: str
    needs_review: bool  # HITL 标记

# 审计子图（可复用）
audit_sub = StateGraph(State)
audit_sub.add_node("scan", scan_node)
audit_sub.add_node("classify", classify_node)
audit_sub.add_node("human_review", human_review_node)  # interrupt 在这里
audit_sub.add_conditional_edges(
    "classify",
    lambda s: "human_review" if s["needs_review"] else END,
)
audit_subgraph = audit_sub.compile()

# 主图
parent = StateGraph(State)
parent.add_node("prep", prep_node)
parent.add_node("audit", audit_subgraph)  # 子图作为节点
parent.add_node("report", report_node)
parent.add_edge("prep", "audit")
parent.add_edge("audit", "report")

app = parent.compile(checkpointer=postgres_saver)
```

**特点**：
- 严重问题触发 HITL，**主流程暂停等人**
- Postgres checkpoint 持久化，**断电也能恢复**
- 子图可以被复用（其他流程也可以调用 `audit_subgraph`）

---

## 七、三者各自的"杀手级场景"

### Task 工具：长任务的上下文管理

**只有它能解决**：主 Agent context 不被淹没。

举例：你让 Claude Code 改一个跨 30 个文件的重构。如果主 Agent 自己读所有文件，几万 token 直接塞满。用 Task 派出去深挖，主 Agent 只拿结论 → **可以跑几小时几百步**。

### Crew：人设化的内容生产线

**只有它**做"角色协作"做得这么自然。

举例：内容运营让 AI 团队"调研 → 写稿 → 校对"。用 Crew 配 3 个 role，业务方改 YAML 就能调整团队结构，**不用找工程师**。

### Subgraph：可审计的复杂业务流

**只有它**能做"嵌套的、可中断、可审计、有状态"。

举例：贷款审批，外层是"申请 → 风控 → 审批 → 放款"，风控内部又是"反欺诈检测 → 信用评估 → 人工复核"。每一层都要能中断、能恢复、能让人介入、能事后审计。**LangGraph 的 subgraph + checkpoint 是唯一能优雅做出来的方案**。

---

## 八、误用警示

### 误用 1：用 Task 做需要往返讨论的事

❌ "我让一个 Task Agent 当用户对话，主 Agent 当后端"——做不到，Task 不能持续对话。

### 误用 2：用 Crew 做需要工程级控制的事

❌ "用 Crew 做支付审批流"——黑盒、不可中断、不可审计、出错只能重来。**生产事故警告**。

### 误用 3：用 Subgraph 做简单的"一次外援"

❌ "我只是想让另一个 prompt 处理一下这段文本，就用 subgraph"——杀鸡用牛刀，state schema 设计成本远超收益。**用一个 LLM call 就够了**。

### 误用 4：用 Subgraph 模拟 Task 的"上下文隔离"

❌ "我希望子图不影响父图状态，所以我用完全独立的 schema"——你需要的不是 subgraph，是**普通的工具调用**或 Task 模式。Subgraph 的核心价值就是"共享 + 透传"，不要它就别用 subgraph。

---

## 九、心智模型记忆口诀

> **Task 是函数，Crew 是模块，Subgraph 是子流程。**

- 函数调用 → Task：进去一个 prompt，出来一个 string
- 模块调用 → Crew：进去一个 dict，出来一个 dict，内部封装好
- 子流程 → Subgraph：和父流程共享变量、共享存储、共享中断机制

如果你写过传统软件：
- **Task ≈ 一次 RPC 调用**
- **Crew ≈ 一个微服务**
- **Subgraph ≈ 一个嵌套函数（共享闭包）**

---

## 十、统一启示

"派子任务"的设计，本质是在权衡 4 个维度：

| 维度 | Task 工具 | Subgraph | Crew 嵌套 |
|---|---|---|---|
| 上下文隔离 | 强（完全隔离） | 弱（共享 state） | 中（inputs/outputs） |
| 父级控制 | 弱（fire-forget） | 强（HITL 透传） | 中（Flow 控制） |
| 状态可见性 | 无 | 完整 | 边界可见 |
| 失败恢复 | 重跑整个 Task | Checkpoint 恢复 | Flow 层捕获 |

**没有银弹**——选哪个取决于你需要哪两个维度。

如果你的子任务：
- **需要彻底隔离父级 context** → Task 工具
- **需要父级随时介入和审计** → Subgraph
- **需要团队角色协作** → Crew + Flow

---

## 十一、扩展阅读

- [multi-agent-frameworks.md](multi-agent-frameworks.md) —— AutoGen / CrewAI / Agents SDK 的协作模式深度对比
- [../production/langgraph-checkpoint-and-hitl.md](../production/langgraph-checkpoint-and-hitl.md) —— LangGraph checkpoint 表结构、HITL 落地
- [react-and-variants.md](react-and-variants.md) —— ReAct 等基础范式
