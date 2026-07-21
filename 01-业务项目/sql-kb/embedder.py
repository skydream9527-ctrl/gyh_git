"""BGE 中文向量模型的加载与编码（惰性单例，build 与检索共用）。

首次调用 get_model() 时才加载模型，并触发首次下载（约 1.3GB）。
"""
from __future__ import annotations

import config

_model = None


def get_model():
    """惰性加载 SentenceTransformer 模型。"""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        print(f"[embedder] 加载模型 {config.EMBED_MODEL} …（首次会下载约 1.3GB）")
        _model = SentenceTransformer(config.EMBED_MODEL)
    return _model


def embed_documents(texts: list[str]) -> list[list[float]]:
    """文档侧编码：不加指令前缀，归一化（配合余弦相似度）。"""
    model = get_model()
    embs = model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=len(texts) > 50,
    )
    return [e.tolist() for e in embs]


def embed_query(text: str) -> list[float]:
    """查询侧编码：bge-zh 建议加指令前缀以提升检索效果。"""
    model = get_model()
    emb = model.encode(
        config.QUERY_INSTRUCTION + text,
        normalize_embeddings=True,
    )
    return emb.tolist()
