# 现代 GPT Block：从教科书 Transformer 到 Llama 3 / Claude

> [transformer.md](transformer.md) 讲了 Transformer 的基础机制（attention、QKV、位置编码、KV cache）。本文讲**从原始 Transformer 到 2026 年现代 LLM**之间发生的五个关键改造，以及它们对 Agent 工程师的实战意义。
>
> 配套：[rope-and-positional-encoding.md](rope-and-positional-encoding.md)（RoPE 深度）、[mqa-gqa-and-kv-cache.md](mqa-gqa-and-kv-cache.md)（KV cache 与并发）、[inference-optimization.md](inference-optimization.md)（推理加速）。

---

## 一、为什么 Agent 工程师要懂这些

很多人把 LLM 当黑盒，结果**这些"黑盒之内"的事会以性能账单和能力边界的形式找上门**：

| 你遇到的现象 | 真正的原因 |
|---|---|
| 长 context Agent 又慢又贵 | KV Cache 大小 = 2 × layers × heads × dim × seq_len |
| Llama 2 在 100K 跑出乱码，Llama 3 不会 | RoPE scaling（NTK / YaRN） |
| Mistral / Llama 3 推理特别快 | GQA 把 KV cache 减了 8 倍 |
| Claude / Gemini 能稳定跑超长 context | RoPE 外推 + GQA + 工程优化的合力 |
| 同样参数量，新模型更聪明 | SwiGLU + RMSNorm + Pre-Norm 的累积红利 |
| 微调小模型时不稳定 | LayerNorm vs RMSNorm，Post-Norm vs Pre-Norm |

不懂 → 选模型、调延迟、估成本全凭直觉。
懂了 → **看一眼模型架构就知道它在长 context 上的表现**。

---

## 二、整体演化：一张图看清

```
[Vanilla Transformer (2017)]            [Modern GPT Block (Llama 3 / Claude / Mistral)]

  ┌─────────────────────┐                ┌─────────────────────┐
  │  Multi-Head Attn    │                │  RMSNorm            │ ← Pre-Norm
  │   (Absolute PosEmb) │                │       ↓              │
  │       ↓              │                │  Multi-Head Attn    │
  │  Add (residual)     │                │   (RoPE + GQA)      │
  │       ↓              │                │       ↓              │
  │  LayerNorm          │ ← Post-Norm    │  Add (residual)     │
  │       ↓              │                │       ↓              │
  │  FFN (GeLU)         │                │  RMSNorm            │
  │       ↓              │                │       ↓              │
  │  Add (residual)     │                │  FFN (SwiGLU)       │
  │       ↓              │                │       ↓              │
  │  LayerNorm          │                │  Add (residual)     │
  └─────────────────────┘                └─────────────────────┘
        × N 层                                   × N 层
```

---

## 三、五个核心改造速览

| 改造 | 旧 | 新 | 收益 |
|---|---|---|---|
| **Norm 位置** | Post-Norm | Pre-Norm | 深层稳定 |
| **Norm 方式** | LayerNorm | RMSNorm | 更快 + 更稳 |
| **位置编码** | 绝对位置 | RoPE | 长度外推 |
| **激活函数** | ReLU/GeLU | SwiGLU | 更强表达 |
| **KV Heads** | MHA | GQA / MQA | KV cache 砍 4-8× |

每一个都不是革命性创新，但**叠加起来让现代 LLM 在长 context 上的表现质变**。

工程师视角：每个改造对你意味着什么——

```
Pre-Norm  → 你能跑 100+ 层的深模型而不爆（GPT-4 估计 120+ 层）
RMSNorm   → 推理快 7-15%（同样硬件）
RoPE      → 训练 8K 的模型能外推到 32K-200K
SwiGLU    → 同样参数量更聪明（评测榜上能感受到）
GQA       → 长 context 推理便宜 4-8×、快 2-4×
```

**实战**：选模型时看架构 spec——有没有 GQA、RoPE 用什么变体，**直接预判它在你 Agent 场景的延迟成本**。

---

## 四、改造 1：Pre-Norm + Residual

### 1. 残差连接

```
y = layer(x) + x
```

让信号有"高速公路"绕过 layer 直达后面。**这是让深层网络可训练的根本**——梯度通过残差路径直接回流，不会消失。

### 2. Norm 放哪里：Post-Norm vs Pre-Norm

```
Post-Norm:   y = LayerNorm(layer(x) + x)
              ↑ Norm 在残差路径"外"

Pre-Norm:    y = layer(LayerNorm(x)) + x
                          ↑ Norm 在残差路径"内"
```

### 3. 为什么 Pre-Norm 让深层模型稳定

**Post-Norm**：每经过一层，残差信号都被 LayerNorm 重新归一化 → 深层时残差作用衰减。

**Pre-Norm**：残差信号**永远不被归一化** → 梯度从最后一层直通第一层。

```
Post-Norm 100 层模型：
  梯度从第 100 层回到第 1 层时，被 LN 缩放了 100 次 → 几乎消失
  → 训练不动

Pre-Norm 100 层模型：
  梯度从第 100 层通过残差直通第 1 层 → 完整保留
  → 能训练
```

### 4. Agent 工程师视角

#### 现代 LLM 都是 Pre-Norm

GPT-3、Llama、Claude、Mistral、Qwen、DeepSeek 全部 Pre-Norm。**Post-Norm 已经是历史**（除了 BERT 系列）。

#### Pre-Norm 让"超深模型"成为可能

```
GPT-2:        48 层（Post-Norm 都已经吃力）
GPT-3:        96 层（Pre-Norm 让这个尺度可行）
GPT-4:        ~120 层（推测）
Llama 3 70B:  80 层
```

更深 = 更强表达 = 更聪明的 Agent。

#### 微调时的稳定性

Agent 工程师常用 LoRA / QLoRA 微调小模型。Pre-Norm 模型：
- **学习率可以大** 5-10×
- **不容易梯度爆炸**
- **fine-tune 收敛快**

跟 RMSNorm 是黄金组合：**Pre-Norm + RMSNorm = 现代 LLM 的标配稳定性方案**。

---

## 五、改造 2：RMSNorm

### 1. LayerNorm 在做什么

$$\text{LayerNorm}(x) = \gamma \cdot \frac{x - \mu}{\sigma} + \beta$$

两步：
1. **零均值化**：减去均值 μ
2. **单位方差化**：除以标准差 σ
3. 可学习的 scale + shift：γ × ... + β

### 2. RMSNorm 的简化

$$\text{RMSNorm}(x) = \gamma \cdot \frac{x}{\text{RMS}(x)}$$

只保留**单位方差化**这一步：
- ❌ 不减均值
- ❌ 不加偏置
- ✅ 保留 scale

```python
def rms_norm(x, gamma):
    rms = (x.pow(2).mean(-1, keepdim=True) + eps).sqrt()
    return gamma * x / rms
```

### 3. 为什么 RMSNorm 够用

理论上：减均值是为了让数值"居中"。但**实证发现**：神经网络中间层的 hidden state 本来就接近零均值（因为初始化 + 优化目标），**显式减均值收益微乎其微**。

去掉之后：
- **计算量减少 ~10-15%**（少一次平均、一次减法、一次加偏置）
- **梯度更稳定**（少了一个数值上敏感的操作）
- **效果几乎不变**

研究在 2019 年就证实了这一点（RMSNorm paper），但直到 Llama 1 (2023) 才大规模在 LLM 里用。

### 4. 工程师视角

| | LayerNorm | RMSNorm |
|---|---|---|
| 浮点运算 | ~6 ops/feature | ~3 ops/feature |
| 可学习参数 | γ + β | 仅 γ |
| 单卡推理速度 | 基线 | +7-15% |
| 训练稳定性 | 标准 | 略优 |
| 长 context | 标准 | 略优 |

**为什么 Agent 工程师要知道**：
- **同样硬件部署，RMSNorm 模型推理快 10%+**
- 选模型时一个隐藏的性能信号
- Llama / Mistral / DeepSeek / Qwen / Claude 全用 RMSNorm

---

## 六、改造 3：RoPE（位置编码）

详见 [rope-and-positional-encoding.md](rope-and-positional-encoding.md)。

### 速览

**问题**：原始 Transformer 用绝对位置编码 → 训练时见过位置 0-512，没见过的位置就懵 → 长度外推一塌糊涂。

**RoPE（Rotary Position Embedding）的核心 trick**：不在 attention 里加位置偏置，**在 Q 和 K 上做旋转**。

```
q_i 旋转 i × θ 度
k_j 旋转 j × θ 度

q_i · k_j = |q||k| × cos((i-j) × θ)  ← 自动得到相对距离！
```

**收益**：
- 编码的是**相对距离**而非绝对位置
- 配合 Position Interpolation / NTK / YaRN，可以**把训练 8K 的模型外推到 200K**
- 现在所有主流 LLM（Llama / Claude / Mistral / Qwen / DeepSeek / Gemini）都用 RoPE

详细原理、数学直觉、长度外推方法、Agent 工程坑见 [rope-and-positional-encoding.md](rope-and-positional-encoding.md)。

---

## 七、改造 4：SwiGLU

### 1. FFN 在 Transformer 里的作用

每层 attention 之后有个 FFN（feed-forward network）：

```
FFN(x) = activation(x @ W1) @ W2
```

这是 Transformer 里**参数量最大的部分**（占 ~2/3 总参数）。**FFN 强弱直接决定模型表达力**。

### 2. 激活函数的演化

```
ReLU(x) = max(0, x)              ← 第一代，简单粗暴
GeLU(x) = x · Φ(x)               ← GPT/BERT 时代，平滑近似
SwiGLU(x) = Swish(x · W_g) · (x · W_u)   ← 现代 LLM
```

### 3. SwiGLU 的核心：门控

```python
def swiglu(x, W_gate, W_up, W_down):
    gate = silu(x @ W_gate)        # 门控信号
    value = x @ W_up                # 值信号
    return (gate * value) @ W_down  # 门控 × 值 → 输出
```

```
x ───┬─→ W_gate ─→ Swish ─┐
     │                       ├─→ × ─→ W_down ─→ output
     └─→ W_up ─────────────┘
```

**关键**：FFN 不再是"简单变换 + 激活"，而是"门控 × 值"——**对每个特征维度独立决定让多少信号通过**。

类比：**SwiGLU 之于 ReLU，类似于 Mixer 之于 Solo**。

### 4. 代价

参数量增加：原来 FFN 用 W1+W2 两个矩阵，SwiGLU 用 W_gate+W_up+W_down 三个。

**所以 SwiGLU 的 hidden_dim 通常是 ReLU FFN 的 2/3**（保持总参数量不变）：

```
ReLU-FFN:    hidden_dim = 4 × d_model
SwiGLU-FFN:  hidden_dim = 8/3 × d_model  (≈ 2.67×)
```

### 5. Agent 工程师视角

SwiGLU 主要是**透明的能力红利**——你看不到，但表现在：
- 同样参数量，benchmark 分数更高
- 更好的 in-context learning（few-shot 跟随能力）
- 微调时数据效率更高

**意义**：当看到"7B 新模型超过 13B 老模型"的报道，**SwiGLU 是其中一个原因**（不是唯一）。

---

## 八、改造 5：MQA / GQA

详见 [mqa-gqa-and-kv-cache.md](mqa-gqa-and-kv-cache.md)。

### 速览

**问题**：经典 MHA（Multi-Head Attention）每个 head 都有独立 K 和 V，KV cache 大到塞不下 GPU。Llama 2 70B 用 MHA 跑 8K context = 21 GB KV cache，**全部 GPU 内存被 KV cache 吃光**。

**GQA（Grouped-Query Attention）**：把 head 分组，组内共享 K/V。

```
n_heads = 64
n_kv_heads = 8        ← K/V 数量（GQA-8）
group_size = 64/8 = 8  ← 每组 8 个 Q-head 共享一组 K/V
```

**收益**：
- KV cache 减少 8 倍（n_heads / n_kv_heads）
- 长 context 推理速度 +2-3×
- 模型质量几乎不掉（实测下降 < 1%）

**MQA（Multi-Query Attention）**：所有 head 共享一组 K/V，KV cache 减少 64 倍，但模型质量下降 ~1.5%。

| | MHA | GQA-8 | MQA |
|---|---|---|---|
| KV cache (Llama 70B 8K) | 21 GB | 2.6 GB | 0.33 GB |
| 减少倍数 | 1× | 8× | 64× |
| 模型质量 | 基线 | -0.5% | -1.5% |

**Llama 3 / Mistral / Qwen 2 / DeepSeek / Claude 都用 GQA**，是现代 LLM 的标配。

详细对比、KV cache 内存估算公式、长 context 并发能力分析见 [mqa-gqa-and-kv-cache.md](mqa-gqa-and-kv-cache.md)。

---

## 九、把五个改造组合在一起：现代 LLM 的"配方"

```python
# 现代 GPT Block 的伪代码（Llama 风格）

class ModernGPTBlock(nn.Module):
    def __init__(self):
        self.attn_norm = RMSNorm(d_model)
        self.attn = MultiHeadAttention(
            n_heads=32,
            n_kv_heads=8,            # GQA-4
            rope=RoPE(theta=500000), # RoPE with NTK
        )
        self.ffn_norm = RMSNorm(d_model)
        self.ffn = SwiGLUFFN(d_model, hidden_dim=8/3 * d_model)
    
    def forward(self, x, kv_cache=None):
        # Pre-Norm + Attention + Residual
        h = x + self.attn(self.attn_norm(x), kv_cache=kv_cache)
        # Pre-Norm + FFN + Residual
        out = h + self.ffn(self.ffn_norm(h))
        return out
```

每一行都是过去 5 年大量论文 + 实证沉淀下来的"最佳实践"。

---

## 十、给 Agent 工程师的检查表

下次选模型 / 调延迟 / 估成本时，**看这些字段**：

| 字段 | 你能学到 |
|---|---|
| `architecture` | 通常是 LlamaForCausalLM 等，能反推风格 |
| `num_hidden_layers` | 层数（影响 KV cache 总量） |
| `num_attention_heads` | Q-head 数 |
| `num_key_value_heads` | **KV head 数（GQA 关键）** |
| `head_dim` | 每个 head 的维度 |
| `intermediate_size` | FFN 隐层大小（通常 8/3 d_model 暗示 SwiGLU） |
| `hidden_act` | 激活函数（"silu" = SwiGLU 系列） |
| `rms_norm_eps` | 用 RMSNorm（vs `layer_norm_epsilon` 是 LayerNorm） |
| `rope_theta` | RoPE base，大值意味着长 context 适配 |
| `max_position_embeddings` | 训练长度 |

```yaml
# Llama 3 70B 配置实例（关键字段）
architecture: LlamaForCausalLM
num_hidden_layers: 80
num_attention_heads: 64
num_key_value_heads: 8        # GQA-8（关键省内存）
hidden_act: silu              # SwiGLU
rms_norm_eps: 1e-5            # RMSNorm
rope_theta: 500000            # 长 context 友好
max_position_embeddings: 8192 # 训练 8K，可外推
```

看到这套配置 = **"这是个长 context 友好、推理高效的现代 LLM"**。

---

## 十一、扩展阅读

- [transformer.md](transformer.md) —— Transformer 基础（attention、QKV、KV cache、prefill/decode）
- [rope-and-positional-encoding.md](rope-and-positional-encoding.md) —— RoPE 深度 + 长度外推（PI / NTK / YaRN）
- [mqa-gqa-and-kv-cache.md](mqa-gqa-and-kv-cache.md) —— KV cache + GQA + 长 context 内存估算
- [inference-optimization.md](inference-optimization.md) —— 量化、投机解码、PagedAttention
- [scaling-law.md](scaling-law.md) —— 模型规模 / 数据 / 算力关系
- [../production/latency-optimization.md](../production/latency-optimization.md) —— 延迟优化的工程实战
