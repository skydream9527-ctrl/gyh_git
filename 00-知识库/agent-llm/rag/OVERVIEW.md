# RAG 检索增强 — 开篇导读

> 这是 [rag/](.) 目录的总入口。读完这一篇，你应该能回答：RAG 到底解决什么问题、一个知识库落到硬盘上"长什么样"、它由哪些部件构成、怎么部署、怎么设计、以及按什么顺序深入本目录其余文件。
>
> 建立完心智模型后，细节按需深入：骨架看 [retrieval-basics.md](retrieval-basics.md)，进阶范式看 [advanced-rag.md](advanced-rag.md)，可跑代码看 [agentic-rag-implementation.md](agentic-rag-implementation.md)，服务器部署看 [../../ai-infra/methods/rag/Linux_RAG知识库搭建指南.md](../../ai-infra/methods/rag/Linux_RAG知识库搭建指南.md)。

---

## 一、RAG 在解决什么问题

**一句话**：RAG（Retrieval-Augmented Generation，检索增强生成）是把你的私有文档加工成"可被语义检索的形态"存起来，问答时按语义捞出最相关的几段塞进提示词，让大模型照着有依据地回答。

它治的是 LLM 的两个硬伤：

- **知识截止**：模型只知道训练时见过的事，不知道上周的新方案。
- **私有数据**：你的指标口径、内部文档、历史决策，模型一无所知。

一个好记的心智模型：

```
开卷考试
  ├─ 大模型   = 考生（有通识和推理能力，但不知道你公司的事）
  ├─ 知识库   = 允许带进考场的参考书
  ├─ 检索     = 拿到题目后 3 秒翻到最相关的那几页
  └─ 生成     = 照着翻到的那几页组织答案，并标注引用
```

> RAG 做的一切，都是为了让这场开卷考"翻书翻得准、答得有依据、能追溯来源"。

---

## 二、RAG *不* 解决什么问题

把 RAG 当万能钥匙是最常见的误区。它不解决：

| 不适用场景 | 更好的选项 |
|---|---|
| 知识量很小（< 100KB） | 直接把全文塞进长上下文，更简单更准 |
| 数值/明细型问答（"上月 GMV 多少"） | Text-to-SQL / 调函数，别用向量检索 |
| 知识高频更新（"今天的 DAU"） | 实时 API + Function Calling |
| 结构混乱/prompt 模糊导致的幻觉 | RAG 只补"知识缺失"，治不了这种 |
| 需要全局视角（"这批文档的主线是什么"） | GraphRAG（见 [advanced-rag.md](advanced-rag.md)） |
| 需要沿路径多跳推理 | Multi-hop / Agentic RAG（见 [agentic-rag-implementation.md](agentic-rag-implementation.md)） |

> **一句话判断**：RAG 是为"知识量大到塞不下、且以事实检索为主"而生的。知识小就别 RAG，要算数就别 RAG，要实时就别 RAG。

---

## 三、心智模型一：知识库落到硬盘上，其实就是一张表

抛开所有花哨概念，一个 RAG 知识库的本体，**就是一张表 + 一个向量索引**。用最主流的 pgvector 方案看最直观：

```
documents 表（记录来源文件）
┌──────┬──────────────┬─────────────┬──────────────┐
│ id   │ filename     │ source_path │ created_at   │
├──────┼──────────────┼─────────────┼──────────────┤
│ 1    │ 指标口径.pdf  │ /uploads/.. │ 2026-07-01   │
└──────┴──────────────┴─────────────┴──────────────┘

chunks 表（知识库的"心脏"——真正被检索的东西）
┌────┬─────────────┬────────────────────────┬───────────────┬─────────────────────────┐
│ id │ document_id │ content（原文片段）      │ metadata      │ embedding（语义向量）     │
├────┼─────────────┼────────────────────────┼───────────────┼─────────────────────────┤
│ 12 │ 1           │ "DAU 口径：自然日活跃…"  │ {业务线:电商} │ [0.021, -0.33, 0.87, …] │ ← 上千个浮点数
│ 13 │ 1           │ "留存率 = 次日回访/…"    │ {业务线:电商} │ [0.11, 0.05, -0.42, …]  │
└────┴─────────────┴────────────────────────┴───────────────┴─────────────────────────┘
                                                              ↑
                                             在这一列上建"向量索引"，
                                             实现"从百万行里按语义找相似"（毫秒级）
```

看懂这张表，就看懂了 RAG 知识库 90% 的形态：

- **`content`**：一小段原文（chunk / 片段）。知识库不是整篇存，是**切碎了存**。
- **`embedding`**：这段原文的"语义指纹"，一串几百到几千维的浮点数。**意思相近的文本，向量在空间里也相近**——这是"按意思检索"成立的根基。
- **`metadata`**：业务线、文档类型、更新时间、权限……用来**过滤**（如"只在电商业务线里搜"）。
- **向量索引**：让"百万行里找最相似的 10 条"从几秒变成几毫秒。

> **一句话记住形态**：RAG 知识库 = 切碎的原文 + 每段的语义向量 + 可过滤的元数据 + 一个让检索变快的向量索引。

---

## 四、心智模型二：7 个部件 + 两条流水线

### 4.1 组成部件

知识库不是孤立的表，它嵌在一条链路里：

```
   [1]文档源 → [2]解析清洗 → [3]切分 → [4]Embedding → [5]向量库（那张表）
                                                              │
   用户提问 → [4]Embedding → [6]检索 → [7]Rerank → 拼进Prompt → 大模型 → 带引用的答案
```

| 部件 | 干什么 | 常见选型 |
|---|---|---|
| ① 文档源 | 原始知识来源 | PDF / Word / Markdown / 网页 / 数据库 |
| ② 解析清洗 | 各种格式抽成纯文本 | pypdf、python-docx、OCR（扫描件） |
| ③ 切分 Chunking | 长文切成小片段 | 按标题/段落切，别死板按字数 |
| ④ Embedding 模型 | 文本 → 语义向量 | BGE-M3（中文强/开源）、text-embedding-3、voyage-3 |
| ⑤ 向量库 | 存向量+原文+元数据，支持相似检索 | pgvector、Milvus、Qdrant、Weaviate |
| ⑥ 检索器 | 按问题捞相关片段 | 向量检索 + 关键词(BM25) 混合 |
| ⑦ Rerank | 对捞回的片段精排 | bge-reranker、cohere-rerank |

> ③④⑥⑦ 每个部件的细节在 [retrieval-basics.md](retrieval-basics.md) 里逐一讲透。记住这张部件图，那些细节文档你就知道各自在讲哪一环。

### 4.2 两条流水线（理解 RAG 的关键）

RAG 有**两条独立流水线**，很多人卡住就是因为把它们混在一起想：

```
━━━ 离线流水线（建库）——文档进来时跑一次，或定期重跑 ━━━
   文档 → 解析 → 切分 → Embedding → 写入向量库
   特点：慢没关系、可批量、可重跑。知识库的"质量上限"在这条线上就定了。

━━━ 在线流水线（问答）——用户每问一次跑一次 ━━━
   问题 → Embedding → 向量检索 top-20 → Rerank top-5 → 拼Prompt(带来源) → 大模型 → 答案+引用
   特点：要快（用户在等）、要准、要能追溯来源。
```

两条线**共用同一个 Embedding 模型**（这点必须一致，否则问题向量和文档向量不在同一空间，检索全废）。

- **离线**决定"书架上有没有这本书、书切得好不好翻"。
- **在线**决定"翻书翻得准不准、答得有没有依据"。

---

## 五、如何部署：三个档位，按需上车

部署不是一步到位，按知识库规模分三档：

| 档位 | 适用场景 | 向量存储 | 部署形态 | 上手成本 |
|---|---|---|---|---|
| **Demo 级** | 个人验证 / < 1 万片段 | Chroma / FAISS（本地文件） | 一个 Python 脚本 | 半天 |
| **团队级** | 部门知识库 / 1–50 万片段 | **PostgreSQL + pgvector** | Docker Compose + FastAPI | 1–2 天 |
| **生产级** | 公司级 / 百万级+ | Milvus / Qdrant 集群 | K8s + 独立向量库 + 网关 | 1–2 周 |

**推荐路线（团队级，工作区已有完整可跑方案）**：

```
Docker Compose
  ├─ PostgreSQL 16 + pgvector      ← 向量+元数据一张库搞定，中小库最省心
  ├─ FastAPI                        ← 提供 /documents/upload 和 /query 两个接口
  └─ 接公司统一 LLM/Embedding 网关   ← 不自己养 GPU
+ Nginx + HTTPS + 每日 pg_dump 备份
```

逐行可复制的搭建步骤（建表 SQL、docker-compose、上传/问答接口、生产配置、排错）见
👉 [../../ai-infra/methods/rag/Linux_RAG知识库搭建指南.md](../../ai-infra/methods/rag/Linux_RAG知识库搭建指南.md)

几个部署关键决策：

- **要不要自己部署模型**：能接公司网关就接，普通 CPU 服务器即可；自建本地模型才需要 GPU。
- **中小库首选 pgvector 而非专用向量库**：向量和业务元数据在同一个 Postgres，能用 SQL 直接做"向量检索 + 元数据过滤 + 权限"的联合查询，少维护一个组件。规模到百万级、延迟扛不住了再迁 Milvus/Qdrant。**别一上来就上重型武器。**
- **向量维度必须对齐**：建表 `vector(3072)` 的维度要等于 Embedding 模型输出维度，不一致直接报错（最高频的坑）。

> ⚠️ **安全提醒**：知识库接口默认要加鉴权，**上传接口尤其不能裸奔**，否则任何人都能往库里塞脏数据或删库。生产务必走 HTTPS + 鉴权 + 权限隔离。

---

## 六、如何设计：设计 = 一条决策链，不是选组件

新手以为"设计 RAG"是选向量库，其实真正的设计是**沿数据流做一串取舍**。照这条链走一遍，方案就出来了：

```
① 文档长什么样？
   结构化(有标题)→按标题切  有表格/代码→独立成块/按函数切  扫描件→先上OCR否则抽出来是空的
        ↓
② 切多大？（chunk_size / overlap）
   FAQ:300-500  产品文档:600-900  技术规范:800-1200  法务制度:1000-1500
   overlap 约取 chunk 的 15%，防止把一句话切两半
        ↓
③ 用哪个 Embedding？
   中文为主→BGE-M3(开源免费/中文强)   英文多语→voyage-3 / text-embedding-3
   ★ 别默认 OpenAI，中文场景 BGE 常更好还免费
        ↓
④ 怎么检索？
   几乎必做"混合检索"：向量(抓语义) + BM25(抓型号/错误码/字段名)，两路用 RRF 合并
        ↓
⑤ 要不要 Rerank？
   生产几乎必加：召回 top-20 → reranker 精排 → 取 top-5
   ★ 性价比最高的一次质量提升，相关性提升 20-40%
        ↓
⑥ 怎么拼 Prompt？
   每段带来源标注[1][2]要求引用 / 最重要片段放开头或结尾(模型对中段记忆差) / 明确"不足就说不知道"
        ↓
⑦ 怎么评测？
   建 50-200 条黄金问答集，持续测 Recall@K / 忠实度 / 答案相关性
   ★ 没有评测集的 RAG 无法迭代——最容易被跳过、又最重要
```

**几条反直觉但重要的设计原则**：

1. **分块是被严重低估的环节**——切得不好，再强的 Embedding 也救不回来。好的结构化分块常比换更贵的模型收益大。
2. **别一上来就上 GraphRAG / Self-RAG**——先把"结构化分块 + 混合检索 + Rerank"这套基本功做扎实，80% 场景就够。详见 [advanced-rag.md](advanced-rag.md) 第十节的反直觉发现。
3. **Long context 不替代 RAG，但能简化 RAG**——中等知识库可以"直接全塞"，成本和延迟仍是约束，两者是互补不是替代。

---

## 七、最常见的六个陷阱（先记住，后细学）

放在导读，因为新做 RAG 的团队 80% 在这里栽。详见 [retrieval-basics.md](retrieval-basics.md) 与 [advanced-rag.md](advanced-rag.md)。

1. **分块切坏了**：按固定字数硬切，切到句子/表格中间 → 召回片段缺上下文，模型答不出。解法：按文档结构切。
2. **只做向量检索，漏掉精确关键词**：型号 `ABC-123`、错误码、字段名向量搜常错过。解法：加 BM25 做混合检索。
3. **不加 Rerank 就上线**：向量召回的 top-K 未必按真正相关度排序。解法：加 cross-encoder reranker，性价比最高。
4. **答案胡编（幻觉）**：召回为空还硬答。解法：system 明确"只能基于上下文答，不足就说不知道" + 降 temperature + 返回引用。
5. **没有评测集**：凭感觉调参，改一版好一版坏说不清。解法：先建黄金问答集，改一版测一版。
6. **Embedding 前后不一致 / 维度不匹配**：建库和查询用了不同模型，或维度对不上。解法：两端锁定同一模型，建表维度对齐。

---

## 八、推荐学习顺序

### 入门（半天建立全局观）
1. **本篇 OVERVIEW** — 建立"一张表 + 两条流水线"的心智模型
2. [retrieval-basics.md](retrieval-basics.md) — 分块、向量化、混合检索、rerank、评测的"骨架"

### 动手（跑通一遍才算会）
3. [../../ai-infra/methods/rag/Linux_RAG知识库搭建指南.md](../../ai-infra/methods/rag/Linux_RAG知识库搭建指南.md) — Docker + pgvector + FastAPI，`docker compose up` 起一套，上传 10 篇文档问答测试

### 进阶（朴素 RAG 在你场景吃瘪时）
4. [advanced-rag.md](advanced-rag.md) — Self-RAG / CRAG / GraphRAG / Adaptive RAG 的机制与取舍
5. [agentic-rag-implementation.md](agentic-rag-implementation.md) — 把 RAG 当工具套进 Agent，用 LangGraph 写出可跑代码

> **最小行动路径**：拿 10 篇手边文档 → 按部署指南起一套 → 问几个你知道答案的问题 → 看 sources 准不准 → 不准就回去调 chunk/加 rerank → 攒 20 条黄金集固化"改一版测一版"的习惯。跑通这一遍，前面所有概念都会从"看过"变成"会了"。

---

## 九、配套工具与生态速览

| 环节 | 工具 / 选型 |
|---|---|
| 文档解析 | pypdf、python-docx、beautifulsoup4、Unstructured；扫描件加 PaddleOCR / Tesseract |
| 分块 | LangChain `RecursiveCharacterTextSplitter`、LlamaIndex `SentenceSplitter` |
| Embedding | BGE-M3（开源/中文强）、text-embedding-3、voyage-3、GTE-Qwen2 |
| 向量库 | pgvector（中小库首选）、Milvus、Qdrant、Weaviate、Chroma/FAISS（Demo） |
| 混合检索 | Elasticsearch / OpenSearch、向量库原生 hybrid、RRF 合并 |
| Rerank | bge-reranker-v2-m3、jina-reranker、cohere-rerank |
| 编排框架 | LangChain、LlamaIndex、LangGraph |
| 评测 | RAGAS、TruLens（Recall@K / Faithfulness / Answer Relevance） |

---

## 十、和本工作区其他模块的关联

- **服务器部署纵深** → [../../ai-infra/methods/rag/Linux_RAG知识库搭建指南.md](../../ai-infra/methods/rag/Linux_RAG知识库搭建指南.md)、[../../ai-infra/OVERVIEW.md](../../ai-infra/OVERVIEW.md)（成本/延迟/效果三角）
- **把 RAG 当 Agent 记忆** → [../agents/memory-systems.md](../agents/memory-systems.md)（长期记忆的向量方案与 RAG 同源）
- **父级导读与阅读地图** → [../OVERVIEW.md](../OVERVIEW.md)、[../READING-MAP.md](../READING-MAP.md)（RAG 在整个 Agent+LLM 体系里的位置）
- **数值型问答走这条，不走 RAG** → [../../数据资产/](../../数据资产/)（nl-sql 的 SQL 模板库、指标口径字典）
- **RAG 产品效果上线验证** → [../../ab-testing/](../../ab-testing/)（离线评测之后回到在线 AB）
- **AI 产品设计方法** → [../../product/](../../product/)

---

## 十一、心法 + Checklist

如果只能记三句：

1. **知识库的本体就是一张"切碎原文 + 语义向量 + 元数据"的表**——先在脑子里"看见"它，其余都是细节。
2. **分块 + 混合检索 + Rerank 这套基本功，打赢 80% 的花哨范式**——先做扎实再谈进阶。
3. **没有评测集的 RAG 无法迭代**——先建 50 条黄金集，再谈优化。

下次设计 / 排查 RAG 前，回答这 10 个问题：

```
□ 1. 分块策略匹配文档结构吗？（不是死板按字数）
□ 2. Embedding 模型在我的场景（中文/长文/领域）上对比评测过吗？
□ 3. 用了 Hybrid（向量 + 关键词）吗？
□ 4. 加了 Reranker 吗？
□ 5. Prompt 里有 citation（引用来源）格式吗？
□ 6. system 里写了"上下文不足就说不知道"吗？
□ 7. 评测黄金集有多少条？多久重跑一次？
□ 8. 在线有"召回为空 / 用户点踩"监控吗？
□ 9. 知识更新频率和索引重建频率匹配吗？
□ 10. 上传/查询接口有鉴权吗？维度对齐了吗？
```

回答不出其中任何一个，先回 [retrieval-basics.md](retrieval-basics.md) 补课。
