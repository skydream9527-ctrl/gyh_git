# MQA / GQA 与 KV Cache：长 context 性能的根基

> KV Cache 是 LLM 推理性能的**单点瓶颈**——它的大小决定了你能不能跑长 context、能不能高并发、单 GPU 能服务多少用户。MQA / GQA 不是"优化"，是"决定上不上线"的差别。本文从 KV cache 是什么讲起，到 MQA / GQA 的实战意义，到长 context Agent 的内存估算公式。
>
> 配套：[modern-gpt-block.md](modern-gpt-block.md)、[rope-and-positional-encoding.md](rope-and-positional-encoding.md)、[transformer.md](transformer.md)、[inference-optimization.md](inference-optimization.md)。

---

## 一、为什么 Agent 工程师必须懂 KV Cache

| 你遇到的问题 | KV Cache 是核心解释 |
|---|---|
| Agent 跑长 context 显存爆了 | KV cache 占主导内存，比模型参数还多 |
| 同样模型 vLLM 比 HF Transformers 快 5× | vLLM 的 PagedAttention 是 KV cache 内存管理 |
| 高并发服务器需要 H100 而不是 A100 | A100 80GB 装不下 GQA 70B + 多并发 KV cache |
| 长 prompt cache 命中能省 5× | Prompt cache 复用前缀的 KV |
| 流式输出 first-token 慢、后续快 | Prefill 阶段算 KV cache，decode 阶段 reuse |

**这些问题的根源都是 KV cache**。不懂它就看不见问题。

---

## 二、KV Cache 是什么

### 1. 自回归生成的核心机制

LLM 生成是逐 token 的：

```
prompt: "今天天气真"
生成 token 1: "好"   → context: "今天天气真好"
生成 token 2: "，"   → context: "今天天气真好，"
生成 token 3: "适"   → context: "今天天气真好，适"
...
```

每一步生成时，模型都要做 attention：

```
当前 token Q · 历史所有 token 的 K, V → 决定下一个 token
```

**问题**：每生成一个 token，都要重新算所有历史 token 的 K, V？太浪费——它们没变。

### 2. KV Cache 的核心思路

历史 token 的 K, V **算一次缓存起来**，下次直接用：

```
prefill 阶段（处理 prompt）:
  对所有 prompt token 计算 K, V，缓存到 KV cache 中

decode 阶段（生成）:
  每生成一个新 token：
    1. 只算新 token 的 Q, K, V
    2. 把新 token 的 K, V 追加到 KV cache
    3. 用新 Q 和 cache 中的所有 K, V 做 attention
    4. 生成下一个 token
```

**省下的计算**：从 O(seq_len²) 降到 O(seq_len)。这是**让 LLM 推理可行**的关键工程。

### 3. KV Cache 的代价：内存

省下了计算，但**内存消耗惊人**：

```
KV_cache_size = 2 × n_layers × n_heads × head_dim × seq_len × batch
                ↑
            (K and V)
```

每个数字都很大：
- `n_layers`: 80 (Llama 70B)
- `n_heads`: 64
- `head_dim`: 128
- `seq_len`: 8K（甚至 100K）
- `batch`: 多并发

```
Llama 2 70B（MHA）8K context, batch=1, FP16：
= 2 × 80 × 64 × 128 × 8192 × 1 × 2 bytes
= 21 GB
```

**21 GB 全是 KV cache**。模型本身 70B × 2 bytes = 140 GB；KV cache 已经占用了不可忽视的一份额。

并发就更夸张：batch=4 → 84 GB KV cache；batch=10 → 210 GB。

### 4. KV Cache 的两大问题

```
问题 1：内存爆炸
  长 context 或高并发时，KV cache 比模型还大

问题 2：碎片化
  不同请求的 cache 大小不同，传统内存分配方式产生大量碎片
  → vLLM 的 PagedAttention 解决这个
```

---

## 三、MHA：经典的"每个 head 独立 K/V"

### 1. Multi-Head Attention 的工作方式

把 attention 拆成 N 个 head 并行做：

```python
for h in range(n_heads):
    Q_h = x @ W_q_h      # head h 的独立 Query
    K_h = x @ W_k_h      # head h 的独立 Key
    V_h = x @ W_v_h      # head h 的独立 Value
    
    attn_h = softmax(Q_h K_h^T / √d) @ V_h

output = concat(attn_1, ..., attn_n) @ W_o
```

每个 head 学习不同的"关注方式"——有的看语法关系，有的看共指，有的看长距依赖。

### 2. KV cache 在 MHA 下

每层、**每个 head**、每个 token 都要存 K 和 V：

```
KV_cache = 2 × n_layers × n_heads × head_dim × seq_len × batch
                          ↑
                      MHA 这里是完整的 n_heads
```

**Llama 2 70B MHA 的痛苦**：n_heads=64，KV cache 巨大，单卡装不下长 context。

---

## 四、MQA：所有 head 共享一组 K/V

### 1. Multi-Query Attention（Shazeer, 2019）

```python
for h in range(n_heads):
    Q_h = x @ W_q_h     # 每个 head 仍有独立 Query
K = x @ W_k             # 所有 head 共享同一个 Key   ← !
V = x @ W_v             # 所有 head 共享同一个 Value ← !

for h in range(n_heads):
    attn_h = softmax(Q_h K^T / √d) @ V  # 用同一份 K, V
```

### 2. KV cache 骤降到 1/n_heads

```
KV_cache = 2 × n_layers × 1 × head_dim × seq_len × batch
                          ↑
                      MQA 这里是 1
```

**Llama 2 70B 改 MQA → KV cache 从 21 GB → 0.33 GB**，节省 64 倍。

### 3. 代价：模型质量下降

所有 head 看同一份 K/V，**每个 head 失去了"独立关注空间"**——表达力受损。

实测：MQA 在某些任务上**质量下降 1-2%**，特别是需要细粒度信息的任务（推理、代码生成）。

### 4. 谁在用 MQA

- PaLM（Google）
- Falcon
- 部分推理优化版本

主流没大规模用。**因为有了更平衡的方案：GQA**。

---

## 五、GQA：折中方案（现代 LLM 标配）

### 1. Grouped-Query Attention（Ainslie et al., 2023）

把 head 分组，**组内共享 K/V**：

```
n_heads = 64
n_kv_heads = 8         ← K/V 数量
group_size = 64/8 = 8   ← 每组 8 个 Q-head 共享一组 K/V

第 0 组：Q-head 0-7 共享 K_0, V_0
第 1 组：Q-head 8-15 共享 K_1, V_1
...
第 7 组：Q-head 56-63 共享 K_7, V_7
```

```python
for h in range(n_heads):
    Q_h = x @ W_q_h           # 64 个独立 Query

for g in range(n_kv_heads):
    K_g = x @ W_k_g           # 8 个 Key
    V_g = x @ W_v_g           # 8 个 Value

for h in range(n_heads):
    g = h // group_size       # head 属于哪一组
    attn_h = softmax(Q_h K_g^T / √d) @ V_g
```

### 2. KV cache 减少 8 倍

```
KV_cache = 2 × n_layers × n_kv_heads × head_dim × seq_len × batch
                          ↑
                      GQA 这里是 n_kv_heads（远小于 n_heads）
```

n_heads=64, n_kv_heads=8 → KV cache 减少 8 倍。

### 3. 模型质量几乎不掉

实测：GQA 相比 MHA **质量下降 < 1%**（甚至有时不掉）。

为什么？8 组 K/V 已经足够提供"多样的关注空间"——不像 MQA 极端到只有 1 组。

### 4. GQA 是现代 LLM 的标配

```
Llama 1 7B:    n_heads=32, n_kv_heads=32     → MHA
Llama 2 70B:   n_heads=64, n_kv_heads=8      → GQA-8
Llama 3 8B:    n_heads=32, n_kv_heads=8      → GQA-4
Llama 3 70B:   n_heads=64, n_kv_heads=8      → GQA-8
Mistral 7B:    n_heads=32, n_kv_heads=8      → GQA-4
Mixtral 8x7B:  n_heads=32, n_kv_heads=8      → GQA-4
Qwen 2 72B:    n_heads=64, n_kv_heads=8      → GQA-8
DeepSeek V2:   特殊架构 MLA（KV 压缩到更小）
Claude:        闭源，但根据性能特征推测用 GQA
```

---

## 六、三种方案对比

```
                        MHA          GQA-8         MQA
─────────────────────────────────────────────────────────
KV cache 大小 (Llama 70B 8K)
                        21 GB        2.6 GB        0.33 GB
减少倍数               1×           8×            64×
推理速度（生成）        基线         +2-3×         +3-5×
模型质量（benchmark）   基线         -0.5%         -1.5%
代表模型              Llama 1     Llama 2/3      PaLM
```

**结论**：GQA 是**最佳性价比**——KV cache 减少 8 倍，质量几乎不掉。

---

## 七、Agent 工程师必须懂的 5 个实战要点

### 实战 1：看模型 spec 里的 `n_kv_heads`

判断模型对长 context 的友好度：

| 模型 | n_kv_heads | 评价 |
|---|---|---|
| Llama 1 7B | 32 (= n_heads) | MHA，长 context 痛苦 |
| Llama 2 7B | 32 | MHA，外推靠 PI |
| Llama 2 70B | 8 | GQA-8，已经很好 |
| Llama 3 8B | 8 | GQA-4，长 context 友好 |
| Mistral 7B | 8 | GQA-4，速度快 |

**判断**：n_kv_heads 越小，长 context 性能越好。**MQA (n_kv_heads=1)** 最激进，但很少用。

### 实战 2：估算长 context Agent 内存

公式（**记住这个**）：

```
KV_cache_GB = 2 × n_layers × n_kv_heads × head_dim × seq_len × batch × 2 / 1e9
                   ↑
              注意是 n_kv_heads 不是 n_heads
```

**例子 1：Llama 3 70B 跑 100K context, batch=4**

```
= 2 × 80 × 8 × 128 × 100000 × 4 × 2 / 1e9
= 131 GB

→ 单卡 H100 (80GB) 装不下，必须 2 卡 + tensor parallel 或量化
```

**例子 2：Llama 3 8B 跑 32K context, batch=8**

```
= 2 × 32 × 8 × 128 × 32000 × 8 × 2 / 1e9
= 33 GB

→ 单卡 A100 80GB 能跑，但加上模型参数 (16GB) 后并发受限
```

**例子 3：Llama 2 70B (MHA) 跑 8K context, batch=1**

```
= 2 × 80 × 64 × 128 × 8000 × 1 × 2 / 1e9
= 21 GB（仅 KV cache）

→ 单卡 H100 80GB - 模型 140GB（FP16） → 装不下！必须量化或多卡
```

### 实战 3：MQA / GQA 决定你能不能服务高并发

并发 = 同时跑的请求数。每个请求需要独立 KV cache。

```
H100 80 GB × 1 卡：

Llama 70B-MHA, INT8 量化（模型 70GB）：
  剩余内存 10GB → 装不下 1 个完整 8K 请求 → OOM
  
Llama 70B-GQA8, INT8 量化（模型 70GB）：
  每个 8K 请求 KV cache ≈ 2.6 GB → 可服务 3-4 并发

Llama 8B-GQA4, FP16（模型 16GB）：
  剩余内存 64GB → 每个 32K 请求 ≈ 4 GB → 可服务 16 并发
```

→ GQA 不是"快了 10%"，是**"能不能上线"的差别**。

### 实战 4：vLLM / TGI 的 PagedAttention 也是为了 KV cache

[../production/latency-optimization.md](../production/latency-optimization.md) 提过的 vLLM——它的核心创新是**像 OS 管虚拟内存一样管 KV cache**：

- 把 KV cache 切成固定大小的 page（比如 16 个 token 一个 page）
- 不同请求的 page 可以混合存放
- 内存碎片大幅减少
- 不同请求可以共享公共前缀的 page（prompt cache 的底层机制）

**效果**：吞吐量 2-4 倍。**所有这些工程优化的对象都是 KV cache**——KV cache 大就性能差，是定律。

### 实战 5：Prompt Caching 的本质

[../production/latency-optimization.md](../production/latency-optimization.md) 里讲的 prompt cache，本质是 **KV cache 跨请求复用**：

```
请求 1: [system_prompt] + [user_query_1]
        计算 KV cache → 存
        生成 → 返回

请求 2: [system_prompt] + [user_query_2]   ← system_prompt 相同
        发现 system_prompt 部分的 KV 已缓存
        只算 user_query_2 部分的 KV
        → 速度快 5-10×，成本省 80-90%
```

**前提**：前缀必须**逐 token 完全相同**——RoPE 是相对位置，不影响这件事；GQA 也不影响（K, V 仍然按 token 算）。

---

## 八、深入：MLA（DeepSeek V2 的进一步压缩）

GQA 已经把 KV cache 减少 8 倍。**还能更激进吗**？DeepSeek V2 给出了答案：**Multi-head Latent Attention (MLA)**。

### 核心思路

```
GQA: 把 K, V 的 head 数减少 → KV cache 大小 = 2 × n_kv_heads × head_dim
MLA: 把 K, V 压缩成低秩 latent → KV cache 大小 = latent_dim（< 2 × n_kv_heads × head_dim）
```

具体做法：
- 不直接缓存 K, V
- 缓存一个低维 latent vector（~512 维）
- 用时通过线性变换还原 K, V

**收益**：DeepSeek V2 的 KV cache 比 GQA 还小 4-5 倍，跑 128K context 内存可控。

**意义**：长 context 推理优化的下一个前沿，**还在演化中**。

---

## 九、长 context 的"免费午餐"幻觉

Agent 工程师容易掉的陷阱：**以为 100K context 是免费的**。

### 真相 1：KV cache 内存随长度线性增长

```
8K context: 2.6 GB
32K context: 10 GB
100K context: 33 GB
1M context: 330 GB ← 不可行
```

### 真相 2：Attention 计算还是 O(n²)

即使 KV cache 用 GQA 减少了内存，**attention 计算量仍随长度二次增长**：

```
8K: 1× 计算
32K: 16× 计算
100K: 156× 计算
1M: 15625× 计算 ← 慢到无法用
```

Flash Attention 等优化能改善常数，但**复杂度天花板还在**。

### 真相 3：长 context 模型的 first-token 慢

prefill 阶段要算所有 prompt token 的 KV → 长 prompt 的 prefill 时间显著：

```
8K prompt prefill: ~300ms
100K prompt prefill: ~3-5s
```

**这就是为什么 Claude / Gemini 处理 100K context 时第一个 token 出来要 3-10 秒**。

### 真相 4：长 context 不等于"会用长 context"

即使能装 200K，模型注意力分布仍可能漂移（详见 [rope-and-positional-encoding.md](rope-and-positional-encoding.md) "lost in the middle"）。

**实战建议**：
- 默认用 RAG 而不是塞所有内容
- 真要长 context 时，**关键信息放开头或结尾**
- 估算成本时，KV cache 内存 + prefill 延迟一起算

---

## 十、关键 takeaway

1. **KV Cache 是 LLM 推理的内存大头**——长 context、高并发时都受它制约。
2. **MHA → GQA → MQA**：是 KV cache 大小和模型质量的权衡，**GQA 是甜点**。
3. **现代 LLM 几乎都是 GQA**——n_kv_heads 是判断长 context 友好度的关键指标。
4. **KV cache 内存估算**：`2 × n_layers × n_kv_heads × head_dim × seq_len × batch × 2 / 1e9 GB`。
5. **vLLM / TGI / Prompt Cache 的核心都是 KV cache 优化**——理解 KV cache = 理解 LLM 推理工程。
6. **长 context 不是免费午餐**：内存线性增长 + attention 计算二次增长 + first-token 延迟显著。

---

## 十一、扩展阅读

- [modern-gpt-block.md](modern-gpt-block.md) —— 现代 GPT Block 整体演化
- [rope-and-positional-encoding.md](rope-and-positional-encoding.md) —— 位置编码 + 长 context 外推
- [transformer.md](transformer.md) —— Attention 与 KV cache 基础
- [inference-optimization.md](inference-optimization.md) —— 量化、Flash Attention、PagedAttention
- [../production/latency-optimization.md](../production/latency-optimization.md) —— Prompt cache + 工具并行 + streaming
- 论文：*Fast Transformer Decoding: One Write-Head is All You Need* (Shazeer 2019, MQA)
- 论文：*GQA: Training Generalized Multi-Query Transformer Models from Multi-Head Checkpoints* (Ainslie 2023, GQA)
- 论文：*Efficient Memory Management for Large Language Model Serving with PagedAttention* (Kwon 2023, vLLM)
- 论文：*DeepSeek-V2: A Strong, Economical, and Efficient Mixture-of-Experts Language Model* (DeepSeek 2024, MLA)
