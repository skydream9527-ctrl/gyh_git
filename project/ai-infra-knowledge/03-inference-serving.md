# 推理引擎与 Serving

> 训练是一次性的成本，推理是持续的成本——一个日活百万的 LLM 应用，推理成本是训练的 10-100 倍。选对推理引擎、配好 batching 和调度，单卡吞吐能差 5-10 倍。本文讲清主流推理引擎的取舍、Continuous Batching、PagedAttention、分离式推理，以及选型决策。

---

## 一、推理和训练的本质区别

| 维度 | 训练 | 推理 |
|---|---|---|
| 瓶颈类型 | 算力密集（compute-bound） | **decode 阶段内存带宽密集（memory-bound）** |
| batch 行为 | 固定大 batch，一次性算 | 请求随来随走，batch 动态变化 |
| 优化目标 | 吞吐（tokens/s） | 吞吐 + 首字延迟（TTFT）+ 单条延迟（TPS） |
| 显存大头 | 优化器状态、激活 | **KV Cache** |
| 重复计算 | 无 | 同样 prompt 前缀可复用 |

**最关键的差异**：推理 decode 阶段是 memory-bound——GPU 算力远没用满，瓶颈在"把权重和 KV Cache 从 HBM 搬到计算单元的带宽"。这意味着：

- 加 GPU 算力没用，**加显存带宽才有用**（H100 比 A100 快主要靠带宽）
- 减少要搬的数据（量化、KV Cache 压缩）比"加快计算"更有效

---

## 二、推理的两阶段：Prefill 与 Decode

```
Prefill（处理输入 prompt）：
  特性：算力密集（compute-bound）
  并行度：高（所有 prompt token 并行算）
  产出：KV Cache（存起来给 decode 用）
  决定：TTFT（首字延迟）

Decode（逐 token 生成）：
  特性：内存带宽密集（memory-bound）
  并行度：极低（每次只算 1 个 token）
  产出：1 个新 token + 追加 KV Cache
  决定：TPS（单条吞吐）、整体吞吐
```

**为什么 decode 慢**：每生成 1 个 token，要把整个模型权重 + 全部 KV Cache 过一遍，但只产出 1 个 token 的计算。算力利用率可能只有 1-2%。这就是为什么 batching 对推理如此重要——**多个请求共享一次权重搬运**。

---

## 三、主流推理引擎对比

| 引擎 | 出品方 | 核心优势 | 核心劣势 | 适合场景 |
|---|---|---|---|---|
| **vLLM** | UC Berkeley | PagedAttention、吞吐高、生态好 | 显存管理激进时偶发 OOM | 通用开源首选 |
| **TensorRT-LLM** | NVIDIA | 极致单卡性能、FP8 支持 | 部署复杂、闭源 kernel、绑定 NVIDIA | 追求极致性能的生产环境 |
| **SGLang** | LMSYS | RadixAttention（前缀复用）、结构化生成快 | 较新，生态在完善 | Agent / 多轮 / 结构化输出 |
| **TGI** | HuggingFace | 与 HF 生态无缝、易部署 | 性能略逊 vLLM | HF 模型快速上线 |
| **LMDeploy** | OpenMMLab | 量化友好、国产硬件支持 | 社区小于 vLLM | 国产卡 / 量化场景 |
| **DeepSpeed-FastGen** | Microsoft | Dynamic Splitfuse（长序列） | 生态不如 vLLM | 长序列场景 |

### 选型建议

- **通用首选 vLLM**：开源事实标准，PagedAttention + Continuous Batching，社区最活跃
- **极致性能选 TensorRT-LLM**：NVIDIA 官方优化，FP8 在 H100 上能再快 1.5-2×，但工程复杂度高
- **Agent / 多轮对话选 SGLang**：RadixAttention 对共享 system prompt 的多轮场景吞吐优势明显
- **结构化输出（JSON/工具调用）选 SGLang 或 vLLM + outlines**：约束解码效率高

---

## 四、Continuous Batching：推理吞吐的核心

### 1. 朴素 batching 的问题

静态 batching：凑齐 N 个请求一起进、一起出。

```
请求 A: "讲个笑话"           → 5 tokens
请求 B: "写一篇 1000 字文章"  → 800 tokens
请求 C: "1+1="               → 1 token

静态 batch [A,B,C]：必须等 B 生成完 800 token 才能结束整个 batch
→ A 和 C 早就算完了，却陪着 B 空等 795 步 → GPU 利用率极低
```

### 2. Continuous Batching（Iteration-Level Batching）

**核心**：不是"一批一起进一起出"，而是**每个 decode step 动态调整 batch**——完成的请求随时退出，新请求随时加入。

```
step 1: batch = [A, B, C]        → 各生成 1 token
step 2: batch = [A, B, C]        → C 完成（"2"），退出
step 3: batch = [A, B, D(新)]    → A 完成，退出
step 4: batch = [B, D, E(新)]    → B 还在写文章...
```

**收益**：GPU 几乎不空等，吞吐提升 5-10×。这是 vLLM/TGI/SGLang 的标配。

### 3. 配合 PagedAttention 才能真正动态

Continuous Batching 的难点：请求进出时 KV Cache 要动态分配/释放。朴素连续分配 → 碎片化严重。**PagedAttention 解决了这个问题**（见下节），两者配合才是完整的方案。

---

## 五、PagedAttention：KV Cache 的虚拟内存

### 1. 朴素 KV Cache 的碎片化问题

朴素管理：每个请求预分配一段连续 KV Cache 空间。

```
请求 A（短）: [KKKK________________]   预留了 2K，用了 200 → 浪费 1.8K
请求 B（长）: [KKKKKKKKKKKKKKKK____]   预留了 2K，用了 1.5K → 浪费 0.5K
请求 C:       [分配失败]              没有连续大块了，虽然总剩余够

→ 大并发下 60-80% 显存被碎片浪费
```

### 2. PagedAttention：借鉴 OS 虚拟内存

把 KV Cache 切成固定大小的"页"（block，如 16 token 一页），按需分配，逻辑连续、物理离散：

```
逻辑视图（请求看到）:  [page0][page1][page2]...
物理显存（实际分配）:  散落在各处的空闲页，用页表映射

请求 A: 用了 3 页（48 token）
请求 B: 用了 100 页（1600 token）
新请求 C: 找 2 个空闲页即可，不用连续
```

**收益**：

- 碎片浪费从 60-80% 降到 < 5%
- 同样显存能服务 2-4× 并发
- 请求进出时只回收页，无需整理内存

### 3. 进阶：Prefix Sharing（前缀复用）

多个请求共享相同前缀（如 system prompt）→ 共享同一组 KV Cache 页：

```
请求 A: [system prompt 共享页][用户问题 A 的页]
请求 B: [system prompt 共享页][用户问题 B 的页]
请求 C: [system prompt 共享页][用户问题 C 的页]
         ↑ 同一组物理页，只存一份
```

vLLM 的 `--enable-prefix-caching`、SGLang 的 RadixAttention 都是做这个。对 Agent / 多轮 / RAG 场景（共享长 system prompt）吞吐提升 2-5×。

---

## 六、分离式推理（Disaggregated Prefill-Decode）

### 1. 问题：Prefill 和 Decode 抢资源

- Prefill 是 compute-bound，吃算力，要大 batch
- Decode 是 memory-bound，吃带宽，batch 小但频繁
- 混在一个集群 → prefill 的大 batch 会阻塞 decode 的低延迟需求

### 2. 解法：Prefill 和 Decode 分到不同 GPU

```
Prefill 集群（算力型）：专门处理新请求的 prompt，产出 KV Cache
        ↓ KV Cache 传输
Decode 集群（带宽型）：专门做逐 token 生成，低延迟
```

**收益**：

- 各自优化：prefill 集群堆算力，decode 集群堆带宽/显存
- TTFT 和 TPS 分别优化，互不干扰
- 长序列场景（prefill 重）收益尤其大

**代价**：KV Cache 跨 GPU 传输（几十 GB），需要高带宽互联。目前是前沿方向（DeepSeek、Mooncake 等在探索），生产落地还在早期。

---

## 七、调度与限流

### 1. 关键调度参数

| 参数 | 含义 | 调大影响 | 调小影响 |
|---|---|---|---|
| `max_num_seqs` | 最大并发请求数 | 吞吐↑、延迟↑、显存风险 | 延迟↓、吞吐↓ |
| `max_model_len` | 最大序列长度 | 显存↑、支持长文 | 截断长请求 |
| `gpu_memory_utilization` | 显存占用比例 | 更多 KV Cache 空间 | OOM 风险 |
| `swap_space` | KV Cache 换出到 CPU | 更高并发、换页慢 | 并发受限 |

### 2. 限流策略

- **并发限流**：超过 `max_num_seqs` 的请求排队（vLLM 默认）
- **Token 速率限流**：按用户/租户限 tokens/min，防滥用
- **优先级调度**：付费用户优先、长请求降级
- **KV Cache 驱逐**：显存满时按 LRU 驱逐低优先级请求的 KV Cache

### 3. 监控指标（必须盯）

| 指标 | 含义 | 告警阈值 |
|---|---|---|
| TTFT（首字延迟） | prefill + 排队时间 | P99 > 2s |
| TPS / ITL（单 token 延迟） | decode 速度 | P99 > 50ms |
| 吞吐（tokens/s/GPU） | 整体效率 | 低于基线 30% |
| KV Cache 利用率 | 显存使用 | > 90% 有 OOM 风险 |
| 排队长度 | 积压请求 | 持续增长 |

---

## 八、选型决策表

| 场景 | 推荐方案 |
|---|---|
| 通用开源部署 | vLLM + Continuous Batching + PagedAttention |
| 追求极致性能（H100） | TensorRT-LLM + FP8 |
| Agent / 多轮 / RAG | SGLang（RadixAttention）或 vLLM + prefix caching |
| 长序列（32K+） | 分离式推理（prefill-decode 分离） |
| 结构化输出（JSON/工具） | SGLang / vLLM + outlines 约束解码 |
| 国产硬件 | LMDeploy / vLLM-Ascend |
| 低延迟单条（< 100ms TTFT） | 小 batch + prefill 专用节点 + 模型量化 |

---

## 九、常见踩坑

1. **`gpu_memory_utilization` 设太高**：设 0.95 看似榨干显存，但峰值波动时 OOM。生产建议 0.85-0.9。
2. **没开 prefix caching**：多轮对话 / Agent 场景不开 prefix caching，吞吐浪费一半以上。
3. **`max_num_seqs` 盲目调大**：并发太高 → KV Cache 不够 → 频繁换页/驱逐 → 延迟飙升。要和显存平衡。
4. **长短请求混排**：一个 2000 token 的请求和一堆 50 token 的请求混排，短请求被长请求拖慢。可按长度分桶调度。
5. **只看吞吐不看尾延迟**：平均吞吐好看，但 P99 TTFT 5s，用户体验灾难。监控必须看分位数。
6. **量化后不评测**：INT4 量化吞吐翻倍但质量掉点没测 → 线上效果劣化。量化必须过评测集。

---

## 十、延伸阅读

- 推理优化技术细节（量化、投机解码、FlashAttention）：[04-inference-optimization.md](04-inference-optimization.md)
- 训练侧并行与显存：[01-distributed-training.md](01-distributed-training.md)
- 上线后的监控、灰度、成本治理：[05-mlops-platform.md](05-mlops-platform.md)
