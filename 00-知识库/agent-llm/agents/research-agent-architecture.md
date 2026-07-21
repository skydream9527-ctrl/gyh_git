# 长任务研究 Agent 架构：用 Claude Code + Manus skill + 自定义 subagent

> 本文是端到端的实战文档：怎么把前面讲过的 Skills、Manus 文件式规划、自定义 subagent 拼起来，搭一个**真正能跑几小时的研究 Agent**。最后对比 OpenAI / Google / Anthropic 的产品级方案，给出投资优先级。
>
> 配套：[long-task-agents.md](long-task-agents.md)、[skills-system-design.md](skills-system-design.md)、[multi-agent-coordination.md](multi-agent-coordination.md)、[../production/langgraph-research-agent-impl.md](../production/langgraph-research-agent-impl.md)。

---

## 一、目标定义

我们要搭的是**长任务研究 Agent**——不是问答机器人，是"给一个研究主题，跑几个小时，产出一份高质量研报"的东西。

具体要求：
- 输入：一个研究主题 + 研究深度（surface / deep / exhaustive）
- 跨多个会话能恢复
- 自主完成：信息搜集 + 分析 + 交叉验证 + 报告撰写
- 用户随时能查进度、可以打断/纠偏
- 产出：一份完整的 markdown 研报 + 引用来源

---

## 二、系统架构

```
┌────────────────────────────────────────────────────────┐
│  主 Agent (Claude Code main loop)                      │
│  ┌──────────────────────────────────────────────┐     │
│  │ 加载 skills:                                  │     │
│  │   1. manus-planning (文件式规划)              │     │
│  │   2. research-protocol (研究方法论)           │     │
│  │   3. citation-management (引用管理)           │     │
│  └──────────────────────────────────────────────┘     │
│                                                        │
│  Tools:                                                │
│    Read, Write, Edit, Bash, WebSearch, WebFetch        │
│                                                        │
│  Subagents (Task 工具):                                │
│    ├── researcher        (找信息 + 总结)                │
│    ├── verifier          (交叉验证、找反证)              │
│    ├── synthesizer       (整合多源信息)                  │
│    ├── outline-writer    (生成大纲)                     │
│    ├── section-writer    (写某一章节)                   │
│    ├── reviewer          (审核章节)                     │
│    └── plan-updater      (更新规划文件)                 │
│                                                        │
│  Workspace:                                            │
│    research/<topic-slug>/                              │
│    ├── task_plan.md                                    │
│    ├── findings.md                                     │
│    ├── progress.md                                     │
│    ├── sources/          (检索到的原始资料)              │
│    ├── notes/            (各专家的笔记)                  │
│    ├── outline.md                                      │
│    └── report.md         (最终输出)                     │
└────────────────────────────────────────────────────────┘
```

---

## 三、研究协议 skill

`.claude/skills/research-protocol/SKILL.md`：

```markdown
---
name: research-protocol
description: |
  Activates rigorous research methodology for long-form research tasks.
  Use when user asks for in-depth research, market analysis, technical deep-dive,
  or any task that needs >1 hour of investigation across multiple sources.
  Do NOT use for quick lookups or single-question queries.
trigger_phrases:
  - "深度研究"
  - "研报"
  - "调研"
  - "deep research"
  - "comprehensive analysis"
---

# Research Protocol

You are coordinating a long-form research task. Follow this protocol strictly.

## Phase Structure

### Phase 1: Scoping (单次 Agent，不派 subagent)
1. Read user's request
2. Identify:
   - Core question(s)
   - Required depth (surface / deep / exhaustive)
   - Likely information sources
   - Estimated effort (hours)
3. Confirm with user before proceeding
4. Write `task_plan.md` (use manus-planning skill)

### Phase 2: Information Gathering (并行派 researcher)
For each sub-topic in task_plan:
- `Task(subagent_type="researcher", prompt="<sub-topic>")`
- 主 Agent 等结果，append to findings.md

**Critical**: 多个 sub-topic 必须**并行派出**（一个 message 多个 Task 调用），不要串行。

### Phase 3: Cross-Verification (并行派 verifier)
For each major claim collected:
- `Task(subagent_type="verifier", prompt="<claim> + <evidence>")`
- Mark each claim: confirmed / disputed / single-source

### Phase 4: Synthesis (单次 synthesizer)
- `Task(subagent_type="synthesizer", prompt="<all confirmed findings>")`
- Output: structured insights, contradictions, gaps

### Phase 5: Outlining (单次 outline-writer)
- `Task(subagent_type="outline-writer", prompt="<synthesis output>")`
- Output: section-by-section outline with key points

### Phase 6: Drafting (并行派 section-writer)
For each section in outline:
- `Task(subagent_type="section-writer", prompt="<section spec> + <findings>")`
- 主 Agent 收集后串成 report.md

### Phase 7: Review (单次 reviewer)
- `Task(subagent_type="reviewer", prompt="<full report>")`
- Apply suggested edits

### Phase 8: Final delivery
- Output report.md to user
- Update progress.md to "complete"

## Quality Bar

- Every factual claim has at least one source (link in `sources/`)
- Disputed claims explicitly flagged
- Reasoning chains traceable in `findings.md`
- Final report should be readable standalone (no "see earlier section")

## Critical Rules

- 永远先派 subagent 出去做事，不要主 Agent 自己读资料（爆 context）
- 主 Agent 只做：规划、汇总、决策
- 每个 phase 结束更新 progress.md
- 中断恢复时：read progress.md → 知道在哪个 phase → 继续
```

---

## 四、各专家 Subagent

### researcher

`.claude/agents/researcher.md`：

```markdown
---
name: researcher
description: |
  Researches a specific sub-topic deeply. Use when main agent needs
  information gathered on a focused topic. Returns structured findings
  with source citations. Do NOT use for verification (use verifier).
tools: WebSearch, WebFetch, Read, Write
model: sonnet
---

You are a research specialist.

## Input
You will receive a sub-topic to research. Example:
"Research: 2026 年 AI Agent 框架的市场份额和增长趋势"

## Process

1. **Scope the sub-topic** (1 minute thinking, no tool call)
2. **Search broadly first** — 3-5 WebSearch queries with different angles
3. **Fetch and read** — WebFetch top sources
4. **Save raw sources** — to `research/<topic-slug>/sources/<source-id>.md`
5. **Output structured findings**

## Output Format (MUST follow)

\`\`\`
## Sub-topic: <name>

### Key findings
- <finding 1, 1-2 sentences>
- <finding 2>

### Source citations
| Finding ref | Source | URL | Excerpt location |
|---|---|---|---|
| 1 | sources/abc.md | https://... | "..." |

### Confidence
- High-confidence claims: [list]
- Single-source claims (need verification): [list]
- Conflicting info found: [list]

### Gaps
- What I couldn't find: [list]
\`\`\`

## Critical Rules

- Don't just summarize what one source says — synthesize across sources
- Flag single-source claims explicitly (verifier will check them)
- Be terse: each finding 1-2 sentences max
- ALWAYS save raw sources to sources/ folder
- If a claim seems too clean / promotional → flag for verification

## When to give up
- After 15 WebSearch + 10 WebFetch with no useful info
- Output: "GAP: <topic> — couldn't find reliable sources"
```

### verifier

`.claude/agents/verifier.md`：

```markdown
---
name: verifier
description: |
  Verifies a specific claim by finding independent corroborating or
  contradicting sources. Use AFTER researcher when a claim is single-source
  or seems important. Do NOT use for general research (use researcher).
tools: WebSearch, WebFetch, Read
model: opus
---

You are a fact-checker. Your job is to **independently verify** a claim.

## Input
You will receive:
- A specific claim
- Original source(s) the claim came from

## Process

1. **Reformulate** the claim 2-3 different ways for searching
2. **Search for independent sources** — Different domains than the original
3. **Apply skepticism**
   - Vendor blog about own product? → low credibility
   - Cited study → check the study itself
   - "Industry-leading" type claims → look for actual data

## Output Format

\`\`\`
## Claim
<original claim>

## Verdict
[CONFIRMED | DISPUTED | UNVERIFIABLE | PARTIALLY-CONFIRMED]

## Reasoning
<2-3 sentences>

## Independent sources
1. [Confirms/Contradicts]: <source> — <key quote>

## Caveats
<What's still uncertain>
\`\`\`

## Critical Rules

- ALWAYS look for at least one independent source (not the original)
- If you only find sources that all cite the same primary → DISPUTED
- Vendor self-claims → require independent corroboration
- "Could not find disconfirming evidence" ≠ confirmed
```

### synthesizer / outline-writer / section-writer / reviewer

骨架类似，每个 1-2 页详细 protocol。**关键差异**：

```yaml
# synthesizer: 看所有 findings + verifications，输出"洞察"
tools: Read
model: opus  # 综合需要强模型

# outline-writer: 看 synthesis 输出，做章节划分
tools: Read, Write
model: sonnet

# section-writer: 写一章
tools: Read, Write, Edit
model: sonnet

# reviewer: 审最终报告
tools: Read, Edit
model: opus  # 审稿需要强模型
```

### plan-updater

详见 [long-task-agents.md](long-task-agents.md) 第五节。

---

## 五、启动方式

用户输入：
> "深度研究：2026 年中国大模型 To B 商业化进展，3 小时内出报告"

主 Agent 行为序列（**这是 Claude Code 自动跑的，不需要你手动指挥**）：

```
[Step 1] skill_router 召回
  → 命中 research-protocol（trigger: "深度研究"）
  → 命中 manus-planning（trigger: 长任务）
  → 加载两个 skill 的 body

[Step 2] Phase 1: Scoping
  → 主 Agent 自己思考，分解成 8 个 sub-topics
  → 创建 research/cn-llm-tob-2026/ 目录
  → 写 task_plan.md（8 phase × 8 sub-topic 矩阵）
  → 询问用户确认

[Step 3] Phase 2: 并行派 researcher（关键！）
  → 一个 message 里输出 8 个 Task 工具调用
  → 8 个 researcher 同时跑（每个独立 context）
  → 主 Agent 等待结果

[Step 4] 收集 8 份 findings
  → 派 plan-updater 更新 findings.md（追加）
  → 派 plan-updater 更新 progress.md（phase 2 done）

[Step 5] Phase 3: 并行派 verifier
  → 主 Agent 看 findings，挑出 ~15 个关键 claim
  → 派 15 个 verifier 并行
  → 收集 verdict

[Step 6] Phase 4: synthesizer
  → 一次 Task 调用，传入全部 findings + verdicts
  → 拿到结构化洞察

[Step 7] Phase 5: outline
  → outline-writer 出大纲

[Step 8] Phase 6: 并行派 section-writer
  → 大纲有 N 章 → 派 N 个 section-writer
  → 每人写一章

[Step 9] Phase 7: reviewer
  → 主 Agent 把章节拼成 report.md
  → 派 reviewer 审

[Step 10] Phase 8: 交付
  → 应用 reviewer 修改建议
  → 把 report.md 给用户
```

---

## 六、中断恢复

**场景**：跑到 Phase 3 一半，用户关电脑了。

第二天打开 Claude Code，进入同一目录：

```
用户：继续昨天的研究
```

主 Agent 行为：
```
[Step 1] manus-planning skill 自动触发（因为目录里有 task_plan.md）
[Step 2] 主 Agent 读 progress.md
  → 发现 phase 3 有 8/15 verifier 完成
[Step 3] 读 task_plan.md
  → 知道整体计划
[Step 4] 派出剩余 7 个 verifier
[Step 5] 继续 phase 4...
```

**整个恢复流程主 Agent 不需要任何指导**——文件就是状态机。

---

## 七、关键设计选择的解释

### 为什么主 Agent 自己不读资料

主 Agent 的 context 是稀缺资源。**让 researcher 子 Agent 读 50 个网页，把核心结论汇报给主 Agent，主 context 永远干净**。

如果主 Agent 自己 WebFetch 50 次，每次返回几千 token，**还没到合成阶段 context 就爆了**。

### 为什么 verifier 必须独立

研究报告最大的失败模式是"vendor PR 当事实"。verifier 子 Agent 拿到的 prompt 里**只有 claim**，没有原始 source 来源——这样它做搜索时不会被"认知锚定"在那个来源上。

### 为什么 plan-updater 单独存在

主 Agent 自己更新文件也行，**但每次更新会消耗 ~500 主 context token**。让 plan-updater 用 haiku 跑，主 Agent 一句话派出去就行：

```
Task(subagent_type="plan-updater", 
     prompt="Append to findings: <要记录的内容>")
```

主 context 只增加一句话。

### 为什么用 Claude Code 而不是 LangGraph

**LangGraph 也能做**，但要写大量 state schema、节点定义、condition edges。**Claude Code 的方案 = 8 个 markdown 文件**，业务方都能改。

LangGraph 适合：流程极其稳定、要求严格 SLA、需要数据库 checkpoint。
Claude Code 适合：原型 → 生产、迭代快、需要工程师以外的人能改。

LangGraph 完整复刻见 [../production/langgraph-research-agent-impl.md](../production/langgraph-research-agent-impl.md)。

---

## 八、实战时的几个坑

### 坑 1：subagent 太多导致主 context 还是爆

每个 Task 返回的结果会进主 context。8 个 researcher 每个返回 3K token = 24K 直接进主 context。

**解决**：让 researcher **把详细内容写到 notes/ 文件**，**只返回简短总结 + 文件路径**。主 Agent 需要细节时再 Read。

### 坑 2：研究主题太广，researcher 跑偏

```
prompt = "Research 2026 中国大模型 To B 商业化"
```
researcher 拿到这种宽 prompt 会乱跑。

**解决**：scoping 阶段一定要**拆得足够细**。每个 researcher 的 prompt 应该是：

```
Research: 智谱 AI 2026 年 To B 收入数据 + 重点客户案例
Focus: 数字、财报披露、媒体报道
Avoid: 营销稿、官方博客
Time: 2025-09 到 2026-05
```

### 坑 3：多轮跑下来 token 成本失控

8 researcher × 8K token + 15 verifier × 5K token + ... ≈ 200K+ token。一次研究跑下来 $5-20 不奇怪。

**解决**：
- 简单工作（researcher 的初步 search）用 sonnet
- 重要决策（synthesizer / reviewer）用 opus
- plan-updater / 格式化工作用 haiku
- 加预算上限 hook，跑超额自动停

### 坑 4：用户中途想纠偏

用户看 findings.md 发现方向不对，想调整。

**解决**：用户**直接编辑 task_plan.md 或 findings.md**，加一个 `## USER NOTE: ...` 章节。主 Agent 每次启动会读这些文件，自动看到用户的指示。**这是文件式规划的隐藏优势**——人和 Agent 共享同一份"工作记忆"。

---

## 九、这套系统的边界

适合：
- ✅ 主题型研究（市场分析、技术调研、政策梳理）
- ✅ 跨多源信息需要交叉验证
- ✅ 跨小时甚至跨天的长任务
- ✅ 需要可审计、可纠偏

不适合：
- ❌ 实时数据（股价、新闻）—— 信息 5 分钟就过期
- ❌ 需要付费数据库（Bloomberg / 学术库）—— Claude Code 的 WebSearch 拿不到
- ❌ 需要 SOTA 学术深度 —— LLM 综合能力 + 公开数据有上限

---

## 十、vs 产品级方案：OpenAI / Gemini / Anthropic Deep Research

我们方案大约能达到产品级方案 **30-50% 的能力**——剩下 50-70% 的差距来自**模型私有能力 + 数据源 + 工程基础设施**，不是架构。

### OpenAI Deep Research（2025）

**模型层面**：
- 用的是基于 **o3 系列**的特化模型（"deep research model"）
- 通过 **end-to-end RL 训练**优化"研究行为"——不是 prompt engineering
- 训练时用人类标注的"研究轨迹"作为正反馈

**Agent 层面**：
- 单 Agent 架构（不是多 Agent 协作！）
- 内部有 **planning → search → read → reason → synthesize** 循环
- 跑一次任务通常 5-30 分钟，调用工具数十次到上百次

**关键差异 1：模型不一样**

OpenAI 的 deep research model 是**专门训出来的**，不是 GPT-4o 加 prompt。

```
我们的方案：通用 LLM + 复杂 prompt + 复杂编排
OpenAI 方案：特化 LLM（已经"内化"研究方法论）+ 简单循环
```

差异最大的地方：
- 我们要在 prompt 里教模型"找不到信息时怎么换关键词"
- OpenAI 模型直接学会了"什么 query 形态在什么场景有效"
- 我们要 verifier 来检测虚假 claim
- OpenAI 模型自己有"这个来源不可信"的内在判断（RL 训出来的）

**意味着**：你 prompt 调得再好，**也比不过专门训练**。但训练成本是九位数美元起。

**关键差异 2：单 Agent 比多 Agent 跑得好（在他们的设定下）**

OpenAI 团队明确说过：deep research 是**单 Agent 多步**，不是多 Agent 协作。

为什么？因为：
- 模型已经学会"自己规划"，不需要 planner agent
- 模型已经学会"自己判断 source 质量"，不需要 verifier agent
- 多 Agent 的协调开销对他们是**负担**而不是**优势**

**这印证了**："多 Agent 不会让答案更聪明，模型够强时单 Agent 更好"。我们做多 Agent 协作 + 协商机制，本质是因为**模型不够强，需要工程补足**。

**关键差异 3：浏览器交互而不是 Search API**

OpenAI 用真浏览器：
- 能登录付费墙
- 能渲染 JS 网站
- 能截图理解视觉内容
- 能跟动态 widget 交互

详见 [../tools-protocols/browser-automation.md](../tools-protocols/browser-automation.md)。

### Google Gemini Deep Research

**关键差异**：
- 基于 Gemini 2.5 Pro 优化
- 强调 **plan-driven**：先生成完整 research plan，给用户看，用户编辑后才开跑
- **2M 上下文窗口**：理论上能把所有 source 一次塞进 context

**架构层面**：
- 有显式的 **plan-edit-execute** 三阶段
- plan 阶段就是大纲式的，用户能改
- execute 阶段是迭代式 search-and-read

**最大特色**：**user in the loop 在 plan 阶段，不在 execute 阶段**。

| | 我们的方案 | Gemini Deep Research |
|---|---|---|
| Plan 是否可见 | task_plan.md（事后看） | **Plan 先确认才执行** |
| 用户能否编辑 plan | 改 markdown 文件 | UI 直接拖拽 |
| 执行透明度 | LangGraph trace | Gemini 实时显示进度 |
| 长 context | RAG/抽取 | **2M 直接吃** |

**Gemini 的杀手锏是 2M context**：能把 50 个 source 完整原文塞进去，而不需要"提取 claim → 抛弃原文"流程。这极大降低了"提取丢信息"的风险。

### Anthropic 的 Multi-Agent Research

详见 [multi-agent-coordination.md](multi-agent-coordination.md) 第四节。

**核心**：他们也用多 Agent，但用 Lead Researcher 集中协调。Lessons learned：**多 Agent 提升 ~90% 的复杂研究质量，但 token 用量是单 Agent 的 ~15 倍**。

**重要 takeaway**：他们也承认多 Agent 在简单问题上不划算。**只有当任务真的复杂到一个 Agent 处理不过来时，多 Agent 才赚回成本**。

### 三家产品级方案对比

| | OpenAI Deep Research | Gemini Deep Research | Anthropic Research |
|---|---|---|---|
| 架构 | 单 Agent + 特化模型 | Plan-Execute + 长 context | 多 Agent + 共享 memory |
| 关键创新 | RL 训练研究行为 | Plan 可编辑 + 2M context | Subagent 自动协商 |
| 用户介入 | 看进度 | **编辑 plan** | 看进度 |
| 跑一次时间 | 5-30 分钟 | 5-30 分钟 | 5-30 分钟 |
| 跑一次成本（公开估算） | $5-30 | $5-20 | $10-40 |
| 我们能学的 | RL 思路 | Plan-edit UX | 多 Agent 协议 |

---

## 十一、跟我们方案的具体差距

### 差距 1：模型质量（最大）
- 没法解决，除非自己训
- **缓解**：尽量用 Opus / GPT-5 等最强模型；针对性 prompt 优化

### 差距 2：浏览器能力
- WebFetch 不能处理 SPA / paywall
- **缓解**：接 Playwright 或 Browser-Use 之类的真浏览器 agent（详见 [../tools-protocols/browser-automation.md](../tools-protocols/browser-automation.md)）

### 差距 3：评测体系
- 我们没有"研报质量评测集"
- 产品级方案有大量人工标注 + 自动评测
- **缓解**：建一个 30-50 个 topic 的黄金集（详见 [../evaluation/research-agent-evals.md](../evaluation/research-agent-evals.md)）

### 差距 4：UX 和实时反馈
- 产品给用户实时进度、可中断、可看引用
- 我们要自己做这些
- **缓解**：把 LangGraph 流式输出接到前端

### 差距 5：可靠性 / 长任务稳定
- 产品级方案有大量重试、降级、错误恢复
- **缓解**：每个节点加 try-except + 重试；用 langsmith 做长期监控

---

## 十二、什么场景值得自己做（不用产品级方案）

### 场景 1：内部数据 / 私域知识

OpenAI / Gemini Deep Research **只能搜公开互联网**。如果你的研究需要：
- 公司内部 wiki
- 内部数据库
- 付费数据源（已订阅）
- 客户提供的资料

**只能自己搭**。我们的方案能接任何数据源。

### 场景 2：定制研究方法论

不同行业的研究方法论不同：
- 法律研究要"先找最高院判决，再找下级法院"
- 医学研究要"先 RCT，再 meta-analysis，最后 case study"
- 投资研究要"先 10-K，再卖方研报，最后产业链上下游"

**通用 deep research 抓不准这些**。我们的方案能在 skill 里写明确的方法论。

### 场景 3：成本敏感 / 高频调用

OpenAI Deep Research 一次几美元。如果你要**每天跑 100 次**，月成本上万美元。

自己搭 + 用便宜模型（Haiku / Gemini Flash）+ 缓存命中过的 query → 成本能压到 1/10。

### 场景 4：可审计 / 合规

合规要求你能解释"这份研报是怎么得出每个结论的"。产品级方案是黑盒。

我们的方案：每个 claim 都有 source、blackboard 全部可查、流程完全可追溯。

---

## 十三、投资优先级（如果你要做这件事）

如果你打算用今天讨论的方案做产品，**建议的投资优先级**：

```
高 ROI（必须做）：
├─ 1. 评测集 + 自动评测 — 没这个所有迭代都是玄学
├─ 2. 浏览器 agent 接入 — 解锁付费源 + 动态网站
└─ 3. 流式 UX — 用户体验决定能不能用

中 ROI（值得做）：
├─ 4. 黑板 + 协商机制 — 多 Agent 协调的核心
├─ 5. 失败重试 + 降级 — 稳定性
└─ 6. 内部数据源 connector — 区分于通用方案的关键

低 ROI（先别做）：
├─ 7. 自己 RL 训模型 — 投入产出比极低
├─ 8. 2M context 替代抽取 — Claude 现在做不到
└─ 9. 完全无 prompt 自主 — 不可能
```

---

## 十四、关键启示

**自己搭研究 Agent，不是为了"超过 OpenAI/Google"——而是为了在他们覆盖不到的场景（内部数据、定制方法论、可审计）做出 80 分的产品**。

通用产品级方案 + 自建定制方案的混合策略，是大多数公司的最优解：
- 大众场景用 OpenAI/Gemini Deep Research（能力强、成本可接受）
- 专业场景用自建方案（能控制数据流、可定制、合规）

---

## 十五、扩展阅读

- [long-task-agents.md](long-task-agents.md) —— Claude Code / OpenHands / Manus / Devin
- [skills-system-design.md](skills-system-design.md) —— Skills 机制
- [multi-agent-coordination.md](multi-agent-coordination.md) —— 协商机制
- [subagent-patterns.md](subagent-patterns.md) —— Task / Crew / Subgraph 对比
- [../production/langgraph-research-agent-impl.md](../production/langgraph-research-agent-impl.md) —— 完整 LangGraph 实现代码
- [../tools-protocols/browser-automation.md](../tools-protocols/browser-automation.md) —— 浏览器接入
- [../evaluation/research-agent-evals.md](../evaluation/research-agent-evals.md) —— 评测体系
