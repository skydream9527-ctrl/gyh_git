# Transformer 结构与 GPT 模型演进

> 本目录从 **2017 年 *Attention Is All You Need*** 起步，沿着两条主线讲清楚现代 LLM 的来路：
>
> 1. **架构演进线**：原始 Encoder-Decoder Transformer → Decoder-only → Pre-Norm/RMSNorm/RoPE/SwiGLU/GQA 的"现代 GPT block" → MoE / 长上下文 / 多模态。
> 2. **模型谱系线**：GPT-1（2018）→ GPT-2 → GPT-3 → InstructGPT/ChatGPT → GPT-4 → GPT-4o / o1 / o3，以及与之对位的 Claude / Gemini / LLaMA / DeepSeek / Qwen 谱系。
>
> 与 [../llm-fundamentals/](../llm-fundamentals/) 的区别：那边按"主题（attention / KV cache / RoPE / 推理）"组织，**本目录按"时间线"组织**，回答"为什么演进成今天这样"。

---

## 阅读顺序

| 顺序 | 文件 | 解决什么问题 |
|---|---|---|
| 1 | [01-transformer-architecture.md](01-transformer-architecture.md) | 原始 Transformer：Self-Attention / Multi-Head / Position Encoding / Encoder-Decoder。建立机制直觉。 |
| 2 | [02-architectural-evolution.md](02-architectural-evolution.md) | 从 2017 原始版到 2026 的"现代 GPT block"经历了哪些关键改造（Pre-Norm、RMSNorm、RoPE、SwiGLU、GQA、MoE）。 |
| 3 | [03-gpt-series-evolution.md](03-gpt-series-evolution.md) | GPT-1 → GPT-4o → o3 的能力跃迁逻辑：参数规模、训练范式、对齐方法、推理范式 4 个维度。 |
| 4 | [04-frontier-models.md](04-frontier-models.md) | 2026 年第一梯队模型横向对比：Claude 4、GPT-4.5/o3、Gemini 2.5、LLaMA 3/4、DeepSeek V3/R1、Qwen 3。 |

---

## 关键问题清单（读完应能回答）

- 原始 Transformer 为什么要用 Encoder-Decoder？为什么 GPT 砍掉了 Encoder？
- Pre-Norm 为什么取代 Post-Norm？RMSNorm 比 LayerNorm 强在哪？
- RoPE 比绝对/相对位置编码好在哪？为什么 NTK / YaRN 能做长度外推？
- GQA 为什么是 MQA 和 MHA 的折中？KV Cache 内存压力怎么估？
- MoE 怎么做到"参数大但激活少"？DeepSeek-V3 和 Mixtral 路由策略差在哪？
- GPT-3 → InstructGPT 的飞跃靠什么？为什么 RLHF 之后还需要 DPO/GRPO？
- o1 / o3 / DeepSeek-R1 引入的"推理时计算（test-time compute）"范式改变了什么？
- 多模态是从"晚期融合（CLIP+LLM）"演进到"原生多模态（GPT-4o / Gemini）"的，区别是什么？

---

## 与本仓库其它资料的关系

| 资料 | 关系 |
|---|---|
| [../llm-fundamentals/transformer.md](../llm-fundamentals/transformer.md) | 主题式机制讲解（Attention / O(n²) / KV Cache）。本目录的 01 章会引用，避免重复。 |
| [../llm-fundamentals/modern-gpt-block.md](../llm-fundamentals/modern-gpt-block.md) | "现代 GPT block 5 大改造"的速查。本目录 02 章是其历史脉络版。 |
| [../llm-fundamentals/rope-and-positional-encoding.md](../llm-fundamentals/rope-and-positional-encoding.md) | RoPE 数学推导。02 章只讲"为什么 RoPE 赢了"。 |
| [../llm-fundamentals/training-stages.md](../llm-fundamentals/training-stages.md) | Pretrain → SFT → RLHF 训练范式。03 章会复用，聚焦"GPT 系列分别在哪一步突破"。 |

---

## 关键参考

- *Attention Is All You Need*（Vaswani et al., 2017）
- *Improving Language Understanding by Generative Pre-Training*（Radford 2018，GPT-1）
- *Language Models are Few-Shot Learners*（Brown et al., 2020，GPT-3）
- *Training language models to follow instructions with human feedback*（Ouyang et al., 2022，InstructGPT）
- *GPT-4 Technical Report*（OpenAI, 2023）
- *Llama 2/3* 技术报告（Meta, 2023/2024）
- *DeepSeek-V3 / DeepSeek-R1* 技术报告（2024-12 / 2025-01）
- Anthropic *Claude 3 / 4 Model Card*（2024 / 2025）
- Sebastian Raschka — *Understanding Large Language Models*（系列博客）
- Andrej Karpathy — *Let's build GPT* / *State of GPT* / *Tokenization*（YouTube）
