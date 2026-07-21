# Skills 系统设计：从最简版到动态召回

> Skills 是 Claude Code 的核心扩展机制。本文讲清它的本质、最小可用版的实现、规模化后的"动态召回"方案、把它接到 LangGraph 的具体写法、以及对比 Cline 的 MCP 自定义工具方式。
>
> 配套：[long-task-agents.md](long-task-agents.md)、[subagent-patterns.md](subagent-patterns.md)。

---

## 一、Skills 是什么（去神秘化）

**Skills = 描述向量化的、按需加载的长指令**。

```
本质上就是一个文件夹里的 SKILL.md：
  ├── frontmatter: name + description（短）
  └── body: 详细指令 + 工具调用示例（长）

机制：
  - description 一直在 Agent context（占 ~50 token）
  - body 仅在 description 被触发时塞进 context（占几千 token）
```

不神秘。你完全可以在自己的 Agent 里复刻。

---

## 二、最小可用版的 Skill 系统

### 文件布局

```
my-agent/
├── skills/
│   ├── data-query/
│   │   └── SKILL.md
│   ├── chart-render/
│   │   └── SKILL.md
│   └── pdf-export/
│       └── SKILL.md
└── agent.py
```

### SKILL.md 文件格式

```markdown
---
name: data-query
description: |
  Use when user asks about querying database, running SQL, or
  retrieving data from data warehouse. Covers SELECT statements,
  joins, aggregations. Do NOT use for INSERT/UPDATE/DELETE.
trigger_keywords: [查询, SQL, 数据查, select]
---

# Data Query Skill

When invoked, follow this protocol:

## Step 1: Identify the data source
Available sources:
- `prod_db` (Postgres, read-only)
- `dw` (Hive via Kyuubi)

## Step 2: Generate SQL
Constraints:
- Always add LIMIT (default 100)
- Never use SELECT *

## Step 3: Execute via tool
Call `run_sql(source, query)` tool.

## Step 4: Format result
- < 10 rows → markdown table
- ≥ 10 rows → summary + first 10 rows
- Numerical → consider chart

## Examples

Q: "查一下昨天的注册用户数"
→ run_sql("dw", "SELECT count(*) FROM users WHERE register_date = '2026-05-31'")

Q: "看看用户表前 10 条"
→ run_sql("prod_db", "SELECT * FROM users LIMIT 10")
```

### 加载机制：分两层 context

```python
class SkillManager:
    def __init__(self, skills_dir: str):
        self.skills = self._load_all(skills_dir)

    def _load_all(self, skills_dir):
        skills = {}
        for skill_dir in Path(skills_dir).iterdir():
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue
            content = skill_md.read_text()
            frontmatter, body = self._parse(content)
            skills[frontmatter["name"]] = {
                "description": frontmatter["description"],
                "body": body,
                "keywords": frontmatter.get("trigger_keywords", []),
            }
        return skills

    def get_index_prompt(self) -> str:
        """这部分一直在 system prompt — 短描述"""
        lines = ["## Available Skills\n"]
        for name, skill in self.skills.items():
            lines.append(f"- **{name}**: {skill['description'].strip()}")
        lines.append(
            "\nWhen a skill matches the task, invoke `load_skill(name)` "
            "first to get full instructions."
        )
        return "\n".join(lines)

    def load(self, name: str) -> str:
        """这部分按需加载 — 完整指令"""
        return self.skills[name]["body"]
```

### 把 load_skill 注册成工具

```python
@function_tool
def load_skill(name: str) -> str:
    """Load full instructions for a named skill. Call this BEFORE
    executing the actual task when a skill matches."""
    return skill_manager.load(name)

agent = Agent(
    name="MyAgent",
    instructions=f"""You are a helpful agent.

{skill_manager.get_index_prompt()}

Workflow:
1. Read the user's request
2. If a skill matches, call load_skill(name) FIRST
3. Follow the loaded skill's protocol
4. If no skill matches, use your general knowledge
""",
    tools=[load_skill, run_sql, render_chart, ...],
)
```

---

## 三、最简版的三个关键设计点

### 设计点 1：description 的写法决定 90% 的效果

**反例**：
```yaml
description: A skill for data queries.
```
→ Agent 永远不知道什么时候触发。

**正例**：
```yaml
description: |
  Use when user asks about querying database, running SQL, or retrieving 
  data. Covers SELECT statements, joins, aggregations. 
  Do NOT use for INSERT/UPDATE/DELETE (use data-mutation skill instead).
```

要素：
- **能力**：能做什么
- **触发**：什么时候用
- **边界**：什么时候**不**用

### 设计点 2：body 必须自包含

Agent 加载 skill body 时，可能已经过了好几轮对话。所以 body 不能依赖"刚才说的"。

**反例**：
```markdown
继续上面的查询，加 ORDER BY...
```

**正例**：
```markdown
When invoked, you will receive:
- A natural language data question
- Optional time range hint

Output format:
- ...
```

### 设计点 3：渐进式触发

更高级的实现：**两阶段加载**。

```
阶段 1（context 内）：只放 description
阶段 2（按需）：用户提问 → 用 keyword + embedding 召回 top-3 skill → 把这 3 个的 description 详细版加载
阶段 3（执行）：选定后 load body
```

这是 Claude Code 实际在做的事——它的 skill 列表用 description 索引，**当 skill 数量 > 30 时就不再全部塞 system prompt**，而是动态召回。

---

## 四、动态召回 + Embedding 检索（规模化方案）

### 1. 为什么需要动态召回

最简版把所有 skill 的 description 都塞到 system prompt：

- 5 个 skill：~250 token，无所谓
- 30 个 skill：~1500 token，开始疼
- 100+ 个 skill（实际生产规模）：**~5000 token 永远在烧**，且 description 越多模型选择越乱

### 2. 三层架构

```
┌─────────────────────────────────────────────────────┐
│  Layer 1: Always-in-context（轻）                   │
│  - 一个 list_relevant_skills(query) 工具说明        │
│  - 几个高频 skill 的极短摘要                         │
└─────────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────┐
│  Layer 2: 动态召回（中）                            │
│  - Agent 调 list_relevant_skills(query)             │
│  - 返回 top-K 候选 skill 的 description             │
└─────────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────┐
│  Layer 3: 完整加载（重）                            │
│  - Agent 选定后调 load_skill(name)                  │
│  - 拿到完整 body                                    │
└─────────────────────────────────────────────────────┘
```

### 3. 实现：从 Skill 文件到向量索引

#### Skill 元数据扩展

```markdown
---
name: data-query
description: |
  Use when user asks about querying database, running SQL...
embedding_text: |
  database query SQL select join aggregation SELECT data warehouse
  postgres hive 查询 数据 SQL 报表 聚合 关联
trigger_phrases:
  - "查一下"
  - "跑个 SQL"
  - "数据查询"
  - "看看表"
---
...
```

`embedding_text` 是**专门给 embedding 用的字段**——比 description 更密集、更多关键词、中英混合。

`trigger_phrases` 是**精确匹配 fallback**——embedding 漏召回时兜底。

#### 索引构建

```python
import numpy as np
from openai import OpenAI

class SkillIndex:
    def __init__(self, skills: dict, embedder):
        self.skills = skills
        self.embedder = embedder
        self.embeddings = {}
        self._build()
    
    def _build(self):
        """启动时一次性 embed 所有 skill"""
        for name, skill in self.skills.items():
            text = self._embed_text(skill)
            self.embeddings[name] = self.embedder.embed(text)
    
    def _embed_text(self, skill: dict) -> str:
        """合成用于 embedding 的文本"""
        parts = [
            skill["description"],
            skill.get("embedding_text", ""),
            " ".join(skill.get("trigger_phrases", [])),
            # 加上 skill body 的前 500 字（提升语义召回）
            skill["body"][:500],
        ]
        return "\n".join(parts)
    
    def retrieve(self, query: str, k: int = 5) -> list:
        """两阶段召回"""
        # 阶段 1：精确触发词
        exact_hits = self._exact_match(query)
        
        # 阶段 2：语义召回
        semantic_hits = self._semantic_match(query, k)
        
        # 合并去重，精确匹配优先
        seen = set()
        result = []
        for name in exact_hits + semantic_hits:
            if name not in seen:
                seen.add(name)
                result.append(name)
        return result[:k]
    
    def _exact_match(self, query: str) -> list:
        hits = []
        q_lower = query.lower()
        for name, skill in self.skills.items():
            phrases = skill.get("trigger_phrases", [])
            if any(p.lower() in q_lower for p in phrases):
                hits.append(name)
        return hits
    
    def _semantic_match(self, query: str, k: int) -> list:
        q_emb = self.embedder.embed(query)
        scores = {
            name: self._cosine(q_emb, emb)
            for name, emb in self.embeddings.items()
        }
        return sorted(scores, key=scores.get, reverse=True)[:k]
    
    @staticmethod
    def _cosine(a, b):
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
```

#### 暴露成工具

```python
@function_tool
def list_relevant_skills(task_description: str) -> str:
    """Find skills that might help with the current task.
    Call this FIRST when the task seems to match a specialized capability.
    
    Args:
        task_description: Natural language description of what you need to do
    
    Returns:
        A list of candidate skills with their descriptions.
        Pick one and call load_skill(name) to get full instructions.
    """
    candidates = skill_index.retrieve(task_description, k=5)
    if not candidates:
        return "No matching skills found. Use general capabilities."
    
    lines = ["Candidate skills (most relevant first):\n"]
    for name in candidates:
        skill = skill_index.skills[name]
        lines.append(f"- **{name}**: {skill['description'].strip()}")
    lines.append(
        "\nIf one matches your task, call load_skill(name) for full instructions."
    )
    return "\n".join(lines)


@function_tool
def load_skill(name: str) -> str:
    """Load full instructions for a specific skill."""
    skill = skill_index.skills.get(name)
    if not skill:
        return f"Skill '{name}' not found. Try list_relevant_skills first."
    return skill["body"]
```

### 4. 三个生产细节

#### 细节 1：Embedding 模型选择

| 选项 | 速度 | 质量 | 成本 |
|---|---|---|---|
| **OpenAI text-embedding-3-small** | 快 | 中 | $0.02/M tokens |
| **OpenAI text-embedding-3-large** | 中 | **高** | $0.13/M tokens |
| **BGE-M3**（本地） | 快 | 中-高 | 免费 |
| **Voyage-3** | 中 | 高 | $0.06/M tokens |

**实战**：100 个 skill 一次 embed 不到 1 万 token，用 large 也就几分钱。**初次构建用最好的，后续增量构建省钱**。

#### 细节 2：Embedding 缓存

```python
import hashlib, pickle
from pathlib import Path

class CachedSkillIndex(SkillIndex):
    def __init__(self, skills, embedder, cache_dir: str):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        super().__init__(skills, embedder)
    
    def _build(self):
        for name, skill in self.skills.items():
            text = self._embed_text(skill)
            text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
            cache_file = self.cache_dir / f"{name}_{text_hash}.pkl"
            
            if cache_file.exists():
                self.embeddings[name] = pickle.loads(cache_file.read_bytes())
            else:
                # 清理同名旧 hash
                for old in self.cache_dir.glob(f"{name}_*.pkl"):
                    old.unlink()
                emb = self.embedder.embed(text)
                cache_file.write_bytes(pickle.dumps(emb))
                self.embeddings[name] = emb
```

**关键**：用 text 的 hash 当 cache key——skill 文件改了 embedding 自动失效。

#### 细节 3：召回质量评测

不评测就是玄学。建一个简单评测集：

```python
EVAL_SET = [
    {"query": "查一下昨天的注册用户数", "expected": "data-query"},
    {"query": "把这个 PDF 转成 markdown", "expected": "pdf-to-md"},
    {"query": "做个流程图展示这个架构", "expected": "diagram-render"},
    # ... 30-50 条
]

def eval_recall(index, eval_set, k=3):
    hits = 0
    for case in eval_set:
        candidates = index.retrieve(case["query"], k=k)
        if case["expected"] in candidates:
            hits += 1
    return hits / len(eval_set)
```

每次改 skill 描述、加新 skill，**先跑评测看 recall 有没有掉**。

### 5. 进阶：分层召回（解决 100+ skill 的真正方案）

当 skill 数 > 100，单纯 top-5 召回也不够。**分类目录 + 类内召回**：

```python
SKILL_CATEGORIES = {
    "data": ["data-query", "data-export", "data-clean"],
    "code": ["code-review", "refactor", "test-gen"],
    "docs": ["pdf-to-md", "markdown-to-pdf", "doc-summary"],
    "web": ["web-scrape", "browser-test"],
}
```

召回流程：
1. 先用 query 选 category（一次小 embedding 比较）
2. 在选中的 category 内做 top-K
3. 跨 category 兜底召回 top-2

这样**单次召回的候选池从 100+ 降到 10 量级，准确率显著提升**。

---

## 五、把 Skills 机制接到 LangGraph

### 1. 接入点设计

LangGraph 是状态机，Skills 系统要无缝接入有几种方案：

```
方案 A：Skills 当工具节点（最直接）
  → skill 加载/调用作为 graph 里的 tool node

方案 B：Skills 当独立子图（最灵活）
  → 每个 skill 是一个 subgraph，主图按需 invoke

方案 C：Skills 当系统提示注入（最轻）
  → state 里维护 active_skills，每个 LLM 节点动态拼 prompt
```

实战推荐 **A + C 组合**。

### 2. 完整实现骨架

#### State 设计

```python
from typing import TypedDict, Annotated, Optional
from operator import add
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    
    # Skills 相关
    active_skill: Optional[str]              # 当前激活的 skill name
    skill_body: Optional[str]                # 当前 skill 的完整 body
    skill_candidates: Annotated[list, add]   # 召回历史（debug 用）
    
    # 任务相关
    task: str
    final_answer: Optional[str]
```

#### 节点设计

```python
from langgraph.graph import StateGraph, END

def skill_router(state: AgentState) -> AgentState:
    """根据当前 task 召回 skill 候选"""
    task = state["task"]
    candidates = skill_index.retrieve(task, k=5)
    
    # 让 LLM 决定要不要用 skill、用哪个
    prompt = f"""Task: {task}

Candidate skills:
{format_candidates(candidates)}

Output JSON: {{"use_skill": true/false, "skill_name": "..." or null, "reason": "..."}}
"""
    decision = llm.invoke(prompt, response_format={"type": "json_object"})
    decision = json.loads(decision)
    
    if decision["use_skill"]:
        skill_body = skill_index.skills[decision["skill_name"]]["body"]
        return {
            "active_skill": decision["skill_name"],
            "skill_body": skill_body,
            "skill_candidates": [{"task": task, "chosen": decision["skill_name"]}],
        }
    return {
        "active_skill": None,
        "skill_body": None,
        "skill_candidates": [{"task": task, "chosen": None}],
    }


def execute_node(state: AgentState) -> AgentState:
    """主执行节点。如果有 active skill，把它的 body 注入 system prompt"""
    base_system = "You are a helpful agent."
    
    if state.get("skill_body"):
        system = f"{base_system}\n\n## Active Skill: {state['active_skill']}\n\n{state['skill_body']}"
    else:
        system = base_system
    
    messages = [{"role": "system", "content": system}] + state["messages"]
    response = llm_with_tools.invoke(messages)
    
    return {"messages": [response]}


def should_continue(state: AgentState) -> str:
    """是否继续 tool 循环"""
    last_msg = state["messages"][-1]
    if last_msg.tool_calls:
        return "tools"
    return END


# 组图
g = StateGraph(AgentState)
g.add_node("skill_router", skill_router)
g.add_node("execute", execute_node)
g.add_node("tools", ToolNode(tools))

g.set_entry_point("skill_router")
g.add_edge("skill_router", "execute")
g.add_conditional_edges("execute", should_continue, {
    "tools": "tools",
    END: END,
})
g.add_edge("tools", "execute")

app = g.compile(checkpointer=postgres_saver)
```

### 3. 关键设计点

#### 设计点 1：skill_router 是显式节点

不是把召回逻辑藏在 LLM 决策里——**显式节点 = 可观测**。LangSmith trace 里能直接看到"哪个 skill 被召回、被选中"。

#### 设计点 2：skill_body 进 state，而不是动态拼

```python
# 反例
def execute_node(state):
    skill = skill_index.get(determine_skill(state))  # ← 每次重新算
    system = base + skill.body

# 正例
def execute_node(state):
    if state.get("skill_body"):                       # ← 用 state 里已有的
        system = base + state["skill_body"]
```

**为什么**：state 持久化到 checkpoint。任务跑到一半中断重启，**skill 不需要重新选**——直接从 state 恢复。

#### 设计点 3：skill 切换的处理

任务跑到一半，子任务可能需要切到不同 skill：

```python
def execute_node(state):
    # ... LLM 输出
    
    # 检查 LLM 是否要求切 skill
    if response.tool_calls:
        for call in response.tool_calls:
            if call["name"] == "switch_skill":
                new_skill = call["args"]["name"]
                return {
                    "messages": [response],
                    "active_skill": new_skill,
                    "skill_body": skill_index.skills[new_skill]["body"],
                }
    return {"messages": [response]}
```

注册 `switch_skill` 工具让 Agent 主动切换。

### 4. 多 Skill 叠加？慎用

诱人的想法：**同时激活多个 skill**。

```python
# 看起来很美好
state["active_skills"] = ["data-query", "chart-render"]
system = base + skill1.body + skill2.body
```

**实战为什么有问题**：
- skill body 通常 1-3K token，叠加几个就吃掉 10K context
- skill 之间的指令可能冲突（"输出 markdown" vs "输出 JSON"）
- 模型选不对 protocol

**正确做法**：**串行切换**。先用 data-query 拿数，再切到 chart-render 画图。每次只有一个 active skill。

### 5. 跟 Subgraph 结合：复杂 skill 用 subgraph

简单 skill 用 prompt 就够。**复杂 skill 内部本身是个流程**——用 subgraph 实现：

```python
# data-analysis skill 内部是多步流程
data_analysis_sub = StateGraph(AnalysisState)
data_analysis_sub.add_node("understand", understand_node)
data_analysis_sub.add_node("query", query_node)
data_analysis_sub.add_node("analyze", analyze_node)
data_analysis_sub.add_node("visualize", visualize_node)
data_analysis_subgraph = data_analysis_sub.compile()

# 注册成"重型 skill"
HEAVY_SKILLS = {
    "data-analysis": data_analysis_subgraph,
    "code-review": code_review_subgraph,
    "research": research_subgraph,
}

def execute_node(state):
    if state.get("active_skill") in HEAVY_SKILLS:
        # 委派给 subgraph
        sub_result = HEAVY_SKILLS[state["active_skill"]].invoke({...})
        return {"messages": [...], "final_answer": sub_result["answer"]}
    # 否则正常 LLM 循环
```

**轻 skill = prompt 注入，重 skill = subgraph**。这个分层非常 work。

---

## 六、Cline 的 MCP 怎么自定义工具

### 1. Cline + MCP 的关系

Cline 不像 Claude Code 有内置 Skills 机制。**Cline 把"扩展性"完全交给 MCP**。

```
Claude Code:  Tools + Skills + Subagents + Hooks  （多层扩展）
Cline:        Tools + MCP servers                  （单层扩展，全靠 MCP）
```

意味着：**在 Cline 里加自定义工具 = 写一个 MCP server**。

### 2. MCP server 的最小结构

```python
# my_mcp_server.py
import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

server = Server("my-custom-tools")

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="query_company_data",
            description="Query the internal company data warehouse. Use for sales, user metrics, finance data.",
            inputSchema={
                "type": "object",
                "properties": {
                    "table": {"type": "string", "description": "Table name"},
                    "date_range": {"type": "string", "description": "e.g., '2026-05-01 to 2026-05-31'"},
                    "metric": {"type": "string"},
                },
                "required": ["table", "metric"],
            },
        ),
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "query_company_data":
        result = await fetch_from_warehouse(
            table=arguments["table"],
            date_range=arguments.get("date_range"),
            metric=arguments["metric"],
        )
        return [TextContent(type="text", text=str(result))]
    raise ValueError(f"Unknown tool: {name}")

async def main():
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
```

### 3. 在 Cline 里注册

打开 Cline 设置 → MCP Servers → 编辑 `cline_mcp_settings.json`：

```json
{
  "mcpServers": {
    "company-data": {
      "command": "python",
      "args": ["/path/to/my_mcp_server.py"],
      "env": {
        "DB_PASSWORD": "${env:DB_PASSWORD}"
      },
      "disabled": false,
      "alwaysAllow": ["query_company_data"]
    }
  }
}
```

`alwaysAllow` 列表里的工具调用**不会弹审批框**——这是 Cline 的可控性体现：**默认每个工具都要 approve，列入白名单的才自动跑**。

### 4. 三种典型自定义工具

#### 工具 1：Read-Only 数据查询（推荐 alwaysAllow）

```python
Tool(
    name="search_jira_tickets",
    description="Search internal Jira. Use to find related issues.",
    ...
)
```

**为什么 alwaysAllow**：只读、可重复、对系统无害。

#### 工具 2：Write 类操作（不要 alwaysAllow）

```python
Tool(
    name="create_pr_comment",
    description="Post a comment on a GitHub PR.",
    ...
)
```

**为什么不 alwaysAllow**：每次都要用户 review 内容才发出去。

#### 工具 3：执行任意命令（强烈不要 alwaysAllow）

```python
Tool(
    name="run_kubectl",
    description="Run a kubectl command.",
    ...
)
```

**为什么**：kubectl delete 可能毁掉生产。

### 5. 比 Claude Code 麻烦在哪

| | Claude Code | Cline |
|---|---|---|
| 自定义工具 | 写 .md 文件（Skill） | 写 Python/TS MCP server |
| 自定义子 Agent | 写 .md 文件（subagent） | ❌ 没有这层 |
| 自定义 hook | settings.json 一行 | ❌ 没有 |
| 工具发现 | description 自动可见 | 必须配置 server |
| 上手 | 5 分钟 | 30 分钟（写 server + 配置） |

**MCP 的优势**：跨工具复用——同一个 MCP server 能给 Claude Code、Cline、Cursor 用。

**MCP 的劣势**：每个工具都要写完整 server，重型，不如 Skill 轻。

---

## 七、复刻 Claude Code 的"插件目录"

进阶：让 skills 可以从外部仓库 install。

```
~/.my-agent/skills/         ← 用户全局
./my-agent/skills/          ← 项目级
./node_modules/some-pkg/skills/  ← 第三方包

加载顺序：项目 > 用户 > 全局 > 第三方
```

实现就是 `_load_all()` 多扫几个目录。

---

## 八、扩展阅读

- [long-task-agents.md](long-task-agents.md) —— Skills 在 Claude Code 长任务里的作用
- [subagent-patterns.md](subagent-patterns.md) —— Skill 与 subagent 的搭配
- [research-agent-architecture.md](research-agent-architecture.md) —— 在研究 Agent 里设计 skill
- [../tools-protocols/mcp.md](../tools-protocols/mcp.md) —— MCP 协议详解
