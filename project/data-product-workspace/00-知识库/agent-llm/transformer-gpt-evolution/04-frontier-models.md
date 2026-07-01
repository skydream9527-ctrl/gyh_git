# 04. 2026 年前沿模型横向对比与选型

> 截至 2026 年 6 月，第一梯队模型已经稳定分为**闭源高端 / 闭源中端 / 开源旗舰 / 开源中小**四档。本文以**开发者视角**横向对比，重点回答：
>
> - 各家旗舰模型的架构特征、能力强项、典型缺陷？
> - 给具体业务场景，怎么选？
> - 价格 / 延迟 / 上下文 / 工具能力四个维度的取舍？

---

## 一、四档地图

```
┌─────────────────────────── 闭源高端 ───────────────────────────┐
│ Claude 4 Opus / GPT-4.5 / o3 / Gemini 2.5 Pro                  │
│ → 复杂推理、长文本、Agent 主控                                   │
└────────────────────────────────────────────────────────────────┘
┌─────────────────────────── 闭源中端 ───────────────────────────┐
│ Claude 4 Sonnet / GPT-4o / o3-mini / Gemini 2.5 Flash          │
│ → 主力工作马，性价比最佳                                         │
└────────────────────────────────────────────────────────────────┘
┌─────────────────────────── 开源旗舰 ───────────────────────────┐
│ DeepSeek V3 / R1 / LLaMA 4 / Qwen 3 / Mistral Large            │
│ → 自部署、可微调、合规可控                                       │
└────────────────────────────────────────────────────────────────┘
┌──────────────────────── 开源中小 / Edge ───────────────────────┐
│ Qwen 3 7B/14B / LLaMA 4 8B / Phi-4 / Gemma 3 / Mistral Nemo   │
│ → 边缘设备、高并发、小模型 + 工具的 Agent                        │
└────────────────────────────────────────────────────────────────┘
```

---

## 二、闭源旗舰横向对比（2026 年 6 月数据）

| 维度 | **Claude 4 Opus** | **GPT-4.5 / o3** | **Gemini 2.5 Pro** |
|---|---|---|---|
| 厂商 | Anthropic | OpenAI | Google DeepMind |
| 架构推测 | MoE + Constitutional AI | MoE + 推理后训练 | MoE + 原生多模态 |
| 标称上下文 | 1M | 128k (4.5) / 200k (o3) | 1M（实测 2M Beta） |
| 多模态 | 文 + 图 | 文 + 图 + 语音（4o）+ 视频（4.5） | 全模态原生（含视频） |
| 推理强项 | 代码、长文档、Agent 主控 | 数学、科学、复杂规划（o3） | 多模态、长文档检索 |
| 工具/Agent | Computer Use 一流 | Function Calling 标杆 | 实时多模态 + Code |
| 输出风格 | 工程级、克制、长输出稳定 | 多变，有时啰嗦 | 准确但有时机械 |
| 缺陷 | 价格贵、有时过度小心 | 信息陈旧（cut-off）、推理慢 | 长输出有时漂移 |
| 典型单价（输入/输出，每 1M token） | $15 / $75（Opus） | $2.5 / $10（4.5）/ ~$60+（o3） | $1.25 / $10（Pro 标准） |

> **价格变化非常快**，部署前以官方价格表为准。表中数字仅作"档位感觉"。

---

## 三、开源旗舰横向对比

| 维度 | **DeepSeek V3 / R1** | **LLaMA 4** | **Qwen 3** | **Mistral Large** |
|---|---|---|---|---|
| 厂商 | DeepSeek（中） | Meta | 阿里 | Mistral AI（法） |
| 架构 | MoE + MLA | MoE + 多模态 | Dense / MoE 双线 | Dense / MoE |
| 总/激活参数 | 671B / 37B | ~400B / ~17B（Maverick） | 235B / 22B（Qwen3-A22B） | 123B（Large 2） |
| 上下文 | 128k | 1M+（Maverick） | 128k / 1M（Turbo） | 128k |
| 推理特化 | R1（极强） | 计划中 | Qwen3-Reasoner | 商业版有 |
| 多语言 | 中文 + 英文极好 | 英文为主，中文较弱 | 中英日韩多语言强 | 欧洲语言强 |
| License | DeepSeek 自有 OSS | LLaMA 3/4 协议（商用受限） | Qwen2/3 协议 | Mistral 商用许可 / OSS 双轨 |
| 部署难度 | MoE 部署门槛高 | 标准 Decoder 友好 | 工具链成熟 | 标准 |
| 性能档位（开源中） | 顶配 | 顶配 | 顶配 | 中高 |

### 关键观察
- **DeepSeek 是 2025 年最大变量**：用极低训练成本逼近闭源旗舰，并且把 R1 系列论文开放，重塑了开源生态预期。
- **LLaMA 4** 把多模态原生纳入，但开源版本有"商用人数门槛"等限制，不像 LLaMA 3 那样全开放。
- **Qwen 3** 在中文、工具调用、多语言上是开源里最完整的，国内厂商首选。
- **Mistral** 在欧洲合规与小模型矩阵（Nemo / Codestral）上有差异化。

---

## 四、能力维度细分对比

### 4.1 代码能力（SWE-Bench Verified, 2026.05 数据）

```
o3 (high)               ~75%
Claude 4 Opus           ~72%
DeepSeek-R1             ~68%
Claude 4 Sonnet         ~64%
GPT-4.5                 ~60%
Gemini 2.5 Pro          ~55%
LLaMA 4 (largest)       ~50%
```

> 代码 Agent（Claude Code、Cursor、Cline）默认主控用 **Claude Sonnet/Opus**，因为输出风格、长度控制、工具协作上更稳。

### 4.2 数学/推理（AIME, 2025）

```
o3                       ~96%
DeepSeek-R1              ~95%
Gemini 2.5 Pro Thinking  ~85%
Claude 4 Opus            ~80%
GPT-4.5                  ~70%
```

### 4.3 长上下文（RULER 128k）

```
Gemini 2.5 Pro          ~92%
Claude 4 Opus           ~88%
DeepSeek-V3             ~80%
GPT-4.5                 ~78%
```

> "标称 1M" 远不等于"有效 1M"。**Needle-in-a-Haystack** 容易过，**RULER（多 needle、推理跨文本）** 才能反映真实长上下文质量。

### 4.4 中文能力

```
Qwen 3                  顶级
DeepSeek V3 / R1        顶级
Claude 4                优（地道、克制）
GPT-4.5                 良（个别表达偏译文腔）
Gemini 2.5              良
LLaMA 4                 中（依赖中文社区微调）
```

### 4.5 工具/Agent 能力（综合 τ-bench / WebArena / Berkeley Function Calling）

```
Claude 4 Opus / Sonnet  顶级（Computer Use 独家强项）
o3                      顶级（推理强，工具调用稳）
GPT-4.5                 优（function call 标杆）
Gemini 2.5 Pro          优
DeepSeek V3             良（开源里最强之一）
Qwen 3                  良
```

---

## 五、按场景选型

### 5.1 通用 Chat / 助手
- **第一档**：Claude 4 Sonnet / GPT-4o / Gemini 2.5 Flash（性价比甜点）。
- **省钱**：Qwen 3 14B / LLaMA 4 17B 自部署（如果有合规/成本压力）。

### 5.2 代码 / Coding Agent
- **闭源**：Claude 4 Sonnet（默认），复杂任务切 Opus。
- **开源**：DeepSeek-V3、Qwen3-Coder、Codestral。

### 5.3 数学/科研推理
- **闭源**：o3（最强但慢且贵），Claude 4 Opus 加 Extended Thinking。
- **开源**：DeepSeek-R1（性价比之王）。

### 5.4 长文档处理
- **首选**：Gemini 2.5 Pro（1M+，有效长度也好）。
- **次选**：Claude 4 Opus（1M，输出长度稳定）。
- **省钱版**：DeepSeek-V3（128k）+ 自建 RAG 补足。

### 5.5 多语言（含日韩越泰等）
- **闭源**：GPT-4.5 / Gemini 2.5 Pro / Claude 4。
- **开源**：Qwen 3 在亚洲语言上最强。

### 5.6 多模态（图/视频/语音）
- **图理解**：Claude / GPT-4o / Gemini 都强；Gemini 在图表 OCR 略胜。
- **语音对话**：GPT-4o Realtime API、Gemini 2.0 Flash Realtime。
- **视频理解**：Gemini 2.5 Pro 一档独大。

### 5.7 边缘部署 / 私有化
- **极小**：Qwen 3 4B、Phi-4-mini、Gemma 3 4B。
- **中等**：Qwen 3 14B、LLaMA 4 8B、Mistral Nemo 12B。
- **强大**：DeepSeek-V3 自部署需要 8×H100 起步，门槛真实存在。

### 5.8 高并发 + 低延迟
- **闭源**：Gemini Flash / Claude Haiku / GPT-4o-mini。
- **开源**：vLLM / SGLang 部署 Qwen 3 7B / LLaMA 4 8B。

---

## 六、主要风险与坑

| 风险 | 说明 | 缓解 |
|---|---|---|
| **价格波动** | 季度调价是常态，o3-mini → o3-mini-high 等档位重命名也常发生 | 接入用 LiteLLM / Portkey 做 Provider 抽象 |
| **API 速率限制** | Tier 升级周期长，瞬时大流量上线必撞墙 | 多供应商热备 + Caching + 排队 |
| **能力漂移** | 同名模型小版本更新可能行为变化 | 自有 eval 集 + version pin |
| **数据合规** | 欧盟 AI Act / 国内大模型备案 | 优先合规清单内的模型，敏感数据走私有部署 |
| **长上下文"虚标"** | 标称 1M，实际 256k 后准确率掉 | 用 RULER 自测 |
| **Token 计量差异** | 同样 prompt 不同家 token 数差 30% 不奇怪 | 成本估算用真实 token 计数 |

---

## 七、未来 12-18 个月观察清单（个人视角，会过时）

| 方向 | 看什么 |
|---|---|
| **推理时计算** | o3 之后还能不能再上一台阶？开源能不能跟上？ |
| **多模态实时** | GPT-4o Realtime 之后，行业能否做到"音视频毫秒级"普及 |
| **Agent 原生模型** | 是否会出现"专门为 Agent 训练"的基础模型（Computer Use 提示了方向） |
| **架构层创新** | Mamba / SSM hybrid、Diffusion LM、Linear Attention 谁先在生产模型里露脸 |
| **小模型的天花板** | 4B-14B 段位能涨到什么水平 |
| **模型 + 工具协同** | "弱模型 + 强工具"会不会反超"强模型 + 弱工具" |

---

## 八、给团队的实操建议

```
┌────────────────────────────────────────────────────────┐
│ 1. 别绑死一家 :  接入用 LiteLLM / Portkey / 自建 Gateway│
│ 2. 自建小 eval 集（每周末跑一次，监控漂移）             │
│ 3. 关键路径用旗舰 + 长尾用中端 + 边缘任务 7B 自部署       │
│ 4. 长上下文用前测真实有效长度，别信标称                  │
│ 5. 多模态/Realtime 任务先做端到端延迟预算               │
│ 6. 推理型模型（o3/R1）用在"想清楚"环节，不是聊天         │
│ 7. 中文场景把 Qwen / DeepSeek 至少作为备选纳入           │
└────────────────────────────────────────────────────────┘
```

---

## 九、与其他章节的衔接

- 模型怎么调用（Function Calling、MCP）：[../tools-protocols/](../tools-protocols/) 与本目录的 [../mcp-deep-dive/](../mcp-deep-dive/)。
- 模型怎么评测（含 Agent eval）：[../agent-evaluation/](../agent-evaluation/)。
- 推理工程（vLLM / 投机解码 / Flash Attention）：[../llm-fundamentals/inference-optimization.md](../llm-fundamentals/inference-optimization.md)。
- Anthropic / OpenAI 内部多 Agent 设计：[../papers/](../papers/)。
