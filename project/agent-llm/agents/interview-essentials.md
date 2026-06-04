# Agent 面试核心题：ReAct 手写 / MCP 辨析 / 记忆系统设计

> 这是一篇**面试追问深挖**——三道字节、OpenAI、Anthropic 系大厂高频题，每题都有"能写出来"和"能答得过追问"两个层级。本文专注后者。
>
> 配套深度阅读：
> - ReAct 全貌 → [react-mechanism-and-strategy.md](react-mechanism-and-strategy.md)
> - MCP 全貌 → [../tools-protocols/mcp.md](../tools-protocols/mcp.md)
> - 记忆系统全貌 → [memory-systems.md](memory-systems.md)、[openviking-vs-hindsight.md](openviking-vs-hindsight.md)

---

## 一、手写 ReAct 循环：能写出来 ≠ 能过面试

> 面试题：**用 Python 不用任何框架，写一个 Agent 主循环，支持工具调用。**

**坑点**：80% 的候选人写出能跑的版本就停了。面试官的真实意图在三个追问：

> Q1: Action 执行失败怎么优雅降级？
> Q2: 怎么判断 Agent 陷入死循环？
> Q3: max_steps 怎么设？

**高分答**：不是简单 `for i in range(10)`，而是**超时兜底 + 重复检测 + 状态回退**三层防御。下面逐层讲。

### 1.1 最小可跑版本（先答这个，再展开）

```python
def react_loop(question: str, tools: dict, llm, max_steps=10):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_WITH_TOOLS},
        {"role": "user", "content": question},
    ]
    for step in range(max_steps):
        resp = llm(messages, stop=["Observation:"])
        thought, action = parse(resp)
        if action.is_final:
            return action.answer
        try:
            obs = tools[action.name](**action.args)
        except Exception as e:
            obs = f"ERROR: {e}"
        messages.append({"role": "assistant", "content": resp})
        messages.append({"role": "user", "content": f"Observation: {obs}"})
    return "Failed: max_steps reached"
```

→ 这是底线版本。**面试官不会在这里给你高分**。下面才是。

### 1.2 第一层防御：Action 失败的"分级降级"

简单 try/except 把错误塞回去，是新手做法。**生产级降级要分错误类型**，对照 [tool-development.md §四.1](../tools-protocols/tool-development.md#四错误处理错误本身也是给模型的输入)：

```python
def execute_action(action, tools, ctx):
    tool = tools.get(action.name)
    if not tool:
        # 错误类型 A：选了不存在的工具 → 提示可用列表
        return Observation.error(
            kind="unknown_tool",
            msg=f"Tool {action.name!r} not found. Available: {list(tools)}"
        )
    try:
        with timeout(tool.timeout_s):
            return Observation.ok(tool(**action.args))
    except ValidationError as e:
        # 错误类型 B：参数错 → 详细反馈让模型重生成
        return Observation.error(
            kind="bad_args", field=e.field, msg=str(e),
            suggestion=e.suggestion
        )
    except TimeoutError:
        # 错误类型 C：超时 → 告诉模型可换更快工具或缩小范围
        return Observation.error(
            kind="timeout",
            msg=f"Tool exceeded {tool.timeout_s}s.",
            suggestion="Try a narrower query or a faster alternative."
        )
    except UpstreamError as e:
        # 错误类型 D：上游故障 → Tool 内部已重试 N 次，告诉模型放弃这条路
        return Observation.error(
            kind="upstream_down", msg=str(e),
            suggestion="Switch to alternative tool or skip this step."
        )
    except Exception as e:
        # 错误类型 E：未知异常 → 记日志，给模型脱敏信息
        log.exception(...)
        return Observation.error(kind="internal", msg="Tool internal error.")
```

**降级策略对照**：

| 错误类型 | 降级动作 | 是否计入 step |
|---|---|---|
| unknown_tool | 列出可用工具 → 让模型重选 | 计 |
| bad_args | 报字段 + 建议 → 让模型重填 | 计 |
| timeout | 提示缩窄查询 | 计 |
| upstream_down | 提示换路径 | 计 |
| internal | 脱敏报错 | **+ 全局错误计数**，超阈值整体熔断 |

**重点**：错误信息里**永远要带 suggestion**——给模型可执行的下一步，否则它会瞎试。

### 1.3 第二层防御：死循环检测

死循环的三种典型形态，单设 `max_steps` 都防不住：

```
形态 A: 同 action 同参数反复调（参数填错改不过来）
形态 B: 两个 action 互相唤醒（A 调 B，B 又导致 A）
形态 C: 表面变化的"假进展"（参数微调但本质重复）
```

**生产级检测**：把 (action_name, normalized_args) 哈希进窗口：

```python
from collections import deque

class LoopDetector:
    def __init__(self, window=4, max_repeat=2):
        self.history = deque(maxlen=window)
        self.max_repeat = max_repeat

    def check(self, action) -> bool:
        sig = (action.name, _canonical(action.args))
        count = sum(1 for s in self.history if s == sig)
        self.history.append(sig)
        return count >= self.max_repeat   # True → 命中循环

    @staticmethod
    def _canonical(args):
        # 关键：归一化——大小写、空格、顺序无关
        return json.dumps(args, sort_keys=True, separators=(",", ":")).lower()
```

**触发循环后的处理**：

```python
if loop_detector.check(action):
    # 不直接 return 失败，先给模型一次"反思机会"
    obs = Observation.error(
        kind="loop_detected",
        msg=f"You've called {action.name} with same args {N} times. "
            f"Past results: {[h.summary for h in past_obs]}. "
            f"Try a fundamentally different approach or give up."
    )
    consecutive_loop_warnings += 1
    if consecutive_loop_warnings >= 2:
        return give_up(reason="repeated_loops")
```

**进阶**：除了 action 哈希，还可以做**语义相似度检测**——如果连续 N 个 thought 的 embedding 余弦相似度 > 0.95，也算循环（应对"不同措辞但意图一致"的情况）。

### 1.4 第三层防御：状态回退

链路长 + 工具有副作用时，单纯停止不够——你要**回到上一个已知好状态**：

```python
class CheckpointedAgent:
    def __init__(self):
        self.checkpoints = []  # [(step, messages_snapshot, world_state)]

    def step(self, ...):
        if self._is_safe_point():
            self.checkpoints.append(self._snapshot())
        try:
            return self._run_step()
        except IrrecoverableError:
            self._rollback_to_last_checkpoint()
            return self._notify_model("Rolled back to step X due to error.")
```

**什么算"安全点"**：

- 上一个工具调用是只读的（搜索、查询）
- 模型刚显式 confirm 了一个阶段性结论
- 关键写操作前

**回退要回什么**：

| 状态层 | 回退策略 |
|---|---|
| messages 上下文 | 直接 truncate 到 checkpoint 处 |
| 已写入的外部副作用 | 调用 compensating action（删订单/反向转账等）—— 需要 Tool 自己提供 |
| 内部 scratchpad / memory | 同 messages |
| 模型决策（已选工具路径） | 通过 prompt 显式告诉模型"刚才那条路不可行" |

→ 不可逆操作的回退本质是**补偿事务**，依赖 Tool 是否设计了 compensating endpoint。这也是 [tool-development.md §四.4](../tools-protocols/tool-development.md#四错误处理错误本身也是给模型的输入) 强调"危险操作 dry_run"的原因。

### 1.5 max_steps 怎么设

最差答案：写个常量 `MAX_STEPS = 10`。
**好答案**：max_steps 是**多维预算**的简化表达，应该按场景套不同维度组合：

```python
class Budget:
    max_steps: int          # 步数上限，常 8-15
    max_tokens: int         # 累计 token 上限（成本兜底）
    max_wall_time_s: int    # 墙钟时间上限（用户体验兜底）
    max_tool_cost_usd: float # 累计 tool API 成本（外部 API 收费场景）
    max_consecutive_errors: int = 3   # 连续错误退出
```

**触发哪个都退出**——不是"全都满才退"。原因：

- 简单 Q&A：3-5 步，超过就基本是错路
- 研究 Agent：15-30 步，靠 token 和 wall_time 兜
- Coding Agent（Claude Code 风格）：50+ 步，靠 token + 用户 confirm 兜

**怎么标定具体值**：

1. 收集生产数据，画"成功 case 的 step 分布"
2. 设上限 = P95 步数 × 1.5
3. 上线后看"刚好打到 max_steps 才完成"的占比，>5% 说明设小了
4. 看"超 max_steps 失败"的 case，多数是 prompt / 工具问题，不是上限太小

**面试金句**：
> "max_steps 不是设防 LLM 死循环的唯一手段，它是**最后一道兜底**。前面要有循环检测、token 预算、wall-time 兜底。max_steps 设小了 P95 的合理任务被砍，设大了死循环烧钱——所以它必须配合分布数据来标定。"

### 1.6 一张图总结手写 ReAct 的"三层防御"

```
┌──────────────────────────────────────────────────────────┐
│ Step Loop                                                │
│                                                          │
│   ① LLM 推理 → action                                    │
│       ↓                                                  │
│   ② 循环检测：同 action 哈希 N 次？  ←─ 第 2 层          │
│       ↓ no                                               │
│   ③ 工具执行（带 timeout）         ←─ 第 1 层           │
│       ├─ ok    → observation                             │
│       └─ error → 分级降级 → observation                  │
│       ↓                                                  │
│   ④ 是否需要 checkpoint？          ←─ 第 3 层           │
│       ↓                                                  │
│   ⑤ 预算检查（steps/tokens/time）                        │
│       ├─ within → 回到 ①                                 │
│       └─ exceeded → graceful exit + checkpoint rollback  │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

→ 能把这张图画清楚 + 解释为什么三层缺一不可，这道题就过了。

---

## 二、MCP 协议辨析：三层关系讲透

> 面试题：**MCP 和 Function Calling 是什么关系？**

**坑点**：很多人答"MCP 是新版 Function Calling"——错。**这两个完全不在同一层**。

### 2.1 三层关系框架

```
┌──────────────────────────────────────────────────────────┐
│ Layer 3: 生态层                                           │
│   MCP（Model Context Protocol）                          │
│   ─ 标准化 LLM 应用 ↔ 工具/数据源 的接入协议             │
│   ─ 解决 M×N 集成问题                                    │
├──────────────────────────────────────────────────────────┤
│ Layer 2: 编排层                                           │
│   Agent 框架（LangGraph / Autogen / 自研）               │
│   ─ 决定何时调工具、怎么处理结果、怎么循环               │
├──────────────────────────────────────────────────────────┤
│ Layer 1: 模型层                                           │
│   Function Calling                                        │
│   ─ 模型按 schema 输出结构化工具调用的能力               │
│   ─ 由模型 SFT 阶段训练出来                              │
└──────────────────────────────────────────────────────────┘
```

**三句话总结**：

- **Function Calling 是模型层能力**：模型"会按 schema 说出我要调哪个工具"
- **Agent 框架是编排层**：在调用 / 循环 / 重试 / 反思上做工程
- **MCP 是生态层协议**：让"工具的实现方"和"用工具的应用方"解耦

它们**不竞争，而是叠加**——一个 MCP server 在里面用 Function Calling 拼接 tool schema，被 Claude Desktop / Cursor / Cline 这些 client 通过 MCP 协议复用。

**面试金句**：
> "Function Calling 解决的是'模型会调工具'，MCP 解决的是'同一个工具不必给每个客户端各写一份适配'。前者在模型权重里，后者在协议规范里。一个工具用 Function Calling 实现，再用 MCP 暴露——两件事，一套链路。"

### 2.2 MCP 解决的"M×N 碎片化"

```
没有 MCP：
   Claude Desktop ──┐
   Cursor          ──┤
   Cline           ──┼── 各自写 GitHub / Slack / Postgres 适配
   Continue        ──┤   M 个客户端 × N 个工具 = M×N 个适配
   ...             ──┘

有 MCP：
   Claude Desktop ──┐
   Cursor          ──┼─→ MCP 协议 ─→ GitHub server
   Cline           ──┤              Slack server
   Continue        ──┤              Postgres server
   ...             ──┘              （每个工具写一次）
   M 个客户端 + N 个 server = M+N
```

→ 这个 M×N → M+N 的转换，跟历史上 USB-C 替代各家私有充电口、ODBC 替代各家私有 DB 驱动、LSP 替代各 IDE 自写语言支持，**是同一类工程问题**。能类比上去就显得你有架构 sense。

### 2.3 追问：Resources / Tools / Prompts 三种原语各在什么场景用

| 原语 | 是什么 | 场景 | 反例 |
|---|---|---|---|
| **Tools** | 可调用的函数 | `search_issues`、`run_sql`、`send_email`——所有"做动作"的 | 别用 Tools 暴露大文件全文 |
| **Resources** | 可读取的数据 / 上下文 | `file://path`、`postgres://schema`、`grafana://dashboard`——所有"作为材料"的 | 别用 Resources 触发副作用 |
| **Prompts** | 用户级触发的工作流模板 | `/review-pr`、`/generate-tests`——slash command 召唤 | 别用 Prompts 替代 system prompt |

**关键判断**：

```
能不能不带参数就有意义？
   是 → 可能是 Resource（"打开就能看"）
   否 → Tool（要带参数调用）

是模型自主调用还是用户主动召唤？
   模型自主 → Tool
   用户召唤 → Prompt
```

**典型组合**（一个数据库 MCP server 同时暴露三类）：

```yaml
tools:
  - run_sql            # 模型按需查询
resources:
  - postgres://schema  # 把 schema 挂进上下文，模型查询时参考
prompts:
  - /explain-table     # 用户在 Cursor 里输 /explain-table users → 触发预制工作流
```

### 2.4 面试可能继续追问

| 追问 | 短答 |
|---|---|
| MCP 鉴权怎么做？ | OAuth 2.1 / API Token；server 决定，client 透传 |
| 跨进程吗？ | stdio（同机）/ SSE / streamable HTTP（远程）三种 transport |
| 相比 OpenAPI 优势？ | OpenAPI 是 REST 描述格式；MCP 是双向 RPC + 上下文协议（含 Resource 通知、Prompt 触发），语义不同 |
| 是不是只能 Anthropic 用？ | 协议公开开源；OpenAI、Google、本地模型都可作为 client，社区已有非 Anthropic client |
| MCP 服务端用什么实现？ | 官方 SDK 有 Python / TypeScript / Go / Rust；最小 server 几十行代码 |

→ 想细看实现，去 [../tools-protocols/mcp.md](../tools-protocols/mcp.md) §四 的最小 server 代码。

---

## 三、Agent 记忆系统设计：会答"记忆污染"才是高手

> 面试题：**设计一个 Agent 的记忆架构，要支持短期+长期。**

**坑点**：写出"短期=上下文+摘要 / 长期=向量库"是 60 分。**90 分必须答"记忆污染"和"过时记忆淘汰"**。

### 3.1 90 分答案的整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                  Agent Runtime                              │
│                                                             │
│  ┌─────────────────────┐      ┌──────────────────────────┐ │
│  │ Short-term Memory   │      │  Long-term Memory        │ │
│  │ (Working Memory)    │      │  (Persistent Memory)     │ │
│  │                     │      │                          │ │
│  │ 1. 当前窗口         │      │ 1. Episodic 向量库       │ │
│  │    最近 N 条原文    │      │    (会话片段嵌入)        │ │
│  │ 2. 滚动摘要         │      │ 2. Semantic KV / Profile │ │
│  │    阶段性结论       │      │    (用户画像/事实)       │ │
│  │ 3. Scratchpad       │      │ 3. Procedural 规则库     │ │
│  │    临时草稿/计算    │      │    (流程模板)            │ │
│  └──────────┬──────────┘      └────────────┬─────────────┘ │
│             │                              │                │
│             └────────┬─────────────────────┘                │
│                      ↓                                      │
│       ┌──────────────────────────────┐                      │
│       │  Hybrid Retrieval Layer      │                      │
│       │  Vector + BM25 + Reranker    │                      │
│       └──────────────────────────────┘                      │
│                      ↓                                      │
│       ┌──────────────────────────────┐                      │
│       │  Memory Hygiene Layer        │  ← 这是 90 分关键    │
│       │  - Conflict detection        │                      │
│       │  - Decay / Archive           │                      │
│       │  - Provenance tracking       │                      │
│       └──────────────────────────────┘                      │
└─────────────────────────────────────────────────────────────┘
```

短期、长期、检索、卫生——**四块缺一不可**。前两块是 60 分，后两块是 30 分。

详细分类请看 [memory-systems.md](memory-systems.md) 的 Episodic / Semantic / Procedural 三分法。

### 3.2 写入侧：先讲清"记什么"

记忆质量 = 写入策略质量。**不是所有对话都该写长期**：

```python
def should_write_long_term(turn) -> WriteDecision:
    # 不写：寒暄、错误对话、试探
    if turn.is_smalltalk: return SKIP
    if turn.contains_correction("我搞错了"): return SKIP

    # 写 Semantic（事实/偏好）：用户陈述自己 + 稳定信息
    if turn.is_user_assertion and turn.about_self:
        return WRITE_SEMANTIC(extract_profile_diff(turn))

    # 写 Episodic（事件）：完成的任务、关键结论
    if turn.is_task_completion:
        return WRITE_EPISODIC(turn.outcome_summary)

    # 写 Procedural（流程）：用户多次重复的工作流
    if pattern_recurrence_detected(turn):
        return WRITE_PROCEDURAL(turn.workflow)

    return SKIP
```

**关键**：每条长期记忆都带 **provenance（来源溯源）**——`(timestamp, session_id, turn_idx, source_message)`。后面所有"卫生层"工作都靠它。

### 3.3 检索侧：三层检索为什么必要

单 vector 召回的两个致命问题：

1. **语义相近但事实矛盾**：去年存的"用户喜欢 React"和今年存的"用户讨厌 React"都召回，模型乱用
2. **关键词命中差**：用户问"我上次改的 SU7 那个文档"，vector 可能漏掉精确名词

**三层检索方案**：

```python
def retrieve_memory(query, user_id, k=5):
    # 层 1: 双路召回
    vector_hits = vector_db.search(embed(query), filter={"user_id": user_id}, k=20)
    bm25_hits   = bm25_db.search(query, filter={"user_id": user_id}, k=20)

    # 层 2: 合并 + Reranker
    merged = reciprocal_rank_fusion(vector_hits, bm25_hits)
    reranked = reranker.rerank(query, merged, top_k=10)  # cross-encoder

    # 层 3: 时间衰减 + 冲突过滤
    scored = apply_decay(reranked)         # 越旧权重越低
    filtered = resolve_conflicts(scored)   # 见 §3.4
    return filtered[:k]
```

**Reranker 这一层很多人省，是失误**——召回出来的 20 条里前 5 条经常不是"最相关"的，cross-encoder 的精确比对能把准确率从 60% 拉到 85%。

### 3.4 记忆污染：检测 + 清理

> 这是面试官真正想听的部分。**记忆污染**有四种形态：

| 形态 | 例子 | 检测手段 |
|---|---|---|
| **冲突** | 同一事实有两个矛盾版本 | NLI 模型判 contradiction，或 LLM-as-judge |
| **过时** | "用户当前在做的项目" 一年没更新 | TTL + 时间衰减 |
| **错误** | 用户当时说错了，没回滚 | provenance 追溯 + 用户更正信号 |
| **幻觉沉淀** | 模型自己产生的错误信息被当事实存了 | 写入前打 source 标记，不写"模型生成"作为事实 |

**冲突解决策略**：

```python
def resolve_conflicts(memories):
    groups = cluster_by_topic(memories)
    out = []
    for group in groups:
        if len(group) <= 1:
            out.extend(group); continue

        # 用 NLI 检测冲突对
        conflicts = detect_contradictions(group)
        if not conflicts:
            out.extend(group); continue

        # 冲突解决：最新 + 最高 confidence + 人工 confirm 优先
        winner = max(group, key=lambda m: (
            m.confirmed_by_user,    # 用户显式确认过的最优
            m.confidence,
            m.last_verified_at,
        ))
        # 不是直接删旧的——标记为 superseded，留 audit trail
        for m in group:
            if m is not winner:
                m.status = "superseded"
                m.superseded_by = winner.id
        out.append(winner)
    return out
```

**核心原则**：**永远不要直接删记忆**——标记 superseded，保留审计链路。否则你无法回答"为什么 Agent 之前知道这个，现在又忘了"。

### 3.5 过时记忆淘汰：分级归档而非粗暴删除

错的做法：`DELETE WHERE created_at < NOW() - INTERVAL '90 days'`——把还在用的记忆删了。

**生产级"分级归档"**：

```
Hot   ─ 最近 30 天 + 最近 30 天有访问  →  主索引（vector + BM25）
Warm  ─ 30-180 天 或 30 天内未访问     →  压缩到摘要存二级库
Cold  ─ 180+ 天且无访问                →  冷归档（S3）+ 仅保留 summary
```

**触发归档**：

```python
def hygiene_job():  # 每天跑一次
    for mem in all_memories():
        score = compute_freshness(mem)  # 时间 + 访问频次 + 引用次数
        if score < HOT_THRESHOLD:
            mem.tier = "warm"
            mem.body = summarize(mem.body)  # 压缩
        if score < WARM_THRESHOLD:
            mem.tier = "cold"
            archive_to_blob(mem)
            keep_only_summary(mem)
```

**关键设计**：

- **访问频次衰减**：每被检索一次更新 `last_accessed`，频次更新会延缓归档
- **引用计数**：当前活跃记忆引用了某条旧记忆 → 旧记忆被"提温"回 warm
- **降级而非删除**：永远保留 summary 和 provenance，需要时可恢复

### 3.6 一张图把所有关系串起来

```
   User Turn
        ↓
   ┌──────────────────────┐
   │  Memory Writer       │
   │  - 决策写不写         │
   │  - 写 episodic/semantic/procedural │
   │  - 打 provenance      │
   └──────────┬───────────┘
              ↓
   ┌──────────────────────┐
   │  Long-term Storage   │←──── Hygiene Job (daily)
   │  Vector + BM25 + KV  │      - decay
   │                      │      - conflict resolve
   └──────────┬───────────┘      - tier archive
              ↓
   On every query:
   ┌──────────────────────┐
   │  Hybrid Retrieval    │
   │  Vector ⊕ BM25       │
   │  → RRF → Reranker    │
   │  → Decay → Conflict  │
   └──────────┬───────────┘
              ↓
   ┌──────────────────────┐
   │  Short-term Window   │
   │  Recent + Summary    │
   └──────────┬───────────┘
              ↓
        Prompt to LLM
```

**面试金句**：
> "短期靠窗口+摘要，长期靠 Vector+BM25+Reranker——这是基线。但是真正区分玩家的是**记忆卫生层**：冲突检测、provenance 溯源、分级归档。没有这一层，记忆系统跑半年就开始幻觉沉淀，质量会反向劣化。"

---

## 四、面试准备 Checklist

```
手写 ReAct
□ 能写出最小可跑版本（30 行内）
□ 能讲分级错误降级（5 类错误 × 不同处理）
□ 能讲循环检测（哈希窗口 + 语义相似度）
□ 能讲 checkpoint + 状态回退（含补偿事务）
□ 能讲 max_steps 是多维预算的简化（steps/tokens/time/cost）

MCP 辨析
□ 能画三层架构图（模型层/编排层/生态层）
□ 能讲 M×N → M+N 的工程价值（USB-C / ODBC / LSP 类比）
□ 能讲 Tools/Resources/Prompts 三种原语的边界
□ 能答鉴权 / transport / 跨厂商 / 跟 OpenAPI 区别

记忆系统
□ 能画整体架构（短期/长期/检索/卫生 四块）
□ 能讲写入决策（什么写 episodic / semantic / procedural）
□ 能讲三层检索（Vector + BM25 + Reranker，且能说出 RRF）
□ 能讲记忆污染四种形态（冲突/过时/错误/幻觉沉淀）
□ 能讲分级归档而非删除（hot/warm/cold + provenance）
```

---

## 五、扩展阅读

- ReAct 全貌 → [react-mechanism-and-strategy.md](react-mechanism-and-strategy.md)、[react-and-variants.md](react-and-variants.md)
- 工具开发工程视角 → [../tools-protocols/tool-development.md](../tools-protocols/tool-development.md)
- MCP 全貌 + 最小 server → [../tools-protocols/mcp.md](../tools-protocols/mcp.md)
- 记忆系统全貌 → [memory-systems.md](memory-systems.md)、[openviking-vs-hindsight.md](openviking-vs-hindsight.md)
- Agent 循环架构 → [agent-loop-architectures.md](agent-loop-architectures.md)
- Anthropic — *Building Effective Agents*（讲了为什么"能 workflow 别 agent"）
- Anthropic — *Effective context engineering for AI agents*（记忆 / 上下文卫生）
- MemGPT 论文（分级记忆 + 摘要漂移问题）