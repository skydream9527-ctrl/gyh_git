# How We Built Our Multi-Agent Research System：Anthropic 多 agent 研究系统的工程经验

> **出处**：Anthropic Engineering Blog [How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
> **发布**：2025-06-13
> **一句话**：Claude 的 Research 功能用 multi-agent 架构（lead + parallel subagents），在内部 research eval 上**比单 agent 好 90.2%**，但代价是**token 用量是普通 chat 的 ~15 倍**——multi-agent 系统的本质是**把 token 花在该花的地方**。

---

## 〇、核心论断（一段读懂）

- Research 任务本质是**开放、动态、路径依赖**的——研究过程中不断根据发现调整方向，**没有一条固定 pipeline 能搞定**。
- Multi-agent 的力量来自三件事：
  1. **并行**：subagents 各自有独立 context window，并行探索不同方面
  2. **压缩**：subagents 在自己的 context 里做大量信息，把"压缩后的关键 tokens"返回给 lead
  3. **关注点分离**：每个 subagent 有自己的 tools / prompt / 探索轨迹
- 关键发现：**Token 用量本身解释了 BrowseComp 性能方差的 80%**——multi-agent 的本质就是"让模型有更多 token 可花"。
- 但代价：**multi-agent 系统比 chat 多用 ~15× token**。**只有任务价值高到足以付得起这成本**才划算。

---

## 一、什么时候 multi-agent 真的有价值

**适合**：
- 研究类任务，**广度优先 / 多方向并行**
- 信息量超出单 context window
- 涉及大量复杂工具

**不适合**：
- 编码任务（**真正可并行的子任务少**，依赖多）
- 所有 agent 必须共享同一 context 的任务
- agent 之间需要实时协调和委派的任务（**LLM 当前还不擅长**）

> **关键反直觉**：作者明确说**当前编码任务大多不适合 multi-agent**——一个流行的反例。

---

## 二、架构：Orchestrator-Worker

```
            User Query
                ↓
        ┌────────────┐
        │  Lead Agent │  ← 分析 / 制定策略 / 把计划存到 memory
        └────────────┘
              ↓
       (spawn 并行 subagents)
              ↓
       ┌────┬────┬────┐
       │ S₁ │ S₂ │ S₃ │  ← 各自独立 context，并行搜索
       └────┴────┴────┘
              ↓ (返回 findings)
       ┌────────────┐
       │  Lead Agent │  ← 综合 / 决定是否继续
       └────────────┘
              ↓ (找够了)
       ┌────────────┐
       │ CitationAgent │  ← 处理引用、对齐 source
       └────────────┘
              ↓
            User
```

要点：
- **Plan 必须存到 memory**——context 超过 200k tokens 会被截断，**计划得活下来**
- Subagents **充当智能过滤器**：迭代用搜索工具采集，最后返回压缩后的列表
- Subagents 数量**动态决定**——不是预先固定
- **CitationAgent** 是单独的 agent——专门做引用对齐，避免污染 lead 的 context

> 和传统 RAG 的区别：RAG 是**静态检索**——挑最相似 chunks 拼成 context；这里是**动态多步搜索**——根据中间发现持续调整。

---

## 三、Token 经济学（最重要的一节）

| 比例 | 数值 |
|---|---|
| Token 用量解释 BrowseComp 性能方差 | **80%** |
| Token + tool calls + model 一起 | **95%** |
| Multi-agent 系统 vs 普通 chat 的 token 用量 | **~15 倍** |
| Agent vs chat | **~4 倍** |
| 升级 Sonnet 3.7 → Sonnet 4 | 收益**大于**翻倍 token 预算 |

**结论**：
- 模型升级是 **token 效率的乘数**——好模型能用更少 token 干更多事
- Multi-agent 架构的**根本作用是给任务"分配更多 token 容量"**——通过把工作分到多个 context window
- 经济可行性：**任务价值必须能 cover 增加的 token 成本**

---

## 四、Prompt Engineering：作者总结的 8 条原则

### 1. Think like your agents
- 跑模拟（用真实 prompt + 工具）观察 agent 一步步的行为
- 失败模式（如：已经搜够了还在继续 / 查询过分冗长 / 选错工具）会**立刻可见**
- "Effective prompting relies on developing an accurate mental model of the agent."

### 2. Teach the orchestrator how to delegate
- Lead agent 给 subagent 的任务必须包含：**objective / output format / 工具与来源指引 / 任务边界**
- 反例：lead 给"research the semiconductor shortage" 这种简短指令——subagents 互相重复（一个查 2021 汽车芯片危机，另两个都查 2025 供应链）
- 没有清晰任务描述 → 重复劳动 / 漏洞 / 找不到信息

### 3. Scale effort to query complexity
直接把规模规则**写进 prompt**：

| 任务类型 | 配置 |
|---|---|
| 简单事实查询 | 1 agent，3-10 tool calls |
| 直接对比 | 2-4 subagents，每个 10-15 calls |
| 复杂研究 | 10+ subagents，明确分工 |

→ 防止"对简单查询过度投资"——早期常见失败模式。

### 4. Tool design and selection are critical
- "Agent-tool interfaces are as critical as human-computer interfaces"——和 [Building Effective Agents](building-effective-agents.md) 的 ACI 概念同源
- 给 agent 显式启发式：**先看所有可用工具 / 工具与意图匹配 / 优先专用工具**
- MCP server 引入"未见过的工具，描述质量参差"的新问题——**坏的 tool 描述能把 agent 带向完全错误的路径**

### 5. Let agents improve themselves
- Claude 4 模型本身就是优秀的 prompt engineer
- 给它一个 prompt 和一种失败模式，它能**诊断原因并提出改进**
- 实例：**tool-testing agent**——给它一个有 bug 的 MCP tool，它反复用、改写描述，直到避开错误。结果：**未来 agent 用新描述完成时间下降 40%**

### 6. Start wide, then narrow down
- 仿照专家研究员：**先看全景，再钻细节**
- Agent 默认会用过长过具体的 query → 返回结果稀少
- 解法：prompt 引导 agent **先短查询 + 评估 + 渐进收窄**

### 7. Guide the thinking process
- Extended thinking mode = **可控的 scratchpad**
- Lead agent 用 thinking 来：**评估工具适配 / 决定 query 复杂度和 subagent 数量 / 定义每个 subagent 的角色**
- Subagents 也 plan，**在 tool 结果后用 interleaved thinking** 评估质量、识别空白、改下一个 query

### 8. Parallel tool calling transforms speed and performance
- 早期 agent 串行搜索——慢得惊人
- 引入两层并行：
  - **Lead 一次起 3-5 个 subagents 并行**（不是串行）
  - **Subagent 内一次调 3+ 工具并行**
- 效果：**复杂 query 研究时间下降高达 90%**——分钟级而不是小时级

---

## 五、评估的特殊挑战

Multi-agent 评估的核心问题：
- **同一个起点，agent 可能走完全不同的合理路径**
- 一个搜 3 个 source，另一个搜 10 个，可能都对
- **不能像传统评测那样"检查是不是按预期步骤走的"**
- 必须**评结果 + 评过程是否合理**——但不能要求"按规定步骤"

### 实操建议

- **从小样本开始**——20 个 query 在早期就够看出大变化（一次 prompt 改动 30% → 80%）
- **LLM-as-judge 在大规模时是必需的**——研究输出是 free-form 文本，没有 single correct answer
- **Rubric 至少包含**：factual accuracy / citation accuracy / completeness / source quality
- 一个 LLM judge 可以**在每次 commit 上评几百题**

> 注：和 [demystifying-evals-for-ai-agents.md](demystifying-evals-for-ai-agents.md) 的方法论高度一致——这是 Anthropic 的"统一立场"。

---

## 六、可靠性挑战（生产化的真问题）

Multi-agent 引入了一组单 agent 没有的工程问题：

- **状态持久化**：agent 跑很久，**任何一步崩了得能恢复**——单点故障会让所有进度灰飞烟灭
- **错误传播**：一个 subagent 的错会影响 lead 的综合
- **观测性**：需要看见每个 subagent 的 transcript，对 debug 至关重要
- **协调通信开销**：agent 之间不共享 memory（只通过 lead），这是设计约束
- **成本控制**：**烧 token 极快**，需要 budget 限制
- **rate limit / retry**：subagent 并行调用 → 容易撞 rate limit

---

## 七、和本仓库现有结论的对照

| 本文论点 | 本仓库已有 |
|---|---|
| Orchestrator-Worker 模式 | [../agents/multi-agent-coordination.md](../agents/multi-agent-coordination.md) ✓（"5 种协商机制 + Anthropic 多 Agent 参考"） |
| Subagent 隔离 + 独立 context | [../agents/subagent-patterns.md](../agents/subagent-patterns.md) ✓ |
| Multi-agent 不适合 coding | 待加：[../agents/long-task-agents.md](../agents/long-task-agents.md) 应明确 |
| Token 是性能主要驱动 | 待加：[../production/cost-and-latency.md](../production/cost-and-latency.md) 应加这条数据 |
| Tool 描述质量 + tool-testing agent | [../tools-protocols/tool-development.md](../tools-protocols/tool-development.md) ✓ |
| Lead 把计划存 memory 防截断 | [../agents/memory-systems.md](../agents/memory-systems.md) ✓ 可补这个反例 |
| 并行 tool calling | [../production/latency-optimization.md](../production/latency-optimization.md) ✓（"7 个延迟优化杠杆"） |
| Extended thinking 当 scratchpad | [../prompting/cot-family.md](../prompting/cot-family.md) ✓ |

---

## 八、反对意见与待验证

- **90.2% 提升是内部 eval**——可能 reward hacking 自己的评测集；外部独立验证不足
- **15× token 是不是真的值**？对中等价值任务（如客服），multi-agent 经济上不划算
- **"Coding 不适合 multi-agent"** 这条结论已被 OpenHands 等部分挑战——专业 coding multi-agent 框架（如 ChatDev、MetaGPT）有自己的卖点
- **CitationAgent 单独存在**：好处是关注点分离，坏处是又多一次 LLM call——是不是可以让 lead 自己做？
- **"模型升级 > 翻倍 token 预算"**：对前沿模型可能成立，但**模型升级也涨钱**，未给完整经济对比
- **"agent improve themselves"** 在 prompt 改写场景成立，但延伸到**架构自改进**目前仍是研究方向

---

## 九、行动项

- [ ] 在 [../agents/multi-agent-coordination.md](../agents/multi-agent-coordination.md) 引言加 Anthropic 这套 token 经济学数据（80% 方差 / 15× token）
- [ ] 在 [../agents/subagent-patterns.md](../agents/subagent-patterns.md) 加一节 **"Anthropic Research 系统的 4 个 subagent pattern"**：Lead / Parallel Search Subagent / CitationAgent / Memory store
- [ ] 在 [../agents/long-task-agents.md](../agents/long-task-agents.md) 加 **"何时不该上 multi-agent"** 一节，引用本文的 coding 反例
- [ ] 在 [../tools-protocols/tool-development.md](../tools-protocols/tool-development.md) 加 **"Tool-testing agent: 让 agent 改写工具描述"** 案例
- [ ] 在 [../production/cost-and-latency.md](../production/cost-and-latency.md) 加一行：**Multi-agent ≈ 15× chat token；Agent ≈ 4× chat token**
- [ ] 在 [../production/latency-optimization.md](../production/latency-optimization.md) 加 **"Lead 并行起 subagent + Subagent 内并行 tool"** 双层并行模式

---

## 十、关键引用

- "**Token usage by itself explains 80% of the variance** in BrowseComp performance."
- "**Multi-agent systems use about 15× more tokens than chats.**"
- "**Most coding tasks involve fewer truly parallelizable tasks than research, and LLM agents are not yet great at coordinating and delegating to other agents in real time.**"
- "**Effective prompting relies on developing an accurate mental model of the agent.**"
- "**Tool descriptions** are like **human-computer interfaces**: bad ones send agents down completely wrong paths."
- "**Start wide, then narrow down**——and **start small with eval**, not 100s of test cases."

> 本文核心：
> **Multi-agent 不神秘——它是一种"让 token 花到对的地方"的架构选择，而不是范式飞跃。**
