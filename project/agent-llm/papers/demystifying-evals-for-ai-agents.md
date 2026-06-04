# Demystifying Evals for AI Agents：Anthropic 对 Agent 评测体系的"祛魅"

> **出处**：Anthropic Engineering Blog [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
> **作者**：Mikaela Grace, Jeremy Hadfield, Rodrigo Olivares, Jiri De Jonghe
> **发布**：2026-01-09
> **一句话**：Agent 评测不是"换个 prompt 让 GPT-4 打分"，是一套**结构化的开发-验证-发布工作流**——评测的成本前置可见、收益是后期复利。

---

## 〇、核心论断（一段读懂）

- 没有评测的 agent 团队，**必然陷入被动 debug 循环**：等用户报错 → 复现 → 改 → 祈祷没回归。
- 有了评测，问题在影响用户**之前**就被看见。
- 评测的**复合价值**容易被低估：成本前置可见，收益（更快 ship、更快换模型、回归保护、研究-产品高带宽通道）后期才显形。
- 评测体系应当与**生产监控、A/B 测试、用户反馈、转录审查、人工系统性研究**一起工作——任何单一层都抓不全。
- 这是 Anthropic 自己运营 Claude Code、Claude.ai 网络搜索、对齐审计 agent 等内部产品**实际跑出来**的方法论，不是空泛指南。

---

## 一、评测的"组件分类法"

文章给出一组**严格定义**——后续讨论都基于这套词汇：

| 概念 | 定义 |
|---|---|
| **Task（任务）** | 单个测试，有定义好的输入和成功标准 |
| **Trial（试验）** | 对一个 task 的一次尝试。因为模型非确定，多次 trial 才能统计 |
| **Grader（评分器）** | 评估某一方面的逻辑；一个 task 可有多个 grader，每个含多个 assertions |
| **Transcript（记录 / 轨迹）** | 一次 trial 的完整记录：输出 / tool calls / reasoning / 中间结果 |
| **Outcome（结果）** | trial 结束时**环境的最终状态**——比 transcript 上"我已下单"更可信的是数据库里**真有那条订单** |
| **Evaluation harness（评估框架）** | 端到端跑评测的基础设施：派任务、并发、记录、评分、汇总 |
| **Agent harness** | 让模型作为 agent 行事的系统：处理输入、编排 tool calls、返回结果（注意：评估的是 **harness + model 一起**） |
| **Evaluation suite（评估套件）** | 围绕一个能力或行为聚集的一组任务（如"客服-退款 / 取消 / 升级"） |

> **重要区分**：**transcript** 说"航班已订"，但**outcome** 是数据库里有没有那条 booking。Agent 评测必须看 outcome。

---

## 二、为什么必须建评测——成本/收益的非对称

| 没有评测 | 有评测 |
|---|---|
| Bug 上线后才发现 | 上线前在评测里出现 |
| 改 A 修 B 引入 C | 回归套件直接拦住 |
| 用户报"感觉变差了"，团队盲飞 | 噪声 vs 真回归可分辨 |
| 换新模型要测几周 | 几天内迁完 |
| 产研沟通低带宽 | **评测就是产研之间最高带宽的通道**（研究员有了可优化的指标） |

> "**The compounding value is easy to overlook because costs are visible upfront and benefits accrue later.**"

文章举的实例：
- **Claude Code**：先靠 Anthropic 内部+外部用户反馈快速迭代，**之后**加上评测——先针对 conciseness、文件编辑等窄域，**再**针对 over-engineering 等复杂行为。
- **Descript**（视频编辑 agent）：围绕 "**不要破坏东西 / 做我让你做的事 / 把它做好**" 三维做评测；从手工评分演化到 LLM-judge + 定期人工校准，最终**两个独立套件**：质量基准 + 回归测试。
- **Bolt AI**：先有产品再补评测，**3 个月内**搭出系统：静态分析 + browser agent 测试 + LLM-judge 评指令遵循。

---

## 三、三类 Grader 的取舍

### 3.1 Code-based（基于代码）

- 方法：精确/正则/模糊字符串匹配、二元测试（fail→pass / pass→pass）、静态分析（lint / type / security）、结果验证（DB 状态、文件状态）、tool call 验证（是否调用、参数）、transcript 分析（轮数、token 数）
- 优势：**快、便宜、客观、可重现、易调试**
- 劣势：**对有效但格式不同的回答太脆**，缺细微差别，不擅评主观任务

### 3.2 Model-based（LLM-as-judge）

- 方法：基于标准（rubric）评分、自然语言断言、成对比较、参考解评估、多 judge 共识
- 优势：**灵活、可扩展、能抓细微差别**、能评开放式输出
- 劣势：**非确定**、比 code 贵、**必须和人工校准**

### 3.3 Human

- 方法：SME（专家）审查、众包评判、抽样、A/B、annotator agreement
- 优势：**黄金标准**——校准 LLM-judge 的最终来源
- 劣势：**贵、慢、需要专家**

> **组合策略**：能 deterministic 就 deterministic；必要时上 LLM-judge；人工只用在**校准 LLM-judge** 和**评高度主观/复杂领域**。

每个 task 可以是**加权**（综合分过阈值）、**二元**（所有 grader 必须过）或**混合**。

---

## 四、能力评测 vs 回归评测

| 类型 | 问的问题 | 通过率应该是 |
|---|---|---|
| **Capability evals**（能力评测） | "agent 能做什么？" | **低**（10–40%）→ 给团队一个"山坡可爬" |
| **Regression evals**（回归评测） | "之前能做的现在还能做吗？" | **接近 100%**——掉了就警报 |

**生命周期**：能力评测拿到高通过率后，**毕业为回归套件**，从此持续跑。
- 例：SWE-Bench Verified 一年内从 30% → >80%，已接近饱和；Qodo 因此重做了一套 agent eval framework 来看更长更复杂的任务。

---

## 五、按 Agent 类型分别讲怎么评

### 5.1 编码 Agent（Coding agents）

**特点**：deterministic grader 自然适用——代码是否运行、测试是否通过。

- **SWE-bench Verified**：给 agent 真实 GitHub issue + 测试套件，**修好失败测试且不破坏现有测试**才算过
- **Terminal-Bench**：端到端技术任务，例如从源码编译 Linux 内核、训练 ML 模型

最佳实践：**先用单元测试验证关键结果，再用 LLM rubric 评代码质量、用 transcript 评行为**。

文章给出的示例任务（修身份验证绕过漏洞）的 grader 组合：
```yaml
graders:
  - deterministic_tests: [test_empty_pw_rejected.py, test_null_pw_rejected.py]
  - llm_rubric: prompts/code_quality.md
  - static_analysis: [ruff, mypy, bandit]
  - state_check: security_logs.event_type == "auth_blocked"
  - tool_calls: [read_file(src/auth/*), edit_file, run_tests]
tracked_metrics:
  - n_turns / n_toolcalls / n_total_tokens
  - time_to_first_token / output_tokens_per_sec / time_to_last_token
```

> 实务上一般只用前 2–3 个 grader；上面的清单是"可选项展示"。

### 5.2 对话 Agent（Conversational agents）

**特点**：互动**本身**就是评测对象——需要一个**第二个 LLM 模拟用户**。

- 多维成功：**ticket 是否解决（state）/ 是否 < 10 轮（transcript）/ 语气是否合适（rubric）**
- 经典 benchmark：**τ-Bench / τ²-Bench**——在零售 / 航司预订等场景里，一个 LLM 演用户、agent 跑现实流程

> 注意点：**LLM 演用户**这件事是对话 agent 评测的关键基础设施，不是可选项。

### 5.3 研究 Agent（Research agents）

**特点**：没有"标准答案"——research 质量是相对任务的。

文章建议的 grader 组合：

| Grader | 评什么 |
|---|---|
| **Groundedness** | 声明是否被检索到的来源支持 |
| **Coverage** | 答案是否覆盖了"必须包含"的关键事实 |
| **Source quality** | 来源权威性（不是"第一个搜到的"） |
| **Exact match**（如有客观答案） | 数字/事实精确匹配 |
| **LLM judge** | 标记不支持的声明、覆盖空白、综合一致性 |

> 警告：**研究质量主观性强，LLM-judge 必须经常和专家人工校准**。

代表性 benchmark：**BrowseComp**——大海捞针式查找问题，"易于验证、难以解决"。

### 5.4 Computer Use Agent（计算机使用 agent）

**特点**：通过和人类一样的界面（截图 / 鼠标 / 键盘）交互，**没有 API**。

- 评测要在**真实或沙盒环境**里跑，验证后端状态——例如 WebArena 不只看页面变化，也看**订单是否真的入库**。
- **OSWorld**：评估脚本检查文件系统 / 应用配置 / DB 内容 / UI 元素属性。
- **关键发现**：**DOM 交互快但 token 重；截图慢但 token 高效**。Anthropic 在 Chrome 版 Claude 中专门评测 agent **是否为每个上下文挑了对的工具**。

---

## 六、不确定性：pass@k 与 pass^k

Agent 行为非确定，**单次结果不可信**。两个核心指标：

| 指标 | 含义 | 适用 |
|---|---|---|
| **pass@k** | k 次尝试中**至少 1 次**通过的概率 | "只要一个能行就行"——多解尝试场景（编码、研究） |
| **pass^k** | k 次尝试**全部**通过的概率 | "每次都得稳"——客户面向 agent |

数学直觉：
- 单次成功率 75%，跑 3 次：**pass@3 ≈ 98%，pass^3 ≈ 42%**
- k=10 时两者讲相反故事：pass@k → 100%，pass^k → 0%

> 选哪个**取决于产品要求**——一锤子买卖看 pass@k，常态服务看 pass^k。

---

## 七、从零到一构建评测：8 步路线图

### Step 0：尽早开始
- **20–50 个真实失败任务**就足以起步——别等"几百个"
- 早期改动效应大，**小样本就能看出来**
- 等越久越难补：评测会从"产品规范"退化为"逆向工程现网"

### Step 1：从你已经在手测的开始
- 翻 bug tracker、support queue
- 用户报告的失败 → 测试用例
- 按用户影响排优先级

### Step 2：写明确的任务和参考解
- **黄金标准**：两个领域专家独立判定能给出一样的 pass/fail
- 任务描述里有歧义 → 指标里就是噪声
- **每个任务都要有一个 reference solution**——证明"可解 + grader 配置正确"
- 反例：Terminal-Bench 中曾有任务"写脚本但没指定路径"，测试又要求特定路径——agent 静默失败，**0% pass@100 通常是任务坏了，不是 agent 笨**

### Step 3：构建平衡的题集
- 测**应该发生**的行为，**也**测**不应该发生**的行为
- **单边评测产出单边优化**
- 反例：Claude.ai 网络搜索——只评"该搜的时候搜了没"，agent 会**几乎搜所有东西**。后来加上"不该搜的时候是否克制"——例如"谁创立了 Apple？" 不需要搜
- 不要让类别失衡

### Step 4：搭可重复的 harness
- 每次 trial **从干净环境开始**
- 共享状态会引入伪相关失败 / 不公平的成功
- 真实事件：内部某些评测里 Claude **通过看上一 trial 的 git history** 占了不公平优势——立刻修
- 多 trial 之间因相同基础设施约束（比如内存）而失败 → 这些 trial **不独立**，结果不可信

### Step 5：评分器要"想清楚"再写
- **优先 deterministic > LLM judge > human**
- **不要测"agent 走的步骤是不是对"**——只评**产出**，否则惩罚创造性
- 多组件任务给 **partial credit**：识别问题 + 验证客户但没退款的客服 agent，比立刻失败的好
- LLM judge：
  - 必须和专家校准
  - 给 judge 一个 escape hatch（"信息不足返回 Unknown"）
  - 一条 rubric 一个 prompt——**不要一次评 5 维**
- 防 grader bug：**Opus 4.5 在 CORE-Bench 最初 42%，修了一堆 grader bug 后跳到 95%**——僵化评分（"96.124991..." 不接受 "96.12"）/ 模糊任务 / 不可重现的随机性
- 防 hack：grader 要让"真解决"比"利用漏洞"容易

### Step 6：读 transcript
- "**除非你读 transcript，否则你不知道 grader 是不是在工作**"
- Anthropic 内部投资了专门的 transcript 查看工具
- 失败要"公平"：清楚 agent 错在哪、为什么
- **当分数没涨，得有信心是 agent 没进步而不是评测在骗人**

### Step 7：监控能力评测的"饱和"
- 当 agent 通过所有可解任务，评测**饱和**——继续优化已无信号
- SWE-Bench Verified 今年从 30% → >80%，**接近饱和**
- 接近饱和时，大能力提升只表现为**小分数提升**，结果具有欺骗性
- Qodo 的反应：开发**新一代 agent eval framework**，覆盖更长更复杂任务

### Step 8：长期维护——所有权 + 开放贡献
- 评测套件是**活的工件**，需要持续关注 + 明确 ownership
- Anthropic 试出来的最有效组合：**专门的 evals 团队拥有核心基础设施 + 领域专家和产品团队贡献任务**
- "让 PM / CSM / sales 用 Claude Code 提交 evaluation task PR"——主动启用他们
- **评测驱动开发**：先写评测定义"未来希望 agent 能做什么"，**起始通过率低**没关系——新模型一发布，跑一遍套件立刻看出哪些赌注成功了

---

## 八、Agent 评测在更大图景里的位置（Swiss Cheese Model）

**没有任何一层 100% 抓得全所有问题**——多层组合才是正解：

| 方法 | 优势 | 劣势 | 适合阶段 |
|---|---|---|---|
| **自动化评测** | 快 / 可重现 / 不影响用户 / 可在每次 commit 跑 | 前期投入大；不维护就漂移 | 发布前 + CI/CD |
| **生产监控** | 真实用户行为 / 抓合成评测漏的 / 是 ground truth | 被动；噪声大；缺标签 | 发布后 |
| **A/B 测试** | 衡量真实结果（留存 / 完成率） / 控制混淆 | 慢；需要流量；只测已部署的变更 | 重大变更 |
| **用户反馈** | 揭示意外问题；真实示例 | 稀疏 / 自选偏 / 用户少解释为何 | 持续 |
| **手工 transcript 审查** | 直觉建立 / 抓微妙问题 / 校准 | 时间密集 / 不扩展 / 审查疲劳 | 持续抽样 |
| **系统性人工研究** | 黄金标准 / 主观任务 / 校准 LLM-judge | 贵 / 慢 / 跨评分员需对齐 | 校准期 |

> **类比**：瑞士奶酪模型——单层有洞，多层叠起来就堵住。

---

## 九、附录提到的开源/商业框架

文章列了几个可参考起步的框架——本仓库选型时可对照：

| 框架 | 定位 |
|---|---|
| **Harbor** | 容器化 agent 跑 / 跨云大规模 trial / 标准化 task & grader 格式（Terminal-Bench 2.0 通过 Harbor registry 发布） |
| **Promptfoo** | 轻量、声明式 YAML、prompt 测试，从字符串到 LLM-judge 都支持。Anthropic 内部产品评测**用过它的一个版本** |
| **Braintrust** | 离线评测 + 生产可观测性 + 实验追踪；`autoevals` 库内置 factuality / relevance 等 grader |
| **LangSmith** | 紧贴 LangChain，trace / 离线 / 在线 / dataset 管理 |
| **Langfuse** | 类似 LangSmith 的 self-hosted 开源替代 |

> Anthropic 的中性立场：**框架只和你跑的任务一样好**——选一个能跑通工作流的，把精力**投在评测本身**。

---

## 十、和本仓库现有结论的对照

| 本文论点 | 本仓库已有 / 应更新 |
|---|---|
| Agent harness ≠ Evaluation harness（两个 harness 概念） | [../agents/long-task-agents.md](../agents/long-task-agents.md) 应加一个术语澄清栏 |
| 三层 grader 分类（code / model / human） | [../evaluation/llm-as-judge.md](../evaluation/llm-as-judge.md) 已有 LLM-judge 章节，可加表对照 |
| pass@k vs pass^k | [../evaluation/research-agent-evals.md](../evaluation/research-agent-evals.md) 应补 ↑ |
| 能力 vs 回归 + "毕业"机制 | [../evaluation/research-agent-evals.md](../evaluation/research-agent-evals.md) 应补 ↑ |
| 4 类 agent 各自评测套路 | **建议新增** [../evaluation/agent-eval-by-type.md](../evaluation/agent-eval-by-type.md) |
| transcript vs outcome 区分 | **建议新增** [../evaluation/outcome-vs-transcript.md](../evaluation/outcome-vs-transcript.md) |
| 8 步路线图 | 可作为 [../evaluation/research-agent-evals.md](../evaluation/research-agent-evals.md) 的"实操步骤"小节 |
| Swiss Cheese Model | [../production/observability.md](../production/observability.md) 可加"评测分层"一节 |
| 评测驱动开发（先写评测占位） | 与 CLAUDE.md 中 "TDD Rules" 同向，可在 [../README.md](../README.md) 第 6 节加一句 |

---

## 十一、反对意见与待验证

- **"20–50 个任务就够"** 在前沿模型饱和的领域可能不够——需要更难的"区分性"任务才能继续看出差异。
- **LLM-judge 校准成本被低估**：人工校准本身就是项目；很多团队没这个预算。
- **能力 vs 回归的"毕业"机制**理论清楚，**实操频率**没说——多久看一次饱和？谁来拍板？
- **状态隔离 + per-trial clean env** 需要相对成熟的容器/沙箱基础设施，小团队冷启动成本不低。
- **τ-Bench / τ²-Bench / WebArena / OSWorld** 是 benchmark 范式，但 **私有评测集** 才是 1st-class——文章对 benchmark vs 私有的取舍说得轻。
- **partial credit 的设计很难**：怎么打分、怎么权重、过程评 vs 结果评——文章给原则没给方法论。
- **CORE-Bench 42% → 95% 的修复故事**，对 benchmark 设计者是教训，对 agent 团队是说"评测错可以让 SOTA 看起来差一倍"——**未来引用任何 benchmark 数字都要谨慎**。

---

## 十二、行动项

如果接受本文观点，要在本仓库做：

- [ ] 在 [../evaluation/research-agent-evals.md](../evaluation/research-agent-evals.md) 引言加 Anthropic 这套术语表（task / trial / grader / transcript / outcome / harness / suite）
- [ ] 新增 [../evaluation/agent-eval-by-type.md](../evaluation/agent-eval-by-type.md)：4 类 agent 各自的评测套路
- [ ] 新增 [../evaluation/outcome-vs-transcript.md](../evaluation/outcome-vs-transcript.md)：把"环境状态 vs 模型自述"作为常识写下来
- [ ] 在 [../evaluation/llm-as-judge.md](../evaluation/llm-as-judge.md) 增加 "**校准 / escape hatch / 一 rubric 一 prompt**" 三条最佳实践
- [ ] 在 [../production/observability.md](../production/observability.md) 加 "**Swiss Cheese Model: 多层评测组合**" 节
- [ ] 把 8 步路线图做成 checklist 模板（`.planning/templates/EVAL-ROADMAP.md`）
- [ ] 在仓库根 [../OVERVIEW.md](../OVERVIEW.md) 评测章节顶部，把 "**评测是产研最高带宽通道**" 设为开场观点

---

## 十三、关键引用

- "**Eval suite 解决了规范的歧义**——两个工程师读同一份初稿，对边缘情况的解释会不同；评测套件迫使大家写下来。"
- "**The compounding value is easy to overlook because costs are visible upfront and benefits accrue later.**"
- "**Tools shouldn't be evaluated by the path; evaluate the agent by the artifact.**"（评产出，不评路径）
- "**0% pass@100 是任务坏的信号，不是 agent 笨。**"
- "**We don't trust eval scores until someone has dug into the details and read some transcripts.**"

> 整篇文章的灵魂句：
> **"读 transcript 是 agent 开发的关键技能。"**
