# Agent 推理延迟优化：怎么降低 50%

> 大多数 Agent 上线后用户反馈第一名是"太慢"。本文给出**可工程化的延迟优化路径**——按 ROI 排序的 7 个杠杆，组合后能降 50-70% 延迟。
>
> 配套：[../production/observability.md](observability.md)、[../production/cost-and-latency.md](cost-and-latency.md)。

---

## 一、先 Profile：你的延迟到底花在哪里

不知道瓶颈就乱优化是徒劳。**所有优化前必须先 profile**。

```python
async def trace_agent_latency():
    timings = {}
    
    t0 = time.time()
    plan = await llm.invoke(planning_prompt)
    timings["llm_planning"] = time.time() - t0
    
    t0 = time.time()
    tool_results = await execute_tools(plan)
    timings["tool_execution"] = time.time() - t0
    
    t0 = time.time()
    response = await llm.invoke(synthesis_prompt + tool_results)
    timings["llm_synthesis"] = time.time() - t0
    
    return timings
```

### 典型分布

一个 5 步 Agent 任务，p50 延迟 30s：

| 环节 | 占比 |
|---|---|
| LLM 推理（含等待） | 60-75% |
| 工具调用（IO） | 15-30% |
| Prompt 拼接 / 序列化 | 5-10% |
| 网络往返 | 5-10% |

**结论**：60-75% 在 LLM。优化 LLM 部分 = 杠杆最大。

---

## 二、七个降延迟杠杆（按 ROI 排序）

### 杠杆 1：Prompt Caching（最大杠杆，必做）

Anthropic / OpenAI / Google 都支持 prompt cache。**第一次请求贵慢，后续命中 cache 的部分**：
- 速度：快 5-10×
- 成本：省 80-90%

**关键**：把**稳定不变的部分放在 prompt 前面**，让 cache 命中：

```python
messages = [
    {"role": "system", "content": LONG_SYSTEM_PROMPT,  # ← 5K token，cache 命中
     "cache_control": {"type": "ephemeral"}},
    {"role": "user", "content": current_query},  # ← 变化部分
]
```

**典型收益**：5K token system prompt + 200 token query 的 Agent，命中 cache 后**整体延迟降 40-60%**。

#### 实战要点

**a) Cache 前缀必须稳定**

```
✅ 稳定（cache 友好）：
   - system prompt
   - tool 定义列表
   - few-shot examples
   
❌ 不稳定（破坏 cache）：
   - 当前时间戳
   - 用户 ID（每次不同）
   - 动态 RAG 召回结果
```

**b) Skills 系统天然 cache 友好**

[skills-system-design.md](../agents/skills-system-design.md)：同 skill body 重复触发就命中 cache。

**c) Cache 有 TTL**

Anthropic：5 分钟（短）/ 1 小时（长，更贵但更划算）
OpenAI：默认有 prompt cache，自动判定

**d) Cache 不是越多越好**

Cache write 比正常 token 贵 25%（Anthropic）。**只 cache 真正会被复用的部分**。

### 杠杆 2：并行工具调用（最大架构杠杆）

Claude Code 一个 message 输出多个 Task 调用 → 并行跑。

```python
# 反例：串行
result_1 = await tool_a()
result_2 = await tool_b()
result_3 = await tool_c()
# 总延迟 = a + b + c

# 正例：并行
result_1, result_2, result_3 = await asyncio.gather(tool_a(), tool_b(), tool_c())
# 总延迟 = max(a, b, c)
```

实战：**研究 Agent 并行 8 个 researcher 子任务**——延迟从 8× 降到 1×。

详见 [../agents/research-agent-architecture.md](../agents/research-agent-architecture.md)、[../agents/multi-agent-coordination.md](../agents/multi-agent-coordination.md)。

#### 前提条件

子任务**真的独立**。有依赖的不能并行：

```
❌ 想并行：
   query → search → analyze
   后两步依赖前一步结果

✅ 能并行：
   topic → [search_aspect_a, search_aspect_b, search_aspect_c]
   三个 aspect 互不依赖
```

#### 反模式

❌ "我让 LLM 自己决定哪些能并行" → LLM 经常判错，错误并行（有依赖却并跑）会出大事故。**显式由代码声明并行边界**。

### 杠杆 3：Streaming + 早期 first-token

让用户看到逐字输出，**心理感知延迟降 50%**（即使总时间不变）：

```python
async for chunk in llm.astream(messages):
    yield chunk  # 边生成边显示
```

**TTFT (Time To First Token) 是用户感知的关键指标**，不是 total time。

#### 实战要点

**a) 流式工具调用**

新版 Claude/OpenAI API 支持 streaming function calls：tool_call 还在生成时你就能开始处理（比如显示 "正在查询..."）。

**b) 渐进式 UI**

```
0s:   "我先理解一下你的问题..."（prompt: thinking 模式 chunk）
2s:   "我会搜以下 5 个 sub-topic..."（plan 输出）
5s:   "正在查询 sub-topic 1/5..."（工具调用进度）
...
```

**用户感知延迟 = 从输入到第一个有用输出**，不是总时长。

**c) Server-Sent Events (SSE) 比 WebSocket 简单**

研究 Agent 这类单向流式输出，SSE 完全够用，比 WebSocket 简单 10×。

### 杠杆 4：模型路由（按任务难度选模型）

不同子任务用不同模型：

```python
SUBTASK_MODELS = {
    "classify":     "haiku",     # 100ms
    "extract":      "haiku",     # 200ms
    "synthesize":   "sonnet",    # 1.5s
    "review":       "opus",      # 3s
}

def route(subtask_type):
    return llm_clients[SUBTASK_MODELS[subtask_type]]
```

**实战**：把 plan-updater / classifier / extractor 类任务全切到 Haiku → **简单步骤延迟降 5×**。

#### 实战要点

**a) Router 自己也要轻量**

```python
# 反例：用 GPT-4 判断"这个子任务该用哪个模型"
# 路由开销 > 路由收益

# 正例：用规则 / 关键词 / Haiku 判断
def route(task_description: str) -> str:
    if any(kw in task_description for kw in ["classify", "extract", "format"]):
        return "haiku"
    if "review" in task_description or "verify" in task_description:
        return "opus"
    return "sonnet"  # 默认
```

**b) 评测每个路由决策**

```
不同任务用不同模型 → 必须每条路径独立评测
否则你不知道"换 Haiku 后质量掉了 5% 还是 30%"
```

详见 [../evaluation/research-agent-evals.md](../evaluation/research-agent-evals.md)。

**c) 跨家族模型混用要小心**

Claude / GPT / Gemini 行为差异大。**不要在一个流程里随意切换家族**——会有"风格不一致"问题（synthesizer 和 reviewer 用不同家族，最终输出语气会不连贯）。

### 杠杆 5：减少推理轮次

很多 Agent 一次任务跑 10+ 轮 LLM 调用，但其中很多是**可以合并的**。

```python
# 反例：3 轮
plan = await llm.invoke("规划")
search_query = await llm.invoke(f"基于 plan 生成 query: {plan}")
analysis = await llm.invoke(f"分析 {search_query} 结果")

# 正例：1 轮
result = await llm.invoke("""
规划 + 生成 query + 分析（一次性输出三个部分的 JSON）
""")
```

**心法**：**让 LLM 一次输出多个决策**，比反复来回快得多。

#### 何时该合并、何时不该合并

```
✅ 该合并：
   - 决策之间纯文本传递（不需要外部数据）
   - 决策有逻辑顺序但都是"思考"
   - 你要的输出是结构化的

❌ 不该合并：
   - 决策之间需要工具调用（合并不了）
   - 一个决策错全错（独立更鲁棒）
   - 决策本身就需要不同 prompt 风格
```

#### 反模式

❌ 一次请求让 LLM 输出 50 个字段的 JSON → 输出 token 太长，速度 ≈ 50 个独立请求

应该：拆成 2-5 个小批次，每批次 5-10 个字段。

### 杠杆 6：上下文长度优化

LLM 推理延迟随 context 长度**亚线性增长**（不是线性，但很接近）：

```
context 5K  → 1.0× 延迟
context 10K → 1.4× 延迟
context 50K → 4.5× 延迟
context 200K → 15× 延迟
```

#### 实战做法

**a) 用 RAG 而不是塞所有文档**

```python
# 反例
prompt = base + "\n\n".join(all_50_documents)  # 200K context

# 正例  
relevant = retriever.search(query, top_k=5)
prompt = base + "\n\n".join(relevant)  # 10K context
```

**b) 子 Agent 隔离 context**

详见 [../agents/long-task-agents.md](../agents/long-task-agents.md)。主 Agent 只看摘要，子 Agent 在自己 context 处理详情。

**c) 历史超过 N 轮自动压缩**

```python
def maybe_summarize_history(messages: list) -> list:
    if total_tokens(messages) < 50000:
        return messages
    # 取最近 5 轮 + 之前的摘要
    recent = messages[-10:]
    older = messages[:-10]
    summary = llm_haiku.invoke(f"Summarize: {older}")
    return [{"role": "system", "content": f"Earlier: {summary}"}] + recent
```

**d) 文件式记忆（Manus）**

详情写到文件，context 只放摘要 + 文件路径。详见 [../agents/research-agent-architecture.md](../agents/research-agent-architecture.md)。

### 杠杆 7：投机解码 / Batch（基础设施杠杆）

如果你自己部署模型（vLLM / TGI）：

- **Speculative decoding**：用小模型预测，大模型验证 → 单 token 延迟降 2-3×
- **Continuous batching**：多请求合并 → 吞吐量上去
- **KV cache reuse**：跨请求共享前缀 → 长 prompt 重用

API 用户用不到这些——但用 vLLM 自部署 7B/13B 模型时，**这是性能差 5× 的关键**。

详见 [../llm-fundamentals/inference-optimization.md](../llm-fundamentals/inference-optimization.md)。

---

## 三、把它们组合到 50% 降幅

### 现实 baseline

一个研究 Agent 任务：

```
现状：
  - 5K system prompt + 多步 LLM 调用
  - 串行调 6 个工具
  - 全程用 GPT-4o
  - 不开 streaming
  
延迟 p50: 45s
```

### 降 50% 的组合方案

```
1. 开启 prompt cache（杠杆 1）
   → system prompt 部分命中 cache
   → 节省 8-12s
   
2. 工具串行 → 并行（杠杆 2）
   → 6 个独立工具并行
   → 节省 6-8s
   
3. 加 streaming（杠杆 3）
   → 用户感知延迟从 45s → ~10s（first-token）
   → （技术延迟不一定降，但用户体验降 70%）
   
4. 简单子任务切 Haiku（杠杆 4）
   → 工具调用前的 routing 决策切 Haiku
   → 节省 2-3s

最终 p50: ~22s（技术延迟）
   或 ~10s（first-token，用户感知）
   
降幅: 50%-78%
```

---

## 四、一个常被忽略的反模式

### 反模式：用更大的模型让 Agent "更聪明" → 实际拖慢一切

```
团队反馈："Agent 答得不够准，换 Opus"
↓
延迟从 30s 涨到 90s
↓
"延迟太高，加一层缓存"
↓
缓存击中率 5%（用户问题千变万化）
↓
还不如改 prompt
```

**正确流程**：先**降低延迟到可接受范围**（用小模型 + 工程优化），**再用评测集判断质量是否够用**。不是先追质量再补救延迟。

---

## 五、50% 降幅的 ROI 排序（推荐顺序）

```
高 ROI（先做）：
  1. Prompt Caching       工程量低，收益大（30-50% 单独贡献）
  2. 工具并行             工程量低，收益大（30-50%）
  3. Streaming           工程量低，UX 收益巨大

中 ROI（再做）：
  4. 模型路由             工程量中（要建 router + 评测）
  5. 减少 LLM 轮次        工程量中（重写 prompt）

低 ROI（最后做）：
  6. Context 压缩         需要 RAG / 摘要基础设施
  7. 自部署 + vLLM 调优   要团队懂模型部署
```

**实战经验**：90% 的团队**做完前 3 项就降 50%+ 了**。后面 4 项是"从 50% 降到 70%"用的。

---

## 六、监控与持续优化

延迟优化不是一次性工作——**没有持续监控会逐渐回归**。

### 必须监控的 4 个指标

```
1. p50 / p95 / p99 延迟
   p50 反映"平均体验"
   p99 反映"长尾"（往往是 cache miss / API 超时）

2. TTFT (Time To First Token)
   用户感知核心
   
3. Tokens per second (生成速度)
   揭示模型 / 网络瓶颈

4. Cache hit rate
   prompt cache 是否真的在工作
```

### 工具

- **LangSmith**（LangChain）—— Agent 全链路 trace，自动统计延迟分布
- **Langfuse** —— 开源替代，自部署友好
- **Helicone** —— 简单代理层，加几行代码就有
- **Phoenix (Arize)** —— ML observability，重型但全

详见 [observability.md](observability.md)。

### 长期治理

```
每周：
  - 看 p99 延迟趋势
  - 找出 top 5 慢请求，分析根因

每月：
  - 评估"是否值得加新优化杠杆"
  - 重新跑 benchmark，看回归

每季度：
  - 重新评估模型路由配置
  - 评估是否需要换底层模型
```

---

## 七、扩展阅读

- [observability.md](observability.md) —— 长期延迟监控
- [cost-and-latency.md](cost-and-latency.md) —— 成本 / 延迟权衡
- [../prompting/prompt-caching.md](../prompting/prompt-caching.md) —— Prompt Cache 详解
- [../llm-fundamentals/inference-optimization.md](../llm-fundamentals/inference-optimization.md) —— 模型层优化
- [../agents/research-agent-architecture.md](../agents/research-agent-architecture.md) —— 并行工具调用实战
