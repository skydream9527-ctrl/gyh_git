# 03. 主流公开 Benchmark 全景

> 公开 benchmark 解决的是"行业内可比"的问题。本文按**类别**梳理主流 benchmark：评的是什么、分数怎么读、什么时候**别相信**它。
>
> 6 类：通用 LLM / 代码 / 数学推理 / Agent / 工具调用 / 长上下文 + 多模态。

---

## 一、为什么 Public Benchmark 不能闭眼信

### 三大风险

| 风险 | 表现 |
|---|---|
| **数据污染** | benchmark 数据已混入预训练，分数虚高 |
| **过拟合** | 模型为刷分专门优化，但泛化崩 |
| **指标不全** | 单一分数掩盖多维能力差异 |

### 红绿灯
```
🟢 用来做粗略选型 / 摸架构脉搏
🟡 用来对比同代模型，但要看版本和数据 cutoff
🔴 当作业务决策唯一依据 → 99% 翻车
```

> 真正决定上线的应该是**业务侧黄金集 + 在线 A/B**。详见 [04-business-eval-pipeline.md](04-business-eval-pipeline.md)。

---

## 二、通用 LLM 能力（学术与综合）

### 2.1 MMLU / MMLU-Pro
- **MMLU**（Massive Multitask Language Understanding, 2020）：57 个学科多选题
- **MMLU-Pro**（2024）：升级版，10 个选项、更难
- **现状**：MMLU 已基本被刷爆（顶模 88%+），MMLU-Pro 区分度更好

```
GPT-4.5         ~91%   ┐
Claude 4 Opus   ~90%   ├─ MMLU
Gemini 2.5 Pro  ~89%   │
LLaMA 4         ~86%   ┘

MMLU-Pro:
o3              ~85%
Claude 4 Opus   ~80%
DeepSeek V3     ~75%
Qwen 3          ~73%
```

### 2.2 HellaSwag / ARC / WinoGrande
经典常识推理。**几乎全饱和**，主要看小模型能不能跟上。

### 2.3 GPQA Diamond
**研究生级别科学问答**（"Google-Proof"——Google 搜不到答案）。
- 区分高端模型的关键 benchmark 之一
- o3-class 模型才能上 80+

### 2.4 BIG-Bench (Hard)
跨领域 200+ 子任务的"硬子集"。覆盖广，但运行成本高。

### 2.5 MT-Bench / Arena-Hard
- **MT-Bench**：80 道多轮问题，GPT-4 当 judge
- **Chatbot Arena (LMSYS)**：人类盲测投票，**Elo 评分**——目前最权威的"主观偏好"榜
- **Arena-Hard**：从 Arena 中蒸馏的硬题集

### 2.6 LiveBench
**每月动态更新题目**，对抗数据污染。是 2025 年学术圈推荐的"反污染"评测。

---

## 三、代码能力

### 3.1 HumanEval / MBPP
- **HumanEval**（OpenAI 2021）：164 道 Python 函数补全
- **MBPP**：974 道入门题
- **现状**：基本饱和（顶模 90+），区分度低

### 3.2 LiveCodeBench
- 持续从 LeetCode / Codeforces 抓取**未被训练**的新题
- 与 LiveBench 同思路，是反污染的"代码版"

### 3.3 SWE-Bench / SWE-Bench Verified
- **SWE-Bench**（Princeton 2024）：真实 GitHub repo 的 issue-修复对，Agent 全流程
- **SWE-Bench Verified**：人工筛过 500 题，确保可解
- **是当前 Coding Agent 的事实标杆**

```
2024 初:   GPT-4 ~2%
2024 中:   Claude 3.5 + 工具 ~33%
2024 末:   Claude 3.5 v2 + scaffolding ~50%+
2025:      o3 / Claude 4 + agent harness ~70%+

→ 这个跃迁说明: SOTA 不是 LLM 单独，是 LLM × Agent harness 的合力
```

### 3.4 LiveCodeBench Agent Mode / SWE-Lancer
- 升级版：**长任务 / 多步 / 多文件 / 真实测试**
- 评的是 Agent 能力，不是单 LLM

### 3.5 BigCodeBench
- 1140 道实用编程题（含库调用）
- 专评"会用真实库"的能力，不只是算法题

---

## 四、数学 / 推理

### 4.1 GSM8K
- 8500 道小学/初中应用题，CoT 经典基准
- **饱和**（顶模 95%+），保留作为 sanity check

### 4.2 MATH
- 12500 道高中竞赛题
- 仍然有区分度

### 4.3 AIME
- **美国数学邀请赛真题**，含 30 题/年
- **o1/o3/R1 时代最重要的数学 benchmark**
- 下表是题目难度与模型表现：

```
GPT-4 (2023)            ~13%
GPT-4 + maj@8           ~25%
Claude 3.5              ~16%
o1                      ~83%
o1-pro                  ~89%
o3                      ~96%
DeepSeek-R1             ~95%
```

### 4.4 FrontierMath
- Epoch AI 发布，**封闭集**（避免泄露）
- 顶级数学家自己只能解 30%
- 顶模目前 ~25%（o3 估计），未来 1-2 年的硬指标

### 4.5 Olympiad-Bench
多语言奥数题集，含中文。

---

## 五、Agent 能力（任务执行）

### 5.1 AgentBench
- **清华 KEG, 2023**
- 8 个环境：操作系统、数据库、知识图谱、卡牌游戏、家庭、网购、网页、横向推理
- **覆盖广，但单任务深度有限**

### 5.2 GAIA
- **Mialon et al., 2023**（FAIR / HuggingFace）
- 466 道**真实世界**问题，需要 Web 搜索、文件解析、推理
- 题目分 3 个 level，level-3 极难
- **是"通用 Agent"的事实基准**

```
GPT-4 + 简单工具    ~15%
Claude 3 Opus       ~28%
Anthropic 内部 Agent ~45%
现在顶模 + 工具       ~60-70%
人类                ~92%
```

### 5.3 WebArena / VisualWebArena
- **CMU, 2023/2024**
- 真实网页环境（购物、地图、Reddit、GitLab）
- Agent 必须导航、点击、填表完成任务
- VisualWebArena 增加视觉版本（screenshot 输入）

### 5.4 OSWorld
- **真实操作系统**（Linux / macOS / Windows）任务
- Computer Use 类 Agent 必看
- 当前顶模仅 ~20-30%，远低于人类

### 5.5 τ-bench (Tau-Bench)
- **Sierra, 2024**
- 模拟真实客服场景（航空、零售）
- 用户由 LLM 扮演，多轮对话 + 工具调用
- 评 **task success + tool correctness + user satisfaction**

### 5.6 MLAgentBench / SWE-Bench Multimodal / WebVoyager
针对**特定垂直**的 Agent benchmark：

| Benchmark | 领域 |
|---|---|
| MLAgentBench | 让 Agent 写 ML 代码 |
| WebVoyager | 视觉 + Web 浏览 |
| MMAU | 多代理协作 |

---

## 六、工具调用（Function Calling）

### 6.1 Berkeley Function Calling Leaderboard (BFCL)
- 加州伯克利维护，**事实工具调用基准**
- 多语言（Python / Java / JS），多类目（simple / parallel / multiple / relevance）
- 持续更新，是行业首选

```
评测维度:
   - Function Selection Accuracy
   - Argument Accuracy
   - Hallucination Rate (调了不存在的函数)
   - Relevance (对该不该调工具的判断)
```

### 6.2 ToolBench / ToolLLM
- 1.6 万 API + 真实任务，规模大
- 但部分 API 已下线，可重复性下降

### 6.3 API-Bank
- 多步、多工具调用 benchmark
- 含 73 个工具的真实 API

### 6.4 Nexus Function Calling
- Nexusflow 维护，覆盖 9 大类工具
- 配套 NexusRaven 模型

---

## 七、长上下文

### 7.1 Needle-in-a-Haystack (NIAH)
- 把一句话埋在 N k token 上下文中，让模型找
- **太简单**——顶模在 200k 都能 100%，但不能反映**多跳推理**

### 7.2 RULER
- NVIDIA 提出，比 NIAH 难得多
- 含 multi-needle、reasoning、aggregation 子任务
- **长上下文的真实评测**

```
Gemini 2.5 Pro     128k 时 ~92%
Claude 4 Opus      128k 时 ~88%
DeepSeek-V3        128k 时 ~80%
GPT-4.5            128k 时 ~78%
```

### 7.3 LongBench / LongBench-Chat
中英双语长文本任务集，含问答、摘要、code、few-shot。

### 7.4 ∞Bench
持续推到 1M context 的极端 benchmark。

---

## 八、多模态

### 8.1 MMMU / MMMU-Pro
- 跨 30 学科的多模态多选题
- **多模态能力首选 benchmark**

### 8.2 MathVista
- 视觉数学推理（图表 / 几何 / 函数图）

### 8.3 ChartQA / DocVQA / OCRBench
- 图表 / 文档 / OCR 类，业务侧最实用

### 8.4 Video-MME
- 视频理解 benchmark
- Gemini 2.5 Pro 在这里独大

---

## 九、综合榜单（meta-leaderboards）

| 榜单 | 维护方 | 用途 |
|---|---|---|
| **Chatbot Arena (LMSYS)** | LMSYS | 主观偏好 Elo |
| **Open LLM Leaderboard** | HuggingFace | 开源模型聚合榜 |
| **LiveBench** | LiveBench team | 反污染综合榜 |
| **HELM** | Stanford CRFM | 学术全面评测 |
| **Artificial Analysis** | 第三方 | 价格 / 速度 / 能力综合 |
| **Vellum / SEAL** | 商业评测 | 含工具/Agent 能力 |

---

## 十、benchmark 阅读建议

### 10.1 看分数前先问 4 个问题
1. **数据 cutoff 多久？** 模型预训练 cutoff > benchmark 发布时间 = 高度怀疑污染
2. **本身是否 contamination-resistant？** LiveBench / FrontierMath 才有保护
3. **Agent 还是 LLM？** SWE-Bench 70% 不是模型 70%，是 harness × 模型
4. **题目分布与你的业务相似吗？** 不像就只能当参考

### 10.2 选模型时怎么用
- **粗筛**：Arena Elo + MMLU-Pro 看大档位
- **代码**：SWE-Bench Verified + LiveCodeBench
- **推理**：AIME + GPQA Diamond
- **Agent**：GAIA + τ-bench + BFCL
- **长上下文**：RULER（不是 NIAH）
- **业务**：自建黄金集 > 一切

### 10.3 避坑清单
- ❌ 别看模型自己宣传的 benchmark 数字（家家都挑赢的发）
- ❌ 别比一两个百分点（统计噪声）
- ❌ 别把单榜冠军当全能冠军
- ✅ 看多个独立 benchmark 的分布
- ✅ 看 dev/prod 自有评测

---

## 十一、典型场景下推荐 benchmark 套餐

### 通用 Chat 助手
```
MMLU-Pro / Arena Elo / MT-Bench / 自建领域集
```

### Coding Agent
```
SWE-Bench Verified / LiveCodeBench / BigCodeBench / 自建仓库集
```

### Research Agent
```
GAIA / 自建领域题集 / 长上下文 RULER
```

### Customer Support Agent
```
τ-bench / 自建对话集 + tool-call eval
```

### Browser/Computer Agent
```
WebArena / OSWorld / 自建网页/系统操作集
```

### RAG 问答系统
```
RAGAS / 自建 needle 集 / 业务问答集
```

---

下一篇：[04-business-eval-pipeline.md](04-business-eval-pipeline.md) — 业务侧实操：黄金集、CI、A/B、监控全流水线。
