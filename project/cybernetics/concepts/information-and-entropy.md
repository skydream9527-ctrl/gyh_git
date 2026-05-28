# 信息与熵：Wiener vs Shannon 的两条路径

> 1948 年，Wiener 和 Shannon 几乎**同时独立**形式化了"信息"——但他们走向了不同的方向。Wiener 把信息视为"控制的基础"，Shannon 把信息视为"通信的极限"。两条路径在今天的 LLM 时代重新汇合。本文梳理这段思想史和它对今天的实操含义。

---

## 一、为什么这件事重要

如果你做 LLM Agent / 数据系统 / AI 工程，"信息"和"熵"是绕不开的概念：

- **Token 经济学**：每个 token 携带多少"信息"？
- **Prompt 设计**：哪些信息必要、哪些是冗余？
- **RAG**：检索"减少不确定性"的能力
- **AI Alignment**：reward 携带的信息量
- **观测系统**：log / trace 真正贡献的"信息"是什么

**理解 Wiener / Shannon 两路视角，能让你在工程上更精准地思考"信息流"**——而不是把"数据多 / 字多"当成"信息多"。

---

## 二、香农的版本：信息 = 不确定性的减少

### 核心定义（1948）

```
H(X) = -Σ p(x) log₂ p(x)         (信息熵)

  X：随机变量（如下一个 token）
  p(x)：每个值的概率
  H(X)：X 的不确定性，单位 bit
```

直觉：

```
完全确定（一定出某个值）：H = 0 bit（没"信息"）
等概率多选（如丢硬币）：    H 最大（最大"不确定性"）

收到一条消息后：
信息 = H(原本不确定性) - H(消息后不确定性)
```

例：

```
没看天气预报：明天 ⛅/☀/🌧 各 1/3 概率 → H ≈ 1.58 bit
看了天气预报"明天晴"：H = 0
信息量 = 1.58 - 0 = 1.58 bit
```

### Shannon 路径的核心问题

> "**用最少的比特把消息无损传过信道**"

→ 通信工程的最优编码、信道容量、压缩极限。
→ 后来发展出无损压缩（Huffman, Arithmetic Coding）、有损压缩（JPEG, MPEG）、纠错码（Reed-Solomon）等。

**Shannon 的信息论是"通信的科学"——它不关心信息的"含义"，只关心"传输效率"**。

---

## 三、Wiener 的版本：信息 = 控制的基础

### 核心思想（1948 *Cybernetics*）

Wiener 几乎和 Shannon 同时给了**形式上几乎一样的公式**——但他的关注点完全不同：

```
信息是控制系统的"输入"
   ↓
没有信息（无反馈）→ 系统盲目
有信息（有反馈）  → 系统能朝目标修正
   ↓
"信息" = "对系统行为有影响的差异"
```

Wiener 关心的不是"传得多快"，是"**系统怎么用信息保持目标**"。

### Wiener 路径的核心问题

> "**有限的信息能维持多大的复杂秩序**"

→ 反馈、稳态、自适应控制、生物 / 机器的"目的性行为"。
→ 这一脉络后来发展为：控制论 → 自适应控制 → 强化学习 → AI 决策。

---

## 四、两条路径的对照

| 维度 | Shannon | Wiener |
|---|---|---|
| 核心问题 | 通信效率 | 控制有效性 |
| 关注点 | 信道、编码、压缩 | 反馈、目标、稳定性 |
| 数学工具 | 信息熵、互信息、信道容量 | 反馈控制、滤波、最优化 |
| 理想终点 | 接近信道容量上限 | 系统稳定逼近目标 |
| 学科后裔 | 通信工程、压缩、编码、ML 评估 | 控制工程、机器人、强化学习、AI 决策 |
| 哲学倾向 | 信息独立于含义 | 信息是控制的"杠杆" |

> **注意**：Wiener 和 Shannon 的"熵公式"长得几乎一样——他们独立推出了同一个数学。差异在**关心什么问题**。

---

## 五、两条路径的现代汇合：LLM

讽刺的是，60 年后这两条路径在大模型上**重新汇合**：

```
LLM 训练：
   - 优化 next-token prediction = Shannon 路径
   - 通过 self-supervised learning 压缩文本信息

LLM 推理 / Agent：
   - 闭环决策 = Wiener 路径
   - 通过反馈调整行为

整体：
   一个 LLM 同时是 Shannon 信道（压缩、生成）+ Wiener 控制器（决策、反馈）
```

**理解这一汇合**对工程设计有直接启示：

- 训练阶段思考 Shannon（什么数据信息密度高？）
- 推理阶段思考 Wiener（什么反馈让系统朝目标走？）
- 评测时两者都要（输出有信息 + 输出符合目标）

---

## 六、几个关键的"信息"概念

### 1. 信息熵 H(X)
单一变量的不确定性。

### 2. 条件熵 H(X | Y)
已知 Y 时 X 还剩下的不确定性。

```
H(X|Y) = H(X) - I(X;Y)
                ↑
              互信息
```

### 3. 互信息 I(X; Y)
"知道 Y 能减少 X 多少不确定性"——**最常用于工程**。

```
I(X; Y) = H(X) + H(Y) - H(X,Y)
```

应用：
- 特征选择（找和 Y 互信息高的 X）
- Reward shaping（reward 应该和真实目标互信息高）
- 模型评估（输入和输出互信息）

### 4. KL 散度 D(p || q)
"用 q 近似 p 时的'信息损失'"。

```
D(p || q) = Σ p(x) log(p(x) / q(x))
```

应用：
- VAE、GAN 等生成模型的 loss
- LLM RLHF 中的 reference 模型 KL 约束
- 评估两个分布的"距离"（不对称）

### 5. 交叉熵
`H(p, q) = -Σ p(x) log q(x)`
- 实际上是 LLM 训练的 loss 函数
- 和 KL 散度只差一个 H(p)

---

## 七、对工程的实操启示

### 1. Token 经济学不是字数经济学
```
"摘要 1000 字 vs 全文 5000 字"
→ 不是 5× 信息量
→ 真信息量取决于互信息和压缩率

建议：评估 prompt 时问"这部分信息能减少模型多少不确定性？"
不是问"它有多少字？"
```

### 2. RAG 的本质是"信息注入"
```
RAG 召回的 chunk 价值 = 它把回答 Y 的不确定性降低多少

评估 RAG 召回质量：
   I(Y; chunk_retrieved) → 越高越好
   不是 chunk 本身的字数 / 相似度分数
```

### 3. Reward shaping 要对齐互信息
```
Goodhart's Law 的根源：
   设计的 reward R 和真实目标 G 的互信息不够
   I(R; G) 低 → 优化 R 不能保证优化 G

建议：reward 设计时显式问"它和真实目标互信息多大？"
```

### 4. 可观测系统要看"有效信息"
```
日志多 ≠ 可观测性强
   - 大量重复 / 冗余日志：H(log | system_state) ≈ 0 → 没信息

可观测性 = log 与系统真实状态的互信息
   建议：评估 trace 时考虑信息密度
```

### 5. CoT 是不是信息？
```
CoT 文字本身可能没"新信息"——它是模型的"思考展开"
但它对最终答案 Y 的互信息可能很大（自我一致性）

含义：CoT 的价值不能用"长度"衡量，要看"和最终答案的互信息"
```

→ 详见 [../../agent-llm/prompting/cot-family.md](../../agent-llm/prompting/cot-family.md)

---

## 八、与控制论其他概念的关系

```
信息（Wiener / Shannon）
   ↓ 形式化
熵
   ↓ 推论
Ashby 必要多样性定律 → V_ctl 信息容量必须 ≥ V_dist
                       → [ashby-requisite-variety.md](ashby-requisite-variety.md)
   ↓ 反馈系统中
反馈消除不确定性 → [feedback-and-homeostasis.md](feedback-and-homeostasis.md)
   ↓ 综合集成
钱学森综合集成 = 多源信息融合 → [../qian-xuesen/meta-synthesis.md](../qian-xuesen/meta-synthesis.md)
```

---

## 九、几个反直觉但深刻的发现

### 1. "信息独立于含义"
- Shannon 视角下，"今晚下雨"和"今晚 ▢ □ ◆"的信息量可能一样
- 信息论不评判"内容好坏"——这是它的科学抽象的代价

### 2. "压缩极限是宇宙级常数"
- 一段文本的最优压缩比是被 Shannon 信息论锁死的
- 任何超过这个极限的压缩都是有损或骗人

### 3. "随机性 ≠ 噪音"
- 随机也可以是高信息（一段加密文本对没钥匙的人就是高熵）
- 信息和随机性的关系比直觉复杂

### 4. "互信息可能为零但相关性不为零"
- 这是控制论 vs 统计的差异
- 互信息捕捉非线性 / 任意关系，相关系数只捕捉线性

### 5. "信息量取决于'对谁'"
- 同一段消息对不同接收者信息量不同
- 这是 Shannon 信息论的固有局限——它假设了通信双方共享的码本

---

## 十、Checklist

```
□ 1. 我是从 Shannon（通信 / 压缩）视角还是 Wiener（控制 / 反馈）视角思考？
□ 2. 我做 prompt / RAG 时，是在算字数还是在估互信息？
□ 3. 我的 reward / KPI 与真实目标互信息多大？
□ 4. 我的可观测系统的 log 信息密度高吗？
□ 5. 我是否区分了"数据量"和"信息量"？
□ 6. 我的 LLM 用 KL 约束 / 交叉熵时清楚它在控制什么吗？
```

---

## 十一、扩展阅读

- 本目录：[feedback-and-homeostasis.md](feedback-and-homeostasis.md)、[ashby-requisite-variety.md](ashby-requisite-variety.md)
- 钱学森专题：[../qian-xuesen/meta-synthesis.md](../qian-xuesen/meta-synthesis.md)
- Shannon (1948) — *A Mathematical Theory of Communication*（**Shannon 信息论奠基**）
- Wiener (1948) — *Cybernetics*, Ch.3（信息观）
- Cover & Thomas — *Elements of Information Theory*（最权威信息论教材）
- James Gleick — *The Information: A History, A Theory, A Flood*（思想史科普，必读）
- 现代视角：Yarin Gal 关于"信息瓶颈"的工作
- ML 视角：*Information Theory and Machine Learning*（NeurIPS workshop 多年）
