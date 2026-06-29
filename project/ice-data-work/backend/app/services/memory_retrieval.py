"""记忆检索：带访问边界的 top-k（材料三 §4.5）。

原则：先过滤（访问边界）再排序（相关性），从源头杜绝越权注入（TDR-3）。
v1：关键词命中打分（中英文分词近似：字符 bigram + 词项）。
v1.5：pgvector 语义检索（IDW_PGVECTOR_ENABLED 开启且可连时启用；否则降级关键词）。
"""
from __future__ import annotations

import re

from app.core.config import get_settings


def retrieve(entries: list[dict], query: str, *, k: int = 5) -> list[dict]:
    """从候选条目中检索与 query 最相关的 top-k。

    entries: memory_svc.read_memory_entries 的输出（已是访问边界内的条目）。
    返回按相关性降序的至多 k 条；query 为空时返回前 k 条（保序）。
    """
    if not entries:
        return []
    # 条目很少时全部注入（无需过滤；符合小记忆全量、pinned 全量的语义）
    if len(entries) <= k:
        return entries
    if not query.strip():
        return entries[:k]

    if _pgvector_ready():
        try:
            return _retrieve_pgvector(entries, query, k)
        except Exception:
            pass  # 降级关键词

    return _retrieve_keyword(entries, query, k)


def _retrieve_keyword(entries: list[dict], query: str, k: int) -> list[dict]:
    q_terms = _tokenize(query)
    if not q_terms:
        return entries[:k]
    scored: list[tuple[float, int, dict]] = []
    for i, e in enumerate(entries):
        text = e.get("content", "") + " " + " ".join(e.get("tags", []))
        e_terms = _tokenize(text)
        score = _overlap_score(q_terms, e_terms)
        # confidence 加权
        if e.get("confidence") == "high":
            score *= 1.2
        if score > 0:
            scored.append((score, i, e))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [e for _, _, e in scored[:k]]


def _retrieve_pgvector(entries: list[dict], query: str, k: int) -> list[dict]:
    """pgvector 语义检索（占位：嵌入 + cosine top-k）。

    真实实现：embed(query) → 在 pgvector 中按条目 mem_id 过滤后 ORDER BY 距离。
    当前未接入嵌入端点，抛异常触发降级。
    """
    raise NotImplementedError("pgvector retrieval not wired yet; degrade to keyword")


def _pgvector_ready() -> bool:
    return get_settings().pgvector_enabled and bool(get_settings().database_url)


def _tokenize(text: str) -> set[str]:
    """中英混合粗分词：英文按词，中文按 bigram。"""
    text = text.lower()
    terms: set[str] = set()
    # 英文/数字词
    for w in re.findall(r"[a-z0-9_]+", text):
        if len(w) >= 2:
            terms.add(w)
    # 中文 bigram
    han = re.findall(r"[\u4e00-\u9fff]", text)
    for i in range(len(han) - 1):
        terms.add(han[i] + han[i + 1])
    # 单字中文也保留（短查询兜底）
    terms.update(han)
    return terms


def _overlap_score(q: set[str], e: set[str]) -> float:
    if not q or not e:
        return 0.0
    inter = q & e
    if not inter:
        return 0.0
    return len(inter) / (len(q) ** 0.5)
