# RAG 检索基础

> RAG（Retrieval-Augmented Generation）是把 LLM 接到企业知识、私有数据、最新文档的标准范式。本文从最小可行实现讲起，覆盖**分块、向量化、混合检索、rerank、评测**——这些是 RAG 落地的"骨架"，决定了系统能不能用。

---

## 一、RAG 在解决什么

LLM 直接回答企业问题的两个硬伤：

1. **知识截止**：模型只知道训练时见过的事
2. **私有数据**：用户的内部文档、个人笔记、公司知识库它一无所知

**RAG 的解法**：

```
用户提问 → 在知识库里检索相关片段 → 把片段塞进 prompt → LLM 基于片段回答
```

简单到有人质疑"这就行了"——但工业 RAG 有大量细节决定**好用 vs 不能用**。

---

## 二、最小 RAG 流水线

```
┌──────────────────────────────────────────────────────────┐
│                                                          │
│   离线（一次性 / 定期）                                    │
│   文档 → 分块 → embedding → 向量库                        │
│                                                          │
│   在线（每次问答）                                         │
│   query → embedding → 检索 top-K → 拼 prompt → LLM 回答   │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

最小代码（约 30 行）：

```python
import openai
from chromadb import Client

# 离线
db = Client().create_collection("docs")
chunks = ["chunk1...", "chunk2...", ...]  # 分好块
embeds = openai.embeddings.create(input=chunks, model="text-embedding-3-small").data
db.add(documents=chunks, embeddings=[e.embedding for e in embeds], ids=[str(i) for i in range(len(chunks))])

# 在线
def rag_answer(q):
    qe = openai.embeddings.create(input=q, model="text-embedding-3-small").data[0].embedding
    results = db.query(query_embeddings=[qe], n_results=5)
    context = "\n\n".join(results["documents"][0])
    return openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": f"基于以下资料回答：\n{context}"},
            {"role": "user", "content": q}
        ]
    ).choices[0].message.content
```

→ 这就是"演示版" RAG。下面讲为什么生产级要做的事多得多。

---

## 三、分块（Chunking）：被严重低估的关键步骤

分块 = 把长文档切成 LLM 能消化的小片段。**它直接决定召回上限**——切得不好，再强的 embedding 也救不回来。

### 1. 固定 Token 数（最朴素）

```python
chunk_size = 500  # tokens
overlap    = 50

chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size - overlap)]
```

| 优势 | 劣势 |
|---|---|
| 实现简单 | 经常切到句子中间、表格中间 |
| 性能可预测 | 上下文断裂 |

### 2. 语义分块（按段落 / 标题）

```python
# 优先按 H1/H2/H3 切；不够小再按段落 / 句子细切
```

工具：LlamaIndex 的 `SentenceSplitter`、LangChain 的 `RecursiveCharacterTextSplitter`。

### 3. 结构化分块

按文档结构走：
- Markdown 按 heading
- HTML 按 DOM tree
- PDF 按页 + heading
- 代码按函数 / class

这是**生产 RAG 的真正基线**——你的文档是结构化的，分块也该是结构化的。

### 4. Late Chunking（2024 主流升级）

传统：先分块再 embed → 每个块独立 embed，丢失了跨块的上下文
Late Chunking：先把整个文档过一遍 embedding 模型 → 在 token 级 embedding 上再做 mean-pool 切块

| 优势 | 劣势 |
|---|---|
| 块的 embedding 包含全文上下文 | 实现复杂、需特定 embedding 模型 |
| 召回精度提升 5-15% | 不是所有 embedding 模型支持 |

### 5. 分块大小的经验

| 文档类型 | 推荐大小 |
|---|---|
| 技术文档 / FAQ | 200-500 token |
| 长报告 / 论文 | 500-1000 token |
| 代码 | 按函数（不固定大小） |
| 多模态（带表格） | 表格独立成块 |

> **分块大小不是越小越好**——块太小 = 召回片段缺上下文，LLM 答不出。块太大 = 一个片段含多个主题，相似度被稀释。

---

## 四、Embedding 模型选型

### 主要选项（截至 2026 年初）

| 模型 | 维度 | 长处 | 成本 |
|---|---|---|---|
| `text-embedding-3-small` (OpenAI) | 1536 | 综合好、便宜 | $0.02/1M token |
| `text-embedding-3-large` (OpenAI) | 3072 | 精度更高 | $0.13/1M token |
| `voyage-3` (Anthropic 推荐) | 1024 | 长文档 + 多语言强 | 类似 OpenAI |
| `BGE-M3` (BAAI 开源) | 1024 | 中文强、开源、多向量支持 | 自部署 |
| `GTE-Qwen2-1.5B-instruct` | 1536 | 中文强、可微调 | 自部署 |
| `e5-mistral-7b` | 4096 | 高精度、推理慢 | 自部署 |

### 选型标准

1. **任务匹配**：技术文档 / 中文 / 长文 → 不同强项
2. **维度 vs 成本**：3072 维 vs 1024 维，索引大小差 3 倍
3. **是否需要 fine-tune**：有领域数据 + 性能瓶颈 → 微调能涨 10-30 个点

> **不要默认 OpenAI**。中文场景 BGE 系列经常更好，且免费。

---

## 五、检索方式：稠密 / 稀疏 / 混合

### 1. 稠密检索（Dense / Vector Search）

embedding 相似度。**捕语义**，"打折"和"折扣"能命中。

### 2. 稀疏检索（Sparse / BM25）

经典关键词检索。**捕精确词**，"型号 ABC123" 这种向量搜常错过的它能命中。

### 3. 混合检索（Hybrid）

**生产 RAG 几乎必须做**：

```python
results = merge(
    dense_search(query, top_k=10),
    bm25_search(query, top_k=10)
)
```

合并方法：
- **RRF**（Reciprocal Rank Fusion，最常用）：每个结果按它在两路中的排名取 `1/(k+rank)` 求和
- 加权线性合并

工具：Elasticsearch 8+、OpenSearch、Weaviate、Qdrant、Milvus 都原生支持 hybrid。

### 4. Multi-vector / ColBERT

每个 token 一个 embedding，检索时做 token 级匹配（"late interaction"）。
- 精度极高
- 索引和检索成本也极高
- 工具：ColBERT、Vespa、Jina ColBERT

工业用得相对少，但精度敏感场景值得评估。

---

## 六、Rerank：Top-K 之后还有一步

向量检索召回 top-50 不一定按真正相关度排序。**Reranker** 是"二次排序模型"：

```
Step 1: 向量库 / BM25 召回 top-50（"宁错放、不漏放"）
Step 2: 用 cross-encoder reranker 对这 50 个 (query, chunk) 对算精确分数
Step 3: 取 top-5 喂 LLM
```

Reranker 类型：

| 类型 | 例子 | 长处 |
|---|---|---|
| Cross-encoder | `bge-reranker-v2-m3`、`jina-reranker-v2`、`cohere-rerank-3.5` | 性价比高 |
| LLM-as-Reranker | 让 GPT-4 重排 | 精度最高、贵 |

**收益**：top-5 的相关性提升 20-40%——RAG 召回质量最大杠杆之一。**几乎所有生产 RAG 都加 reranker**。

---

## 七、Query 改写：用户问题不直接拿去检索

用户的原始问题往往不适合检索：太模糊、太长、有代词、多个意图混在一起。

### 1. Query Rewriting

```
原始：上次说的那个新功能现在咋样？
改写：[功能 X] 当前进展、状态、上线时间
```

### 2. HyDE（Hypothetical Document Embedding）

让 LLM 先"假装"写一篇答案 → 用这个假答案的 embedding 去检索（比 query 的 embedding 更接近文档分布）。

### 3. Multi-Query

让 LLM 把一个问题拆成多个子查询，每个分别检索 → 合并去重。

### 4. Step-back Prompting

让 LLM 先归纳出"高层概念"再检索（"问支付失败" → "支付系统架构"）。

> **生产经验**：Multi-Query + HyDE 是两个最稳定有效的改写策略。

---

## 八、上下文拼装

检索到 top-K 之后**怎么塞进 prompt**也有讲究：

### 1. 顺序

```
LLM 对中段记忆差（lost in the middle）
→ 把最重要片段放开头或结尾，不重要的放中间
```

### 2. 引用 / Citation

```
prompt 里给每个片段加 [1] [2] [3]
要求 LLM 在回答中标注引用
```

让用户能验证答案来源——RAG 产品的标配。

### 3. 格式化

```
< chunk_1 source="doc_A.pdf" page="3">
内容...
</chunk_1>
```

XML 标签是 Anthropic 推荐的，能让模型更好理解结构。

### 4. 控制总 token 量

```
检索到的片段 + system + history 不能超 context window
若超出 → 降低 top-K 或先做摘要
```

---

## 九、评测：没评测的 RAG 不能改进

### 离线评测

构建**黄金集**（50-200 条 query + 期望答案 + 期望召回片段）：

| 指标 | 测什么 | 工具 |
|---|---|---|
| Recall@K | 期望片段在 top-K 里吗 | 手算 |
| MRR | 第一个相关片段排第几 | 手算 |
| Faithfulness | 回答是否忠于检索片段（不是幻觉） | RAGAS |
| Answer Relevance | 回答是否切题 | RAGAS、TruLens |
| Context Precision | 检索的片段都相关吗 | RAGAS |

→ 详见 [../evaluation/llm-as-judge.md](../evaluation/llm-as-judge.md)

### 在线监控

- 用户点踩率
- 检索为空 / 命中过少的 query 占比
- 平均检索片段数 / token 占比

---

## 十、生产 RAG 的"高级配方"

把上面所有杠杆叠起来 + 再加几招：

```
1. 离线：
   - 结构化分块（Markdown heading / 代码 function 等）
   - Late Chunking（如果 embedding 模型支持）
   - 多种 embedding（密集 + 稀疏 + 关键词索引）

2. 在线：
   query → Multi-Query 改写
        → HyDE 候选答案
        → Hybrid Retrieval (dense + BM25)
        → Cross-encoder Rerank
        → Top-K 注入 prompt（带 citation 格式）
        → LLM 回答
        → 后处理：检查 citation 完整性
```

效果通常比朴素 RAG 提升 30-100%。

---

## 十一、什么时候不该用 RAG

不是所有"接知识"问题都该 RAG：

| 场景 | 更好的选项 |
|---|---|
| 知识量小（< 100KB） | 直接全部塞进 long context |
| 数值密集型问答 | Text-to-SQL / 调函数 |
| 需要推理多个事实 | RAG + Agent（多轮检索） |
| 需要全文遍历 | 直接全文给 LLM（如果窗口够） |
| 知识高频更新 | 实时 API + Function Calling |

---

## 十二、Checklist

```
□ 1. 分块策略匹配文档结构吗？
□ 2. embedding 模型在我场景上做过对比评测吗？
□ 3. 用了 Hybrid（语义 + 关键词）吗？
□ 4. 加了 reranker 吗？
□ 5. query 做了改写 / HyDE 吗？
□ 6. prompt 里有 citation 格式吗？
□ 7. 评测黄金集有多少条？多久重跑一次？
□ 8. 在线有"召回为空"和"用户点踩"监控吗？
□ 9. 知识更新频率 vs 索引重建频率匹配吗？
□ 10. 是否考虑过"长 context + 不用 RAG"作为对比 baseline？
```

---

## 十三、扩展阅读

- 相关：[../agents/memory-systems.md](../agents/memory-systems.md)、[../evaluation/llm-as-judge.md](../evaluation/llm-as-judge.md)
- Lewis et al. (2020) — *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*（RAG 原始论文）
- Gao et al. (2023) — *Precise Zero-Shot Dense Retrieval without Relevance Labels*（HyDE）
- Khattab & Zaharia (2020) — *ColBERT*
- BAAI — *BGE-M3 Technical Report*
- RAGAS / TruLens 文档
- LangChain RAG cookbook、LlamaIndex 文档
- 本仓库 [knowledge-base/RAG/](../../../knowledge-base/RAG/) 现有沉淀
