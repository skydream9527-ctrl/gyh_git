# 推理优化技术

> 推理 serving 解决"怎么调度"，本文解决"怎么让单次推理本身更快更省"。量化、投机解码、FlashAttention、算子融合、KV Cache 压缩——这些是把单 token 成本再砍 2-5 倍的杠杆。配合 [03-inference-serving.md](03-inference-serving.md) 的 batching，才是完整的推理优化栈。

---

## 一、优化全景：先定位瓶颈

推理优化的所有技术，都在解决两个瓶颈之一：

```
Prefill 阶段（compute-bound）：
  瓶颈 = GPU 算力
  优化方向 → 减少计算量（量化、稀疏、投机解码）
  杠杆：FlashAttention、算子融合、FP8

Decode 阶段（memory-bound）：
  瓶颈 = 显存带宽（搬权重 + 搬 KV Cache）
  优化方向 → 减少要搬的数据
  杠杆：量化（权重+KV）、KV Cache 压缩、MQA/GQA
```

**先判断你的场景卡在哪**：

| 症状 | 瓶颈 | 主攻方向 |
|---|---|---|
| TTFT 慢、长 prompt 卡 | Prefill 算力 | FlashAttention、FP8、投机解码 |
| TPS 慢、decode 吐字慢 | Decode 带宽 | 权重量化、KV 量化、GQA |
| 高并发 OOM | KV Cache 显存 | KV 压缩、GQA、prefix caching |
| 单卡吞吐低 | 综合 | 量化 + batching + 算子融合 |

---

## 二、量化（Quantization）

### 1. 原理与收益

把高精度权重（FP16/BF16）压成低精度（INT8/INT4/FP8），**显存减半甚至 1/4，decode 带宽需求同步下降 → 速度提升**。

| 精度 | 权重显存 | decode 速度 | 质量损失 | 硬件要求 |
|---|---|---|---|---|
| FP16/BF16 | 100% | 基准 | 0 | 通用 |
| FP8 | 50% | 1.5-2× | 极小 | H100+ |
| INT8 | 50% | 1.5-2× | 小 | A100/H100 |
| INT4 | 25% | 2-3× | 中 | A100/H100 |
| INT2 | 12.5% | 3-4× | 大（多数不可用） | - |

### 2. 权重量化 vs KV Cache 量化

| 量化对象 | 作用 | 难点 |
|---|---|---|
| 权重（Weight-only） | 减显存、减 decode 带宽 | 反量化开销 |
| KV Cache | 减显存（高并发关键） | 精度敏感，长序列累积误差 |
| 激活（Weight+Activation） | 减计算量 | 激活有离群值，难量化 |

**decode 是 memory-bound，权重量化收益最大**；高并发场景 KV Cache 量化收益也大。

### 3. 主流量化方案

| 方案 | 类型 | 精度 | 特点 |
|---|---|---|---|
| **GPTQ** | 训后权重量化 | INT4/8 | 逐层用二阶信息校准，质量好，推理需反量化 |
| **AWQ** | 训后权重量化 | INT4 | 保护"重要"权重，质量优于 GPTQ，流行 |
| **SmoothQuant** | 权重+激活 | INT8 | 平滑离群值，W8A8 速度快 |
| **LLM.int8()** | 权重+激活 | INT8 | 混合精度（离群值 FP16），安全但慢 |
| **FP8（NVIDIA）** | 权重+激活 | FP8 | H100 原生支持，速度最快，质量接近 BF16 |
| **GGUF/llama.cpp** | 权重 | INT2-8 | CPU/边缘部署，量化档位丰富 |

### 4. 选型建议

- **生产 GPU 推理**：AWQ INT4（质量/速度平衡）或 FP8（H100 极致速度）
- **保守不丢质量**：SmoothQuant W8A8 或 FP8
- **CPU / 边缘**：GGUF（llama.cpp 生态）
- **必须过评测**：任何量化都要在业务评测集上验证，INT4 一般掉点 1-3%，但特定任务（数学、代码）可能掉更多

---

## 三、投机解码（Speculative Decoding）

### 1. 问题：decode 的串行瓶颈

decode 每次只生成 1 个 token，必须等上一个 token 算完才能算下一个 → 严格串行，GPU 算力大量闲置。

### 2. 思路：小模型猜，大模型验

```
1. Draft 模型（小/快）一次猜 k 个 token：[t1, t2, t3, t4]
2. Target 模型（大/准）一次并行验证这 k 个 token + 算 1 个
3. 接受猜对的连续前缀，从第一个错的 token 开始重新生成
```

**为什么快**：大模型一次并行验证 k 个 token 的成本 ≈ 生成 1 个 token 的成本（prefill 并行）。如果小模型猜得准（接受率高），相当于一次出 k 个 token。

### 3. 变体

| 方案 | Draft 来源 | 特点 |
|---|---|---|
| 经典投机解码 | 独立小模型 | 需要训练/选择匹配的小模型 |
| Medusa | 大模型自己加多个预测头 | 不用小模型，头要训练 |
| EAGLE | 用大模型隐藏状态预测 | 接受率高，当前 SOTA 之一 |
| Lookahead | N-gram / 自回归猜测 | 零额外模型，简单 |
| 投机 + 量化 | 小模型 INT4 + 大模型 BF16 | 双重加速 |

### 4. 收益与适用

- **接受率 70%+ 时，吞吐提升 2-3×**
- 适合：生成式任务（对话、写作、代码），draft 模型易获取
- 不适合：极度确定性任务（接受率低，反而有开销）

---

## 四、FlashAttention：attention 的算子融合极致

### 1. 问题：标准 attention 的内存瓶颈

标准 attention：`S = QK^T`（[seq, seq] 矩阵）→ mask → softmax → `O = SV`。

```
问题：S 矩阵 [seq, seq] 要写回 HBM 再读出来
  seq=8K → S 是 8K×8K×2bytes = 128MB，每层每步都要读写
  HBM 带宽成为瓶颈，且 SRAM 装不下整个 S
```

### 2. FlashAttention 的解法：分块 + 不写中间矩阵

```
把 Q, K, V 切成块，在 SRAM 里算：
  for each Q block:
    for each K,V block:
      在 SRAM 内算 QK^T → online softmax → 累加到 O
  全程不把 S 写回 HBM
```

**收益**：

- HBM 读写量降一个数量级
- prefill 提速 2-4×，长序列收益更大
- 显存：不再存完整 S 矩阵，省 [seq, seq] 显存
- **数学等价**，结果和标准 attention 完全一致（不是近似）

### 3. 版本演进

| 版本 | 改进 |
|---|---|
| FlashAttention v1 | 分块 + online softmax |
| FlashAttention v2 | 更好的并行度、减少非 matmul 计算 |
| FlashAttention v3 | 针对 H100 FP8/TMA 优化，速度再翻倍 |

**现状**：现代框架（PyTorch 2.x、vLLM、TGI、HF Transformers）默认开启，不用手动管。长序列场景务必确认用的是 FA2/FA3。

---

## 五、KV Cache 压缩

高并发 / 长序列场景，KV Cache 是显存大头。压缩方向：

### 1. 架构层：MQA / GQA（从根上减 KV 头数）

| 架构 | KV 头数 | KV Cache 大小 | 质量 |
|---|---|---|---|
| MHA（标准） | = Q 头数 | 100% | 基准 |
| MQA | 1 | 1/N（N=头数） | 掉点明显 |
| GQA（推荐） | 分组共享（如 8） | 8/N | 接近 MHA |

**GQA 是现代大模型标配**（Llama 2/3、Mistral 都用），KV Cache 直接砍到 1/4-1/8，几乎不损质量。详见 [agent-llm/llm-fundamentals/mqa-gqa-and-kv-cache.md](../agent-llm/llm-fundamentals/mqa-gqa-and-kv-cache.md)。

### 2. 量化 KV Cache

把 KV Cache 从 FP16 压成 INT8/FP8：

- 显存减半，高并发吞吐提升明显
- 精度敏感：长序列累积误差，需配合 per-token scaling
- vLLM / TensorRT-LLM 支持 FP8 KV Cache

### 3. 驱逐 / 剪枝

- **滑动窗口**：只保留最近 W 个 token 的 KV（如 Mistral 的 sliding window attention）
- **H2O / Heavy-Hitter**：识别重要 token 保留，其余驱逐
- **StreamingLLM**：保留 attention sink（开头几个 token）+ 滑动窗口，实现"无限长"生成

### 4. 卸载

KV Cache 换出到 CPU 内存 / NVMe，显存不够时兜底。代价是换页延迟，适合低 QPS 长序列场景。

---

## 六、其他优化

### 1. 算子融合

推理侧同样适用（详见 [02-training-optimization.md](02-training-optimization.md) 第四节）：fused softmax、fused LN、fused bias+act。vLLM/TensorRT-LLM 内部已做。

### 2. 稀疏注意力

长序列时只让每个 token attend 一部分（local + global）：

- Longformer、BigBird、Sparse Transformer
- 适合超长文档（16K+），但现代模型多用 GQA + 旋转位置编码 + 直接长 context 替代

### 3. 蒸馏

用大模型蒸馏出小模型，从根上减计算量。适合"质量要求可接受、成本敏感"的场景。

### 4. 早退 / 多出口

DeepSeek-MoE 等架构支持提前退出，简单 token 早退、难 token 走完整网络。

---

## 七、优化组合的实战收益

一个典型优化栈的累积收益（以 70B 模型为例，相对裸 HF Transformers）：

| 优化项 | 单项收益 | 累积吞吐 |
|---|---|---|
| 裸 HF Transformers（基准） | - | 1× |
| + Continuous Batching | 3-5× | 3-5× |
| + PagedAttention | 1.5× | 5-8× |
| + FlashAttention 2 | 1.5× | 8-12× |
| + AWQ INT4 量化 | 2× | 16-24× |
| + Prefix Caching（多轮场景） | 2× | 30-48× |
| + 投机解码 | 2× | 60-96× |

**结论**：优化是叠加的，但收益递减且有交互。建议按"收益大、风险低"顺序逐步加：batching → PagedAttention → FlashAttention → 量化 → prefix caching → 投机解码。

---

## 八、常见踩坑

1. **量化没评测就上线**：INT4 在通用 benchmark 掉 1%，但在你的数学/代码任务可能掉 8%。必须用业务评测集。
2. **投机解码用不匹配的小模型**：draft 和 target 分布差异大 → 接受率低 → 反而更慢。draft 要和 target 同源或蒸馏。
3. **FlashAttention 没真开**：装了包但 fallback 到标准 attention。检查日志确认 `flash_attn` 实际启用。
4. **KV 量化在长序列翻车**：INT8 KV Cache 在 32K+ 序列累积误差导致质量下降。长序列用 FP8 KV 或不量化。
5. **只优化单卡不看整体**：单卡吞吐翻倍，但网络/调度成新瓶颈。端到端压测。
6. **滑动窗口影响长依赖**：sliding window attention 省显存但丢失长程信息，文档摘要等任务质量下降。

---

## 九、延伸阅读

- 推理引擎与 serving 调度：[03-inference-serving.md](03-inference-serving.md)
- 训练侧显存与算子优化：[02-training-optimization.md](02-training-optimization.md)
- KV Cache 深度原理（MQA/GQA）：[../agent-llm/llm-fundamentals/mqa-gqa-and-kv-cache.md](../agent-llm/llm-fundamentals/mqa-gqa-and-kv-cache.md)
- 推理优化总览（产品视角）：[../agent-llm/llm-fundamentals/inference-optimization.md](../agent-llm/llm-fundamentals/inference-optimization.md)
