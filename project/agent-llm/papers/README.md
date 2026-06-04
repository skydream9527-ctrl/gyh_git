# Papers — Agent / AI 论文与 Talk 讨论

> 收录与 Agent / AI 工程相关的论文、技术 Talk、行业演讲，做**结构化讨论**而非简单转译。每篇一个文件，按"背景 → 核心观点 → 关键论据 → 与本仓库的连接 → 反对意见 → 行动项"展开。

---

## 阅读约定

- **不只抄摘要**：核心做法、结构、数据要尽可能写全；不写"读论文就够了"。
- **必带"反对意见"**：每篇至少列一条本仓库现有结论可能与之冲突的点，强迫思考。
- **连接到落地**：每篇必须给出"如果接受这个观点，本仓库哪些文档需要更新 / 新增"。
- **保留原文链接和出处**：缺失出处时显式标注 `TODO`，不要伪造。
- **关键引用直接引原话**——避免"二手转译"误差。

---

## 当前清单

### 工程范式 / 工业 Talk

| 文件 | 主题 | 一句话 |
|---|---|---|
| [harness-engineering-codex.md](harness-engineering-codex.md) | OpenAI Codex 团队 "Harness Engineering"（2026-02） | 5 个月用 Codex 自身写 100 万行（人类零行），工程师工作变成**为 agent 设计环境、约束、反馈** |
| [building-effective-agents.md](building-effective-agents.md) | Anthropic "Building Effective Agents"（2024-12） | **简单 composable patterns 优于复杂框架**——5 种 workflow + 1 种 agent，强调 ACI |
| [multi-agent-research-system.md](multi-agent-research-system.md) | Anthropic "Multi-Agent Research System"（2025-06） | Multi-agent 比单 agent 好 90.2%，但 **15× token 成本**——本质是"把 token 花到对的地方" |

### 评测体系

| 文件 | 主题 | 一句话 |
|---|---|---|
| [demystifying-evals-for-ai-agents.md](demystifying-evals-for-ai-agents.md) | Anthropic "Demystifying Evals for AI Agents"（2026-01） | 三类 grader / pass@k vs pass^k / 4 类 agent 评测套路 / 8 步评测路线图 / Swiss Cheese 多层组合 |

### 经典论文 / 综述

| 文件 | 主题 | 一句话 |
|---|---|---|
| [react-yao-2022.md](react-yao-2022.md) | ReAct（Yao et al, 2022） | Thought-Action-Observation 模板，**当代所有 agent loop 的事实标准** |
| [reflexion-shinn-2023.md](reflexion-shinn-2023.md) | Reflexion（Shinn et al, 2023） | **Verbal RL**：用自然语言反思代替梯度更新，跨 trial 学习 |
| [lilian-weng-llm-agents.md](lilian-weng-llm-agents.md) | Lilian Weng "LLM Powered Autonomous Agents"（2023-06） | **Planning / Memory / Tool Use** 三组件框架——业界事实词汇 |

---

## 阅读顺序建议

**入门路线**（按时间和概念递进）：
1. [lilian-weng-llm-agents.md](lilian-weng-llm-agents.md) — 拿到分类法
2. [react-yao-2022.md](react-yao-2022.md) — 看核心 loop
3. [reflexion-shinn-2023.md](reflexion-shinn-2023.md) — 看跨 trial 学习
4. [building-effective-agents.md](building-effective-agents.md) — 看工程模式
5. [multi-agent-research-system.md](multi-agent-research-system.md) — 看真实系统经验
6. [demystifying-evals-for-ai-agents.md](demystifying-evals-for-ai-agents.md) — 看怎么评
7. [harness-engineering-codex.md](harness-engineering-codex.md) — 看最前沿范式

**问题导向路线**：
- 想搭 agent → ReAct → Building Effective Agents → Reflexion
- 想做评测 → Demystifying Evals → Building Effective Agents（评估部分）
- 想做生产化 → Harness Engineering → Multi-Agent Research System
- 想要分类法 → Lilian Weng → Building Effective Agents

---

## 与仓库其它部分的连接

- Agent 架构 → [../agents/](../agents/)
- Agent 评测 → [../evaluation/](../evaluation/)
- 工程化 / 框架 → [../production/](../production/)
- 工具协议 → [../tools-protocols/](../tools-protocols/)

---

## 新增一篇时的模板

```markdown
# <标题>

> **出处**：<会议/期刊/Blog + URL>
> **作者**：<>
> **发布**：<YYYY-MM>
> **一句话**：<本文核心主张>

## 〇、核心论断（一段读懂）
## 一、背景与动机
## 二、核心观点 / 方法
## 三、关键论据 / 实验
## 四、和本仓库现有结论的对照
## 五、反对意见 / 待验证
## 六、行动项
## 七、关键引用
```

---

## 待补清单（候选）

如果要继续扩，下面这些值得专门写一篇：

- **Toolformer**（Schick et al, 2023）— LLM 自学使用工具
- **Voyager**（Wang et al, 2023）— Minecraft 终身学习 agent
- **Generative Agents**（Park et al, 2023）— 25 个 agent 模拟小镇，已在 Lilian Weng 篇提及但值得展开
- **OpenDevin / OpenHands** 论文 — 多 agent 开源参考
- **SWE-Bench / SWE-Bench Verified**（Jimenez et al, 2024）— 编码 agent 标准评测
- **GAIA**（Mialon et al, 2023）— 通用 AI 助理评测
- **Anthropic Computer Use**（2024-10）— 屏幕级 agent 范式
- **MCP** 官方协议设计文档 — 工具协议标准化
- **Agent SDK / Strands SDK** 设计文档对比
