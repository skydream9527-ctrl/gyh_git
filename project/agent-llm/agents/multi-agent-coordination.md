# 多 Agent 协调与协商：避免冗余、保证一致

> 本文专注于多 Agent 系统中的"协调机制"：subagent 之间如何避免冗余工作、如何处理冲突、如何同步状态。配合 [multi-agent-frameworks.md](multi-agent-frameworks.md) 看协作框架，本文讲底层协议。

---

## 一、冗余从哪来

并行派 N 个 subagent，每个独立 context、不知道彼此存在。结果几乎必然有以下问题：

```
冗余类型              典型现象
─────────────────────────────────────────────────────────
完全重叠              researcher A 和 B 都搜了"智谱 2026 收入"
部分重叠              A 搜了智谱 To B、B 搜了所有 LLM 公司 To B（含智谱）
信息冲突              A 说 "营收 5 亿"、B 说 "营收 8 亿"、没人对账
覆盖盲区              所有人都漏了某个关键 sub-topic
依赖错位              A 的结论应该是 B 的输入，但他们并行跑了
```

光靠"主 Agent 在 scoping 时拆好"解决不了——因为：
- LLM 拆解的子任务边界天然模糊（"智谱营收" 和 "国产大模型营收" 必然重叠）
- 跑起来后才知道哪些信息已经被找到
- 静态拆分无法处理"中途发现新方向"

---

## 二、五种协商机制（按复杂度递增）

### 机制 1：共享黑板（Blackboard Pattern）—— 最实用

所有 subagent **写到同一个文件 / 表**，每个新 subagent **启动前先读**。

```
research/<topic>/blackboard/
├── claims.jsonl         ← 每条记录一个 claim + source + 谁发现的
├── searches.jsonl       ← 已经搜过的 query 列表
└── reservations.jsonl   ← "我现在在做 X" 的认领
```

每个 researcher 的 protocol：

```markdown
## Before searching:
1. Read blackboard/claims.jsonl — 哪些事实已经知道
2. Read blackboard/searches.jsonl — 哪些 query 已经跑过，跳过
3. Append to reservations.jsonl: 我要做 X，避免别人重复

## After each finding:
1. Append to claims.jsonl
2. Append your queries to searches.jsonl
```

**优点**：实现简单，纯文件，跨 subagent 自动去重。
**陷阱**：并发写入要小心——多个 subagent 同时 append 可能撞车。解法：每个 subagent 写自己的 `claims_<agent_id>.jsonl`，主 Agent 启动新 subagent 前 merge，或者用 Postgres 等事务安全的存储。

### 机制 2：协调员 Agent（Coordinator Pattern）

不让 subagent 直接互通，**插一个 coordinator 在中间**：

```
                    ┌─ researcher A
[Coordinator] ──────┼─ researcher B
                    └─ researcher C
                    
Coordinator 工作：
- 收集每个 researcher 的"打算搜什么"
- 检测重叠 → 让某个 researcher 改方向
- 收集 findings → 检测冲突 → 派 verifier
```

**优点**：决策集中，能做更聪明的协调（比如"A 你别搜了，B 已经覆盖"）。
**缺点**：coordinator 自己要消耗 context；多了一层延迟。

### 机制 3：阶段化栅栏（Phase Barrier）

不是真协商，是**强制同步点**：

```
Phase 2a: N 个 researcher 并行做"扫描式"调研（每人搜 3 个 query）
   ↓ 栅栏：等所有人完成
Phase 2b: 主 Agent 看汇总，重新分配 sub-topic
   ↓
Phase 2c: N 个 researcher 第二轮，避开已覆盖的
   ↓ 栅栏
Phase 2d: 主 Agent 看是否还有 gap
   ↓
Phase 3: verifier...
```

**优点**：每轮之间主 Agent 重新分工，不会失控。
**缺点**：失去并行带来的速度优势。

### 机制 4：发布-订阅（Pub/Sub）

每个 subagent 发现新 claim 时**广播事件**，其他 subagent 订阅：

```
researcher A → publish("found_claim", {claim, source, agent_id})
                   ↓
researcher B 订阅 "found_claim"，收到后判断：
  - 如果在我研究范围内 → 加到我的 known_facts
  - 如果跟我即将搜的重叠 → 跳过那个 query
```

**优点**：实时协调，理论上最优。
**缺点**：实现复杂，subagent 必须长驻不能 fire-forget。Claude Code 的 Task 是一次性的，做不了；LangGraph 自己写可以。

### 机制 5：探测 + 抢占（Probe & Claim）

每个 researcher 启动时**先做轻量级探测**，再决定要不要"抢占"这个方向：

```
Step 1: researcher 收到 sub-topic
Step 2: 在 reservations 找最近 5 分钟内的认领
Step 3: 看自己的 sub-topic 跟已认领的有多大重叠
   - 重叠 > 70% → 主动放弃，回报 "deferred to <other agent>"
   - 重叠 30-70% → 缩小自己的范围（避开重叠部分）
   - 重叠 < 30% → 继续，写入 reservations
Step 4: 进入主流程
```

**优点**：分布式去中心化，自然分工。
**缺点**：依赖 reservation 的时效性（agent 挂了要清理）。

---

## 三、实战推荐：黑板 + 探测的组合

90% 的多 Agent 系统用**机制 1 + 机制 5 的组合**就够了：

```
共享黑板（持久化）：claims / searches / reservations 三个文件 / 表
+
新 subagent 启动协议：
  1. 读 reservations 看别人在做什么
  2. 读 claims 看已经有什么结论
  3. 读 searches 看哪些 query 跑过
  4. 在 reservations 写下自己要做什么
  5. 开干，过程中持续 append 到 claims/searches
```

### 用 Jaccard 相似度判重叠（不要用 LLM）

```python
def overlap_score(topic_a: str, topic_b: str) -> float:
    a = set(extract_keywords(topic_a))
    b = set(extract_keywords(topic_b))
    if not sa or not sb:
        return 0.0
    return len(a & b) / len(a | b)  # Jaccard
```

**为什么不用 LLM 判**：贵 + 慢 + 不稳定。Jaccard 0.01 秒，足够用。

---

## 四、Anthropic 的协议同步参考

Anthropic 在 2025 年 6 月发了博客 *"How we built our multi-agent research system"*，是少有的**生产级多 Agent 系统的公开复盘**。

### 系统结构

```
┌────────────────────────────────────────────────┐
│  Lead Researcher (Orchestrator)                │
│  ─ 看用户问题，规划策略                          │
│  ─ 决定派几个 subagent、各自做什么              │
│  ─ 综合结果，决定要不要再来一轮                  │
└────────────┬───────────────────────────────────┘
             │ 派任务（结构化）
             ▼
┌────────────────────────────────────────────────┐
│  N × Subagents (Researchers)                   │
│  ─ 每个独立 context                             │
│  ─ 自带 web search + 读文档工具                 │
│  ─ 独立思考、不互相通信                         │
│  ─ 完成后回报结构化结果                         │
└────────────────────────────────────────────────┘
             │ 引用提取
             ▼
┌────────────────────────────────────────────────┐
│  Citation Agent                                │
│  ─ 看完整 report                                │
│  ─ 把每个事实链接到具体源                       │
└────────────────────────────────────────────────┘
```

关键：**没有 subagent 互相通信。** 协议同步 100% 通过 Lead Researcher 中转。

### 同步机制：四个关键设计

#### 设计 1：结构化任务派发

Lead 给每个 subagent 的不是自然语言 prompt，是**结构化任务对象**：

```python
{
  "objective": "Find specific information about X",
  "expected_output_format": "List of facts with sources",
  "boundaries": "Only sources from after 2024",
  "tools_to_use": ["web_search", "browse"],
  "task_complexity": "moderate",
  "delegation_constraints": {
    "max_searches": 10,
    "max_browse": 5
  }
}
```

**为什么这样**：
- subagent 不需要理解上下文（Lead 已经过滤好了）
- 边界明确，不会跑偏
- 资源上限避免单 subagent 烧掉太多 token

**这是协议同步的第一层**：通过"任务规约"避免冗余。Lead 给 subagent 1 派"找 A 的财报数据"，给 subagent 2 派"找 A 的产品策略"——边界由 Lead 切清楚，不靠 subagent 自己协商。

#### 设计 2：Token Budget 管理

博客里反复强调：

> Multi-agent systems can use 15× more tokens than chats.

意思是天然 token 黑洞，必须显式管理。Anthropic 的做法：

```
任务复杂度评估
   │
   ├── simple    → 1 个 subagent，预算 ~5K token
   ├── moderate  → 2-4 subagent，预算 ~50K token
   └── complex   → 10+ subagent，预算 ~500K token
```

**Lead Researcher 自己被训练成会估算复杂度**——不能见任务就派 10 个 subagent。

这是**第二层同步**：通过预算分配控制并行度。

#### 设计 3：异步 + 结果聚合

subagent 是**异步并行**的，但结果聚合是**同步聚合点**：

```
Lead 派出 5 个 subagent
   ▼
  [并行执行，各自跑]
   ▼
所有结果到 → Lead 看汇总
   ▼
判断：信息够了吗？
   ├── 是 → 进入综合阶段
   └── 否 → 派下一轮（基于已有信息派"补漏"任务）
```

**关键**：Lead 是**严格的栅栏（barrier）**，不让 subagent 之间互相影响。

跟前面"机制 3：阶段化栅栏"完全一致。Anthropic 选择栅栏不是"没办法"，是**故意选**——他们在博客里明确说试过 subagent 互通，效果反而差。

#### 设计 4：Memory 文件共享（关键）

虽然 subagent 不互相通信，但他们**通过共享文件传递大对象**：

```
任务跑到第 30 步，context 200K token 快爆
   │
   ▼
Lead 把当前研究计划写到 plan.md（外部记忆）
   ▼
context 重置（只保留最关键摘要）
   ▼
继续下一阶段，需要 plan 时从 plan.md 读
```

这就是 **Manus 式文件记忆**，但用法更精细：
- 不是"每步都写文件"，是"context 快爆时主动 dump"
- subagent 也能读 plan.md，**间接共享 Lead 的规划**
- 但 subagent **不能写 plan.md**，避免冲突

**这是第三层同步**：通过 Lead 单点维护的共享文件，让 subagent **隐式同步**而不直接通信。

### 跟我们方案的本质对比

| 维度 | 我们的 LangGraph 方案 | Anthropic 系统 |
|---|---|---|
| 协商粒度 | subagent 自己看 blackboard 调整 | Lead 提前切清楚边界 |
| 通信方向 | subagent ↔ blackboard ↔ subagent | subagent → Lead → subagent |
| 冲突处理 | 探测 + 抢占 | 任务规约时就避免 |
| 实现复杂度 | 中（要写 blackboard 层） | 高（要训 Lead 估算复杂度） |
| 模型依赖 | 通用 LLM 即可 | **Lead 必须很强**，才能切好任务 |

**核心洞察**：Anthropic 的方案**把"协调智能"压在 Lead 身上**，subagent 是"哑工人"。我们的方案让 subagent 也聪明（自己协商）。

为什么 Anthropic 选前者？因为**Lead 模型可以被针对性优化**（system prompt + 训练数据），而 subagent 协商需要每个 subagent 都聪明——在大规模时不划算。

---

## 五、几个值得偷的设计

把 Anthropic 经验抽象成可借鉴的模式：

### 模式 1：任务规约对象化

不要给 subagent 传自然语言 prompt，传结构化对象。

```python
@dataclass
class ResearchTask:
    objective: str
    expected_output_format: str
    constraints: dict
    budget: dict  # max_searches, max_tokens
    required_tools: list[str]
```

### 模式 2：复杂度评估前置

跑之前先估算复杂度：

```python
def estimate_complexity(task: str) -> Literal["simple", "moderate", "complex"]:
    prompt = f"""Estimate research complexity:
{task}

Output JSON: {{"complexity": "simple|moderate|complex", "reasoning": "..."}}
"""
    return llm_haiku.invoke(prompt)["complexity"]


COMPLEXITY_CONFIG = {
    "simple":   {"n_subagents": 1, "budget_per": 5000},
    "moderate": {"n_subagents": 4, "budget_per": 15000},
    "complex":  {"n_subagents": 10, "budget_per": 50000},
}
```

避免简单问题杀鸡用牛刀。

### 模式 3：Subagent 的 Try-and-Adjust

博客里提到：subagent 跑歪时，Lead 会**指示它换策略**而不是重启。

```
Subagent 报告："搜了 5 次都没找到，可能这个数据不公开"
Lead 决策：
   ├── 接受这个结论（标记为 gap）
   ├── 让 subagent 换关键词再试
   └── 派另一个 subagent 用不同方法（比如查公司财报）
```

很多自家方案是 subagent 自己决定放弃。**让 Lead 做这个判断更好**——Lead 看全局，知道这个信息有多重要。

---

## 六、协商机制的反模式

### 反模式 1：让 subagent 互相对话

❌ "让 researcher A 和 B 直接通信讨论分工"

**为什么不行**：消息往返爆 token，决策不稳定（详见 [multi-agent-frameworks.md](multi-agent-frameworks.md) 反模式四）。

### 反模式 2：过度细粒度的同步

❌ 每个 search query 之前都查黑板

**为什么不行**：每次 search 前都 Read 文件 = N 倍 IO。**粒度应该在"启动时" + "重要发现时"**，不是每个原子操作。

### 反模式 3：用 LLM 判断"重叠度"

❌ "调用 LLM 判断 sub-topic A 和 B 是否重叠"

**为什么不行**：贵 + 慢 + 不稳定。**用关键词集合 + Jaccard 相似度，0.01 秒，足够用**。

---

## 七、扩展阅读

- [multi-agent-frameworks.md](multi-agent-frameworks.md) —— AutoGen / CrewAI / Agents SDK 协作模式
- [research-agent-architecture.md](research-agent-architecture.md) —— 在研究 Agent 中应用协商机制
- [../production/langgraph-research-agent-impl.md](../production/langgraph-research-agent-impl.md) —— LangGraph 中的黑板实现
