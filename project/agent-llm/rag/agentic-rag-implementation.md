# Agentic RAG 落地：CRAG 与 Self-RAG 的具体实现

> [advanced-rag.md](advanced-rag.md) 讲了 Self-RAG / CRAG / GraphRAG 的**机制和概念**。本文是配套的**实现篇**：用 LangGraph 写出可跑的代码、对比两者的工程权衡、给出叠加用法。
>
> 配套阅读：[../production/langgraph-checkpoint-and-hitl.md](../production/langgraph-checkpoint-and-hitl.md)、[../agents/multi-agent-frameworks.md](../agents/multi-agent-frameworks.md)。

---

## 一、为什么这两个最值得先落地

CRAG 和 Self-RAG 是 Agentic RAG 里**最实用、性价比最高**的两个模式：

- **CRAG（Corrective RAG）**：检索完之后**判断质量**，差就纠正（重写查询 / 上网搜）
- **Self-RAG**：每一步都让 LLM 自己决定**要不要检索 / 检索了有没有用 / 答案有没有支撑**

思路完全不同——一个是"事后补救"，一个是"全程自省"。

---

## 二、传统 RAG vs Agentic RAG

### 传统 RAG Pipeline 长什么样

```
query → embed → vector_search(top_k=5) → rerank → prompt模板拼接 → LLM → answer
```

代码上是**一条直线**：

```python
def rag(query: str) -> str:
    embedding = embed_model.embed(query)
    docs = vector_store.search(embedding, top_k=5)
    reranked = reranker.rerank(query, docs)
    context = "\n".join(d.text for d in reranked[:3])
    prompt = f"Context:\n{context}\n\nQ: {query}\nA:"
    return llm.complete(prompt)
```

**特点**：
- 流程**固定**，每次查询走一样的路径
- **单轮**：检索一次，回答一次
- 没有"想想还要不要再查""换个问法再查""结合多个来源对比"
- **质量天花板很低**：复杂问题、多跳问题、需要交叉验证的问题都答不好

### Agentic RAG 的核心区别

把 RAG 从"管道"升级为**"事件驱动 / 状态机驱动的检索流程"**——可以循环、可以分支、可以自我纠错。

---

## 三、CRAG —— 简单粗暴有效

### 核心流程

```
query → retrieve → [Grader: 文档相关吗?]
                       ├─ correct  → 直接生成答案
                       ├─ ambiguous → 重写查询 + 网搜补充 → 生成
                       └─ incorrect → 完全走网搜 → 生成
```

### 用 LangGraph 实现（推荐，因为有分支）

```python
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END

class CRAGState(TypedDict):
    question: str
    documents: list
    web_results: list
    grade: Literal["correct", "ambiguous", "incorrect"]
    answer: str

# --- 节点定义 ---

def retrieve(state):
    docs = vector_store.similarity_search(state["question"], k=5)
    return {"documents": docs}

def grade_documents(state):
    """对每个文档打分，汇总成一个判断"""
    relevant_count = 0
    for doc in state["documents"]:
        prompt = f"""Question: {state["question"]}
Document: {doc.page_content}
Is this document relevant to the question? Answer only 'yes' or 'no'."""
        if "yes" in llm.invoke(prompt).lower():
            relevant_count += 1

    ratio = relevant_count / len(state["documents"])
    if ratio >= 0.6:
        grade = "correct"
    elif ratio >= 0.2:
        grade = "ambiguous"
    else:
        grade = "incorrect"
    return {"grade": grade}

def rewrite_query(state):
    """检索质量差时，重写查询"""
    new_q = llm.invoke(
        f"Rewrite this for better web search: {state['question']}"
    )
    return {"question": new_q}

def web_search(state):
    results = tavily_client.search(state["question"], max_results=3)
    return {"web_results": results}

def generate(state):
    context = "\n".join(d.page_content for d in state["documents"])
    if state.get("web_results"):
        context += "\n--- Web ---\n" + "\n".join(
            r["content"] for r in state["web_results"]
        )
    answer = llm.invoke(f"Q: {state['question']}\nContext: {context}\nA:")
    return {"answer": answer}

# --- 路由函数 ---

def route_after_grade(state) -> str:
    return {
        "correct": "generate",
        "ambiguous": "rewrite",
        "incorrect": "rewrite",
    }[state["grade"]]

# --- 组图 ---

g = StateGraph(CRAGState)
g.add_node("retrieve", retrieve)
g.add_node("grade", grade_documents)
g.add_node("rewrite", rewrite_query)
g.add_node("web_search", web_search)
g.add_node("generate", generate)

g.set_entry_point("retrieve")
g.add_edge("retrieve", "grade")
g.add_conditional_edges("grade", route_after_grade, {
    "generate": "generate",
    "rewrite": "rewrite",
})
g.add_edge("rewrite", "web_search")
g.add_edge("web_search", "generate")
g.add_edge("generate", END)

app = g.compile()
```

### CRAG 的工程要点

1. **Grader 用小模型**：每个文档都要打分，用 GPT-4 成本爆炸。**Haiku / GPT-4o-mini / 本地 7B** 完全够用。
2. **三档比二档好**：correct / incorrect 二分会过于激进；ambiguous 这档"既用本地也补网搜"是 CRAG 论文的精髓。
3. **网搜要 fallback**：Tavily / Serper / Brave 任选；记得加超时和缓存。

---

## 四、Self-RAG —— 更精细，更贵

### 核心思想

让 LLM 输出特殊 token，**自己反思**整个过程：

| Token | 含义 | 触发动作 |
|---|---|---|
| `[Retrieve]` | 现在需不需要检索？ | yes → 走检索；no → 直接答 |
| `[IsRel]` | 检索到的这个文档相关吗？ | irrelevant → 丢弃 |
| `[IsSup]` | 我的答案被文档支持吗？ | unsupported → 重新生成 |
| `[IsUse]` | 答案对用户有用吗？(1-5 分) | 选最高分版本 |

### 简化实现（不依赖微调模型，用 prompt 模拟）

```python
class SelfRAGState(TypedDict):
    question: str
    need_retrieval: bool
    documents: list
    relevant_docs: list
    answer: str
    is_supported: bool
    iteration: int

def decide_retrieve(state):
    """[Retrieve] token 模拟"""
    prompt = f"""Question: {state['question']}
Do you need to retrieve external knowledge to answer this?
Some questions (math, common sense, creative writing) don't need retrieval.
Answer 'yes' or 'no'."""
    decision = "yes" in llm.invoke(prompt).lower()
    return {"need_retrieval": decision}

def retrieve_and_filter(state):
    """检索 + [IsRel] 过滤"""
    docs = vector_store.similarity_search(state["question"], k=10)
    relevant = []
    for doc in docs:
        check = llm.invoke(
            f"Q: {state['question']}\nDoc: {doc.page_content}\n"
            f"Is this doc relevant? yes/no:"
        )
        if "yes" in check.lower():
            relevant.append(doc)
    return {"documents": docs, "relevant_docs": relevant[:3]}

def generate_with_check(state):
    """生成 + [IsSup] 验证"""
    if state.get("relevant_docs"):
        context = "\n".join(d.page_content for d in state["relevant_docs"])
        answer = llm.invoke(f"Context:\n{context}\nQ: {state['question']}\nA:")
    else:
        answer = llm.invoke(f"Q: {state['question']}\nA:")

    # 自我验证
    if state.get("relevant_docs"):
        verify = llm.invoke(
            f"Answer: {answer}\nDocs: {context}\n"
            f"Is the answer fully supported by the docs? yes/no:"
        )
        is_supported = "yes" in verify.lower()
    else:
        is_supported = True  # 无 RAG 模式不检查

    return {
        "answer": answer,
        "is_supported": is_supported,
        "iteration": state.get("iteration", 0) + 1,
    }

def route_retrieve(state):
    return "retrieve" if state["need_retrieval"] else "generate"

def route_after_generate(state):
    # 不支持 + 还有重试次数 → 回去再来一次
    if not state["is_supported"] and state["iteration"] < 2:
        return "retrieve"
    return END

# --- 组图 ---

g = StateGraph(SelfRAGState)
g.add_node("decide", decide_retrieve)
g.add_node("retrieve", retrieve_and_filter)
g.add_node("generate", generate_with_check)

g.set_entry_point("decide")
g.add_conditional_edges("decide", route_retrieve, {
    "retrieve": "retrieve",
    "generate": "generate",
})
g.add_edge("retrieve", "generate")
g.add_conditional_edges("generate", route_after_generate, {
    "retrieve": "retrieve",
    END: END,
})
```

### Self-RAG 的工程要点

1. **原版需要微调模型**：论文里用 Llama2 微调专门输出 reflection token，效果最好。**简化版用 prompt 模拟**也能跑，成本低得多但质量打折。
2. **必须有迭代上限**：`iteration < 2`，否则会无限循环。
3. **两次 LLM 检查 = 三倍 token**：开销不是闹着玩的，**只在高价值场景用**（医疗、法律、研报）。

---

## 五、CRAG vs Self-RAG 对比

| | CRAG | Self-RAG |
|---|---|---|
| 思路 | 一次检索后纠错 | 全流程自反思 |
| LLM 调用次数 | ~3 次 | 5-10 次 |
| 实现难度 | 中等 | 较高 |
| 效果上限 | 中等 | 高（需微调更好） |
| 性价比 | **高** | 低 |
| 推荐起步 | ✅ 先上这个 | 后期优化用 |

---

## 六、一个常被忽略的点：两者可以叠加

**这两个不是非此即彼，可以叠加**：

- 入口处用 Self-RAG 的 `[Retrieve]` 决定要不要检索
- 检索完后用 CRAG 的 grader 做质量分级
- 生成后用 Self-RAG 的 `[IsSup]` 做事实核查

实战中，**Self-RAG 的"决定要不要检索"和 CRAG 的"检索后纠错"组合最香**——前者省钱（简单问题不查），后者保质（复杂问题查准）。

```
[Self-RAG: 要不要检索?]
   ├─ no  → 直接答
   └─ yes → [retrieve] → [CRAG: 质量分级]
                            ├─ correct → 答
                            ├─ ambiguous → 重写 + 网搜 → 答
                            └─ incorrect → 网搜 → 答
                                            │
                                            ▼
                                  [Self-RAG: 答案被支撑吗?]
                                       ├─ yes → 输出
                                       └─ no  → 回到 retrieve
```

---

## 七、什么时候还是用传统 RAG

- **QPS 很高、延迟敏感**：每次都让 LLM 决策，p99 能爆
- **问题简单**：FAQ、单文档摘要这种，多走几步纯属浪费
- **预算紧**：Agentic RAG 的 token 消耗是直线 RAG 的 3-10 倍

---

## 八、Workflows / LangGraph 哪个写 Agentic RAG 更好

| | LlamaIndex Workflows | LangGraph |
|---|---|---|
| 抽象 | Event + Step（actor 风格） | State + Node（状态机风格） |
| 心智模型 | "消息在 step 间传" | "全局 state 沿图流动" |
| 可视化 | 自动从类型推图 | 显式 add_node/add_edge |
| HITL / Checkpoint | 有，但没 LangGraph 成熟 | 一等公民 |
| RAG 组件 | **原生丰富** | 需要自己接 |

**实战经验**：
- 主战场是检索 → **LlamaIndex Workflows**
- 主战场是流程编排 + 复杂 HITL → **LangGraph**
- 都重 → 常见组合是 **LangGraph 做外层流程，内部检索 step 用 LlamaIndex 的 retriever / reranker**（不一定要用 Workflows，用它的组件就行）

---

## 九、扩展阅读

- [advanced-rag.md](advanced-rag.md) —— Self-RAG / CRAG / GraphRAG 的概念与机制
- [retrieval-basics.md](retrieval-basics.md) —— RAG 基础与朴素 RAG 失败模式
- [../production/langgraph-checkpoint-and-hitl.md](../production/langgraph-checkpoint-and-hitl.md) —— LangGraph 状态持久化（用于多轮 RAG 中断恢复）
- [../production/frameworks-landscape.md](../production/frameworks-landscape.md) —— LlamaIndex Workflows 与 LangGraph 的全景定位
