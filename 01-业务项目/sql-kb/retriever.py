"""混合检索：向量（Chroma）+ 关键词（BM25）→ RRF 融合 → top-K。

这是给下游 agent 用的稳定接口层：
  from retriever import retrieve, build_fewshot_prompt
  results = retrieve("按城市统计新增用户", k=5)
  prompt  = build_fewshot_prompt("按城市统计新增用户", results)  # 喂给 LLM 生成 SQL 草稿

本模块只做「检索」，不调用 LLM——SQL 生成交给下游 agent。
"""
from __future__ import annotations

import json
import re

import config
import embedder
from schema import Requirement


def _tokenize(text: str) -> list[str]:
    """轻量分词：英文标识符（表名/字段）整体保留，中文按单字。"""
    return re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*|\d+|[\u4e00-\u9fff]", text.lower())


def _rrf(rank_lists: list[list[str]], k: int) -> list[str]:
    """Reciprocal Rank Fusion：多路排名各取 1/(k+rank) 求和后重排。"""
    scores: dict[str, float] = {}
    for lst in rank_lists:
        for rank, rid in enumerate(lst):
            scores[rid] = scores.get(rid, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores, key=lambda x: scores[x], reverse=True)


class Retriever:
    def __init__(self) -> None:
        import chromadb
        from rank_bm25 import BM25Okapi

        # 记录以 jsonl 为准（含完整 SQL 等载荷）
        self.records: dict[str, Requirement] = {}
        self.order: list[str] = []
        with open(config.JSONL_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                r = Requirement.from_dict(json.loads(line))
                self.records[r.id] = r
                self.order.append(r.id)

        # dense：连接已建好的 Chroma（集合不存在 = 还没建索引）
        client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))
        try:
            self.collection = client.get_collection(config.COLLECTION_NAME)
        except Exception as e:
            raise RuntimeError(
                f"未找到向量库集合 '{config.COLLECTION_NAME}'，请先运行 build_index.py 建立索引。"
                f"（原始错误：{e}）"
            ) from e

        # 一致性检查：jsonl 与 Chroma 必须同步重建，否则检索会错位
        n_jsonl, n_chroma = len(self.order), self.collection.count()
        if n_jsonl != n_chroma:
            import warnings

            warnings.warn(
                f"记录数不一致：requirements.jsonl={n_jsonl} 条，Chroma={n_chroma} 条；"
                f"很可能改了 jsonl 但没重跑 build_index.py，请重新运行 build_index.py。",
                stacklevel=2,
            )

        # sparse：内存重建 BM25（几百条零成本）
        corpus = [_tokenize(self.records[i].bm25_text()) for i in self.order]
        self.bm25 = BM25Okapi(corpus)

    def _dense_ids(self, query: str, n: int, allowed: set[str] | None) -> list[str]:
        q_emb = embedder.embed_query(query)
        # 有过滤时多召回一些，之后按 allowed 过滤
        n_query = len(self.order) if allowed is not None else n
        n_query = min(max(n_query, n), len(self.order))
        res = self.collection.query(query_embeddings=[q_emb], n_results=n_query)
        ids = res["ids"][0] if res.get("ids") else []
        if allowed is not None:
            ids = [i for i in ids if i in allowed]
        return ids[:n]

    def _sparse_ids(self, query: str, n: int, allowed: set[str] | None) -> list[str]:
        scores = self.bm25.get_scores(_tokenize(query))
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        ids: list[str] = []
        for i in ranked:
            if scores[i] <= 0:
                break
            rid = self.order[i]
            if allowed is not None and rid not in allowed:
                continue
            ids.append(rid)
            if len(ids) >= n:
                break
        return ids

    def retrieve(self, query: str, k: int | None = None, filters: dict | None = None) -> list[dict]:
        """返回 top-K 相似历史需求（含完整 SQL），按融合相关度倒序。

        filters 形如 {"biz_line": "增长"}，按记录字段等值过滤。
        """
        k = k or config.TOP_K
        n = config.RECALL_N

        allowed: set[str] | None = None
        if filters:
            allowed = {
                rid
                for rid, r in self.records.items()
                if all(str(getattr(r, kk, "")) == str(vv) for kk, vv in filters.items())
            }
            if not allowed:
                return []

        dense = self._dense_ids(query, n, allowed)
        sparse = self._sparse_ids(query, n, allowed)
        fused = _rrf([dense, sparse], config.RRF_K)[:k]
        return [self.records[rid].to_dict() for rid in fused if rid in self.records]


# ---- 模块级便捷接口（惰性单例，下游 import 即用）----
_default: Retriever | None = None


def get_retriever() -> Retriever:
    global _default
    if _default is None:
        _default = Retriever()
    return _default


def retrieve(query: str, k: int | None = None, filters: dict | None = None) -> list[dict]:
    return get_retriever().retrieve(query, k=k, filters=filters)


def build_fewshot_prompt(query: str, results: list[dict]) -> str:
    """把检索结果拼成可直接喂给下游 LLM 的 few-shot prompt。"""
    blocks = []
    for i, r in enumerate(results, 1):
        blocks.append(
            f"[参考{i}] 需求：{r['title']}\n"
            f"描述：{r['desc']}\n"
            f"SQL：\n{r['sql']}"
        )
    refs = "\n\n".join(blocks) if blocks else "（无历史参考）"
    return (
        "你是数据分析 SQL 助手。下面是历史上与当前需求最相似的需求及其 SQL，"
        "请参考它们的表名、字段和写法，为新需求生成 SQL 草稿；"
        "拿不准的表名 / 字段请显式标注 TODO 供人工确认。\n\n"
        f"{refs}\n\n"
        f"【新需求】{query}\n"
        "【SQL 草稿】"
    )
