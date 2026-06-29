# Harness Engineering：在 agent-first 世界里用好 Codex

> **出处**：OpenAI 官网博客 [Harness Engineering: Leveraging Codex in an Agent-First World](https://openai.com/index/harness-engineering/)
> **作者**：Ryan Lopopolo（Member of the Technical Staff, OpenAI）
> **发布**：2026-02-11
> **一句话**：Codex 团队 5 个月用 Codex 自身写了一个 100 万行代码的内部 Beta 产品（人类零行手写），"工程师" 的工作从写代码变成**为 agent 设计环境、约束、反馈**——这就是 harness engineering。

---

## 〇、最关键的事实（一段读懂）

- 起点：2025 年 8 月底，空仓库，**第一个 commit 是用 Codex CLI + GPT-5 跑出来的脚手架**。
- 5 个月内：**100 万行代码 / ≈1500 个 PR / 平均每人每天 3.5 个 PR**。
- 团队规模：**3 人 → 7 人**，吞吐量随团队成长**正向放大**。
- **零行手写代码**：人类直接写代码被定义为"failure mode"——"agent 没做到，说明 harness 缺了一个能力"。
- 工程师做什么：**设计环境（context）、设计约束（architecture）、设计反馈（entropy 管理）**。

> "**The bottleneck was the environment, not the model.**"
> 模型能力够了；缺的是结构、工具、反馈、清晰约束。

---

## 一、什么是 "Harness"

OpenAI 在文中给的定义（关键 4 条）——一个 harness 是这样一组系统设计与实现：

1. **Constrain**：约束 agent 能做什么
2. **Inform**：告诉 agent 该做什么
3. **Verify**：验证 agent 是否做对
4. **Correct**：在 agent 出错时纠正它

**Harness engineering ≠ Context engineering**：
- Context engineering 问：*agent 应该看到什么？*
- Harness engineering 问：*系统应该阻止什么、度量什么、纠正什么？*

> 这是本文的"分类学贡献"——把过去模糊的"agent 工程"切成两件事：**给模型看什么** vs **包住模型怎么干活**。

---

## 二、三大支柱（The Three Pillars）

OpenAI 把成功的 harness 总结为 **3 根柱子**。这是全文最经典的章节，下面逐根展开。

### 支柱 1：Context Engineering — "给地图，不给手册"

**核心教训**：context 是稀缺资源。一个一千页的 instruction 文件会把任务、代码、相关文档**挤出 context**——agent 要么漏掉关键约束，要么对错误目标过拟合。

具体做法：

| 做法 | 细节 |
|---|---|
| **AGENTS.md ≈ 100 行** | 短，作为"地图"，指向仓库其他位置的"真理之源" |
| **真理之源版本化** | 设计文档 / 架构图 / 执行计划 / 质量评分，**和代码一起 versioned** |
| **动态可观测性** | Chrome DevTools Protocol 接进运行时，agent 能"看见" UI、复现浏览器侧 bug |
| **每任务隔离的 observability stack** | 日志 / 指标 / spans，按任务隔离 |
| **可度量的约束语句** | "startup should complete under 800ms" 不再是口号，**直接可量化** |
| **仓库面向 Codex 可读性优化** | 不再是 "for human first"，是 "**for agent first**" |

> "**Anything the agent cannot access in-context does not exist.**"
> Agent 拿不到的上下文 = 不存在。

### 支柱 2：Architectural Constraints — 架构靠机器强制，不靠文档

最反直觉的一条：**架构边界不写在 README 里，写在 lint / test / dependency graph 里**，让违反它的代码**根本无法 merge**。

具体做法：

- **强制依赖图**：`Types → Config → Repo → Service → Runtime → UI`
- **结构性测试**（structural tests）：在 CI 里检查依赖方向是否合规
- **自定义 linter**：检查命名、模块边界、语义正确性
- **关键技巧**：**linter 错误信息直接当修复指令写**——每条失败信息都教 agent 怎么修

> "**The system is not just blocking mistakes; it is training the agent while it works.**"
> 系统不只是阻止错误，是在工作中训练 agent。

**第一性原理**：Agent 在受限解空间里表现更好。约束不是限制，**约束就是脚手架**。

### 支柱 3：Entropy Management — 对抗"AI 槽点累积"

**Agent 会复制已有模式——好的也复制，坏的也复制。漂移不可避免。**

早期失败：团队每周五花 ~20% 时间手工清"AI slop"。**不可扩展**。

后来的解法：

| 机制 | 作用 |
|---|---|
| **Golden rules** | 显式版本化的质量标准 |
| **Quality grades** | 给代码各区块打质量分，**随时间追踪** |
| **后台清理 agent** | 周期性扫"过期文档 / 违反约束 / 模式漂移"，开小 refactor PR，**大多数自动 merge** |

类比：这是**代码质量的垃圾回收**。人类品味只输入一次（编码进规则），之后由 agent 持续执行。

> "**Cleanup throughput scales proportionally with code generation throughput.**"
> 清理吞吐量必须随生成吞吐量同比例放大。

---

## 三、工程工作怎么变了

### 人类**停止做的事**

- **永远不直接写代码**——这不是失误，是 *核心哲学*。
- 一旦看到"我手敲了一行"，就把它当成"harness 缺一个能力"的信号。

### 人类**开始做的事**

当 agent 卡住，工程师问的问题不再是 "怎么改 prompt？"，而是：

1. **什么能力缺失了？**（→ 加 tool）
2. **什么约束没被强制？**（→ 加 linter / 结构性测试）
3. **怎么让这类失败永不再发生？**（→ 写一条机器可执行的规则）

> "**Every agent mistake is an opportunity to engineer a solution so the agent never makes that mistake again.**"
> 每一次 agent 出错都是一次"让它永不重犯"的工程机会。

工程问题从 **"What should we prompt?"** 转向 **"What capability is missing, and how do we make it visible and enforceable?"**

### 复利效应

- 每加一条约束，未来 agent 的工作可靠性 ↑
- 每多一个 cleanup agent，人类维护负担 ↓
- 系统越来越能"在没有人盯着的情况下"吸收 agent 产出

→ **Harness 是会复利的资产**，不是 sprint 任务。

---

## 四、知识管理（Knowledge Management）

因为整个仓库都是 agent-generated，仓库**首先服务 Codex 的"可读性"**：

- Design documents 与代码同版本
- Architecture maps agent 直接可读
- Execution plans 把任务分解为 agent 大小的单元
- Quality grades 按区块追踪健康度
- 后台 agent 周期性扫描文档缺口和约束违规，自动开 cleanup PR

**结论**：仓库知识不是 README 的副产品，是**一个 versioned product**，由 agent 自己维护新鲜度。

---

## 五、已达到的规模

| 指标 | 5 个月 |
|---|---|
| 代码量 | ~1,000,000 行 |
| PR 数 | ~1,500 |
| 人均 PR 吞吐 | 3.5 / 天 |
| 团队 | 3 → 7 人 |
| 团队成长后吞吐 | **持续上升**（不衰减） |

> 关键反直觉点：**团队增长没有让人均吞吐下降**——因为人没在写代码，每加一个人是加一个 harness 设计者。

---

## 六、七条核心 Lessons（原文末尾原话）

1. **Context is scarce** — 一张短地图胜过一本长手册
2. **Enforce architecture mechanically** — 结构性测试抓的是 instruction 抓不到的
3. **Write errors that teach** — linter 错误信息要兼任"agent 教学指令"
4. **Automate entropy** — 清理必须随生成同比例扩展
5. **Every mistake is a harness bug** — 把修复编码进系统，不要只补输出
6. **Observable environments unlock reliable prompts** — 可度量的约束取代"愿景式"约束
7. **The bottleneck was the environment, not the model** — 瓶颈在环境，不在模型

---

## 七、和本仓库现有结论的对照

| 本文关键观点 | 本仓库已有 / 应更新 |
|---|---|
| Harness ≠ Context | 概念对照：[../README.md](../README.md) 第 5 节 "工具协议与生态" |
| 用结构性测试强制架构 | [../production/observability.md](../production/observability.md)、`.planning/codebase/APPROVED-PATTERNS.md`（CLAUDE.md 已有约束） |
| 短 AGENTS.md + 链入深层文档 | 仓库根 `AGENTS.md` 已是这个范式（CLAUDE.md 提及）✓ |
| 后台 cleanup agent | [../agents/long-task-agents.md](../agents/long-task-agents.md) 中"维护型 agent"小节可加 |
| Linter error 当 agent 教程 | [../tools-protocols/tool-development.md](../tools-protocols/tool-development.md) 应加一节"error message as instruction" |
| 仓库面向 agent 可读性优先 | [../agents/skills-system-design.md](../agents/skills-system-design.md) 同向 |
| 失败 = harness bug | [../agents/long-task-agents.md](../agents/long-task-agents.md) 中失败模式表的"根因"修订 |

---

## 八、反对意见与待验证

- **3.5 PR/人/天 ≠ 普适生产力**：Codex 团队是模型团队，非常熟悉模型行为；其他团队复刻这个数字非常难。
- **零行手写**是哲学而非铁律：在外部团队，**部分手写 + 渐进迁移**可能是更合理路径，否则陷入"为了不写代码而堆 harness"的反过度工程。
- **架构强制 vs 创新**：把架构钉死在 dependency graph 里，对探索性项目可能扼杀变化。Codex 项目是已知架构，不是探索期。
- **Cleanup agent 的成本未披露**：后台 agent 持续扫描和开 PR，**算力成本可能不小**，论文未给数字。
- **AGENTS.md ~100 行**对小项目够；大型 monorepo（>10M 行）能否还撑得住？OpenAI 没说。
- **可观测性栈"per-task isolated"**：好，但工程实现复杂度高（容器 / 沙箱 / 日志路由），中小团队搭不起。

---

## 九、行动项（如果接受这些观点）

- [ ] 在 [../agents/long-task-agents.md](../agents/long-task-agents.md) 里加一节 **"Harness Engineering: 长任务 agent 框架的统一抽象"**，把 6 失败模式归到 `Constrain / Inform / Verify / Correct` 四象限
- [ ] 新增 [../tools-protocols/error-as-instruction.md](../tools-protocols/error-as-instruction.md)：写 linter / API error 时**默认假设 agent 会读它**
- [ ] 在 [../production/observability.md](../production/observability.md) 加 **"Per-task isolated observability"** 小节
- [ ] 在 [../agents/skills-system-design.md](../agents/skills-system-design.md) 头部加一句："仓库本身就是最大的 skill 仓库——前提是 agent 可读"
- [ ] 在 [../README.md](../README.md) 第 4 节"Agent 架构"末尾新增一项："**Harness Engineering（OpenAI Codex 团队范式）**"
- [ ] 把 7 条 Lessons 做成 checklist，挂到仓库根 `.planning/codebase/APPROVED-PATTERNS.md`

---

## 十、关键引用

- "The engineer's job shifts from writing code to designing environments, specifying intent, and building feedback loops that allow agents to do reliable work."
- "Anything the agent cannot access in-context does not exist."
- "The system is not just blocking mistakes; it is training the agent while it works."
- "Every agent mistake is an opportunity to engineer a solution so the agent never makes that mistake again."
- "The bottleneck was the environment, not the model."

> 整篇文章可以用一句话压缩：
> **从写代码 → 写让 agent 不会犯错的系统**。
