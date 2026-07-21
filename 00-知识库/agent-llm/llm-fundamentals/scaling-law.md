# Scaling Law 与能力涌现

> Scaling Law 是过去 10 年大模型领域**最重要的实证规律**——它告诉你"加多少倍参数和数据能让模型变多强"，并解释了为什么 ChatGPT 不是渐进进化、而是**临界点突破**的产物。

---

## 一、为什么这件事重要

如果你是 PM / 工程师，理解 Scaling Law 能帮你回答几个工业里的关键问题：

| 问题 | 答案的形状 |
|---|---|
| "更大的模型一定更好吗？" | 给定算力预算下不一定——存在最优模型大小 |
| "我加 10 倍数据值得吗？" | 边际收益按幂律递减，能预测到底涨多少 |
| "为什么 GPT-2 不会 CoT、GPT-3 会？" | 涌现现象：能力在某个规模阈值后突然出现 |
| "再训 1 个数量级会发生什么？" | Scaling Law 给的是 loss 的预测，不是能力的预测 |
| "什么时候 Scaling Law 撞墙？" | 数据墙（高质量数据用尽）、推理成本墙、算法瓶颈 |

---

## 二、原始 Scaling Law（OpenAI, 2020）

Kaplan et al., 2020 用 GPT-2 系列做了大规模实验，得到一个惊人简洁的规律：

```
模型在测试集上的 loss L 满足：

   L(N, D, C) ≈ C₀ · N^(-α_N) + D₀ · D^(-α_D) + L_∞

其中：
   N = 模型参数量
   D = 训练数据量（token）
   C = 算力预算
   α_N ≈ 0.076
   α_D ≈ 0.095
   L_∞ = 不可约误差
```

**核心观察**：

1. **幂律**：loss 随参数量和数据量按**幂律下降**——画在对数坐标上是直线
2. **算力 / 参数 / 数据三者强耦合**：给定算力 C，存在最优 N* 和 D*
3. **预测性极强**：在小规模上拟合的曲线，能精确预测大规模上的 loss

> 这就是为什么 OpenAI / Anthropic / Google 敢花上亿美元训一个模型——**他们用小模型拟合 scaling 曲线，外推确认大模型的 loss 会到某个值才动手**。这是工业级的预测科学。

---

## 三、Chinchilla 修正（DeepMind, 2022）

Kaplan 原始的最优配比是"加参数 > 加数据"，但 DeepMind 重做实验发现**早期模型严重欠训了数据**。

**Chinchilla 法则**：

```
最优配比：N : D ≈ 1 : 20

参数量 N → 训练 token 数 D ≈ 20 × N

例：
   7B 模型最优训 ~140B token
   70B 模型最优训 ~1.4T token
   400B 模型最优训 ~8T token
```

**实验证据**：用一样的算力，70B 训 1.4T token（Chinchilla）比 280B 训 300B token（Gopher）显著更强。

**业界影响**：

- 之后的 LLaMA、Qwen、DeepSeek 都按 Chinchilla 比例（甚至更"过度训练"）
- LLaMA 3 8B 训了 15T token，远超 Chinchilla 比例（1:1875）——为了**推理时小模型也能强**

> Chinchilla 修正解释了为什么"小模型 + 海量数据"反而比"大模型 + 少数据"更强。这彻底改变了开源模型的训练范式。

---

## 四、能力涌现（Emergent Abilities）

### 现象

某些能力在小模型上完全不存在，到了某个规模阈值**突然出现**。Wei et al. (2022, *Emergent Abilities of Large Language Models*) 给了 137 个例子。

```
任务：3 位数加法（X + Y = ?）
表现：
   1B 模型   → 接近随机猜
   8B 模型   → 接近随机猜
   62B 模型  → 接近随机猜
   137B 模型 → 突然准确率 70%+ ←！
```

```
任务：CoT 推理
   GPT-3 175B  → 跟着 think step by step 没用，答得更差
   GPT-3.5     → 显著提升
   GPT-4       → 大幅领先
```

### 涌现的具体能力（部分）

- 算术（多步骤、进位）
- 多步推理（CoT）
- 指令跟随（zero-shot）
- 跨语言泛化
- 代码生成
- 复杂指令执行
- 工具使用 / Function Calling
- 上下文学习（ICL）从有效到强大

### 为什么会"涌现"

学术圈仍有争议，主流解释：

1. **任务的"非线性结构"**：完成多步任务需要**所有子能力都到位**——只要一个子能力不行，整体就 0 分。Scaling 时多个子能力同时跨越阈值，整体表现"突然"暴涨。
2. **度量人为离散**：用准确率（0/1）测试，看起来突然；用 log-perplexity 测试，曲线是平滑的（Schaeffer 2023, *Are Emergent Abilities a Mirage?*）

无论怎么解释，**工程上的事实是**：很多能力你只有在足够大的模型上才能用——这决定了选模型的策略。

---

## 五、Scaling 三个维度的现状（2024-2026）

### 1. 参数 + 数据
- 主流前沿模型在 0.5-2T 参数级（dense）
- MoE 架构（如 GPT-4、DeepSeek-V3、Mixtral）让"激活参数"远小于"总参数"，是另一种 scaling
- DeepSeek-V3 671B 总参 / 37B 激活 → 推理成本可控

### 2. 推理时 Scaling（Test-time Compute）
- 2024 年开始的新方向：**让模型在推理时多思考**（OpenAI o1、DeepSeek R1）
- 用同一个模型，加 100 倍推理算力 → 数学 / 代码能力大幅提升
- 这条路线的 Scaling Law 还在被实证刻画

### 3. 数据 Scaling 的危机
- 高质量公开文本几乎用完（"data wall"）
- 解决方向：合成数据、多模态扩展、数据反复使用、过滤更严

---

## 六、Scaling Law 的实操含义

### 1. 选模型时
- **不要只看参数量**：DeepSeek-V3 37B 激活强过很多 70B dense 模型
- 看**训练 token 量** + **后训练质量** + **基准评分**

### 2. 自己训模型时（如果有这预算）
- 严格按 Chinchilla 或更高比例训数据
- 算 N : D ≈ 1 : 20 是下限，1 : 100 + 是头部开源水平

### 3. 选能力时
- 涌现能力不可强求——某些能力在 7B 模型上做不到，硬调 prompt 也没用
- 升级模型规模通常比"更努力调 prompt"性价比高

### 4. 对未来判断
- "下一代模型大概率比这一代强"——Scaling Law 还没饱和
- 但**单纯加 scale 的边际成本指数上升**，混合 scaling（参数 + 数据 + 推理时计算）是新方向

---

## 七、几个反直觉的事实

### 1. "更小的模型有时更可靠"
- 大模型能力强，但**幻觉空间也大**
- 简单分类、关键词抽取等任务，3B 模型经常比 70B 更稳

### 2. "加参数到 1T 不一定比 100B 强"
- 数据是新瓶颈
- 算法 / 架构改进的红利可能比纯 scaling 大

### 3. "MoE 让 scaling 经济模型变了"
- 总参 1T 但激活 50B → 推理成本接近 50B dense
- 主流大模型未来会更倾向 MoE

### 4. "推理时 scaling 是新军备竞赛"
- o1 / R1 路线开了一扇门：**用同样的训练成本，推理时多算就能更强**
- 但用户体验上要求等更久 → 不是所有产品都能用

### 5. "Scaling 不能解决所有问题"
- 工具使用、Agent 决策、长链路稳定性 —— scale 帮上忙但不充分
- 工程层、产品层的杠杆有时更大

---

## 八、Scaling Law 与产品节奏

```
作为 PM 应该知道：

每 12-18 个月：
  • 同价位的模型能力上一个台阶
  • 你年初做不到的产品形态，年末可能做到了

每 24-36 个月：
  • 整个产品边界重画一次
  • 之前做不到的"长链路 Agent"突然变得可行

策略含义：
  • 不要把当前模型的限制当永久限制做产品定型
  • 把模型作为可替换的部件，业务逻辑解耦
  • 每年至少做一次"如果模型变强 10 倍，我们的产品该怎么变"演练
```

---

## 九、Checklist

```
□ 1. 我对模型的选择是否基于"参数量 + 训练数据量 + 后训练质量"三件套？
□ 2. 我是否清楚某个能力是涌现的（不能靠 prompt 弥补）？
□ 3. 我是否考虑过 MoE / 推理时 scaling 等新维度？
□ 4. 我是否会为"6-12 个月后模型大幅升级"留出架构空间？
□ 5. 我用的"最佳模型"是当前最强还是性价比最高？
```

---

## 十、扩展阅读

- 本目录：[transformer.md](transformer.md)、[training-stages.md](training-stages.md)
- Kaplan et al. (2020) — *Scaling Laws for Neural Language Models*（OpenAI 原始论文）
- Hoffmann et al. (2022) — *Training Compute-Optimal Large Language Models*（Chinchilla 论文）
- Wei et al. (2022) — *Emergent Abilities of Large Language Models*
- Schaeffer et al. (2023) — *Are Emergent Abilities of Large Language Models a Mirage?*
- OpenAI o1 / DeepSeek R1 技术报告（推理时 scaling 的标杆）
- Lilian Weng — *Scaling and the Path to AGI* 系列
- Andrej Karpathy 各种 keynote 中关于 scaling 的论述
