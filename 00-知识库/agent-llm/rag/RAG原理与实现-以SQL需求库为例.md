# RAG 原理与实现 —— 以本地 SQL 需求检索库(sql-kb)为例

> 这份文档用 6 个问题把 RAG 从"是什么"讲到"怎么落地",并全程用工作区里真实的 [sql-kb](../../../sql-kb/) 项目做实例印证——每讲一个原理,都指到对应的代码。
>
> - 想先建全局心智模型 → 先读 [OVERVIEW.md](OVERVIEW.md)
> - 想深挖检索骨架/进阶范式 → [retrieval-basics.md](retrieval-basics.md)、[advanced-rag.md](advanced-rag.md)
> - 本篇定位:**原理 + 本地实战代码的对照讲解**,适合"边学原理边看自己项目"。

标注:本文涉及的模型能力、业界方案为公开资料归纳,已按理解重述。

---

## 目录

1. [经典 RAG 知识库的结构有哪些](#一经典-rag-知识库的结构)
2. [用的是什么语言模型?原理是什么](#二用的是什么模型原理是什么)
3. [RAG 知识库存储了什么](#三rag-知识库存储了什么)
4. [输入内容怎么切分和向量化](#四输入怎么切分和向量化)
5. [怎么做检索?输入什么?怎么实现](#五怎么做检索)
6. [RAG 业界优化方案有哪些,特点是什么](#六业界优化方案有哪些)

---

## 一、经典 RAG 知识库的结构

RAG 系统由**两条流水线**构成,一条离线、一条在线,它们共享一个向量库和一个 embedding 模型:

```
━━━ 离线建库（文档进来时跑一次 / 定期跑）━━━
  文档 → 解析清洗 → 切分 → Embedding → 写入向量库
                                          │
━━━ 在线检索（每次提问跑一次）━━━          │ 共享
  提问 → Embedding → 向量检索 → 重排 → 拼上下文 →（可选）LLM 生成
```

拆成部件是 7 个:

| # | 部件 | 职责 | 属于哪条链路 |
|---|------|------|------|
| 1 | 文档源 | 原始知识来源 | 离线 |
| 2 | 解析清洗 | 各种格式抽成纯文本 | 离线 |
| 3 | 切分 Chunking | 长文切成语义片段 | 离线 |
| 4 | Embedding 模型 | 文本→向量(两条链路共用) | 离线+在线 |
| 5 | 向量库 | 存向量+原文+元数据,支持相似检索 | 离线存 / 在线查 |
| 6 | 检索器 | 按问题捞相关片段(向量+关键词) | 在线 |
| 7 | 生成(可选) | LLM 基于检索结果回答 | 在线 |

> 结构的详细讲解见 [OVERVIEW.md 第三、四节](OVERVIEW.md)。

### 👉 在 sql-kb 里,这 7 个部件对应哪些文件

| 部件 | sql-kb 对应 |
|------|-------------|
| ① 文档源 | `data/真实样例/` 里的取数脚本 |
| ② 解析清洗 + ③ 切分 | [`parse.py`](../../../sql-kb/parse.py) —— 把脚本切成"一段需求=一条记录" |
| ④ Embedding | [`embedder.py`](../../../sql-kb/embedder.py) —— BGE 中文模型 |
| ⑤ 向量库 | [`build_index.py`](../../../sql-kb/build_index.py) 写入 Chroma;完整记录存 `requirements.jsonl` |
| ⑥ 检索器 | [`retriever.py`](../../../sql-kb/retriever.py) —— 向量+BM25+RRF |
| ⑦ 生成 | **本项目不做**,纯检索;交给下游 agent(见第二节) |

配置中枢 [`config.py`](../../../sql-kb/config.py) 和数据结构 [`schema.py`](../../../sql-kb/schema.py) 贯穿所有部件。

---

## 二、用的是什么模型?原理是什么?

**先破一个常见误解:RAG 里其实有两类模型,角色完全不同。**

| 角色 | 干什么 | 是不是"会聊天的大模型" |
|------|--------|----------------------|
| **嵌入模型(Embedding)** | 把文本变成向量,用来算"谁和谁语义相近" | 不是。它只输出向量,不生成文字 |
| **生成模型(LLM)** | 基于检索到的资料生成答案 | 是。GPT / Claude / 本地大模型 |

sql-kb 目前**只用了嵌入模型(纯检索)**,生成留给下游 agent。所以这两个分开讲。

### 2.1 嵌入模型:sql-kb 用的是 BGE-large-zh-v1.5

```python
# config.py
EMBED_MODEL = "BAAI/bge-large-zh-v1.5"
```

**原理(尽量说人话):**

1. 它是一个 **Transformer 编码器**(BERT 类结构),输入一句话,输出一串数字(向量,这里是 1024 维)。
2. 训练用的是**对比学习**:把"意思相近的句子对"拉近、"不相近的"推远。训练完,**语义相近的文本,向量在空间里也相近**——这就是"按意思检索"能成立的根基。
3. 一句话有很多 token,每个 token 都有向量,最后用**池化(pooling)**汇成一个定长句向量。
4. sql-kb 里向量做了**归一化**(长度变 1),这样"余弦相似度"就等于向量点积,和向量库的距离度量对上。

> Transformer / 注意力机制的底层原理见 [../llm-fundamentals/transformer.md](../llm-fundamentals/transformer.md)。

**一个关键实现细节:query 和 document 编码方式不同(双塔思想)。**

```python
# embedder.py
def embed_documents(texts):        # 文档侧：直接编码
    ... model.encode(texts, normalize_embeddings=True)

def embed_query(text):             # 查询侧：加一句指令前缀
    ... model.encode(config.QUERY_INSTRUCTION + text, normalize_embeddings=True)
```

bge 中文模型**官方要求检索时给 query 加一句指令前缀**(`"为这个句子生成表示以用于检索相关文章："`),文档侧不加。这是模型训练时就这么设定的,照做能提升召回。

### 2.2 生成模型:sql-kb 不用,下游 agent 接

sql-kb 检索出"最像的历史需求 + SQL"后就停了。真正"写新 SQL 草稿"是下游 agent 的事,那里才用 LLM。sql-kb 只负责把料喂好:

```python
# retriever.py —— 把检索结果拼成给 LLM 的 few-shot
def build_fewshot_prompt(query, results): ...
```

**LLM 生成原理一句话:** 自回归的"预测下一个词"——给它"历史相似 SQL + 新需求",它逐 token 续写出新 SQL。因为上下文里带了你团队**真实的表名和写法**,生成结果比空想准得多。这就是"检索增强生成"里"增强"的含义。

> 为什么"检索增强"能压制幻觉、LLM 生成的更多细节,见 [OVERVIEW.md](OVERVIEW.md) 与 [retrieval-basics.md](retrieval-basics.md)。

---

## 三、RAG 知识库存储了什么?

通用答案:**切碎的原文 + 每段的向量 + 可过滤的元数据 + 一个加速检索的索引**。

### 👉 在 sql-kb 里,存储分两处(有意为之)

```
requirements.jsonl（真相源，人可读，含完整 SQL）
  每行一条 = 一个子需求的全部字段
        │
        │ build_index.py 读它，向量化后写入 ↓
        ▼
chroma_db/（向量库，负责"快速找相似"）
  存：向量 + metadata + document
```

**一条记录长什么样**(见 [`schema.py`](../../../sql-kb/schema.py) 的 `Requirement`):

| 字段 | 例子 | 用途 |
|------|------|------|
| id | `req-005` | 唯一标识,两处存储靠它对应 |
| title | `2026抖音上滑人群` | 子需求标题 |
| desc | `圈选近7天活跃…` | **描述,向量主要嵌它** |
| sql | `with s1 as (...)...` | **载荷:检索命中后返回,不参与向量** |
| tables | `[hive....dwm_...]` | 来源表,给关键词检索用 |
| biz_line/date/author | `增长 / 2026-07-06 / 张三` | 元数据,支持过滤 |
| source | `抖音上滑人群售卖` | 需求组(同一文件多段共享) |

**为什么向量只嵌描述、SQL 只当载荷?**

```python
# schema.py
def to_embedding_text(self):     # 向量化文本：source+title+desc，不含 sql
    parts = [self.source, self.title, self.desc]
    ...
```

因为 SQL 里全是 `SELECT/FROM/WHERE` 关键词,直接嵌会污染语义、让相似度失真。所以 SQL 作为"命中后要返回的东西"存着,但不拿去算相似度。这是这个场景最重要的一个设计决策。

**注意 Chroma 的一个限制**:metadata 只接受 str/int/float/bool,所以 `tables` 这个列表要拼成逗号串才能存:

```python
# schema.py
def to_chroma_metadata(self):
    return {..., "tables": ",".join(self.tables), ...}
```

---

## 四、输入怎么切分和向量化?

### 4.1 切分:按"语义单元",不按字数

**通用原则**:一个 chunk 要是"能独立理解的完整语义单元"。普通文档按标题/段落切;但 sql-kb 的场景特殊——**一个取数需求(描述+SQL)就是一个单元,SQL 绝不能从中间切开**。

sql-kb 的真实文档是"注释 + 裸 SQL"的脚本,切分规则是:**按 `;` 分句 + 段间 `----` 注释归属**。核心是 [`parse.py`](../../../sql-kb/parse.py) 里的状态机:

```python
pending = []      # 攒着的段间注释（还没归给哪条 SQL）
cur_sql = []      # 当前语句缓冲
started = False   # 当前语句是否已出现实质 SQL 内容

# 逐行扫描：
#   注释行 + started=False → 下一条需求的描述（进 pending）
#   注释行 + started=True  → SQL 内部注释（如 CTE 里的），原样保留，不分段
#   遇到 ; 结尾 → flush() 收一条
```

**难点**:文件里 CTE(`with s1 as (...)`)内部也全是 `----` 注释,不能被误当成分段点。解法就是**用 `;` 判断语句边界,而不是用注释**——`started` 这个开关区分"语句还没开始"(注释是新需求描述)还是"语句进行中"(注释是 SQL 内部的)。

`flush()` 的三分支决定了粒度:

```python
if pending:      # 有新描述 → 新记录
elif records:    # 没新描述 → 并入上一条（count 校验/导出 SQL 就这样被并进去）
else:            # 文件开头就是 SQL → 用文件名当标题
```

实测效果:一个含 4 段取数的文件切成 4 条;一个"大圈选+count校验+导出"的文件合成 1 条。**规则没写死,是三分支自然推导的结果**。

> 分块的通用策略(固定/语义/结构化/Late Chunking)与 chunk 大小经验见 [retrieval-basics.md 第三节](retrieval-basics.md)。

### 4.2 向量化:批量编码 + 归一化

切好的记录进 [`build_index.py`](../../../sql-kb/build_index.py):

```python
texts = [r.to_embedding_text() for r in records]   # 取"描述"文本
embeddings = embedder.embed_documents(texts)        # BGE 批量编码
collection.add(ids=..., embeddings=..., metadatas=..., documents=...)
```

`embed_documents` 里 `normalize_embeddings=True` 做归一化,配合建库时的 `metadata={"hnsw:space": "cosine"}`(余弦距离),保证检索时度量一致。

---

## 五、怎么做检索?

### 5.1 检索输入的是什么

**输入 = 用户的自然语言需求描述**(如 `"按城市统计每日新增用户"`),不是 SQL。因为要匹配的是历史**需求描述**之间的语义相似。

### 5.2 怎么实现:双路召回 + RRF 融合

[`retriever.py`](../../../sql-kb/retriever.py) 的 `retrieve` 主流程:

```python
dense  = self._dense_ids(query, n, allowed)     # ① 向量检索：抓语义
sparse = self._sparse_ids(query, n, allowed)    # ② BM25：抓精确词（表名/字段）
fused  = _rrf([dense, sparse], config.RRF_K)[:k]  # ③ RRF 融合，取前 k
return [self.records[rid].to_dict() for rid in fused ...]  # ④ 用 id 取完整记录
```

- **① 向量检索**:`embed_query(query)` 把问题变向量,Chroma 返回最相似的一批 id。捕捉语义("新增用户"≈"注册用户")。
- **② BM25 关键词**:内存里对 `title+desc+tables` 打分,捕捉精确词(搜某张表名能命中)。分数为 0 就丢弃。
- **③ RRF 融合**:把两路排名合并。
- **④ 取回载荷**:融合结果是 id,再从 `records` 取出含完整 SQL 的记录返回。

**RRF 原理 + 手算**:

```python
def _rrf(rank_lists, k):          # k=60
    scores = {}
    for lst in rank_lists:
        for rank, rid in enumerate(lst):
            scores[rid] += 1.0 / (k + rank + 1)   # 排名越靠前分越高
    return 按分数倒序
```

举例,两路召回:
```
向量路: [A, B, C]      BM25路: [B, D, A]
A: 1/61 + 1/63 = 0.0323
B: 1/62 + 1/61 = 0.0325   ← 两路都靠前，最高
D: 1/62         = 0.0161
C: 1/63         = 0.0159
→ 融合排序：B, A, D, C
```

RRF 的妙处:**只看排名不看原始分数**,所以能把"余弦相似度"和"BM25 分数"这两种量纲不同的分数公平合并。这是业界最常用的融合法,不用调权重。

**过滤**(如只在某业务线里搜):先算出满足条件的 `allowed` id 集合,两路都只在集合内取。

> 混合检索、rerank、query 改写等的完整讲解见 [retrieval-basics.md 第五~七节](retrieval-basics.md)。

---

## 六、业界优化方案有哪些?

朴素 RAG 在场景变复杂时会吃瘪,业界的优化按"作用在哪个环节"分四类:

### 6.1 分块 / 索引优化

| 方案 | 特点 / 解决什么 | 代价 |
|------|----------------|------|
| 结构化分块 | 按标题/代码函数/表格切,尊重文档结构 | 需按文档类型定制 |
| Late Chunking | 块向量含全文上下文,召回精度提升 | 需特定 embedding 模型 |
| Contextual Retrieval(Anthropic) | 入库前用 LLM 给每块补一句上下文,失败率明显降 | 建库要额外 LLM 调用 |

### 6.2 检索优化(性价比最高,优先做)

| 方案 | 特点 / 解决什么 | 代价 |
|------|----------------|------|
| **混合检索(向量+BM25)** | 语义+精确词兼顾;几乎必做 | 低 |
| **Rerank(重排)** | 召回 top-20 用 cross-encoder 精排取 top-5,相关性提升 20-40% | 一次额外模型调用 |
| Query 改写(HyDE / Multi-Query / Step-back) | 把模糊/多意图问题改写得更适合检索 | 每次查询加 LLM 调用 |

### 6.3 流程优化(让 RAG"更聪明")

| 方案 | 特点 / 解决什么 | 代价 |
|------|----------------|------|
| Self-RAG | 让模型自己判断"要不要检索、检索得好不好" | 需微调专门模型 |
| CRAG(Corrective) | 召回质量自评,不相关就用 Web 兜底 | 需训评估器 + Web 调用 |
| Adaptive RAG | 按问题复杂度路由到不同检索流程 | 路由错了更糟 |
| Multi-hop / Iterative | 多步检索,解决需要"沿路径深挖"的问题 | 延迟、成本上升 |

### 6.4 结构优化

| 方案 | 特点 / 解决什么 | 代价 |
|------|----------------|------|
| GraphRAG(微软) | 抽实体建知识图谱,能答"全局型"问题(朴素 RAG 死角) | 建库成本极高 |

> 以上每个方案的机制、决策树、反直觉发现见 [advanced-rag.md](advanced-rag.md);用 LangGraph 落地 CRAG/Self-RAG 见 [agentic-rag-implementation.md](agentic-rag-implementation.md)。

### 👉 sql-kb 用了哪些、下一步该加哪个

| 状态 | 方案 | 说明 |
|------|------|------|
| ✅ 已用 | 结构化分块 | 按需求段切,不按字数 |
| ✅ 已用 | 混合检索 + RRF | 向量抓语义、BM25 抓表名 |
| ⬜ 建议下一步 | **Rerank** | 性价比最高,加一个 bge-reranker 即可,召回质量再上一档 |
| ⬜ 可选 | Query 改写 | 需求描述口语化严重时再加 |
| ❌ 暂不需要 | GraphRAG / Self-RAG | 几百条规模,过度设计 |

**给 sql-kb 的一句话建议**:先把"加 Rerank"作为下一步——它对当前架构改动最小、收益最直接;GraphRAG/Self-RAG 这些在几百条规模上是过度设计,别上。

---

## 延伸阅读(同知识域)

- [OVERVIEW.md](OVERVIEW.md) —— RAG 全景:一张表 + 两条流水线 + 部署三档 + 设计决策链
- [retrieval-basics.md](retrieval-basics.md) —— 检索骨架:分块/向量化/混合检索/rerank/评测
- [advanced-rag.md](advanced-rag.md) —— 进阶范式:Self-RAG / CRAG / GraphRAG / Adaptive
- [agentic-rag-implementation.md](agentic-rag-implementation.md) —— 用 LangGraph 落地可跑代码
- 服务器部署 → [../../ai-infra/methods/rag/Linux_RAG知识库搭建指南.md](../../ai-infra/methods/rag/Linux_RAG知识库搭建指南.md)
- 本文的实战对象 → [sql-kb 项目](../../../sql-kb/)(`README.md` 讲用法,本文讲原理)
