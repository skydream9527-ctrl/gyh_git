# 01. 原始 Transformer 架构（2017）

> 本文目标：用最少的数学讲清楚 2017 年原始 Transformer 的**架构骨架与设计动机**。读完你能在白板上画出 Encoder-Decoder + Multi-Head Attention 的全图，并解释每个模块为什么存在。
>
> 与 [../llm-fundamentals/transformer.md](../llm-fundamentals/transformer.md) 的分工：那边偏"机制直觉与工程后果（O(n²)、KV Cache、prompt cache）"；本文偏"原始论文设计 + 后续被改造的部分"。

---

## 一、问题：2017 年之前 NLP 的瓶颈

| 模型 | 优点 | 致命缺点 |
|---|---|---|
| **RNN / LSTM** | 天然处理序列 | 串行计算，长距离依赖会"遗忘"，训练慢 |
| **Seq2Seq (RNN-Encoder + RNN-Decoder)** | 可做翻译 | encoder 必须把整句话压成一个向量，瓶颈严重 |
| **Seq2Seq + Attention（Bahdanau 2014）** | 解码时回看 encoder 各位置 | 仍然 RNN 串行 |
| **CNN（ConvS2S）** | 可并行 | 长距离要堆很多层 |

> **核心痛点**：要么并行不行（RNN），要么长距离不行（CNN），要么瓶颈太窄（一个 context vector）。

Transformer 的论文标题就是宣战：**Attention Is All You Need**——只用 attention，不要 RNN，不要 CNN。

---

## 二、整体架构图

原始 Transformer 是为**机器翻译（English → German）**设计的，所以是 Encoder-Decoder 结构：

```
输入序列                                               输出序列
"I love AI"                                          "Ich liebe KI"
   │                                                       ▲
   ▼                                                       │
┌──────────────┐                                  ┌──────────────┐
│ Input Embed  │                                  │ Output Embed │
│  + Pos Enc   │                                  │  + Pos Enc   │
└──────┬───────┘                                  └──────┬───────┘
       │                                                 │
       ▼                                                 ▼
  ┌─────────┐                                       ┌─────────┐
  │Encoder  │                                       │Decoder  │
  │ Layer 1 │                                       │ Layer 1 │
  │  ┌───┐  │                                       │  ┌───┐  │
  │  │MHA│  │                                       │  │Masked MHA│
  │  └───┘  │                                       │  └───┘  │
  │  ┌───┐  │                                       │  ┌───┐  │
  │  │FFN│  │                                       │  │Cross-Attn│ ←─── Encoder 输出
  │  └───┘  │                                       │  └───┘  │
  └────┬────┘                                       │  ┌───┐  │
       │                                            │  │FFN│  │
       │  × 6 层                                    │  └───┘  │
       │                                            └────┬────┘
       │                                                 │  × 6 层
       └────────────── Encoder 输出 K, V ────────────────┘
                                                         │
                                                         ▼
                                                   ┌──────────┐
                                                   │  Linear  │
                                                   │ + Softmax│
                                                   └──────────┘
                                                         │
                                                         ▼
                                                   "Ich liebe KI"
```

**关键观察**：

1. **Encoder 6 层 + Decoder 6 层**（论文 base 版），每层结构高度模块化。
2. **Encoder 用普通 Self-Attention**（双向），**Decoder 用 Masked Self-Attention**（单向，只能看左边）。
3. **Decoder 多一个 Cross-Attention**：Q 来自 decoder，K/V 来自 encoder——这是 encoder 信息流入 decoder 的唯一通道。
4. **每个 sub-layer 都是**：`Sub-layer → Add(残差) → LayerNorm`（这就是 Post-Norm，后面会讲为什么被淘汰）。

---

## 三、核心模块逐一拆解

### 3.1 Token Embedding + Position Encoding

```
token_id → Embedding 矩阵 → 词向量（512 维）
                                  +
                          Position Encoding（512 维）
                                  ↓
                              输入到 Encoder
```

**为什么要加位置编码？**
Self-Attention 是**置换等变**的——把句子里的 token 顺序打乱，输出也只是跟着打乱。所以模型本身**不知道顺序**。必须显式注入位置信息。

**原始论文用 sin/cos 位置编码**：

```
PE(pos, 2i)   = sin(pos / 10000^(2i/d))
PE(pos, 2i+1) = cos(pos / 10000^(2i/d))
```

直觉：每个位置编成一个独特的"波形指纹"，**任意两个位置的距离可以通过线性变换从 PE 中恢复**。

> 这套方案在 GPT-2 时代被换成可学习的位置嵌入，又在 LLaMA / GPT-NeoX 时代被换成 **RoPE**（旋转位置编码）。详见 [02-architectural-evolution.md](02-architectural-evolution.md) §3。

### 3.2 Multi-Head Self-Attention

**单头公式**：

```
Q = X · W_Q
K = X · W_K
V = X · W_V
Attention(Q, K, V) = softmax(QK^T / √d_k) · V
```

**为什么要 Multi-Head？** 原文 8 头。直觉：

> 一个头只能学一种"关注模式"。多头让模型在**不同子空间**并行学多种关系：句法、共指、语义、长距离…

```
                  ┌─ Head 1 ─→ output 1 ┐
   X (输入) ──→  ├─ Head 2 ─→ output 2 ┤  → Concat → Linear → 输出
                  ├─ ...                 │
                  └─ Head 8 ─→ output 8 ┘
```

每个 head 的维度从 d_model=512 降到 d_k=64，**总计算量与单头 512 维相当**（因为 8 × 64 = 512），但表达力更丰富。

> 这套 MHA 后来在 LLaMA 时代被 **GQA**（Grouped-Query Attention）替代——多个 query head 共享一组 K/V，大幅降低 KV Cache 内存。详见 [02-architectural-evolution.md](02-architectural-evolution.md) §5。

### 3.3 Feed-Forward Network（FFN）

每层的"思考"部分：

```
FFN(x) = max(0, x·W1 + b1) · W2 + b2     # ReLU
```

维度变化：`512 → 2048 → 512`（升 4 倍再降回）。

**为什么 FFN 占模型 ~⅔ 参数？**
Attention 在做"信息混合"，FFN 在做"信息加工"。可以理解为：

- Attention：决定"谁和谁说话"
- FFN：每个 token 各自"消化吸收"

> 后来 ReLU 被换成 SwiGLU（GLU 门控 + Swish 激活），FFN 中间维度也从 4× 调到 2.67×。详见 [02-architectural-evolution.md](02-architectural-evolution.md) §4。

### 3.4 残差 + LayerNorm

每个 sub-layer 都包了一层：

```
output = LayerNorm( x + SubLayer(x) )
```

**残差**：让梯度直接回传，深网络才能训得动。
**LayerNorm**：稳定每层的激活分布。

> 原始论文是 **Post-Norm**（先残差后 Norm），训练 100+ 层时不稳定。GPT-2 之后基本都改 **Pre-Norm**（先 Norm 再做 sub-layer），后续又把 LayerNorm 改成 **RMSNorm**。详见 [02-architectural-evolution.md](02-architectural-evolution.md) §2。

### 3.5 Decoder 的 Masked Self-Attention

为什么 decoder 要 mask？因为训练时**不能让模型看到未来的 token**——否则就是答案泄露。

```
QK^T 计算后，把上三角（未来位置）填 -∞，softmax 后变 0：

        t1   t2   t3   t4
   t1 [ ✓  -∞  -∞  -∞ ]
   t2 [ ✓   ✓  -∞  -∞ ]
   t3 [ ✓   ✓   ✓  -∞ ]
   t4 [ ✓   ✓   ✓   ✓ ]
```

这是**自回归**（autoregressive）的本质——预测 t 时只能用 1..t-1。

GPT 系列就是把 decoder 单拎出来做的（**decoder-only**），不要 encoder、不要 cross-attention。

### 3.6 Cross-Attention（仅 decoder 有）

Decoder 的第二个 attention 子层：

```
Q ← decoder 上一层输出
K, V ← encoder 最终输出
```

> 这是机器翻译的核心：解码德语时，每一步都要去看英语原文。GPT 砍掉它，是因为 GPT 的输入和输出在同一个序列里（"语言建模"任务不需要分两端）。

---

## 四、Encoder-only / Decoder-only / Encoder-Decoder 三大流派

原始 Transformer 同时有 Encoder 和 Decoder。**后来被拆成三个流派**：

| 流派 | 代表 | 训练任务 | 适用场景 |
|---|---|---|---|
| **Encoder-only** | BERT, RoBERTa, DeBERTa | Masked LM（双向上下文） | 理解（分类、NER、语义检索 embedding） |
| **Decoder-only** | GPT 系列, LLaMA, Claude, Qwen | Autoregressive LM（左到右） | 生成（chat、coding、推理） |
| **Encoder-Decoder** | T5, BART, FLAN-T5 | Span corruption / seq2seq | 翻译、摘要等明确"输入→输出"任务 |

**为什么 Decoder-only 赢了？**

1. **训练任务最朴素**——下一个词预测（LM），数据只要文本就行。
2. **In-Context Learning** 出现于 Decoder-only（GPT-3, 2020），打开了 Few-shot 能力。
3. **统一处理理解与生成**：你可以让 GPT 做分类（用 prompt 引导），但不能让 BERT 流畅生成。
4. **Scaling 友好**：参数 10×，能力跃升明显，BERT-style 模型规模化收益小得多。

> 这条线后来被 OpenAI 的 *GPT-3 Few-Shot Learners*（2020）和 ChatGPT（2022）彻底推到舞台中央。详见 [03-gpt-series-evolution.md](03-gpt-series-evolution.md)。

---

## 五、原始论文留下的"暗坑"清单

这些坑后来都被填掉，理解它们有助于理解后续演进的动机：

| 暗坑 | 后果 | 谁解决了 |
|---|---|---|
| Post-Norm 深层不稳定 | 100+ 层训不动 | Pre-Norm（GPT-2 / 后续所有） |
| LayerNorm 计算重 | 推理慢、显存大 | RMSNorm（LLaMA） |
| 绝对位置编码外推差 | 训练 2k 不能推 32k | RoPE → NTK / YaRN |
| MHA KV Cache 大 | 长上下文显存炸 | MQA → GQA |
| O(n²) attention | 长序列贵 | Flash Attention（IO-aware） / 稀疏 attention |
| FFN 占参数大 | 大模型推理慢 | MoE（Mixtral / DeepSeek-V3） |
| ReLU 死神经元 | 训练后期收益低 | SwiGLU / GeGLU |

读完 [02-architectural-evolution.md](02-architectural-evolution.md) 你会看到：**今天主流的 LLaMA-style block 几乎每一处都跟原始论文不一样了**——但骨架仍然是那张图。

---

## 六、知识点速查

```
╔══════════════════════════════════════════════════════╗
║                  原始 Transformer 速查                 ║
╠══════════════════════════════════════════════════════╣
║ 论文     : Attention Is All You Need (NeurIPS 2017)   ║
║ 作者     : Vaswani et al. (Google Brain / Toronto)    ║
║ 任务     : 机器翻译 WMT'14 EN-DE / EN-FR              ║
║ 架构     : 6-layer Encoder + 6-layer Decoder          ║
║ d_model  : 512   d_ff: 2048   heads: 8   d_k: 64      ║
║ Norm     : Post-Norm + LayerNorm                       ║
║ Pos Enc  : Sinusoidal（不可学习）                       ║
║ Activation: ReLU                                       ║
║ 训练数据 : ~4.5M 句对（EN-DE）                         ║
║ 参数量   : 65M（base）/ 213M（big）                    ║
║ 核心贡献 : Self-Attention + Multi-Head + Pos Enc       ║
╚══════════════════════════════════════════════════════╝
```

下一篇：[02-architectural-evolution.md](02-architectural-evolution.md) — 这张图怎么一步步演化成 2026 的 LLaMA-style block。
