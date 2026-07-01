# Skill 和 Tool 的本质区别

> 这两个概念经常被混用，但它们解决的是**完全不同**的问题。本文用最短篇幅讲清两者的本质差异、各自的工程心智模型、以及在产品设计中怎么协同使用。
>
> 配套：[skills-system-design.md](skills-system-design.md)（Skills 实现）、[../tools-protocols/tool-development.md](../tools-protocols/tool-development.md)（Tool 开发）。

---

## 一、一句话区分

> **Tool 是"我能做什么"，Skill 是"我应该怎么做这一类问题"**。

- **Tool**：可执行函数（read_file / send_email / run_sql）
- **Skill**：方法论文档（debug-protocol / research-methodology / code-review-checklist）

---

## 二、七个维度的对比

| 维度 | Tool | Skill |
|---|---|---|
| **本质** | 可执行函数 | 方法论文档 |
| **执行** | LLM 调用即跑 | LLM 加载即读 |
| **粒度** | 原子操作 | 多步流程 |
| **接口** | input/output schema | trigger 描述 + body |
| **状态** | 无状态 | 无状态（但描述工作流） |
| **复用** | 跨 Agent 复用 | 通常项目内复用 |
| **类比** | 函数库（lodash） | 设计模式（GoF） |

---

## 三、一个例子让你立刻分清

任务："查一下昨天的注册用户数"

### Tool 视角

```
Agent 决定调用 run_sql 工具
→ run_sql("SELECT count(*) FROM users WHERE date='2026-06-01'")
→ 返回结果
→ Agent 自己组织答案
```

### Skill 视角（data-query skill）

```
Agent 加载 data-query.md skill body：
  "## Step 1: Identify the data source
   ## Step 2: Generate SQL with LIMIT
   ## Step 3: Execute via run_sql tool
   ## Step 4: Format result based on row count"

→ 按 protocol 走，调用的还是 run_sql 这个 Tool
```

**关键**：Skill **不是替代 Tool**，是**告诉 Agent 怎么用 Tool**。

---

## 四、为什么这个区分重要

### 重要 1：开发心智不同

| | Tool 开发 | Skill 开发 |
|---|---|---|
| 谁来做 | API 工程师 | 产品经理 / 业务专家 |
| 关心什么 | schema 设计 / 参数校验 / 错误处理 | 流程规约 / 最佳实践 / 边界条件 |
| 文件类型 | 代码（Python/TS） | Markdown |
| 测试 | 单元测试 | LLM 行为评测 |

很多团队把这两件事混在一起做，结果两边都做不好——**API 工程师写出 50 页方法论**，**产品经理改不了 Tool**。分开后效率显著提升。

### 重要 2：扩展边界不同

- **加 Tool = 给 Agent 新能力**（之前不能做 X，现在能了）
- **加 Skill = 给 Agent 新方法论**（之前能做 X 但不知道怎么做好，现在知道了）

```
没有 search_jira_tickets tool → Agent 永远不能查 Jira
有 tool 但没 jira-triage skill → Agent 知道怎么查，但不知道"应该按什么流程查、查到怎么处理"
```

业务方可以**自己写 Skill**（改 markdown），但不能自己加 Tool（要写代码）。

### 重要 3：上下文成本不同

```
Tool 注册：
  schema 始终在 system prompt → 每次对话都带 → 永久 token 成本
  
Skill 加载：
  description 始终在 → 短
  body 仅触发时加载 → 用完即弃 → 单次 token 成本
```

**100 个 skill 比 100 个 tool 更省 context**——Skill body 按需加载。

详见 [skills-system-design.md](skills-system-design.md) 第四节"动态召回 + Embedding 检索"。

### 重要 4：可缓存性不同

- Tool 调用结果可缓存（同 input → 同 output）
- Skill body 在 prompt 里（**prompt cache 友好**——同 skill 多次触发，cache 命中）

详见 [../production/latency-optimization.md](../production/latency-optimization.md)。

### 重要 5：评测方式不同

```
Tool 评测：
  ✅ 给定 input，是否返回正确 output？（unit test 即可）
  ❌ 不需要 LLM 介入评测
  
Skill 评测：
  ✅ Agent 在什么情况触发了这个 skill？（trigger 准确性）
  ✅ 加载后 Agent 是否按 protocol 走？（行为一致性）
  ❌ 必须 LLM-as-Judge 或人工
```

详见 [../evaluation/research-agent-evals.md](../evaluation/research-agent-evals.md)。

---

## 五、判断公式：Skill 还是 Tool？

```
要做的事是"一次原子操作"？
   ├─ 是 → Tool
   │     例：read_file / send_email / run_sql / fetch_url
   │
   └─ 否，是"多步骤的方法论"？
         ├─ 是 → Skill
         │     例：debug-protocol / research-methodology / code-review-checklist
         │
         └─ 都不是，是"复杂业务流程"？
               → 这其实是 Subgraph 或 Crew 该解决的
               → 详见 [subagent-patterns.md](subagent-patterns.md)
```

### 边界情况：什么是 Tool 不该做的

❌ 把多步流程包装成一个"宏 tool"
```python
@tool
def full_research_pipeline(topic: str) -> str:
    """A comprehensive research pipeline that does scoping, searching,
    verifying, synthesizing, and writing a report."""
    # 巨大无比的实现
```

**问题**：黑盒、不可观测、调试灾难、无法部分复用。

✅ 应该是 Skill 描述方法论，Skill 内部组合多个 Tool：
```yaml
# research-protocol skill 描述流程
# 内部组合 web_search / web_fetch / save_file 等 Tool
```

---

## 六、跟 MCP / Function Calling 的关系

| | Function Calling | MCP | Claude Code Skill |
|---|---|---|---|
| 角色 | LLM 调函数的协议 | 跨厂商工具协议 | 方法论加载机制 |
| 颗粒度 | Tool | Tool | Skill |
| 谁来注册 | 应用代码 | MCP server | SKILL.md |
| 跨工具复用 | 无 | ✅ | ❌（绑 Claude Code） |
| LLM 选择机制 | 看 schema | 看 schema | 看 description |

**实战**：
- Tool 用 MCP 实现（跨工具复用，详见 [../tools-protocols/mcp.md](../tools-protocols/mcp.md)）
- Skill 用 markdown 写（业务方能改）
- **两个机制并存最优**

---

## 七、协同设计：一个真实例子

假设你做一个"销售数据分析 Agent"。

### Tool 层（API 工程师做）

```python
@tool
def query_sales_data(
    region: str, 
    start_date: str, 
    end_date: str,
    metric: Literal["revenue", "orders", "users"],
) -> dict:
    """Query sales data warehouse."""
    # ... SQL 实现

@tool
def render_chart(
    data: list[dict],
    chart_type: Literal["line", "bar", "pie"],
) -> str:
    """Render chart, return URL."""
    # ... 渲染实现

@tool
def send_to_slack(channel: str, message: str) -> bool:
    """Post message to Slack."""
    # ...
```

每个 Tool 都是**原子、可测试、独立**的。

### Skill 层（业务方写）

`weekly-sales-report skill`：

```markdown
---
name: weekly-sales-report
description: Use when user asks for weekly sales summary or weekly business review.
---

# Weekly Sales Report Protocol

## Step 1: Determine scope
- 默认：上周（周一到周日）
- 默认 region：所有
- 用户指定的优先

## Step 2: Pull data (并行)
对 ["NA", "EU", "APAC"] 三个区域，并行调用：
- query_sales_data(region, start, end, "revenue")
- query_sales_data(region, start, end, "orders")

## Step 3: Identify highlights
- 同比增长 > 20% → 标记"📈 高增长"
- 环比下降 > 15% → 标记"⚠️ 下滑预警"
- 创历史新高 → 标记"🎉 新高"

## Step 4: Render visuals
- 整体趋势：line chart
- 区域对比：bar chart

## Step 5: Compose & send
按这个模板写 Slack 消息：
[模板...]
然后 send_to_slack(channel="#sales-weekly", message=...)
```

### 协同的好处

- **Tool 改了不影响 Skill**：query_sales_data 内部换数据源，Skill 不用改
- **Skill 改了不影响 Tool**：业务想加"季度报告 skill"，写一个新 .md 就行
- **同一套 Tool 服务多个 Skill**：weekly / monthly / quarterly 都用同一组 Tool

---

## 八、反模式

### 反模式 1：Skill 里硬编码具体 SQL

```markdown
# 反例
## Step 2:
SELECT revenue FROM sales WHERE region='NA' AND date >= '2026-06-01'
```

❌ 把 SQL 细节锁在 Skill 里 → SQL 应该是 Tool 实现细节

✅ 应该：
```markdown
## Step 2: Query sales using query_sales_data tool with parameters...
```

### 反模式 2：Tool description 里写方法论

```python
# 反例
@tool
def query_sales_data(...):
    """Query sales data. Step 1: ... Step 2: ... When you encounter 
    high growth regions, you should... For weekly reports, prefer..."""
```

❌ 把方法论塞在 tool description → 永久占 context

✅ Tool 只描述"做什么 + 参数"。方法论放 Skill。

### 反模式 3：让一个东西既是 Skill 又是 Tool

❌ "我把方法论包装成一个 prompt 模板，让 LLM 当 tool 调用"

→ 这就是 Skill。**Skill 加载机制是 prompt cache 友好的，Tool 调用是带回调开销的**。在 Tool 这层做错地方了。

---

## 九、总结：决策心法

```
新需求来了，问自己三个问题：

1. 这是"一个原子操作"吗？
   → 是：Tool
   → 否，下一题

2. 这是"做某类问题的方法论"吗？
   → 是：Skill
   → 否，下一题

3. 这是"完整的业务流程"吗？
   → 是：Subgraph / Crew / 主 Agent 流程
   → 否：你需求没想清楚，回去重想
```

---

## 十、扩展阅读

- [skills-system-design.md](skills-system-design.md) —— Skill 系统的实现细节
- [../tools-protocols/tool-development.md](../tools-protocols/tool-development.md) —— Tool 开发的工程视角
- [../tools-protocols/mcp.md](../tools-protocols/mcp.md) —— MCP 协议（Tool 的跨工具复用）
- [../tools-protocols/function-calling.md](../tools-protocols/function-calling.md) —— Function Calling 基础
- [subagent-patterns.md](subagent-patterns.md) —— 当任务是"完整流程"而非 Skill 时
