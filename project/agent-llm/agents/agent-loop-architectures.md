# Agent 循环架构对比：感知-行动循环 vs 状态机循环

> 不同的 Agent 在底层有完全不同的"循环结构"。本文剖析三种主流循环——**感知-行动循环**（OpenClaw / Computer Use / Browser-Use 这一类屏幕/浏览器 Agent）、**状态机循环**（LangGraph）、**ReAct 循环**——的本质差异，以及在什么场景下选哪种。
>
> 配套：[react-and-variants.md](react-and-variants.md)、[long-task-agents.md](long-task-agents.md)、[../tools-protocols/browser-automation.md](../tools-protocols/browser-automation.md)。

---

## 一、循环结构是 Agent 的"脊椎"

很多人对比 Agent 框架时只比"功能"，忽略了**底层循环结构本身的差异**。

底层循环决定：
- Agent 的**输入是什么**（屏幕？state？观察？）
- 决策的**频率**（每个像素一次？每个节点一次？）
- 错误恢复的**方式**（重新看屏幕？重置 state？）
- 性能特性（延迟、成本、并发）

**选错循环 = 后期所有优化都是补丁**。

---

## 二、三种主流循环

```
循环 1：感知-行动循环（Perception-Action Loop）
  Screenshot → LLM(看图) → 输出动作 → 执行 → Screenshot → ...
  代表：OpenClaw、Anthropic Computer Use、Browser-Use、Skyvern

循环 2：状态机循环（State Machine Loop）
  State → Node(函数) → State 变更 → 条件边 → 下一个 Node
  代表：LangGraph

循环 3：ReAct 循环（Thought-Action-Observation）
  Thought → Action → Observation → Thought → ...
  代表：经典 LangChain Agent、AutoGPT、大多数早期 Agent
```

每种循环背后有不同的**心智模型**——理解了心智模型，框架选型就不会跑偏。

---

## 三、循环 1：感知-行动循环（OpenClaw 类）

### 1. 它到底在做什么

```
┌────────────────────────────────────────────────┐
│  while not done:                               │
│      screenshot = capture()                     │
│      action = LLM(prompt + screenshot)          │
│      execute(action)                            │
│      done = check_completion()                  │
└────────────────────────────────────────────────┘
```

**特点**：
- 输入是**像素**（或 DOM 树，对 Browser-Use 这类）
- 输出是**固定动作集**（mouse_click(x,y) / type / scroll / key_press）
- 每一步都重新"看一眼"屏幕

### 2. 核心心智模型："Agent 像一个有眼睛和手的人"

不需要为每个网站写脚本——Agent 像人类一样**看着屏幕做决定**。

任务："去 Bloomberg 查 Apple 股价图"，Agent 的内部思考：
```
看截图 → "我看到 Bloomberg 主页有个搜索框"
       → 输出：mouse_click(347, 128)（点搜索框）
看新截图 → "搜索框激活了，我需要输入"
       → 输出：type_text("AAPL")
看新截图 → "出现了下拉建议"
       → 输出：mouse_click(下拉项坐标)
...
```

### 3. 关键架构决策

#### a) 视觉分辨率

每张截图都要喂 LLM。分辨率高 = 信息全 = token 贵。

```
1920×1080 截图 ≈ 2400 token
4K 截图 ≈ 8000 token
低分辨率（缩放后）≈ 800 token，但小元素看不清
```

**实战**：缩放到 1280×800 是性价比最优区间。

#### b) 动作空间设计

Computer Use 的动作集（公开的）：
```
mouse_move(x, y)
left_click(x, y)
right_click(x, y)
double_click(x, y)
type_text(text)
key_press(key)         # "enter", "tab", "ctrl+c"
scroll(direction, amount)
screenshot()           # 主动截图
```

**为什么这样设计**：
- 跟人类动作 1:1 对应（迁移性最好）
- 原子操作，不复合（可组合性强）
- 故意不暴露 DOM API（保持 vision-only 心智）

#### c) 历史管理

每次决策都要看截图历史还是只看当前？

```
方案 A：只看当前 screenshot
  ✅ context 短
  ❌ 不知道"我刚才做了什么、为什么"

方案 B：看 N 个 screenshot 历史
  ✅ 有上下文
  ❌ context 爆炸（每张图 2000 token）

方案 C：当前 screenshot + 文字 history
  ✅ 平衡
  → 主流方案
```

OpenClaw / Computer Use 都用方案 C：当前截图 + 之前 K 步的动作描述。

### 4. 失败模式

| 失败 | 原因 |
|---|---|
| 点错坐标 | 视觉模型坐标推断不准 |
| 误读数字 | 小字体 / 模糊截图 OCR 失败 |
| 卡循环 | 一直点同一个不响应的按钮 |
| Captcha 卡死 | 没有人工兜底 |
| 状态丢失 | Agent 不知道"我刚才做完什么了" |

### 5. 适合场景

✅ GUI-only 任务（没有 API 的老 SaaS）
✅ 跨应用流程（浏览器 + Excel + Notion）
✅ 不可控目标（网站随时改版、动态内容）
✅ 一次性任务（不值得写脚本）

❌ 性能敏感（每步 3-15 秒）
❌ 高频调用（成本爆炸）
❌ 严格可控（概率性输出）

---

## 四、循环 2：状态机循环（LangGraph）

### 1. 它到底在做什么

```python
class State(TypedDict):
    messages: list
    current_step: str
    data: dict

# 不是循环，是图遍历
graph.add_node("planner", plan_fn)
graph.add_node("executor", exec_fn)
graph.add_node("reviewer", review_fn)
graph.add_conditional_edges("executor", should_continue, {
    "yes": "executor",
    "review": "reviewer",
    "end": END,
})

# 实际执行
state = initial_state
while not done:
    next_node = decide_next(state, graph)
    state = next_node(state)        # 节点修改 state
    done = (next_node == END)
```

**特点**：
- 输入是**结构化 State 对象**（TypedDict / Pydantic）
- "动作"是**任意 Python 函数**（不限于 GUI 操作）
- 决策一部分由 LLM 做（在节点里），一部分由**图结构**做（条件边）

### 2. 核心心智模型："Agent 是一个状态机沿着图前进"

不是"让 LLM 决定一切"——你**显式画出**流程图，**只在需要 LLM 判断的地方让 LLM 介入**。

```
[开始] → [planner: 规划] → [search: 调 API] → [judge: LLM 判够不够]
                                                    ↓
                                         不够 ──→ [search] (回去)
                                         够   ──→ [synthesize] → [END]
```

**关键**：图结构是显式的，不是 LLM 学出来的。

### 3. 关键架构决策

#### a) State 是契约

State schema 定义死了**所有节点能读什么、写什么**：

```python
class State(TypedDict):
    messages: Annotated[list, add_messages]    # 累积
    current_phase: str                          # 覆盖
    findings: Annotated[list, add]             # 累积
    user_id: str                                # 不变
```

每个字段的 reducer 决定多次写入怎么合并。**这是 LangGraph 跟 ReAct 最大的差异**——状态是**强类型、显式管理**的。

详见 [subagent-patterns.md](subagent-patterns.md) 第 4 节"State Schema 设计的 7 大陷阱"。

#### b) 节点是黑盒

```python
def my_node(state: State) -> dict:
    # 节点内部可以：
    # - 调 LLM
    # - 调任何 API
    # - 跑 SQL
    # - 调子图
    # - 不调任何东西，纯计算
    return {"field_to_update": new_value}
```

节点**不必是 LLM**。"调 SQL 然后处理结果"也是合法节点。这是 LangGraph 比 ReAct 灵活得多的地方。

#### c) 条件边是确定性的

```python
def route(state: State) -> str:
    if state["budget_used"] > state["budget_limit"]:
        return "stop"
    if not state["findings"]:
        return "search_again"
    return "synthesize"
```

路由函数**不调 LLM**，是普通 Python。意味着流程**完全可预测、可测试**。

#### d) Checkpoint 是一等公民

每个节点跑完，State 自动持久化（Postgres / SQLite / Redis）。**进程崩了重启即恢复**。

详见 [../production/langgraph-checkpoint-and-hitl.md](../production/langgraph-checkpoint-and-hitl.md)。

### 4. 失败模式

| 失败 | 原因 |
|---|---|
| 节点抛异常 | 内部代码 bug 或 API 失败 |
| 死循环 | 条件边逻辑错误，永远不进 END |
| State 字段冲突 | reducer 选错（详见 subagent-patterns 陷阱 2） |
| Checkpoint 表爆 | 没设 TTL |

跟感知-行动循环的失败模式**完全不同**——这里是软件工程的失败模式，不是"AI 行为"的失败模式。

### 5. 适合场景

✅ 业务流程编排（审批、客服、研究）
✅ API + LLM 混合（大部分是调函数，偶尔 LLM 决策）
✅ 要求可审计可恢复（金融、合规）
✅ 多团队协作（流程图大家都能看）

❌ GUI-only 任务（你画不出图）
❌ 完全不可预测的探索（图结构反成束缚）

---

## 五、循环 3：ReAct 循环（经典 Agent）

### 1. 它到底在做什么

```
while not done:
    thought = LLM("基于当前情况我该怎么做？" + history)
    if thought.is_final_answer:
        return thought.answer
    action = LLM("具体调什么工具？" + thought)
    observation = execute(action)
    history.append((thought, action, observation))
```

**特点**：
- 输入是**自然语言历史**（thoughts + actions + observations 串起来）
- "动作"是**工具调用**（Function Calling）
- 决策**完全由 LLM 做**——没有图结构

详见 [react-and-variants.md](react-and-variants.md)。

### 2. 核心心智模型："Agent 自言自语着干活"

```
Thought 1: 我需要先找出张教授去年发的 AI 顶会论文。
Action 1: search_papers(author="张教授", year=2024)
Observation 1: 找到 2 篇...
Thought 2: 现在看第二作者...
Action 2: get_paper_details(id="xxx")
...
```

### 3. 跟前两个的本质差异

| | ReAct | 状态机 | 感知-行动 |
|---|---|---|---|
| 状态形式 | 文本历史 | 结构化对象 | 屏幕像素 |
| 决策者 | 全 LLM | LLM + 图 | 全 LLM |
| 流程是否可见 | 看历史 | 看图 | 看截图 |
| 工程化 | 难 | 容易 | 中等 |

**ReAct 是 LLM-native 的**：你完全相信 LLM 会做对的决定。这在简单任务上够用，复杂任务下问题大：
- 历史变长，模型注意力分散
- 没有"显式状态"，跑歪了找不到原因
- 没有结构化恢复机制

### 4. 现状（2026 视角）

ReAct 在 2022-2023 是主流。**现在主要作为底层范式存在**，新框架很少再用纯 ReAct：
- LangGraph 用状态机包裹 ReAct
- Claude Code 用工具循环 + 显式 TodoWrite 替代纯 ReAct
- 多 Agent 框架（CrewAI / AutoGen）在 ReAct 之上加协作层

详细历史见 [react-and-variants.md](react-and-variants.md)。

---

## 六、三种循环的核心差异表

| 维度 | 感知-行动（OpenClaw 类） | 状态机（LangGraph） | ReAct（经典） |
|---|---|---|---|
| **输入** | 屏幕截图 / DOM | 结构化 State | 文本历史 |
| **动作空间** | 固定（GUI 原语） | 任意函数 | 工具调用 |
| **决策者** | 全 LLM | LLM + 图结构 | 全 LLM |
| **状态表达** | 隐式（在屏幕里） | 显式（TypedDict） | 隐式（在历史里） |
| **可恢复性** | 弱 | **强**（checkpoint） | 弱 |
| **可观测性** | 截图序列 | State 演化 + Trace | 文本历史 |
| **失败模式** | 点错位置 / 误读 | 节点异常 / state 冲突 | 历史漂移 / 死循环 |
| **延迟** | 慢（每步 3-15s） | 快（节点级） | 中等 |
| **成本** | 高（图像 token） | 中等 | 中等 |
| **可控性** | 低 | **高** | 中等 |
| **适合规模** | 单任务 | 生产系统 | 中小型 |

---

## 七、它们其实可以嵌套

最重要的洞察：**这三种循环不是互斥的，可以分层组合**。

### 模式 1：状态机外壳 + 感知-行动末端

```
LangGraph 主图（状态机循环）
   │
   ├── Node 1: scoping（普通 LLM call）
   ├── Node 2: data_fetch_via_api（调 SQL）
   ├── Node 3: visual_chart_extract  ← 这里调 OpenClaw
   │              ↓
   │       OpenClaw 跑感知-行动循环
   │       去 Bloomberg 截股价图，提取数据点
   │              ↓
   │       返回结构化数据
   ├── Node 4: synthesize（LLM）
   └── Node 5: report
```

**为什么这样最优**：
- 主流程清晰可控（LangGraph）
- 只在"必须 GUI"的环节用感知-行动（成本可控）
- 整体可恢复、可审计

### 模式 2：状态机外壳 + ReAct 节点

```
LangGraph 主图
   │
   ├── Node 1: classify
   ├── Node 2: research_react_agent  ← 这里跑 ReAct 子循环
   │              ↓
   │       ReAct Agent 自由探索（适合 open-ended）
   │              ↓
   │       返回结论
   └── Node 3: report
```

**为什么这样**：当某段任务**真的需要 LLM 自由探索**（比如"调研一个我也不知道答案的问题"），ReAct 比状态机更适合。但**外壳还是状态机**，给整体加结构。

### 模式 3：三层嵌套

```
LangGraph 主图（状态机）
   ↓
   某个 ReAct Agent 节点
   ↓
   ReAct 中调用 OpenClaw 工具（感知-行动）
```

实战中**这种三层嵌套并不少见**——每一层选择最合适的循环。

---

## 八、决策框架：选哪种循环

```
你的任务长什么样？
│
├─ "目标清楚、流程能画图、可能要审计"
│   → 状态机循环（LangGraph）
│
├─ "目标清楚、就是要操作 GUI"
│   → 感知-行动循环（OpenClaw / Computer Use）
│
├─ "目标模糊、需要自由探索"
│   ├─ 简单（< 10 步）→ ReAct
│   └─ 复杂（> 10 步）→ 状态机包 ReAct
│
└─ "都有"
    → 嵌套：状态机外壳 + 内部按场景选
```

---

## 九、一个常被忽略的真相

**循环架构的选择决定了你能做什么、做不到什么——但工程实践中很多人只看"框架名字"不看底层循环**。

很多团队选了 LangChain（ReAct 底子）做生产 Agent，发现长任务不可控；
转 LangGraph（状态机）后才发现：**问题不是 LangChain 不好，是 ReAct 循环不适合那种场景**。

同样地：很多团队尝试纯 Computer Use 做"研究 Agent"，发现慢得不能忍——**问题不是 Computer Use 不好，是感知-行动循环本来就不适合"流程清晰"的任务**。

**先选循环，再选框架**。

---

## 十、扩展阅读

- [react-and-variants.md](react-and-variants.md) —— ReAct 循环深度
- [long-task-agents.md](long-task-agents.md) —— 长任务 Agent 的循环选择
- [subagent-patterns.md](subagent-patterns.md) —— 状态机里嵌套子循环
- [../tools-protocols/browser-automation.md](../tools-protocols/browser-automation.md) —— 感知-行动循环的工具实现
- [../production/frameworks-landscape.md](../production/frameworks-landscape.md) —— 各框架的循环架构归类
