# RoPE 与位置编码：让 Attention 感知相对位置

> Agent 工程师**不懂 RoPE 会反复踩三个坑**：(1) 长 context 模型不一定真的"长"；(2) prompt 顺序敏感性比预期大；(3) 长 context 的"中段失忆"是有原因的。本文从位置编码的根本问题讲起，到 RoPE 的数学直觉，最后落到长度外推（PI / NTK / YaRN）的工程实战。
>
> 配套：[modern-gpt-block.md](modern-gpt-block.md)、[mqa-gqa-and-kv-cache.md](mqa-gqa-and-kv-cache.md)、[transformer.md](transformer.md)。

---

## 一、位置编码到底要解决什么

Attention 本质是"集合操作"——它对输入的顺序**完全无感**。如果你不告诉模型"哪个 token 在前哪个在后"，"狗咬人" 和"人咬狗" 在 attention 里是一样的。

数学上：
```
Attention(Q, K, V) = softmax(Q K^T / √d) V
```

如果把序列里两个 token 的位置交换，Q、K、V 的对应行也跟着换 → softmax 输出对应行也换 → **结果和原来等价**（permutation invariant）。

**位置编码就是"告诉模型顺序"的机制**——把位置信息注入 Q、K（或者 hidden state），打破这种顺序无关性。

---

## 二、三代方案的演化

### 第一代：绝对位置编码（原始 Transformer 2017）

给每个位置 i 加一个固定向量 PE_i：
```
input_embed[i] = token_embed[i] + PE[i]
```

PE_i 用三角函数生成（正弦余弦混合）。

**问题**：
- 训练时见过位置 0-512，**没见过的位置就懵**
- 模型学的是"这个位置的特征"，不是"位置之间的关系"
- 长度外推一塌糊涂

**用过的代表**：原始 Transformer、BERT、GPT-1/2。

### 第二代：相对位置编码（T5 / Transformer-XL）

不在输入加位置，而在 attention 里加偏置：
```
attn(Q, K) = softmax((Q @ K^T + B[i-j]) / √d)
```

`B[i-j]` 是"位置 i 和 j 的相对距离对应的偏置"。模型学的是相对距离。

**问题**：
- 增加计算量（attention 矩阵每个位置都要查 B 表）
- 实现复杂、推理慢
- 表达能力有限

**用过的代表**：T5、Transformer-XL、ALiBi（一种简化变体）。

### 第三代：RoPE（Rotary Position Embedding，Su et al., 2021）

**核心 trick**：不在 attention 里加位置偏置，**在 Q 和 K 上做旋转**。

```
q_i 旋转 i × θ 度
k_j 旋转 j × θ 度

q_i · k_j = |q||k| × cos((i-j) × θ)  ← 自动得到相对距离！
```

**用过的代表**：现在所有主流 LLM——GPT-3.5+、Llama 全系、Claude、Gemini、Mistral、Qwen、DeepSeek。

---

## 三、RoPE 的数学直觉

### 1. 把 hidden state 想象成 2D 旋转

把 hidden state 的每两个相邻维度看作一个 2D 平面上的点 (x, y)。

绝对位置 i 处的旋转角度 = i × θ：

```
位置 0 的 q：(1, 0)        旋转 0°
位置 1 的 q：(0.7, 0.7)    旋转 45°
位置 2 的 q：(0, 1)        旋转 90°
...
```

### 2. 关键性质：点积只和相对距离有关

位置 i 的 query 旋转 i × θ，位置 j 的 key 旋转 j × θ。**做点积时，旋转角度相互抵消，只剩 `(i-j) × θ`**——也就是**相对距离**。

```
位置 0 的 q：(1, 0)        旋转 0°
位置 1 的 k：(0.7, 0.7)    旋转 45°
点积 = cos(45°) = 0.707    ← 距离 1
                                  
位置 0 的 q：(1, 0)        旋转 0°
位置 5 的 k：(-1, 0)       旋转 180°  
点积 = cos(180°) = -1      ← 距离 5

位置 100 的 q：(...)       旋转 100°
位置 101 的 k：(...)       旋转 101°
点积只看 1° 的差            ← 距离仍是 1
```

**距离越远 → 点积越小 → attention 越弱**。这正是我们想要的。

### 3. 多频率：低维敏感近距离，高维敏感远距离

不同维度用不同 θ：低维 θ 大（高频，旋转快，敏感于近距离）、高维 θ 小（低频，旋转慢，敏感于远距离）。

```
维度 0-1:    θ = 1          → 转一圈 (2π) 只需 6 个位置
维度 2-3:    θ = 0.1         → 转一圈需要 60 个位置
维度 4-5:    θ = 0.01        → 转一圈需要 600 个位置
...
维度 d-2,d-1: θ = 1/10000    → 转一圈需要 60000 个位置
```

**多频率叠加 = 既能区分近邻又能感知全局**。这是 RoPE 编码丰富信息的关键。

### 4. 实现（伪代码）

```python
def apply_rope(x, position):
    """
    x: hidden state, shape (batch, seq, head_dim)
    position: 位置 index
    """
    # 把维度两两配对成 2D 平面
    x_pairs = x.view(*x.shape[:-1], -1, 2)  # (batch, seq, head_dim/2, 2)
    
    # 每对应该旋转多少角度
    theta = 10000 ** (-torch.arange(0, head_dim, 2) / head_dim)
    angle = position * theta  # (head_dim/2,)
    
    # 旋转矩阵
    cos = torch.cos(angle)
    sin = torch.sin(angle)
    
    # 应用旋转
    x_rotated = torch.stack([
        x_pairs[..., 0] * cos - x_pairs[..., 1] * sin,
        x_pairs[..., 0] * sin + x_pairs[..., 1] * cos,
    ], dim=-1)
    
    return x_rotated.flatten(-2)
```

实战中这是高度优化的 CUDA kernel，但本质就是上面这个。

---

## 四、为什么 RoPE 能"长度外推"

### 1. 核心原因

RoPE 编码的是**相对距离**，不是**绝对位置**。模型训练时学的是 `(i-j)` 这个差，不是 `i` 这个值。

意味着：训练在 8K 上，看的最大相对距离是 `8K-1`。如果你直接跑 16K，**有一半的 (i-j) 是模型没见过的**——会崩。

但你只要**让 (i-j) 落到训练分布里**，模型就能跑。这就有了三代外推方案。

### 2. Position Interpolation（PI，Meta 2023）

把 16K 的位置缩放到 8K 范围：

```
原本 q_15000 旋转 15000 × θ
PI 后 q_15000 旋转 (15000/2) × θ  ← 等效于训练时的 7500 位置
```

**简单粗暴有效**。Llama 2 → Llama 2 Long 用的就是这个，把 4K 扩到 32K。

**问题**：所有维度都一样缩放，**高频维度（小 θ）压缩后，近距离信息丢失**——因为本来高频维度区分 1 vs 2 vs 3 这种细微差，缩小后全压在一起。

### 3. NTK-aware Scaling

PI 的问题：所有维度都一样缩放。

NTK-aware 的洞察：**让高频维度少缩放（保持精细），低频维度多缩放（处理远距离）**。

数学上等价于：调整 RoPE 的 base θ：

```python
# 原始 RoPE
theta_i = 10000 ** (-2i/d)

# NTK-aware（扩展长度 L_new）
new_base = 10000 * (L_new / L_train) ** (d / (d - 2))
theta_i_new = new_base ** (-2i/d)
```

**实战标识**：Llama 3 的 `rope_theta = 500000`（vs Llama 1 的 10000）就是这个思路——把 base 调大让 RoPE 适应长 context。

### 4. YaRN（Yet another RoPE eNhancement）

在 NTK 基础上，对不同频率做更精细的处理 + 加一个 attention 温度修正。**目前外推效果最好**。

YaRN 的细节：
- 高频维度：保持原 RoPE
- 中频维度：用 NTK-aware 缩放
- 低频维度：用 PI（线性缩放）
- 加一个 temperature 因子修正 softmax 锐度（长 context 时 softmax 会变扁平）

**用 YaRN 的代表**：Mistral / Qwen / DeepSeek 的长 context 版本都用 YaRN。

### 5. 三代外推方法对比

| 方法 | 核心 | 简单度 | 长度上限 | 质量 |
|---|---|---|---|---|
| **PI** | 线性缩放位置 | 极简 | 4-8× | 中（高频丢失） |
| **NTK-aware** | 调整 base θ | 简单 | 4-16× | 好 |
| **YaRN** | 分频率 + 温度修正 | 复杂 | 8-32× | 最好 |

---

## 五、Agent 工程师必须懂的 RoPE 工程坑

### 坑 1：长 context 模型不一定真"长"

```
Llama 2 7B "支持" 4K
├── PI 扩到 32K → 80% 任务能跑，但精度下降
└── 直接跑 32K → 输出乱码

Llama 3 8B "支持" 128K  
├── 训练时真见过长样本（> 32K）
└── 配合 RoPE base 调整 → 真能用
```

**判断技巧**：看模型卡里的 `rope_theta`：
- Llama 1：`rope_theta = 10000`（4K 训练，外推差）
- Llama 2：`rope_theta = 10000`（4K 训练，靠 PI 外推）
- Llama 3：`rope_theta = 500000`（8K → 128K 适配，NTK 思路）
- Mistral 7B v0.2：`rope_theta = 1000000`

**rope_theta 越大 → 长 context 适应性越好**（粗略规律）。

### 坑 2：长 context 的"中段失忆"

即使 RoPE 让模型能"看到" 200K，它**注意力分布仍然不均匀**。研究（"Lost in the Middle", Liu et al., 2023）表明：

```
position    attention strength
─────────────────────────────
0-1000      ⭐⭐⭐⭐⭐   开头（强）
1000-50000  ⭐         中段（弱，"lost in the middle"）
50000-100000 ⭐⭐       结尾（中）
```

**为什么**：
- 开头：因果 attention 让所有后续 token 都能看到，模型对开头位置过拟合
- 结尾：最近的 token 距离短，注意力天然强
- 中段：处于不利位置——既不在开头也不在最近

**实战策略**：
- 长 context 时，**关键信息放开头或结尾**，不要塞中间
- "needle in a haystack" 类任务：测试模型在中段的提取能力是否真的够用
- RAG 系统：把最相关的文档放最后（最接近用户问题）

### 坑 3：RoPE 让 prompt 顺序非常敏感

因为是相对位置，**调换 prompt 顺序 = 完全不同的 RoPE 编码**。

```
prompt v1: "示例1, 示例2, 示例3, 问题"
prompt v2: "示例3, 示例1, 示例2, 问题"

→ 同样信息，不同顺序
→ 每个 token 的位置变了，RoPE 编码完全不同
→ 模型行为可能差很多
```

Few-shot 例子的顺序、文档拼接的顺序，对结果影响**比绝对位置编码时代大得多**。

**实战**：
- few-shot 示例：把"最相似于当前问题"的放最后
- RAG 文档：按相关性递增排序（最重要的接近问题）
- 多轮对话：注意系统 prompt 长度变化时，所有后续位置都会偏移

### 坑 4：prompt cache 与 RoPE 兼容

[../production/latency-optimization.md](../production/latency-optimization.md) 讲的 prompt cache：
```
Cache 前缀必须稳定 → 后续命中
```

**RoPE 的好处**：因为是相对位置，前缀稳定时**前缀的 K、V 在不同请求间可以共享**（同一位置编码同一结果）。

**陷阱**：如果你在 prompt 中间动态注入内容（比如时间戳），会让所有后续 token 的位置偏移 → cache miss。

**正确做法**：动态内容放最后，稳定内容放前面。这刚好和"中段失忆"建议一致——把关键稳定内容放开头，让 cache 命中 + 注意力强。

### 坑 5：fine-tune 长 context 模型要 careful

如果你要 fine-tune 一个长 context 模型（比如把 Llama 3 8B 在你自己的 32K 数据上微调）：
- **不要改 rope_theta**（会破坏预训练对齐）
- **微调数据的长度分布要覆盖目标长度**（不能全是 4K 数据，否则微调后长度能力退化）
- LoRA 时 attention 的 Q、K projection 必须包括（K 是 RoPE 应用的目标）

---

## 六、跟 ALiBi 等其他方案的对比

ALiBi（Attention with Linear Biases）是 RoPE 的"竞品"，被 BLOOM / MPT 用过：

```
ALiBi: 在 attention score 上直接加一个跟距离成比例的负数偏置
attn(Q, K) = softmax((Q K^T - m × |i-j|) / √d)
```

| | RoPE | ALiBi |
|---|---|---|
| 编码方式 | 旋转 Q/K | attention bias |
| 长度外推 | 需要 PI/NTK/YaRN | 天然外推（线性） |
| 模型质量 | 高 | 略低 |
| 实现复杂度 | 中 | 简单 |
| 代表模型 | Llama / Claude / Mistral | BLOOM / MPT |

**现状**：ALiBi 简单但质量稍逊，**主流已经全部转向 RoPE + 各种外推方案**。

---

## 七、关键 takeaway

1. **位置编码是"告诉 attention 顺序"的机制**——没有它，"狗咬人" = "人咬狗"。
2. **RoPE 通过旋转 Q/K 编码相对位置**——数学优雅，效果好，长度外推友好。
3. **长度外推靠 PI / NTK-aware / YaRN**——它们都是"让没见过的相对距离落回训练分布"的不同手法。
4. **rope_theta 是长 context 友好度的关键信号**——值越大，长 context 适应性通常越好。
5. **RoPE 让 prompt 顺序敏感**——few-shot 顺序、RAG 文档顺序、稳定前缀位置都要设计。
6. **"中段失忆" 是 RoPE 时代依然存在的现象**——长 context 时关键信息放开头或结尾。

---

## 八、扩展阅读

- [modern-gpt-block.md](modern-gpt-block.md) —— 现代 GPT Block 的整体演化
- [mqa-gqa-and-kv-cache.md](mqa-gqa-and-kv-cache.md) —— KV cache 与长 context 内存
- [transformer.md](transformer.md) —— Attention 基础
- [../production/latency-optimization.md](../production/latency-optimization.md) —— prompt cache 实战
- 论文：*RoFormer: Enhanced Transformer with Rotary Position Embedding* (Su et al., 2021)
- 论文：*Extending Context Window of Large Language Models via Positional Interpolation* (Chen et al., 2023)
- 论文：*YaRN: Efficient Context Window Extension of Large Language Models* (Peng et al., 2023)
- 论文：*Lost in the Middle: How Language Models Use Long Contexts* (Liu et al., 2023)
