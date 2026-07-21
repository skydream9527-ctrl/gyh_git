# sql-kb — 历史需求 SQL 检索库（本地）

把历史 N 个「需求描述 + SQL」沉淀成本地可检索的知识库：**输入一个新需求描述，检索出历史上最相似的几个需求和它们当时写的 SQL**，供复用参考。

- ✅ **做**：语义 + 关键词混合检索，返回 top-K 相似需求（含完整 SQL、表名、相似度）
- ❌ **不做**：不生成 SQL（交给下游 agent 用检索结果做 few-shot）、不连库执行 SQL

纯本地、免 Docker、几百条量级、CPU 可跑。

---

## 目录结构

```
sql-kb/
├── data/
│   └── sample_需求文档.md   # 示例文档（展示默认解析格式）
├── config.py                # 模型、路径、检索参数（改这里）
├── schema.py                # 一条需求记录的结构
├── embedder.py              # BGE 中文向量模型加载/编码
├── parse.py                 # ★ 长文档 → requirements.jsonl（依赖你的格式）
├── build_index.py           # requirements.jsonl → Chroma 向量库
├── retriever.py             # 混合检索 + RRF + few-shot（给下游 agent 的接口）
├── search.py                # 命令行检索入口
├── requirements.jsonl       # 解析后的标准记录（可人工核对/手改）
└── chroma_db/               # 向量库持久化（build 后自动生成）
```

---

## 快速开始

```bash
# 1. 装依赖（首次 build 会自动下载 bge-large-zh-v1.5，约 1.3GB）
pip install -r requirements.txt

# 2. 把你的历史需求文档放到 data/ 下（先用示例跑通）
#    真实文档格式若与示例不同，改 parse.py（见下节）

# 3. 解析成标准记录，并核对拆分是否正确
python parse.py data/你的需求文档.md      # 不带参数则解析示例文档
#    → 打开 requirements.jsonl 检查每条 title/desc/sql/tables 对不对

# 4. 建向量索引
python build_index.py

# 5. 检索
python search.py "按城市统计每日新增用户"
```

---

## 数据格式与 parse（唯一需要按你文档定制的地方）

`parse.py` 默认识别的格式（见 `data/sample_需求文档.md`）：

- 每个二级标题 `## xxx` = 一个需求，标题即 `title`（自动去掉 “需求：” 前缀）
- 节内 ```` ```sql ... ``` ```` 代码块 = `sql`
- `- 业务线：xxx` / `- 日期：xxx` / `- 需求方：xxx` / `- ID：xxx` = 元信息
- 其余正文 = `desc`
- `tables` 从 SQL 自动正则抽取，**无需手标**

> 如果你的真实文档是 Excel、或用别的分隔符组织，**只需改 `parse.py` 的 `parse_markdown()`**，
> 后面的 build / 检索链路完全不用动——它们只认标准的 `requirements.jsonl`。
>
> 也可以完全跳过 parse，直接手写/导出 `requirements.jsonl`（一行一条 JSON，字段见 `schema.py`）。

---

## 检索用法（CLI）

```bash
python search.py "短剧留存怎么算"              # 友好输出
python search.py "短剧留存" --k 3              # 只要 3 条
python search.py "圈选push人群" --biz-line 增长 # 按业务线过滤
python search.py "按城市统计新增" --json        # 输出 JSON（供程序消费）
python search.py "按城市统计新增" --fewshot     # 输出可直接喂给 LLM 的 prompt
```

---

## 给下游 agent 用（生成 SQL 草稿）

本库只到「检索」为止，SQL 生成由你的 agent 完成。两个接口：

```python
from retriever import retrieve, build_fewshot_prompt

query = "统计每个城市近 30 天新增用户，按渠道分"
hits = retrieve(query, k=5)                 # -> [{id,title,desc,sql,tables,biz_line,date,author}, ...]
prompt = build_fewshot_prompt(query, hits)  # 把 top-K 拼成 few-shot，喂给 LLM 生成草稿
# answer = your_llm(prompt)
```

三种接入方式，按需选：

| 方式 | 怎么用 | 适合 |
|------|--------|------|
| Python import | `from retriever import retrieve` | agent 与本库同进程 |
| CLI | `python search.py "..." --json` | agent 用 shell 调、跨语言 |
| 封装 MCP tool / skill | 把 `retrieve` 包成工具 | 接入你工作区的 nl-sql / 数据分析 agent |

这样下游生成的 SQL 天然带**你团队真实的表名和写法**，比模型空想准得多——本质是给 nl-sql 加了一层检索增强。

---

## 配置（config.py）

| 项 | 默认 | 说明 |
|----|------|------|
| `EMBED_MODEL` | `BAAI/bge-large-zh-v1.5` | 中文向量模型；有公司 embedding 网关可改用 API |
| `TOP_K` | 5 | 最终返回条数 |
| `RECALL_N` | 20 | 向量/BM25 每路各召回条数 |
| `RRF_K` | 60 | RRF 融合常数 |

---

## 日常维护

新增需求后：把新条目追加进原文档（或 `requirements.jsonl`）→ 重跑 `python parse.py` + `python build_index.py`。几百条全量重建只需几分钟。

---

## 设计要点（为什么这么做）

1. **按需求条目切，不按字数切**：一个需求（描述+SQL）是一个完整语义单元，SQL 绝不能被切开。
2. **向量只嵌「标题+描述」，不嵌 SQL**：SQL 的 `SELECT/FROM/WHERE` 关键词会污染语义，让相似度失真。SQL 作为载荷存着，命中后返回。
3. **混合检索（向量 + BM25）**：向量抓语义（“新增用户”≈“注册用户”），BM25 抓精确词（表名 `dwd_user_xxx`、字段、错误码）。用 RRF 融合，无需调权重。
4. **纯检索、不生成**：复用历史 SQL，检索出来让人/agent 改，比 LLM 现编可靠；生成解耦到下游。

---

## 与工作区数据资产层的关系

本库是 [`00-知识库/数据资产/SQL模板库`](../00-知识库/数据资产/SQL模板库/) 的**上游原始层**：

- 本库 = 全量历史需求，未提炼，用于「找相似、快速复用」
- SQL模板库 = 人工精选、参数化、已验证的模板，喂给 nl-sql

用法闭环：从本库检索高频相似需求 → 提炼成参数化模板 → 沉淀进 SQL模板库。


## 原理讲解

想搞懂这个库背后的 RAG 原理（用了什么模型、怎么切分/向量化/检索、业界还有哪些优化方案），
见知识库文档：[RAG 原理与实现 — 以 SQL 需求库为例](../00-知识库/agent-llm/rag/RAG原理与实现-以SQL需求库为例.md)。

- 本 README 讲 **怎么用**
- 上面那篇讲 **为什么这么设计、背后的原理**
