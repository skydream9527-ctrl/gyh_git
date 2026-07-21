# 02. 架构演进：从 2017 原始 Transformer 到 2026 现代 GPT block

> 本文沿时间线讲清楚 9 年间架构层面的关键改造。每一项改造都附**动机（解决什么问题）→ 做法 → 影响**三段式。
>
> 读完你能回答："今天的 LLaMA-3、DeepSeek-V3、Claude 4 在 block 层面跟 2017 原版有哪些差别？为什么是这些差别？"

---

## 一、演进时间线总览

```
2017  原始 Transformer (Encoder-Decoder, Post-Norm, Sinusoidal PE, MHA, ReLU, LayerNorm)
        │
        ├── 2018  GPT-1: Decoder-only + Pretrain→Finetune
        │
2018-19 ├── BERT (Encoder-only, MLM) ─── 一度主导 NLU
        │
2019    ├── GPT-2: Pre-Norm 取代 Post-Norm
        │           layer_norm 移到 sub-layer 输入端，深层稳定性大涨
        │
2020    ├── GPT-3: 96 层 / 175B / In-Context Learning
        │           证明只靠 Decoder-only + 规模化能涌现 Few-Shot
        │
2021    ├── RoFormer (Su et al.): RoPE 出现 ─── 但当时未被主流采用
        │
2022    ├── PaLM / Chinchilla / GLM-130B: 大规模实验
        │           Chinchilla scaling law: 数据应配 ~20×参数量 token
        │
2023.02 ├── LLaMA 1: 集成 Pre-Norm + RMSNorm + RoPE + SwiGLU
        │           ─── 这是现代 GPT block 的事实标准模板
        │
2023.07 ├── LLaMA 2: GQA (Grouped-Query Attention) ─── 长上下文降本关键
        │
2023.12 ├── Mixtral 8×7B: Sparse MoE ─── 让 MoE 在开源界普及
        │
2024    ├── LLaMA 3 / Qwen2 / DeepSeek-V2: GQA + 长上下文 + MoE 全面普及
        │
2024.12 ├── DeepSeek-V3: MLA (Multi-head Latent Attention) ─── 进一步压 KV Cache
        │
2025-26 └── Claude 4 / GPT-4.5 / Gemini 2.5 / Qwen3:
                  原生多模态 + 1M 长上下文 + Hybrid MoE
```

---

## 二、改造 #1：Post-Norm → Pre-Norm（2019）

### 动机
原始 Transformer 是 Post-Norm：

```
x  → SubLayer →  +x  → LayerNorm  →  下一层
                  ↑残差
```

问题：当层数堆到 50+，**残差信号经过 LayerNorm 后被压缩**，深层梯度消失，训不动。论文里 6 层够用，但 GPT-2 想堆 48 层就出大问题。

### 做法：Pre-Norm

```
x → LayerNorm → SubLayer → +x → 下一层
                            ↑残差通路完全打通
```

LayerNorm 移到 sub-layer 入口，**残差通路从输入到输出无损**。

### 影响
- **训练稳定**：可以堆到 100+ 层（GPT-3 是 96 层），warmup 也没那么娇贵。
- **代价**：表达力略弱于 Post-Norm（数据上有 paper 报告 Post-Norm 在小模型上稍优），但工程上压倒性胜利。
- **现状**：2019 年后所有主流 LLM 都用 Pre-Norm。

> 参考：*On Layer Normalization in the Transformer Architecture*（Xiong et al., ICML 2020）。

---

## 三、改造 #2：LayerNorm → RMSNorm（2023）

### 动机
LayerNorm 公式：

```
LN(x) = γ · (x - μ) / σ + β       (μ, σ 在最后一维上算)
```

两个开销：(1) 算 μ 要 reduce-mean，(2) 有 β 参数。

实验发现：**减均值（centering）这一步对结果几乎没贡献**，纯粹是浪费。

### 做法：RMSNorm

```
RMSNorm(x) = γ · x / RMS(x)       RMS(x) = sqrt(mean(x²))
```

只做缩放，不减均值，没有 β。

### 影响
- **算子更简单**：去掉 reduce-mean，少一次 pass。
- **推理快 ~7-10%**（实测，long context 下更明显）。
- **效果几乎一致**——T5、LLaMA、Qwen、DeepSeek 都用了。
- **现状**：2023 LLaMA 之后，主流模型清一色 RMSNorm。

> 参考：*Root Mean Square Layer Normalization*（Zhang & Sennrich, NeurIPS 2019），但真正普及靠 LLaMA。

---

## 四、改造 #3：Sinusoidal/Learned PE → RoPE（2023 普及）

### 动机三连击

| 方案 | 缺点 |
|---|---|
| Sinusoidal（原版） | 加在输入上，**和 Attention 计算解耦**，长度外推勉强但效果差 |
| Learned PE（GPT-2） | 训练长度 = 推理长度的硬上限，**完全不能外推** |
| Relative PE（T5） | 引入 bias 参数，长 context 实现复杂 |

> 想做长上下文的**根本瓶颈**：训练在 4k 上，推理希望到 32k / 128k。Sin/Cos 和 Learned 都不行。

### 做法：RoPE（Rotary Position Embedding）

把位置编码做成**对 Q/K 的旋转矩阵**：

```
对每对维度 (2i, 2i+1)，根据位置 m 旋转角度 θ_m,i：

[ q_2i  ]    [ cos(mθ_i)  -sin(mθ_i) ] [ q_2i  ]
[ q_2i+1] →  [ sin(mθ_i)   cos(mθ_i) ] [ q_2i+1]

其中 θ_i = 10000^(-2i/d)  ← 高维度旋转慢，低维度旋转快
```

关键性质：**两个位置 m 和 n 的 attention score 只依赖于它们的相对距离 (m-n)**，但实现上是**绝对位置**注入到 Q/K 的，不需要额外参数。

### 长度外推的几个套路

| 方法 | 思路 | 何时用 |
|---|---|---|
| Position Interpolation (PI) | 线性压缩位置坐标 | 简单粗暴，需要少量微调 |
| **NTK-aware Scaling** | 高频维度旋转更慢 | 不微调也能扩 2-4× |
| **YaRN** | NTK + 温度系数 + 注意力缩放 | 当前主流，可扩 16× |
| LongRoPE / DCA | 动态调 θ | 1M context 必备 |

### 影响
- **几乎所有主流模型都用了 RoPE**：LLaMA、Qwen、Mistral、DeepSeek、ChatGLM。
- 长上下文能力**大幅解锁**：从 LLaMA1 的 2k 一路推到 LLaMA3.1 的 128k、Qwen2.5-1M。
- Anthropic Claude 3 / Gemini 1.5 Pro 是公开**没确认**用 RoPE 的，可能用了别的方案（外部猜测包括 ALiBi 变体或自研）。

> 详细推导：[../llm-fundamentals/rope-and-positional-encoding.md](../llm-fundamentals/rope-and-positional-encoding.md)。

---

## 五、改造 #4：ReLU → SwiGLU（2022 后普及）

### 动机
原始 FFN：

```
FFN(x) = ReLU(x·W1) · W2         # 只用 W1, W2 两个矩阵
```

ReLU 有"死神经元"问题，且 FFN 是模型 ⅔ 参数量，不优化太亏。

### 做法：SwiGLU（GLU + Swish）

```
FFN_SwiGLU(x) = ( Swish(x·W1) ⊙ x·V ) · W2
                              ↑GLU 门控
```

引入第三个矩阵 V 做"门控"——决定每个维度过去多少信息。中间维度从 4× 调到 ~2.67× 以保持参数量近似不变。

### 影响
- **PaLM（2022）**首次大规模验证 SwiGLU 效果好。
- **LLaMA 系**全用，是事实标准。
- **代价**：多一个矩阵 V，但维度下调后总参数持平，**效果稳定提升 1-2%**。
- **GeGLU**（GELU + GLU）是另一选择，效果差不多，看团队习惯。

---

## 六、改造 #5：MHA → MQA → GQA（2023）

### 动机
Multi-Head Attention 的 KV Cache 内存压力：

```
KV Cache 大小 = 2（K和V） × n_heads × seq_len × d_head × n_layers × dtype
              = 2 × 32 × 32k × 128 × 32 × 2字节
              ≈ 16 GB    ← 单 batch 单序列！
```

长上下文下，**KV Cache 比模型权重还大**。这直接限制了"一张 GPU 能并发多少 session"。

### 三种方案对比

```
MHA: 每个 query head 配一对独立的 K/V head
   Q1 Q2 Q3 ... Q32
   |  |  |     |
   K1 K2 K3 ... K32     V1 V2 V3 ... V32      (32 套 K/V)

MQA (Multi-Query Attention): 所有 Q 共享 1 对 K/V
   Q1 Q2 Q3 ... Q32
    \  \  \    /
        K1            V1                       (1 套 K/V)
   ↑KV Cache 压到 1/32，但效果掉

GQA (Grouped-Query Attention): Q 分组，组内共享 K/V
   Q1 Q2 Q3 Q4   Q5 Q6 Q7 Q8 ...
    \  \  /  /    \  \  /  /
       K1, V1         K2, V2  ...              (8 组，8 套 K/V)
   ↑KV Cache 压到 1/4，效果几乎不掉
```

### 影响
- **LLaMA 2 70B**：首次大规模上 GQA。
- **几乎所有现代 LLM**：GQA 已成默认（LLaMA 3、Qwen2、Mistral 7B、Claude 3 实测形态）。
- **DeepSeek V2/V3 的 MLA**：再进一步——把 K/V 投影到一个低秩 latent space，KV Cache 再压 5-10×。

> 详细：[../llm-fundamentals/mqa-gqa-and-kv-cache.md](../llm-fundamentals/mqa-gqa-and-kv-cache.md)。

---

## 七、改造 #6：Dense → MoE（2023-2024 普及）

### 动机
"想要更大模型，但推理时不想多花 N 倍算力"。

### 做法：Mixture of Experts

每个 FFN 层不是一个大 FFN，而是**多个并行的小 FFN（experts）+ 一个 router**：

```
                  ┌─ Expert 1 ─┐
                  ├─ Expert 2 ─┤    每个 token 只走 top-K 个
   token  →  Router            ├──→ 加权求和
                  ├─ Expert N ─┤    (例如 K=2 / N=8)
                  └─ ...       ┘
```

**示例**：Mixtral 8×7B
- 总参数 47B
- 每个 token 实际激活 ~13B（因为 router 只选 top-2 expert）
- 推理速度 ≈ 13B 模型，能力 ≈ 47B 模型

### 影响与坑
- **路由不平衡**：某些 expert 被冷落，需要负载均衡 loss。
- **训练复杂度高**：MoE 训练不稳定，需要专门技巧。
- **DeepSeek-V3**（2024.12）：256 个 expert，超细粒度，token 路由 8 个，配合 MLA，达到与 GPT-4 同档能力但激活参数仅 37B。
- **闭源**：GPT-4、Gemini Ultra、Claude Opus 几乎肯定是 MoE，但都没公开细节。

> 参考：*Switch Transformer*（Fedus 2021）、*Mixtral of Experts*（2023）、*DeepSeekMoE*（2024）。

---

## 八、改造 #7：Flash Attention / PagedAttention（2022-2023）

这两项**不是模型架构改动，而是 attention 计算/存储的工程优化**——但对 LLM 的实际可用性影响巨大。

### Flash Attention（Dao et al. 2022）
**核心思路**：传统 attention 把 N×N 注意力矩阵写到 HBM（显存），IO 占大头。FlashAttention **分块计算 + 不写出中间矩阵**，数学等价但 IO 量降一两个量级。

### PagedAttention / vLLM（Kwon et al. 2023）
**核心思路**：把 KV Cache 像操作系统分页那样按 block 管理，**消除内存碎片**，吞吐量翻倍以上。

### 影响
现在所有生产级推理引擎（vLLM、TGI、TensorRT-LLM、SGLang）都基于这两项做。

---

## 九、改造 #8：长上下文（2023-2026）

### 三个杠杆
1. **位置编码外推**：RoPE + NTK / YaRN（讲过）。
2. **稀疏 / 滑窗 attention**：Mistral 用滑动窗口（local + global），Gemini 1.5 用 Ring Attention（多 GPU 分块）。
3. **上下文缓存**：Anthropic Prompt Caching、DeepSeek Context Cache、Gemini Context Cache——把长 system prompt 的 K/V **预计算并缓存**，新请求复用。

### 现状（2026 上半年）
- 主流：128k - 200k 通用
- 长板：Gemini 2.5 Pro 1M、Claude 4 Opus 1M、Qwen 2.5-Turbo 1M
- "有效"长度 ≠ 标称长度：实际 needle-in-haystack / RULER 测试中，超过 200k 后多数模型都掉。

---

## 十、把所有改造拼回去：现代 GPT Block（LLaMA-3 风格）

```
              ┌─────────────────────────────────────────┐
              │                                         │
   x ────→ RMSNorm ─→ Self-Attention (GQA + RoPE)       │
              │                                         │
              │← Residual ────────────────────────── + ←┘
              │
              ↓
              ┌─────────────────────────────────────────┐
              │                                         │
              RMSNorm ─→ FFN(SwiGLU)                    │
              │                                         │
              │← Residual ────────────────────────── + ←┘
              ↓
            下一层
```

对比 2017 原版：

| 模块 | 2017 原版 | 2026 LLaMA-3 风格 |
|---|---|---|
| 整体结构 | Encoder-Decoder | **Decoder-only** |
| Norm | Post-Norm + LayerNorm | **Pre-Norm + RMSNorm** |
| 位置编码 | Sinusoidal | **RoPE** |
| Attention | MHA | **GQA**（DeepSeek 用 MLA） |
| FFN | ReLU + 4× | **SwiGLU + ~2.67×** |
| 激活模式 | Dense | **可选 MoE** |
| Attention 内核 | Naïve O(n²) | **Flash Attention 2/3** |
| 推理 | 朴素 KV Cache | **PagedAttention + Prefix Cache** |

骨架还是那张图，但每一处都被换过零件。

---

## 十一、还在演进中（2025-2026）

| 方向 | 代表 | 状态 |
|---|---|---|
| **MLA**（DeepSeek） | DeepSeek-V2/V3 | 论文公开，开源界开始跟进 |
| **Mamba / State Space Models** | Mamba 2、Jamba | 与 Transformer 混合，长序列效率优势，但生态弱 |
| **Linear Attention 卷土重来** | RWKV-7、RetNet | 推理 O(n)，但能力上限有限，作为 Hybrid 模块更现实 |
| **Test-time Compute** | OpenAI o1/o3、DeepSeek-R1 | 不是架构改动，是**推理范式**改动——把"想"放进去，详见 [03-gpt-series-evolution.md](03-gpt-series-evolution.md) §6 |
| **Diffusion LM** | Mercury Coder | 离散 diffusion 做生成，并行解码，速度快 |

---

## 十二、给开发者的实操建议

| 你在做什么 | 该选什么模板 |
|---|---|
| 训自己的 LLM | LLaMA-3 风格：Decoder-only + Pre-Norm + RMSNorm + RoPE + GQA + SwiGLU |
| 部署生产推理 | vLLM / SGLang / TensorRT-LLM（自带 FlashAttn + PagedAttn） |
| 长上下文应用 | 优先 prompt cache + 测 NIAH/RULER 看有效长度 |
| 想压成本/上规模 | MoE（Mixtral / DeepSeek 路线），但要有训练能力 |
| 要做研究/对比 | 直接拿 nanoGPT / litgpt 起步，魔改各零件 |

---

下一篇：[03-gpt-series-evolution.md](03-gpt-series-evolution.md) — 在这个架构演进的基础上，GPT 系列模型本身（GPT-1 → o3）走过了什么路。
