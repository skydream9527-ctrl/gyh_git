# Transformer 架构

> 本文目标：在不抠数学细节的前提下，让你建立对 Transformer 的**机制直觉**——理解它为什么强、为什么贵、为什么有上下文长度限制、为什么对位置敏感。这些直觉直接决定你做 Agent 和产品时的所有架构选择。

---

## 一、为什么不能跳过 Transformer

如果你做 LLM 应用、做 Agent、做评测、调 prompt，**有没有 Transformer 直觉**会反复体现在差距上：

| 没直觉的人会问 | 有直觉的人知道 |
|---|---|
| "为什么 prompt 里调一下顺序，结果差很多？" | Attention + 位置编码让相对位置直接进入计算 |
| "为什么长上下文会变慢、变贵？" | Attention 是 O(n²)，KV Cache 解释了为什么"输出比输入便宜" |
| "为什么 prompt cache 有用？" | 因为前缀的 K/V 可以复用 |
| "为什么模型有时候'忘记'中段的内容？" | "Lost in the middle"，与位置编码和注意力分布有关 |
| "为什么 streaming 出第一个 token 慢、后面快？" | Prefill 阶段做完整 attention，decode 阶段只需增量 |

读完本文你应该能自己回答上面所有问题。

---

## 二、一段话讲清 Transformer

Transformer 是 Google 在 2017 年的论文 *Attention Is All You Need* 里提出的架构，**核心创新是用"注意力"完全替代了 RNN/CNN**。它的本质机制是：

> **每个位置的输出，都是把所有位置（包括自己）按"相关性"加权求和而成的。**

这一改动带来三个根本性后果：

1. **并行**：每个位置可以同时计算（RNN 必须按顺序），训练效率直接拉到 GPU 集群可饱和。
2. **长程依赖**：任意两个位置都直接相连（不必走 N 步），长文本上能力大幅强于 RNN。
3. **可堆叠**：每一层都做"重新混合"，深层能学到层级化的语义结构。

> 没有 Transformer 就没有 GPT、Claude、Gemini——它们都是 Transformer 的变种（具体是 decoder-only 自回归模型）。

---

## 三、自注意力（Self-Attention）：核心引擎

### 直觉

把句子里每个 token 想成一个人，attention 在做的事：

> "我（query）想找现在最相关的人（key），把他们身上的信息（value）按相关度抽过来，混进我自己。"

数学上是这样的：

```
对每个 token，先变成三个向量：
   Q (query)：我在找什么
   K (key)：我能被什么找到
   V (value)：我有什么信息

注意力权重 = softmax(Q · K^T / √d)
输出      = 注意力权重 · V
```

### 一个具体例子

句子：`The cat sat on the mat because it was tired.`

要算 `it` 的表示时，模型会通过 attention 把高权重放在 `cat` 上（共指消解）。这件事 RNN 要按顺序读 8 步才能"知道"，attention 一步就连上。

### 关键观察：O(n²) 复杂度

每个 token 都要和所有 token 算相关性 → 序列长度 n 时，attention 计算量是 **O(n²)**。

这是一切"长上下文很贵"的根源：

- n = 1k：1M 次计算
- n = 32k：1B 次计算（增长 1000 倍）
- n = 1M：1T 次计算（增长 100 万倍）

后面我们会看到 Flash Attention、PagedAttention、稀疏注意力是怎么治这个病的。

---

## 四、多头注意力（Multi-Head）：为什么不止一个头

把 Q/K/V 切成多份（典型 8 / 16 / 32 头），每个头独立做 attention，最后拼起来：

```
头 1：可能学到"指代关系"
头 2：可能学到"主谓关系"
头 3：可能学到"语法位置"
...
```

**直觉**：每个头是一个"专门的注意力专家"。多头让同一层能同时捕捉多种关系。

工程上：多头不增加总计算量（每个头的维度被切小），但参数效率和表达力大幅提升。

---

## 五、位置编码：Transformer 的"时间感"

Self-attention 本身**不知道顺序**——所有 token 进去都是一袋词。要让它知道"这是第 1 个、第 2 个 token"，必须**人为注入位置信息**。

历史上有几种主流方案，每一代都解决了上一代的痛点：

### 1. 绝对位置编码（原始 Transformer / BERT）
- 给每个位置一个固定的 sin/cos 向量加到词嵌入上
- 缺点：训练时见过的位置，推理时才能用——硬切到没见过的长度直接失效

### 2. 学习的绝对位置嵌入（GPT-2/3）
- 把位置当作 vocab 的一部分，学一个 embedding
- 缺点：同上，且训练数据"位置分布"会被记进去

### 3. **相对位置（T5 / ALiBi）**
- 不告诉模型"绝对位置"，告诉它"两个 token 隔多远"
- 优势：天然外推到更长序列

### 4. **RoPE（Rotary Position Embedding，现代主流）**
- 把位置信息**旋转**到 Q 和 K 向量里
- LLaMA / Qwen / Mistral / DeepSeek 都用 RoPE
- 优势：相对位置 + 数学性质优雅 + 容易外推
- **变体**：YaRN、NTK-aware scaling 让 RoPE 模型支持超长上下文

### 业务影响

```
你给模型一个长 prompt → 位置编码决定模型怎么"感知"顺序
→ 模型对 prompt 内容的位置高度敏感
→ "重要信息放开头或结尾"是 prompt 工程的真理之一
→ "Lost in the middle" 现象（中段信息被忽略）也是位置编码的副作用
```

---

## 六、三种 Transformer 变体

不是所有 Transformer 都长一样。三种主流变体：

| 类型 | 代表模型 | 用途 | 工作方式 |
|---|---|---|---|
| **Encoder-only** | BERT, RoBERTa | 理解、分类、Embedding | 双向 attention，看全局，输出向量 |
| **Decoder-only** | GPT, Claude, LLaMA | 生成 | 单向 attention（只看左边），自回归预测下一个 token |
| **Encoder-Decoder** | T5, BART | 翻译、摘要 | 编码源 → 解码目标 |

**现代 LLM（GPT-4, Claude, LLaMA, Qwen…）几乎都是 decoder-only**。原因：自回归生成 + 架构简单 + 训练 / 推理统一。

> 这也是为什么 LLM 输出是逐 token 的——decoder-only 的本质是"看着前面的 token 预测下一个"。

---

## 七、KV Cache：为什么"输入贵、输出便宜"

理解 KV Cache 是理解 LLM 成本和延迟的关键。

### 推理的两阶段

```
1. Prefill：把整个 prompt 喂进去
   - 对每个位置算 K, V，存起来
   - 计算量：O(n²)，n = prompt 长度
   - 慢，决定首字延迟（TTFT）

2. Decode：一个 token 一个 token 输出
   - 新 token 的 Q 只和已存的 K/V 算 attention
   - 计算量：O(n)，n = 当前总长度
   - 相对快，决定吞吐
```

```
Prefill (一次)：       Decode (每生成一个 token)：
 ┌───────────┐          ┌───────────┐
 │ token₁    │  ┐       │ token₁    │   K/V 已缓存
 │ token₂    │  │ 全部   │ token₂    │   K/V 已缓存
 │ token₃    │  │ 算 K/V │ token₃    │   K/V 已缓存
 │ token₄    │  │  存   │ ...        │
 │ token₅    │  ┘       │ tokenₙ ←─ │   只算这个的 K/V
 └───────────┘          └───────────┘
```

### 这解释了一切

- **为什么输入 token 比输出 token 便宜（按 API 计价）**：输入是 prefill 一次性算完，输出是逐步算每一步还要复制 KV
- **为什么"长 prompt + 短输出" vs "短 prompt + 长输出" 完全不同的延迟特性**：第一种 TTFT 高、整体快；第二种 TTFT 低、整体慢
- **为什么 prompt cache（Anthropic / OpenAI）这么有用**：把前缀的 K/V 存起来跨请求复用，prefill 成本几乎归零
- **为什么 KV Cache 内存爆炸是 LLM 部署的头号难题**：序列越长 cache 越大，影响并发数

---

## 八、推理优化的三大杠杆

### 1. Flash Attention
- 重新设计 attention 的 GPU 访存模式（tiling + 不显式存中间矩阵）
- 让 attention 从内存带宽瓶颈变成计算瓶颈
- 实测速度 2-4 倍，长序列尤其明显
- 现在几乎所有训练 / 推理框架默认开启

### 2. PagedAttention（vLLM）
- 把 KV Cache 切成"页"管理（类似操作系统虚拟内存）
- 解决 KV Cache 内存碎片问题，吞吐量提升 2-4 倍
- vLLM 的核心创新

### 3. 投机解码（Speculative Decoding）
- 用一个**小模型**先预测 N 个 token，**大模型**一次性验证
- 平均能让大模型速度提升 1.5-3 倍
- Mendel-style speculative decoding、EAGLE、Medusa 是变体

---

## 九、长上下文的真相

模型说支持 100K / 1M 上下文 ≠ 你能塞 100K / 1M 字进去**且效果不掉**。

实测维度：

1. **能不能塞**：API 是否接受
2. **能不能找**：Needle-in-Haystack 测试（藏一个事实进长文本里能不能召回）
3. **能不能用**：在长文本里**做推理**（不只是检索）

很多模型 1 通过、2 部分通过、3 严重退化。这就是为什么 RAG 至今没有被"超长上下文"取代——长上下文很贵，且推理能力随长度衰减。

详见 [../rag/retrieval-basics.md](../rag/retrieval-basics.md) 的相关讨论。

---

## 十、把 Transformer 直觉装进决策

下次遇到这些情况，回想一下原理：

```
□ "Prompt 调一下顺序结果大变" → Attention + 位置编码
□ "为什么模型不'读完' 100K 上下文" → 位置编码外推 + 注意力衰减
□ "为什么开 prompt cache 能省钱" → KV Cache 复用前缀
□ "为什么用 GPT-3.5 跑分类比 GPT-4 还稳" → 大模型在简单任务上 attention 容易过度发散
□ "为什么 streaming 第一个字慢" → Prefill 是 O(n²)
□ "为什么长链路 Agent 越跑越贵" → 历史 K/V 持续增长
□ "为什么 fine-tune 比 prompt 工程稳定" → fine-tune 改的是权重，prompt 只是改条件分布
```

---

## 十一、扩展阅读

- 本目录其他笔记：
  - [training-stages.md](training-stages.md) — Pretrain / SFT / RLHF / DPO
  - [inference-optimization.md](inference-optimization.md) — 量化、投机解码、Flash Attention 详细
  - [scaling-law.md](scaling-law.md) — Chinchilla 与涌现
- Vaswani et al., *Attention Is All You Need* (2017) — 必读源头
- Jay Alammar, *The Illustrated Transformer* — 可视化最好的入门
- Andrej Karpathy, *Let's build GPT: from scratch, in code, spelled out* — 200 行代码从零实现
- Andrej Karpathy, *State of GPT* (Microsoft Build 2023) — 训练流程总览
- Lilian Weng — *The Transformer Family* 系列博客
- vLLM 论文 — *Efficient Memory Management for LLM Serving with PagedAttention*

→ 下一步建议：读 [../agents/react-and-variants.md](../agents/react-and-variants.md) 看 Agent 怎么把这台"语言机器"变成"会做事的机器"。
