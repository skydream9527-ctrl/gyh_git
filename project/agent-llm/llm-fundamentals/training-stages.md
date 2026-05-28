# LLM 训练流程：Pretrain → SFT → RLHF / DPO

> 现代 LLM（GPT-4、Claude、LLaMA、Qwen、DeepSeek 等）几乎都遵循同一套三阶段流水线。理解这套流水线能让你**在产品决策时知道"这个能力是哪一步给的"——也就知道哪些能力靠 fine-tune 改得动、哪些不行**。

---

## 一、为什么 PM / 产品工程师该懂训练流程

不懂训练流程时常见的认知错误：

| 错误认知 | 真相 |
|---|---|
| "GPT-4 比 GPT-3.5 是因为模型变大了" | 主要是后训练（RLHF / DPO）做得好 |
| "fine-tune 一下就能让模型说中文风格" | 风格可以，但底层知识盘子在 pretrain 就定了 |
| "我的数据少，fine-tune 几百条就行" | SFT 通常要几千-几万条；几百条容易破坏模型 |
| "RLHF 是为了让模型更聪明" | RLHF 主要是为了让模型**更对齐人类偏好**，不是更"懂" |
| "开源模型只要 LoRA 就能拉齐 GPT-4" | LoRA 改不了 pretrain 的能力天花板 |

下面把整个流水线讲清楚。

---

## 二、三阶段全貌

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   1. Pretrain          学语言、世界知识、推理      99% 算力   │
│      (预训练)          数据：万亿 token 文本                 │
│      ↓                                                      │
│   2. SFT               学"如何按指令回答"          1% 算力    │
│      (监督微调)        数据：几万到几百万条人写指令-回答     │
│      ↓                                                      │
│   3. RLHF / DPO        学"按人类偏好回答"          ~1% 算力   │
│      (偏好对齐)        数据：人类排序 / 评分的成对回答        │
│                                                             │
└─────────────────────────────────────────────────────────────┘

每一步给模型注入的是不同维度的能力：
   Pretrain → 知识 + 语法 + 推理底子
   SFT      → 听话（按指令格式回答）
   RLHF/DPO → 让人喜欢（无害、有帮助、礼貌）
```

---

## 三、阶段 1：Pretrain（预训练）

### 在做什么

在巨量文本上让模型学**预测下一个 token**——这是唯一目标。所有"涌现的能力"都是这个目标的副产品。

### 数据

- 规模：10T - 30T token（万亿级）
- 来源：网页（CommonCrawl、Refined Web）、书、代码、维基、论文、社交、对话
- 关键：**数据质量** > 数据量。脏数据让模型学到错误模式，洗数据是 LLM 公司的核心壁垒

### 计算

- 几千张 H100 训几个月
- LLaMA 3 70B：约 $30M+ 算力
- GPT-4：估计 $50M+
- 这一步**普通公司不可能复现**——开源 base model 是大厂的公共物品

### 产物

**Base Model**：能补全文本，但**不会按指令回答**。

```
你输入：写一首诗给我
Base Model 输出：
   写一首诗给我，关于秋天的。我想要一首七言律诗。最好能...
   （它在补全你的提示，不在执行）
```

---

## 四、阶段 2：SFT（监督微调）

### 在做什么

让模型学会"按指令回答"。本质还是预测下一个 token，但数据格式是：

```
[Instruction]: 写一首关于秋天的七言绝句
[Response]: 银杏黄金落地，
            梧桐细雨敲窗。
            ...
```

模型学到："看到这种 instruction 格式，就该输出 response 部分"。

### 数据

- 规模：几万到几百万条
- 来源：
  - 人类标注员撰写（贵但质量高）
  - LLM 生成 + 人类筛选（Self-Instruct, Evol-Instruct）
  - 合成数据（用更强模型蒸馏）
- 关键：**多样性** > 数量。100 万条 100 个领域的数据比 100 万条单领域好

### 产物

**Instruct Model**：能按指令回答，但行为可能粗糙（有害、不礼貌、容易跑偏）。

> 注：你下载的 `meta-llama/Llama-3-8B-Instruct` 是 SFT + 偏好对齐后的版本；`meta-llama/Llama-3-8B` 是只完成 pretrain 的 base。

### LoRA / QLoRA：高效微调

全参数 SFT 一个 70B 模型要几十张 H100。**LoRA**（Low-Rank Adaptation）只训练**低秩适配器**（增加 0.1-1% 参数），算力降两个数量级。

- LoRA：训练时省内存，推理时合并回原模型
- QLoRA：base model 4-bit 量化 + LoRA，进一步省 70% 显存
- 工程实践：90% 公司只做 LoRA / QLoRA，不做全量 SFT

---

## 五、阶段 3：偏好对齐（RLHF / DPO）

### 为什么需要这一步

SFT 完之后模型可能：
- 给出有害答案（怎么造炸弹）
- 拒绝得太敷衍 / 太啰嗦
- 写代码格式乱
- 不会说"我不知道"

但这些**没法用 SFT 修**——你写不出"理想回答"，你只知道"看到两个回答时哪个更好"。

### 思路

让人类**对比**两个回答说哪个好，模型学这个偏好。

```
Prompt: 怎么造炸弹？
回答 A: 你需要 ... [详细步骤]
回答 B: 我不能提供这种信息...

人类标注：B > A
```

### RLHF（Reinforcement Learning from Human Feedback）

经典做法（OpenAI 的 InstructGPT 论文，2022）：

```
1. 训"奖励模型"（Reward Model）：
   输入 prompt + 回答，输出"人类有多喜欢"的分数
   数据：成对回答 + 人类偏好标注

2. 用强化学习 PPO：
   让 LLM 输出在 RM 下得分高的回答
   同时加 KL 约束防止偏离 SFT 模型太远
```

### DPO（Direct Preference Optimization, 2023）

最近主流取代 RLHF 的方法。**绕过显式 RM 和 RL**：

```
直接最大化：log P(chosen | prompt) - log P(rejected | prompt)
（再加一些数学正则项）
```

| 维度 | RLHF | DPO |
|---|---|---|
| 实现 | 复杂（RM + PPO） | 简单（一个 loss） |
| 稳定性 | 不稳定（RL 老问题） | 稳定 |
| 效果 | 略好 | 接近 |
| 算力 | 高 | 中 |

> **现在多数开源 / 中小公司直接用 DPO**。变体：IPO、KTO、ORPO、SimPO。

### Constitutional AI（Anthropic）

让 AI 自己批评自己的回答（基于一组规则），用 AI 反馈训练。降低人工成本。

### RLAIF
更进一步：人类完全不参与，用强 LLM 当评判员。规模化主流方向。

---

## 六、训练数据决定能力的天花板

一个产品组的常识级误区：

```
"我们要做法律 Agent，把 100 万条法律问答 fine-tune 进去就行"

真相：
- 100 万条 fine-tune 数据 vs 几万亿 token pretrain → fine-tune 是花瓶
- 模型对法律的理解 90% 来自 pretrain 时见过的法条 / 判例
- fine-tune 只能改风格、强化已有知识、教格式
- 想让模型"懂法律"，**只有更换 base 模型**或**继续预训**（continual pretraining）
```

→ 详见 [scaling-law.md](scaling-law.md)：模型能力的"天花板"在 pretrain 阶段定下来。

---

## 七、几个关键的"哪个阶段决定了什么"

| 现象 / 能力 | 主要由哪个阶段决定 |
|---|---|
| 中文 / 英文 / 多语言 | Pretrain（数据中比例） |
| 知识截止日期 | Pretrain（数据收集时间） |
| 数学 / 代码能力 | Pretrain + 后续指令微调 |
| 长上下文能力 | Pretrain 阶段或继续预训 |
| 听不听话（指令跟随） | SFT |
| 不说有害话 | RLHF / DPO |
| 拒绝得礼貌 | RLHF / DPO |
| 输出格式整齐 | SFT + RLHF |
| 风格 / 语气 | SFT 数据风格主导 |
| Function Calling | SFT 阶段加专门数据 + RLHF 优化 |
| 长链路 Agent 决策 | 这是"涌现"能力，pretrain + 后训共同作用 |

---

## 八、产品决策的实操含义

### 1. 选 base model 时
- 看的不是 SFT 后的 chat 版表现
- **本质看 pretrain 数据**（中文 token 比例、代码比例、知识截止等）

### 2. 自己 SFT 时
- LoRA 一般够用
- 数据量经验：**500-5000 条**（少了过拟合，多了边际收益递减）
- 不要做"风马牛不相及"的多任务混合 fine-tune

### 3. 自己做偏好对齐
- 中小公司绝大多数直接用 DPO
- 数据：1000-10000 条偏好对就能见效
- 别从零做 RLHF（PPO 调起来很难）

### 4. 模型蒸馏
- 用强模型（GPT-4、Claude 4）生成数据 SFT 小模型
- 是当前最实用的"低成本对齐"路径
- DeepSeek-V3、Qwen 系列等都重度依赖蒸馏

---

## 九、Checklist：选模型 / 训模型时问自己

```
□ 1. 这是 base 还是 instruct？
□ 2. 它的 pretrain 数据语言比例如何？
□ 3. 知识截止时间足够新吗？
□ 4. 上下文窗口够吗？
□ 5. 我要做的事是 SFT 能解决，还是需要换 base？
□ 6. 我有多少标注数据？够 SFT 吗？
□ 7. 偏好对齐用 RLHF 还是 DPO？数据从哪来？
□ 8. 用 LoRA 还是全参？
□ 9. 评测怎么做？（→ [../evaluation/llm-as-judge.md](../evaluation/llm-as-judge.md)）
```

---

## 十、扩展阅读

- 本目录：[transformer.md](transformer.md)、[scaling-law.md](scaling-law.md)、[inference-optimization.md](inference-optimization.md)
- OpenAI — *Training language models to follow instructions with human feedback* (InstructGPT 论文)
- Rafailov et al. (2023) — *Direct Preference Optimization: Your Language Model is Secretly a Reward Model*（DPO 论文）
- Anthropic — *Constitutional AI: Harmlessness from AI Feedback*
- Andrej Karpathy — *State of GPT* (Microsoft Build 2023)
- Hugging Face TRL 文档（DPO / PPO 实操）
- LLaMA 系列、Qwen 系列、DeepSeek 系列技术报告（每篇都讲了完整流水线）
