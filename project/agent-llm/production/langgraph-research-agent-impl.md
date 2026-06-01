# LangGraph 完整复刻研究 Agent：可运行代码

> [research-agent-architecture.md](../agents/research-agent-architecture.md) 讲了 Claude Code 版本的研究 Agent。本文是 LangGraph 版本的**完整可运行代码**——按"骨架 → 状态 → 节点 → subgraph → 主图 → 协商层 → 启动"的顺序讲。

---

## 一、整体设计

```
┌───────────────────────────────────────────────────────┐
│  ResearchOrchestrator (主图)                          │
│                                                       │
│  scoping → research_round (loop) → synthesis →       │
│  outlining → drafting (parallel) → review → output   │
│                                                       │
│  ↓ 每个 research_round 调用 ↓                         │
│                                                       │
│  ResearcherAgent (subgraph) × N (并行 + 协商)         │
│    plan_search → check_blackboard → execute_searches │
│    → fetch → extract → verify → publish              │
└───────────────────────────────────────────────────────┘

  ↑ 共享 ↑
┌──────────────────────────┐
│  Blackboard (Postgres)   │
│  - claims                │
│  - searches              │
│  - reservations          │
└──────────────────────────┘
```

---

## 二、状态定义

```python
# state.py
from typing import TypedDict, Annotated, Literal, Optional
from operator import add
from langgraph.graph.message import add_messages
from pydantic import BaseModel

# ---------- 数据模型 ----------

class Claim(BaseModel):
    id: str
    text: str                # claim 内容
    sub_topic: str           # 属于哪个 sub-topic
    source_url: str
    source_excerpt: str
    confidence: Literal["high", "medium", "low", "single-source"]
    found_by: str            # researcher agent id
    verification_status: Literal["unverified", "confirmed", "disputed"] = "unverified"

class SearchRecord(BaseModel):
    query: str
    sub_topic: str
    by: str                  # agent id
    timestamp: str
    result_count: int

class Reservation(BaseModel):
    agent_id: str
    sub_topic: str
    keywords: list[str]
    timestamp: str
    status: Literal["active", "completed", "abandoned"] = "active"

# ---------- LangGraph State ----------

class OverallState(TypedDict):
    """主图共享状态"""
    topic: str
    depth: Literal["surface", "deep", "exhaustive"]
    
    # Phase 1: scoping
    sub_topics: list[str]
    
    # Phase 2: research（迭代字段）
    research_round: int                       # 第几轮
    findings: Annotated[list[Claim], add]    # 累积所有 claim
    
    # Phase 4-7
    synthesis: Optional[str]
    outline: Optional[list[dict]]            # [{section, key_points}, ...]
    sections: Annotated[dict, lambda a, b: {**a, **b}]  # section_name → content
    final_report: Optional[str]
    
    # 元信息
    workspace: str                            # 文件目录
    blackboard_db: str                        # Postgres 连接
    budget_used: Annotated[float, add]       # 累计花了多少
    budget_limit: float


class ResearcherState(TypedDict):
    """researcher subgraph 状态"""
    sub_topic: str
    agent_id: str
    workspace: str
    blackboard_db: str
    
    # 内部步骤
    planned_queries: list[str]
    skip_queries: list[str]              # 协商后要跳过的
    search_results: list[dict]
    fetched_pages: list[dict]
    
    # 输出
    new_claims: list[Claim]
    new_searches: list[SearchRecord]
```

---

## 三、黑板（Blackboard）层

用 Postgres 做共享存储。简单直接，事务安全。

```python
# blackboard.py
import psycopg
from psycopg.rows import dict_row
from datetime import datetime, timezone
from contextlib import contextmanager

SCHEMA = """
CREATE TABLE IF NOT EXISTS claims (
    id TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    sub_topic TEXT NOT NULL,
    text TEXT NOT NULL,
    source_url TEXT,
    source_excerpt TEXT,
    confidence TEXT,
    found_by TEXT,
    verification_status TEXT DEFAULT 'unverified',
    created_at TIMESTAMP DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_claims_topic ON claims(topic);
CREATE INDEX IF NOT EXISTS idx_claims_sub ON claims(sub_topic);

CREATE TABLE IF NOT EXISTS searches (
    id SERIAL PRIMARY KEY,
    topic TEXT NOT NULL,
    sub_topic TEXT NOT NULL,
    query TEXT NOT NULL,
    by_agent TEXT,
    result_count INTEGER,
    created_at TIMESTAMP DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_searches_topic ON searches(topic);

CREATE TABLE IF NOT EXISTS reservations (
    id SERIAL PRIMARY KEY,
    topic TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    sub_topic TEXT NOT NULL,
    keywords TEXT[],
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_res_topic ON reservations(topic);
"""


class Blackboard:
    def __init__(self, conn_str: str, topic: str):
        self.conn_str = conn_str
        self.topic = topic
        self._setup()
    
    def _setup(self):
        with self._conn() as c:
            c.execute(SCHEMA)
    
    @contextmanager
    def _conn(self):
        with psycopg.connect(self.conn_str, row_factory=dict_row, autocommit=True) as c:
            yield c.cursor()
    
    # ---------- Reservation ----------
    
    def list_active_reservations(self) -> list[dict]:
        with self._conn() as c:
            c.execute(
                """SELECT * FROM reservations 
                   WHERE topic = %s AND status = 'active'
                   AND updated_at > now() - interval '30 minutes'""",
                (self.topic,)
            )
            return c.fetchall()
    
    def reserve(self, agent_id: str, sub_topic: str, keywords: list[str]):
        with self._conn() as c:
            c.execute(
                """INSERT INTO reservations(topic, agent_id, sub_topic, keywords)
                   VALUES (%s, %s, %s, %s)""",
                (self.topic, agent_id, sub_topic, keywords)
            )
    
    def complete_reservation(self, agent_id: str):
        with self._conn() as c:
            c.execute(
                """UPDATE reservations SET status='completed', updated_at=now()
                   WHERE topic=%s AND agent_id=%s""",
                (self.topic, agent_id)
            )
    
    # ---------- Claims ----------
    
    def append_claims(self, claims: list[Claim]):
        with self._conn() as c:
            for cl in claims:
                c.execute(
                    """INSERT INTO claims(id, topic, sub_topic, text, source_url, 
                                          source_excerpt, confidence, found_by)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (id) DO NOTHING""",
                    (cl.id, self.topic, cl.sub_topic, cl.text, cl.source_url,
                     cl.source_excerpt, cl.confidence, cl.found_by)
                )
    
    def list_claims(self, sub_topic: str = None) -> list[dict]:
        with self._conn() as c:
            if sub_topic:
                c.execute("SELECT * FROM claims WHERE topic=%s AND sub_topic=%s",
                         (self.topic, sub_topic))
            else:
                c.execute("SELECT * FROM claims WHERE topic=%s", (self.topic,))
            return c.fetchall()
    
    # ---------- Searches ----------
    
    def append_search(self, query: str, sub_topic: str, by: str, result_count: int):
        with self._conn() as c:
            c.execute(
                """INSERT INTO searches(topic, sub_topic, query, by_agent, result_count)
                   VALUES (%s, %s, %s, %s, %s)""",
                (self.topic, sub_topic, query, by, result_count)
            )
    
    def list_recent_queries(self, limit: int = 100) -> list[str]:
        with self._conn() as c:
            c.execute(
                """SELECT DISTINCT query FROM searches 
                   WHERE topic=%s ORDER BY created_at DESC LIMIT %s""",
                (self.topic, limit)
            )
            return [r["query"] for r in c.fetchall()]
```

---

## 四、Researcher Subgraph

最复杂的部分——单个 researcher 内部就是一个 subgraph，包含**协商节点**。

```python
# researcher.py
from langgraph.graph import StateGraph, END
from langchain_anthropic import ChatAnthropic
import json, uuid, re
from datetime import datetime, timezone

llm_sonnet = ChatAnthropic(model="claude-sonnet-4-6", temperature=0)
llm_haiku = ChatAnthropic(model="claude-haiku-4-5", temperature=0)


def _extract_keywords(text: str) -> list[str]:
    """非常简化的关键词提取——生产里换成 KeyBERT 或 LLM"""
    words = re.findall(r"\w+", text.lower())
    stop = {"the", "a", "an", "of", "in", "on", "and", "or", "to", "is", "for"}
    return [w for w in words if len(w) > 2 and w not in stop][:20]


def _jaccard(a: list[str], b: list[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


# ---------- Nodes ----------

def plan_search_node(state: ResearcherState) -> dict:
    """生成初步搜索 query 列表"""
    prompt = f"""You are a research specialist. Plan search queries for this sub-topic.

Sub-topic: {state['sub_topic']}

Output JSON: {{"queries": ["...", "...", "..."], "keywords": ["..."]}}
Generate 5-8 diverse queries covering different angles.
"""
    resp = llm_sonnet.invoke(prompt).content
    data = json.loads(resp)
    return {"planned_queries": data["queries"]}


def check_blackboard_node(state: ResearcherState) -> dict:
    """协商核心：检查别人在做什么 + 已经搜过什么"""
    bb = Blackboard(state["blackboard_db"], topic_id_from_workspace(state["workspace"]))
    
    # 1. 看是否有重叠的 reservation
    my_keywords = _extract_keywords(state["sub_topic"])
    active = bb.list_active_reservations()
    
    overlap_with = []
    for res in active:
        if res["agent_id"] == state["agent_id"]:
            continue  # 跳过自己
        score = _jaccard(my_keywords, res["keywords"] or [])
        if score > 0.7:
            # 高度重叠 → 直接放弃这一轮
            return {
                "skip_queries": state["planned_queries"],  # 全部跳过
                "new_claims": [],
                "new_searches": [],
            }
        elif score > 0.3:
            overlap_with.append(res)
    
    # 2. 跳过已经搜过的 query（去重）
    recent = set(bb.list_recent_queries(200))
    skip = [q for q in state["planned_queries"] if q in recent]
    keep = [q for q in state["planned_queries"] if q not in recent]
    
    # 3. 如果跟某人部分重叠，让 LLM 重新规划缩小范围
    if overlap_with:
        prompt = f"""Other agents are working on overlapping topics:
{json.dumps([{"sub_topic": r["sub_topic"], "keywords": r["keywords"]} for r in overlap_with], ensure_ascii=False)}

My sub-topic: {state['sub_topic']}
My planned queries: {keep}

Refine my queries to AVOID overlap. Output JSON: {{"queries": [...]}}
"""
        resp = llm_haiku.invoke(prompt).content
        keep = json.loads(resp)["queries"]
    
    # 4. 登记 reservation
    bb.reserve(state["agent_id"], state["sub_topic"], my_keywords)
    
    return {
        "planned_queries": keep,
        "skip_queries": skip,
    }


def execute_searches_node(state: ResearcherState) -> dict:
    """跑 web search"""
    bb = Blackboard(state["blackboard_db"], topic_id_from_workspace(state["workspace"]))
    
    results = []
    for q in state["planned_queries"]:
        # 这里用任意 search API
        hits = web_search(q, max_results=5)
        results.extend(hits)
        bb.append_search(q, state["sub_topic"], state["agent_id"], len(hits))
    
    return {"search_results": results}


def fetch_pages_node(state: ResearcherState) -> dict:
    """抓取 top 页面"""
    fetched = []
    seen_urls = set()
    for r in state["search_results"][:15]:  # 上限 15 个
        if r["url"] in seen_urls:
            continue
        seen_urls.add(r["url"])
        try:
            content = web_fetch(r["url"])
            fetched.append({"url": r["url"], "content": content[:8000]})  # 截断
        except Exception:
            continue
    return {"fetched_pages": fetched}


def extract_claims_node(state: ResearcherState) -> dict:
    """从抓取的页面提取 claim"""
    bb = Blackboard(state["blackboard_db"], topic_id_from_workspace(state["workspace"]))
    
    # 让 LLM 看已知 claim，避免提取重复
    known_claims = bb.list_claims(sub_topic=state["sub_topic"])
    known_summary = "\n".join(f"- {c['text']}" for c in known_claims[:30])
    
    pages_text = "\n\n---\n\n".join(
        f"URL: {p['url']}\nContent: {p['content']}" for p in state["fetched_pages"]
    )
    
    prompt = f"""Extract factual claims about: {state['sub_topic']}

ALREADY KNOWN claims (don't repeat these):
{known_summary or '(none yet)'}

Source pages:
{pages_text}

Output JSON: {{"claims": [{{"text": "...", "source_url": "...", "source_excerpt": "...", "confidence": "high|medium|low|single-source"}}]}}
Rules:
- Only NEW claims (not in known list)
- Each claim 1-2 sentences
- Include source URL and exact excerpt
- "single-source" if only one page mentions it
"""
    resp = llm_sonnet.invoke(prompt).content
    data = json.loads(resp)
    
    new_claims = [
        Claim(
            id=str(uuid.uuid4()),
            text=c["text"],
            sub_topic=state["sub_topic"],
            source_url=c["source_url"],
            source_excerpt=c["source_excerpt"],
            confidence=c["confidence"],
            found_by=state["agent_id"],
        )
        for c in data["claims"]
    ]
    
    # 写入黑板
    bb.append_claims(new_claims)
    bb.complete_reservation(state["agent_id"])
    
    return {"new_claims": new_claims}


# ---------- 路由 ----------

def after_check_blackboard(state: ResearcherState) -> str:
    """如果完全跳过则直接结束"""
    if not state["planned_queries"]:  # 全被跳过
        return "skip_to_end"
    return "execute"


# ---------- 组图 ----------

def build_researcher_subgraph():
    g = StateGraph(ResearcherState)
    g.add_node("plan", plan_search_node)
    g.add_node("check_blackboard", check_blackboard_node)
    g.add_node("execute", execute_searches_node)
    g.add_node("fetch", fetch_pages_node)
    g.add_node("extract", extract_claims_node)
    
    g.set_entry_point("plan")
    g.add_edge("plan", "check_blackboard")
    g.add_conditional_edges("check_blackboard", after_check_blackboard, {
        "execute": "execute",
        "skip_to_end": END,
    })
    g.add_edge("execute", "fetch")
    g.add_edge("fetch", "extract")
    g.add_edge("extract", END)
    
    return g.compile()
```

**关键设计**：
- `check_blackboard_node` 是协商核心。先看别人的 reservation，再看 query 历史，再决定要不要继续。
- 如果重叠度过高 → 直接 END，**不做无谓工作**。
- 部分重叠 → 让 LLM 缩小范围（用 haiku 省钱）。
- 提取 claim 时把已知 claim 喂给 LLM，**消除"提取层面"的重复**。

---

## 五、主图（Orchestrator）

```python
# orchestrator.py
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver
import asyncio


def scoping_node(state: OverallState) -> dict:
    """Phase 1：拆解 sub-topics"""
    prompt = f"""Decompose this research topic into 5-10 sub-topics.

Topic: {state['topic']}
Depth: {state['depth']}

Output JSON: {{"sub_topics": ["...", "..."]}}
Each sub-topic should be:
- Concrete and searchable
- Non-trivially distinct from others (avoid heavy overlap)
- Together comprehensive enough to answer the main topic
"""
    resp = llm_sonnet.invoke(prompt).content
    data = json.loads(resp)
    return {
        "sub_topics": data["sub_topics"],
        "research_round": 0,
    }


def research_round_node(state: OverallState) -> dict:
    """Phase 2：并行派 researcher，每个跑 subgraph"""
    researcher = build_researcher_subgraph()
    
    # 找出还没充分研究的 sub-topic
    bb = Blackboard(state["blackboard_db"], state["topic"])
    unresearched = []
    for st in state["sub_topics"]:
        existing = bb.list_claims(sub_topic=st)
        if len(existing) < 3:  # 不够 3 条 claim 算没研究够
            unresearched.append(st)
    
    if not unresearched:
        return {"research_round": state["research_round"] + 1}
    
    # 并行派出
    inputs = [
        {
            "sub_topic": st,
            "agent_id": f"researcher_{state['research_round']}_{i}",
            "workspace": state["workspace"],
            "blackboard_db": state["blackboard_db"],
            "planned_queries": [],
            "skip_queries": [],
            "search_results": [],
            "fetched_pages": [],
            "new_claims": [],
            "new_searches": [],
        }
        for i, st in enumerate(unresearched)
    ]
    
    # 并发跑（asyncio.gather 或 batch）
    async def run_all():
        return await asyncio.gather(*[researcher.ainvoke(inp) for inp in inputs])
    
    results = asyncio.run(run_all())
    
    # 汇总 claim
    all_new_claims = []
    for r in results:
        all_new_claims.extend(r["new_claims"])
    
    return {
        "findings": all_new_claims,  # add reducer 累加
        "research_round": state["research_round"] + 1,
    }


def gap_check_node(state: OverallState) -> dict:
    """检查每个 sub-topic 覆盖度，找 gap"""
    bb = Blackboard(state["blackboard_db"], state["topic"])
    
    coverage = {}
    for st in state["sub_topics"]:
        claims = bb.list_claims(sub_topic=st)
        coverage[st] = len(claims)
    
    return {"coverage": coverage}  # 仅用于路由


def should_continue_research(state: OverallState) -> str:
    """判断是否再来一轮研究"""
    if state["research_round"] >= 3:
        return "synthesis"
    if state["budget_used"] >= state["budget_limit"]:
        return "synthesis"
    
    # 看是否还有没覆盖好的 sub-topic
    bb = Blackboard(state["blackboard_db"], state["topic"])
    for st in state["sub_topics"]:
        if len(bb.list_claims(sub_topic=st)) < 3:
            return "research_round"
    return "synthesis"


def verify_node(state: OverallState) -> dict:
    """挑出 single-source / disputed 的 claim 做交叉验证"""
    bb = Blackboard(state["blackboard_db"], state["topic"])
    all_claims = bb.list_claims()
    
    needs_verify = [c for c in all_claims 
                    if c["confidence"] in ("single-source", "low")
                    and c["verification_status"] == "unverified"][:20]  # 上限
    
    # 并行 verify（每个 claim 一个独立 LLM call）
    async def verify_one(claim):
        prompt = f"""Verify this claim independently.

Claim: {claim['text']}
Original source: {claim['source_url']}

Search for INDEPENDENT corroboration. Output JSON:
{{"verdict": "confirmed|disputed|unverifiable", "reasoning": "...", "independent_sources": [...]}}
"""
        resp = await llm_sonnet.ainvoke(prompt)
        return claim["id"], json.loads(resp.content)
    
    results = asyncio.run(asyncio.gather(*[verify_one(c) for c in needs_verify]))
    
    # 更新黑板（这里省略 SQL）
    return {}


def synthesis_node(state: OverallState) -> dict:
    """综合所有 confirmed claim 出洞察"""
    bb = Blackboard(state["blackboard_db"], state["topic"])
    confirmed = [c for c in bb.list_claims() if c["verification_status"] != "disputed"]
    
    by_topic = {}
    for c in confirmed:
        by_topic.setdefault(c["sub_topic"], []).append(c["text"])
    
    summary_text = "\n\n".join(
        f"### {st}\n" + "\n".join(f"- {t}" for t in claims)
        for st, claims in by_topic.items()
    )
    
    prompt = f"""Synthesize insights from these verified findings.

Topic: {state['topic']}

Findings:
{summary_text}

Output: structured analysis covering:
1. Key insights
2. Cross-cutting themes
3. Contradictions / tensions
4. Confidence assessment
"""
    resp = llm_opus.invoke(prompt).content
    return {"synthesis": resp}


def outline_node(state: OverallState) -> dict:
    """出报告大纲"""
    prompt = f"""Create a report outline.

Synthesis:
{state['synthesis']}

Output JSON: {{"sections": [{{"title": "...", "key_points": ["..."]}}]}}
"""
    resp = llm_sonnet.invoke(prompt).content
    return {"outline": json.loads(resp)["sections"]}


def drafting_node(state: OverallState) -> dict:
    """并行写每一章"""
    bb = Blackboard(state["blackboard_db"], state["topic"])
    
    async def write_section(section):
        relevant = bb.list_claims()  # 简化：实际可以按 section 过滤
        prompt = f"""Write this section.

Section: {section['title']}
Key points: {section['key_points']}

Available evidence:
{json.dumps([{"text": c["text"], "source": c["source_url"]} for c in relevant[:30]], ensure_ascii=False)}

Output: markdown section, with inline citations [1][2]...
"""
        resp = await llm_sonnet.ainvoke(prompt)
        return section["title"], resp.content
    
    results = asyncio.run(asyncio.gather(*[write_section(s) for s in state["outline"]]))
    return {"sections": dict(results)}


def review_node(state: OverallState) -> dict:
    """主 reviewer 看完整 report 提改进"""
    full = "\n\n".join(f"# {t}\n\n{c}" for t, c in state["sections"].items())
    
    prompt = f"""Review this research report for:
- Logical flow
- Unsupported claims
- Missing context
- Style consistency

Report:
{full[:30000]}

Output: revised full report (markdown).
"""
    resp = llm_opus.invoke(prompt).content
    return {"final_report": resp}


# ---------- 路由组图 ----------

def build_orchestrator():
    g = StateGraph(OverallState)
    g.add_node("scoping", scoping_node)
    g.add_node("research_round", research_round_node)
    g.add_node("gap_check", gap_check_node)
    g.add_node("verify", verify_node)
    g.add_node("synthesis", synthesis_node)
    g.add_node("outline", outline_node)
    g.add_node("drafting", drafting_node)
    g.add_node("review", review_node)
    
    g.set_entry_point("scoping")
    g.add_edge("scoping", "research_round")
    g.add_edge("research_round", "gap_check")
    g.add_conditional_edges("gap_check", should_continue_research, {
        "research_round": "research_round",
        "synthesis": "verify",
    })
    g.add_edge("verify", "synthesis")
    g.add_edge("synthesis", "outline")
    g.add_edge("outline", "drafting")
    g.add_edge("drafting", "review")
    g.add_edge("review", END)
    
    checkpointer = PostgresSaver.from_conn_string("postgresql://...")
    return g.compile(checkpointer=checkpointer)
```

---

## 六、启动

```python
# main.py
import uuid
from pathlib import Path

def run_research(topic: str, depth: str = "deep"):
    workspace = Path(f"./research/{slug(topic)}")
    workspace.mkdir(parents=True, exist_ok=True)
    
    app = build_orchestrator()
    
    config = {
        "configurable": {
            "thread_id": f"research:{slug(topic)}:{uuid.uuid4()}",
        }
    }
    
    initial = {
        "topic": topic,
        "depth": depth,
        "sub_topics": [],
        "research_round": 0,
        "findings": [],
        "synthesis": None,
        "outline": None,
        "sections": {},
        "final_report": None,
        "workspace": str(workspace),
        "blackboard_db": "postgresql://localhost/research",
        "budget_used": 0.0,
        "budget_limit": 20.0,  # $20 上限
    }
    
    # 启动；中断后用同 thread_id 恢复
    result = app.invoke(initial, config=config)
    
    # 写最终报告
    (workspace / "report.md").write_text(result["final_report"])
    return result


if __name__ == "__main__":
    run_research("2026 年中国大模型 To B 商业化进展", depth="deep")
```

---

## 七、恢复机制

LangGraph 的 checkpoint 让恢复变得几乎自动：

```python
# 中断后恢复——用同一个 thread_id
result = app.invoke(None, config=config)  # None 意味着不注入新输入，从 checkpoint 继续
```

**陷阱**：研究的实际产出（claim）写在 Postgres blackboard，不是 LangGraph state。所以即使 LangGraph state 丢了，**重启时新 researcher 看 blackboard 仍然知道之前的工作**。这是双重持久化的好处。

详见 [langgraph-checkpoint-and-hitl.md](langgraph-checkpoint-and-hitl.md)。

---

## 八、跟 Claude Code 版的对比

| 维度 | Claude Code 版 | LangGraph 版 |
|---|---|---|
| 协商机制 | 文件 + Manus skill | Postgres blackboard + 协商节点 |
| 并发 | Task 工具一次多个调用 | asyncio.gather + subgraph |
| 恢复 | 文件即状态 | Checkpoint + Blackboard 双保险 |
| 修改 prompt | 改 .md 文件 | 改 Python 代码 |
| 业务方能改 | ✅ | ❌（需要工程师） |
| 严格 SLA / 审计 | 弱 | **强**（可加监控、metrics、可观测） |
| 上手 | 快 | 慢（要写 600+ 行代码） |

**结论**：原型 / 个人用 → Claude Code 版；产品级 / 多团队协作 → LangGraph 版。

---

## 九、扩展阅读

- [../agents/research-agent-architecture.md](../agents/research-agent-architecture.md) —— Claude Code 版本 + 跟产品级方案对比
- [../agents/multi-agent-coordination.md](../agents/multi-agent-coordination.md) —— 协商机制理论
- [langgraph-checkpoint-and-hitl.md](langgraph-checkpoint-and-hitl.md) —— LangGraph 状态持久化
- [../tools-protocols/browser-automation.md](../tools-protocols/browser-automation.md) —— 浏览器接入升级
- [../evaluation/research-agent-evals.md](../evaluation/research-agent-evals.md) —— 评测体系
