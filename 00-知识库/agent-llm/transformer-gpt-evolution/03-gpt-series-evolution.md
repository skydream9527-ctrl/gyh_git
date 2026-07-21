# 03. GPT 系列演进：从 GPT-1 到 o3

> 本文聚焦 OpenAI 自己的 GPT 谱系（含 ChatGPT 和 o 系），按时间线讲清楚**每一代的核心突破**与**对应的训练范式跃迁**。架构层面的事详见 [02-architectural-evolution.md](02-architectural-evolution.md)，本文侧重"训练 + 数据 + 对齐 + 推理范式"。
>
> 4 个跃迁维度：**参数规模 / 训练数据 / 对齐方法 / 推理范式**。

---

## 一、总览时间线

```
2018.06  GPT-1     117M    BookCorpus (~1B token)        Pretrain → Finetune
2019.02  GPT-2     1.5B    WebText (40GB)                Zero-shot 出现
2020.05  GPT-3     175B    300B token mix                In-Context Learning
2022.01  InstructGPT  ~ GPT-3 + RLHF                     人类对齐
2022.11  ChatGPT   GPT-3.5 + RLHF + 多轮                 产品形态爆发
2023.03  GPT-4     ?(estimate ~1.8T MoE)                 多模态（text+image input）
2024.05  GPT-4o    "o" = omni                             原生多模态（text+vision+audio I/O）
2024.09  o1-preview / o1                                  Test-time compute / Hidden CoT
2025.01  o3 / o3-mini                                     更深的推理 + 工具使用
2025.02  GPT-4.5                                          基础模型质感跃迁
```

---

## 二、GPT-1（2018）：Pretrain + Finetune 范式确立

**论文**：*Improving Language Understanding by Generative Pre-Training*

### 核心思想
两阶段：

```
Stage 1 (Pretrain): 在大规模无标注文本上做语言建模
                    目标：P(x_t | x_<t)
                    数据：BookCorpus 7000 本书 ~1B token

Stage 2 (Finetune): 在下游任务的标注数据上微调
                    分类、推理、相似度…
                    每个任务一个微调好的模型
```

### 突破点
- **证明了"先 LM 预训练，再下游微调"在 NLP 上 work**——之前主流是从头训练任务专属模型。
- 架构：12 层 Decoder-only Transformer，117M 参数。

### 局限
- 每个下游任务都要单独 finetune 一份。
- 数据规模和参数规模都太小，没有"涌现"。

---

## 三、GPT-2（2019）：Zero-shot 萌芽

**论文**：*Language Models are Unsupervised Multitask Learners*

### 核心思想
"如果模型足够大、数据足够多元，**不微调也能做下游任务**"。

```
Pretrain on WebText (40GB, 8M 网页)
       ↓
直接 Zero-shot 做翻译、问答、摘要
```

### 突破点
- **规模化第一弹**：1.5B 参数（13× GPT-1）。
- **首次展示 Zero-shot 能力**——给个 prompt"翻译: Hello → ", 模型能续写德语。
- 当时 OpenAI **拒绝放出最大版本**，理由"怕被滥用"——开了 LLM 安全争论先河。

### 架构层改动
- 把 LayerNorm 放到 sub-layer 输入端 → **Pre-Norm 雏形**（详见 02-架构演进）。

---

## 四、GPT-3（2020）：Few-Shot 涌现，缩放定律实证

**论文**：*Language Models are Few-Shot Learners*

### 核心数据
- **175B 参数**（116× GPT-2）。
- **300B token** 训练数据（Common Crawl 经过去重和过滤，加 books、Wikipedia）。
- **96 层 / 12288 维 / 96 头**。

### 突破点：In-Context Learning（ICL）

```
Prompt:
  Translate English to French:
  sea otter => loutre de mer
  peppermint => menthe poivrée
  cheese =>

Output: fromage
```

模型**不更新权重**，只是看了 few-shot 例子就学会模式——这是"上下文里学习"。

### 论文里的关键观察
- **能力随规模平滑提升**，但 Few-Shot 这一档要 ~10B 才显著。
- **某些能力是涌现的**——例如算术、单词重排，小模型基本不会，到了某个规模突然会了。

### 局限
- 还不会"听人话"——给了 prompt 它会续写，但不会回答开放问题。
- 经常胡说八道（hallucination）、乱拒绝、犯安全性错误。

---

## 五、InstructGPT / ChatGPT（2022）：RLHF 对齐

**论文**：*Training language models to follow instructions with human feedback*（2022.03）

### 三阶段训练

```
Step 1: SFT (Supervised Fine-Tuning)
        人工写的 prompt-answer 对，监督学习。
        让模型学会"回答而不是续写"。

Step 2: Reward Model
        采集人类偏好数据：同一 prompt 多个答案，标注哪个更好。
        训一个 reward model 预测"答案有多好"。

Step 3: PPO (RL)
        用 reward model 给的分数，做强化学习微调。
        最大化"符合人类偏好"的概率。
```

### 突破点
- **InstructGPT 1.3B 版本在人类偏好评测上超越 GPT-3 175B**——证明对齐比规模重要。
- **ChatGPT（2022.11）= GPT-3.5 + RLHF + 多轮对话格式 + 安全护栏**，5 天破百万用户，2 个月破亿，引爆 LLM 应用。

### 此后被改进
| 方法 | 改进点 | 代表 |
|---|---|---|
| **DPO**（2023） | 不要 reward model，直接用 preference 数据做对比学习 | LLaMA-3 / Mistral |
| **GRPO**（2024） | 不要 critic，省内存适合大模型 | DeepSeek-R1 |
| **RLAIF** | 用 LLM 生成偏好数据替代人工 | Claude 系 Constitutional AI |
| **Constitutional AI**（Anthropic） | 用一组"宪法原则"自我修订，再做 RL | Claude 系 |

> 详见 [../llm-fundamentals/training-stages.md](../llm-fundamentals/training-stages.md)。

---

## 六、GPT-4（2023）：多模态 + 推理大跃迁

**报告**：*GPT-4 Technical Report*（披露极少架构细节）

### 突破点
- **能力跨阶**：律师考试、SAT、AP 多门科学考试达到人类前 10%。
- **Vision input**：能看图片做推理。
- **Steerability**：System prompt 大幅可控。
- **128k context**（GPT-4 Turbo, 2023.11）。

### 架构猜测（外部分析）
- **可能是 ~1.8T 参数 MoE**（Geohot 等多方推测，OpenAI 没确认）。
- 训练 token 预计 13T 左右，多语言、代码、长文本。

### 工程升级
- **Predictable scaling**：能用小模型预测大模型损失，避免大规模训练翻车。
- **System Card** 引入：模型评估 + 对齐数据公开化。

---

## 七、GPT-4o / 4o-mini（2024）：原生多模态

**关键词**："o" = "omni"——一个模型端到端处理 text / vision / audio I/O。

### 此前 vs 此后

```
GPT-4 + DALL·E + Whisper + TTS:
  audio in → Whisper 转文字 → GPT-4 → 文字 → TTS 转语音
  (3 个独立模型 pipeline，~3-5 秒延迟)

GPT-4o:
  audio in ─→ 单模型 ─→ audio out
  (端到端，~300ms 延迟，能感知语气和情绪)
```

### 突破点
- **原生多模态训练**：图像/语音/文字在同一个 transformer 里 token 化，预训练阶段就一起学。
- 同期 Gemini（Google）也是类似思路。

### 后续
- **GPT-4o-mini**（2024.07）：成本击穿地板，跟 Haiku / Flash 同档。
- 这一档的开源对位是 LLaVA、Qwen-VL、Gemma 3、InternVL 等。

---

## 八、o1 / o3（2024-2025）：Test-time Compute 范式革命

**关键词**：**推理时计算**——把"思考"当成第一类资源。

### 此前的范式

```
Prompt → LLM → Answer       (一次 forward, 推理时计算 ~固定)
```

提升能力的杠杆是：**更多预训练数据 + 更多参数**。

### o1/o3 引入的新范式

```
Prompt → LLM (内部思考 N 步) → Answer
              ↑
         可以想 1 秒、10 秒、100 秒、…
         "思考时长"成为新的 scaling 维度
```

### 关键技术拼图（OpenAI 没公开细节，外部推测）
1. **Process Reward Model**：不仅评估最终答案，还评估每一步推理是否合理。
2. **大规模 RL on chain-of-thought**：让模型学会自我纠错、回溯、规划。
3. **隐藏 CoT**：用户看到的是简短答案，模型内部"草稿纸"是隐藏的（OpenAI 选择不暴露）。

### 突破点
- AIME（数学竞赛）从 GPT-4 的 ~13% 跃到 o1 的 83%、o3 的 96%。
- ARC-AGI（人类直觉推理）o3 首次接近人类水平。
- **可调"思考时长"**：o1-preview / o1 / o1-pro / o3-mini / o3 是同一家族不同推理预算的版本。

### DeepSeek-R1（2025.01）
- **完全开源**，训练流程也大量披露。
- 用 GRPO 替代 PPO，训练成本极低。
- 证明"思考能力"可以直接通过 RL 从 base model 涌现，不一定需要复杂的 PRM。

> 这是 2024-2025 的最大变化——见详细 [../papers/](../papers/) 下相关阅读。

---

## 九、GPT-4.5（2025.02）：基础模型质感跃迁

OpenAI 自己定位 GPT-4.5 是"基础模型最大一次升级"——不靠推理时计算，纯靠预训练 + 后训练让"模型本身更聪明、更有同理心、更少胡说"。

### 与 o 系的分工
```
o 系（推理型）：硬题/数学/代码 → 想得久、慢、贵
4.5（基础型）：日常对话/写作/创意 → 反应快、感觉自然
```

OpenAI 内部把这条策略叫做 **"two tracks"**——基础模型 vs 推理模型，按场景挑。

---

## 十、对位的非 OpenAI 模型谱系

| 谱系 | 关键节点 |
|---|---|
| **Anthropic Claude** | Claude 1（2023.03）→ 2 → 2.1（200k）→ 3 Haiku/Sonnet/Opus（2024.03）→ 3.5 Sonnet（2024.06，推理 + 代码强）→ 3.7 Sonnet（2025.02，extended thinking）→ Claude 4 Opus（2025） |
| **Google Gemini** | Gemini 1（2023.12）→ 1.5 Pro 1M context（2024.02）→ 2.0 Flash（多模态实时）→ 2.5 Pro（2025.03，推理） |
| **Meta LLaMA** | LLaMA 1（2023.02）→ 2（2023.07，70B）→ 3（2024.04，8B/70B）→ 3.1（2024.07，405B + 128k）→ 3.2 多模态 → 4 系列（2025） |
| **DeepSeek** | V2（2024.05，MLA）→ V3（2024.12，MoE）→ R1（2025.01，开源推理） |
| **Qwen（阿里）** | Qwen 1（2023）→ 2（2024）→ 2.5（2024.09）→ 2.5-1M → 3（2025） |

详细横向对比见 [04-frontier-models.md](04-frontier-models.md)。

---

## 十一、关键能力跃迁地图

```
能力           | 出现于                    | 触发条件
─────────────|─────────────────────────|─────────────────
续写文本       | GPT-1 (2018)            | 任意规模 LM
Zero-shot      | GPT-2 (2019)            | 1B+ 参数
Few-shot ICL   | GPT-3 (2020)            | 10B+ 参数
代码生成       | Codex / GPT-3 (2021)    | 在代码数据上预训练
指令跟随       | InstructGPT (2022)      | SFT + RLHF
对话           | ChatGPT (2022)          | 多轮 + RLHF
工具使用       | GPT-4 + plugins (2023)  | Function Calling
多模态(图)     | GPT-4V (2023)           | 联合预训练
长上下文       | GPT-4 Turbo / Claude 2  | RoPE + YaRN / 工程
原生多模态     | GPT-4o / Gemini (2024)  | 端到端联合训练
深度推理       | o1 / o3 / R1 (2024-25)  | Test-time CoT + RL
1M context     | Gemini 1.5 / Qwen-1M    | 滑窗 / 缓存 / 改 attention
```

---

## 十二、四个维度的演进总结

```
┌─────────────────────────────────────────────────────────────┐
│ 1. 参数规模  : 117M  → 175B  → ~1T+ MoE                     │
│ 2. 训练数据  : 1B    → 300B  → 10T+ token，多语言+多模态     │
│ 3. 对齐方法  : 无    → SFT   → RLHF → DPO/GRPO/Const.AI     │
│ 4. 推理范式  : 一次  → ICL   → Tool Use → Test-time Compute │
└─────────────────────────────────────────────────────────────┘
```

每一代 GPT 的"突破"基本都对应至少一个维度上的台阶式跃迁。

---

## 十三、给应用开发者的启示

| 启示 | 落地策略 |
|---|---|
| **基础模型 vs 推理模型分工** | 日常用 4o/Sonnet/Flash，硬题用 o3/Opus + Extended thinking |
| **测试 prompt 必须有"模型能力"维度** | 每升一代旧 prompt 可能瞬间失效（变好或变坏） |
| **In-Context Learning 在小模型上不可靠** | 7B 量级模型做严肃任务最好走 finetune / 工具补强 |
| **多模态 != 多段拼接** | 真正的 multimodal 模型理解效率好得多，但成本也高 |
| **对齐 ≠ 安全** | 模型回答合理 ≠ 安全无虞，业务侧要做内容审核 + 工具权限分层 |

---

下一篇：[04-frontier-models.md](04-frontier-models.md) — 2026 年第一梯队模型横向对比与选型建议。
