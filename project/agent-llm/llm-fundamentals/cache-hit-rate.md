# 缓存命中率：LLM 推理成本与延迟的隐形杠杆

> 一个 Agent 的 system prompt 有 8K token。每次请求都重算这 8K → 首字延迟 2s、输入费 $0.024。把前缀缓存住、命中率做到 90% → 首字延迟 300ms、输入费 $0.0024。**同一个模型、同一套硬件，仅缓存命中率一项就差 10 倍**。这不是"优化"，是"决定能不能上线"的差别。本文讲清缓存命中率是什么、怎么算、受什么影响、如何系统性提高，以及 API 侧和自部署侧的不同打法。
>
> 配套：[inference-optimization.md](inference-optimization.md)、[mqa-gqa-and-kv-cache.md](mqa-gqa-and-kv-cache.md)、[../production/latency-optimization.md](../production/latency-optimization.md)。
>
> 注意区分：本文讲的是 **LLM 推理侧的语义缓存**（KV Cache / Prefix Cache / Prompt Cache 的复用命中率）。训练侧的存储层级缓存（SRAM/HBM/DRAM 命中率）是另一个话题，见 [../../ai-infra-knowledge/01-distributed-training.md](../../ai-infra-knowledge/01-distributed-training.md) 第五节。

---

## 一、为什么 Agent 工程师必须懂缓存命中率

| 你遇到的问题 | 缓存命中率是核心解释 |
|---|---|
| Agent 多轮对话越聊越慢 | 每轮都重算历史 + system prompt，前缀没复用 |
| 同样 prompt 别人 API 费用是你 1/5 | 人家 prompt cache 命中率 90%，你 0% |
| 自部署 vLLM 吞吐远低于 benchmark | 没开 prefix caching，KV Cache 每次从头算 |
| TTFT（首字延迟）居高不下 | prefill 阶段没命中缓存，长 prompt 全量重算 |
| RAG 系统检索到同一文档却每次都慢 | 检索结果没固化成稳定前缀，缓存无法命中 |
| 工具调用 Agent 成本爆炸 | 几十个工具定义塞在 prompt 里，每次重算 |

**这些问题的根源都是缓存命中率**。它不是"锦上添花"的优化，而是 LLM 应用成本和延迟的一阶变量。

> 记一条铁律：**LLM 推理最贵的不是"生成"，是"重复计算已经算过的前缀"**。缓存命中率衡量的就是"有多少前缀没被重复计算"。

---

## 二、缓存命中率是什么

### 1. 定义

**缓存命中率（Cache Hit Rate）= 命中缓存的 token 数 / 总输入 token 数**。

注意是**按 token 加权**，不是按请求数——一个 10K token 的请求命中 9K，比 10 个 100 token 的请求全命中贡献大得多。

```
请求输入 = [可缓存前缀] + [不可缓存后缀]
命中率   = 可缓存前缀中实际命中的 token / 总输入 token
```

### 2. 举例

```
请求 A: [system 5000 token][工具定义 2000 token][用户问题 300 token]
        └── 稳定，可缓存 ──┘└── 稳定，可缓存 ─┘└── 每次变 ──┘

第一次请求：前缀没缓存 → 命中率 0%，全量 prefill 7300 token
第二次请求：前缀 7000 token 命中 → 命中率 7000/7300 ≈ 96%
                              只需 prefill 新增的 300 token
```

**收益是双重的**：

- **延迟**：prefill 计算量从 7300 token 降到 300 token → TTFT 大幅下降
- **成本**：API 侧 cache read 打 1-5 折；自部署侧省下的算力可服务更多并发

### 3. 为什么 LLM 推理特别适合缓存

LLM 推理有一个独特性质：**大量请求共享稳定前缀**。

| 场景 | 共享的稳定前缀 |
|---|---|
| Agent / 多轮对话 | system prompt、人设、工具定义 |
| RAG | 检索到的同一份文档 |
| 客服 / 角色扮演 | 角色设定、知识库 |
| 代码助手 | 仓库上下文、代码规范 |
| Few-shot | 示例样本 |

这些前缀动辄几千到几万 token，且**跨请求完全一致**——天然适合缓存。命中率做高了，等于把这部分计算成本摊薄到接近 0。

---

## 三、两类缓存：API 侧 vs 自部署侧

缓存命中率的概念在两种部署形态下实现机制不同，但度量方式一致。

### 1. API 侧（Prompt Cache）

OpenAI、Anthropic、Google 等厂商内置的功能。你按规则组织 prompt，厂商自动缓存前缀。

| 维度 | Anthropic | OpenAI |
|---|---|---|
| 触发条件 | 前缀完全一致到 token 级 | 前缀完全一致到 token 级 |
| 最低长度 | 1024 token | 1024 token |
| 缓存写入门槛 | 1024 token 起，按 32 token 增量 | 自动，无增量门槛 |
| 价格 | write 1.25× / read 0.1× | read 50% 折扣 |
| TTL | 5 分钟（默认）/ 1 小时（可选） | ~5-10 分钟 |
| 控制方式 | `cache_control` 标记 | 自动 |

**关键限制**：你**看不到也控不了**命中率细节，只能从账单的 `cache_read_input_tokens` 字段反推。

### 2. 自部署侧（Prefix Caching / KV Cache 复用）

vLLM、SGLang、TGI 等推理引擎自己实现。把请求的 KV Cache 按前缀复用。

| 引擎 | 机制 | 开启方式 |
|---|---|---|
| vLLM | PagedAttention + prefix caching | `--enable-prefix-caching` |
| SGLang | RadixAttention（前缀树复用） | 默认开启 |
| TGI | prefix caching | 配置项 |
| TensorRT-LLM | KV Cache reuse | 配置项 |

**自部署的优势**：命中率完全可控、可观测、可调优；不限于厂商 TTL；可做更激进的共享（如同 system prompt 跨用户共享）。

### 3. 对比

| 维度 | API Prompt Cache | 自部署 Prefix Caching |
|---|---|---|
| 实现方 | 厂商 | 自己 |
| 可观测性 | 弱（只看账单） | 强（全链路指标） |
| 控制粒度 | 粗（标记 + TTL） | 细（驱逐策略、容量、分桶） |
| 跨用户共享 | 通常不支持 | 可自己实现 |
| TTL 限制 | 厂商决定（5min-1h） | 自己定 |
| 适用 | 用 API 的应用 | 自部署推理 |

---

## 四、影响命中率的 5 个因素

### 1. 前缀稳定性（最关键）

缓存命中的前提是**前缀逐 token 完全一致**。任何一个 token 不同，从分歧点开始全部 miss。

```
请求 A: [system][tools][用户问题 A]   ← 前缀 [system][tools] 稳定
请求 B: [system][tools][用户问题 B]   ← 命中 [system][tools]
请求 C: [system][tools_v2][用户问题]  ← tools 改了 → 从 tools 起全 miss
```

**常见破坏稳定性的做法**：

- prompt 里塞了时间戳、随机 ID、用户名等动态内容
- 工具定义顺序每次不同（如按字典序不稳定）
- few-shot 示例随机采样
- 多轮对话把历史拼进前缀时格式不一致

### 2. TTL（存活时间）

缓存过期后即使前缀一致也 miss。

- API 侧：受厂商 TTL 限制（5min-1h），低频应用容易过期
- 自部署：可自己设，但容量有限，TTL 长不一定留得住

### 3. 容量与驱逐策略

缓存空间有限，满了要驱逐。驱逐策略影响命中率：

| 策略 | 做法 | 适合 |
|---|---|---|
| LRU（最近最少用） | 驱逐最久没访问的 | 通用默认 |
| LFU（最不常用） | 驱逐访问次数最少的 | 有热点前缀 |
| FIFO | 先进先出 | 简单但不优 |
| 优先级 | 按业务价值保留 | 付费/高价值请求优先 |

**容量不够时，命中率会被驱逐压低**——这是高并发场景命中率上不去的主因。

### 4. 并发与竞争

高并发下多个请求同时 miss 同一前缀 → 都去算一遍 → 都想写缓存 → 缓存只保留一份，但计算浪费了 N 份。这叫 **cache stampede（缓存击穿）**。

解法：single-flight（同一前缀只算一次，其他请求等结果）或预热。

### 5. 长度门槛

多数缓存要求前缀达到最低长度（如 1024 token）才缓存。短前缀不缓存 → 短 prompt 应用命中率天然低。

---

## 五、如何系统性提高命中率

### 1. Prompt 设计：把稳定内容前置（最高杠杆）

**核心原则**：稳定内容放最前，易变内容放最后。

```
❌ 差的设计：
[prompt]
你是一个助手。当前时间：{timestamp}    ← 动态内容混在前缀里
用户 {username} 你好
[system instructions 5000 token]
[tools 2000 token]
{user_input}

→ timestamp/username 一变，后面全 miss，命中率 ≈ 0

✅ 好的设计：
[prompt]
[system instructions 5000 token]        ← 最稳定，放最前
[tools 2000 token]                       ← 稳定，次之
[fixed few-shot examples]                ← 稳定
────── 以下为易变内容 ──────
当前时间：{timestamp}
用户 {username} 你好
{user_input}

→ 前缀 7000+ token 稳定，命中率可达 90%+
```

**实战要点**：

- **system prompt 完全固定**：不放任何动态变量
- **工具定义稳定排序**：按固定顺序，不按字典序随机
- **few-shot 固定**：不要每请求随机采样，用固定示例集
- **多轮对话历史**：放在 system/tools 之后、新问题之前（历史是逐步增长的，天然形成可缓存前缀）
- **动态内容集中放末尾**：时间戳、用户名、session ID、当前输入

### 2. Prompt 版本管理

prompt 改一个字 → 整个前缀缓存失效 → 命中率归零。

- **灰度改 prompt**：新旧版本并行时，命中率会分裂。尽量集中流量到新版本，快速完成切换
- **prompt 版本化**：用 `system_prompt_v3` 这样的显式版本，便于排查命中率下降
- **避免频繁改 system prompt**：每次改动都是一次全量缓存重建

### 3. 缓存策略调优（自部署）

- **容量充足**：监控驱逐率，驱逐率高就扩容或调 TTL
- **TTL 匹配访问模式**：高频前缀 TTL 长，低频的短（或主动预热）
- **分桶 / 分级缓存**：热门 system prompt 单独大容量桶，长尾请求小桶
- **跨用户共享**：同一应用所有用户共享 system prompt → 命中率随用户数上升而上升

### 4. 防缓存击穿（stampede）

- **single-flight**：同一前缀并发请求只算一次，其余等结果复用
- **预热**：部署后/版本更新后主动跑一遍热门前缀，把缓存填满再放流量
- **stale-while-revalidate**：过期了先用旧缓存服务、后台异步刷新

### 5. Agent / 多轮场景专项

Agent 是缓存命中率的"金矿"——system prompt + 工具定义动辄上万 token，且跨轮次跨用户稳定。

| Agent 组件 | 缓存策略 |
|---|---|
| system prompt | 完全固定，放最前，跨用户共享 |
| 工具定义（function schemas） | 固定顺序，紧随 system |
| few-shot 示例 | 固定集，不要随机 |
| 对话历史 | 增量追加，天然形成可缓存前缀 |
| RAG 检索结果 | 同一文档的 chunk 固定，可做文档级缓存 |
| 工具调用返回 | 易变，放最后 |

**多轮对话的累积收益**：

```
第 1 轮: prefill [system 5K][tools 2K][Q1 100]      命中 0
第 2 轮: prefill [system 5K][tools 2K][A1+Q2 300]   命中 7K（system+tools）
第 3 轮: prefill [system 5K][tools 2K][A1+A2+Q3 500] 命中 7K
...
→ 每轮都命中 7K 稳定前缀，只有增量部分需要重算
```

轮次越多、稳定前缀越长，命中率收益越大。这就是为什么**长 system prompt 的 Agent 应用，缓存命中率是成本生死线**。

### 6. API 侧的额外技巧

- **用 `cache_control` 显式标记**（Anthropic）：把可缓存段落显式标出
- **分段标记**：长 prompt 可分多个 cache breakpoint，前缀失效时只丢后半段
- **TTL 选择**：高频用 5 分钟默认，低频重要场景用 1 小时（Anthropic）
- **监控账单的 `cache_read_input_tokens`**：这是你唯一能看到的命中率信号

---

## 六、监控指标

### 1. 核心指标

| 指标 | 定义 | 目标 |
|---|---|---|
| 命中率 | 命中 token / 总输入 token | Agent 场景 > 80% |
| 节省成本 | (1 - 实际付费/无缓存付费) | > 70% |
| TTFT 改善 | 有缓存 vs 无缓存的首字延迟 | 降 50%+ |
| 驱逐率 | 被驱逐的缓存 / 写入的缓存 | < 10% |
| 缓存利用率 | 已用缓存空间 / 总容量 | 70-85% |

### 2. 分场景看命中率

整体命中率会掩盖问题，要分场景拆：

- 按 prompt 版本：哪个版本命中率低
- 按用户/租户：是否有用户行为异常破坏前缀
- 按时段：低频时段是否因 TTL 过期命中率下降
- 按前缀长度：短 prompt 场景命中率天然低，单独评估

### 3. 告警

- 命中率突然下降 > 20% → 可能 prompt 被改、缓存故障 → P0
- 驱逐率持续 > 30% → 容量不足 → P1
- TTFT 上升 + 命中率下降 → 缓存失效 → P1

---

## 七、常见踩坑

1. **动态内容混在前缀里**：时间戳、用户名、随机 ID 放在 system prompt 中 → 命中率归零。动态内容一律放末尾。
2. **工具定义顺序不稳定**：按 dict 遍历顺序拼 prompt，不同 Python 版本顺序不同 → 前缀不一致。显式排序。
3. **多轮对话历史格式不一致**：每轮拼接历史的格式有细微差异（空格、换行）→ 从分歧点 miss。用固定模板。
4. **频繁改 system prompt**：每次小改都让全量缓存失效。攒一批改动一起上，或用灰度快速切换。
5. **只看请求命中率不看 token 命中率**：10 个短请求全命中看着 100%，实际省的 token 不如 1 个长请求命中 90%。按 token 加权统计。
6. **自部署没开 prefix caching**：vLLM 默认不开（部分版本），生产环境务必确认 `--enable-prefix-caching` 生效。
7. **容量不够硬撑 TTL**：TTL 设很长但容量小，缓存还没过期就被驱逐。容量和 TTL 要一起调。
8. **API 侧不监控 `cache_read_input_tokens`**：以为开了 prompt cache 就生效，实际命中率很低却不知道。必须看账单字段。
9. **缓存击穿没防护**：热门前缀过期瞬间，大量请求同时 miss 重复计算。上 single-flight 或预热。
10. **RAG 检索结果不固化**：每次检索 chunk 顺序/内容微变 → 前缀不稳定。同一文档的 chunk 做稳定哈希排序。

---

## 八、延伸阅读

- 推理优化全貌（batching、量化、投机解码）：[inference-optimization.md](inference-optimization.md)
- KV Cache 原理与 MQA/GQA 压缩：[mqa-gqa-and-kv-cache.md](mqa-gqa-and-kv-cache.md)
- 生产环境延迟优化：[../production/latency-optimization.md](../production/latency-optimization.md)
- 生产环境可观测性：[../production/observability.md](../production/observability.md)
- 训练侧的存储层级缓存（不同场景的同源概念）：[../../ai-infra-knowledge/01-distributed-training.md](../../ai-infra-knowledge/01-distributed-training.md) 第五节
