"""建立索引：读 requirements.jsonl → BGE 向量化 → 存入 Chroma。

BM25（关键词）不在这里建——它在检索时从 jsonl 内存重建（几百条零成本），
所以本脚本只负责 dense 向量。几百条全量重建只需几分钟。

用法：
  python build_index.py                # 用 config.JSONL_PATH
  python build_index.py my.jsonl
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import config
import embedder
from schema import Requirement


def load_records(jsonl_path: Path) -> list[Requirement]:
    records: list[Requirement] = []
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(Requirement.from_dict(json.loads(line)))
    return records


def _dedup(records: list[Requirement]) -> list[Requirement]:
    seen: set[str] = set()
    uniq: list[Requirement] = []
    dups: set[str] = set()
    for r in records:
        if r.id in seen:
            dups.add(r.id)
            continue
        seen.add(r.id)
        uniq.append(r)
    if dups:
        print(f"[warn] 存在重复 id，仅保留首次出现：{sorted(dups)}", file=sys.stderr)
    return uniq


def build(jsonl_path: str | Path | None = None) -> int:
    import chromadb

    jsonl_path = Path(jsonl_path or config.JSONL_PATH)
    if not jsonl_path.exists():
        print(f"找不到 {jsonl_path}，请先运行 parse.py 生成。", file=sys.stderr)
        return 0

    records = _dedup(load_records(jsonl_path))
    if not records:
        print("没有可索引的记录。", file=sys.stderr)
        return 0

    texts = [r.to_embedding_text() for r in records]
    print(f"向量化 {len(records)} 条需求 …")
    embeddings = embedder.embed_documents(texts)

    client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))
    # 全量重建：先删旧 collection，避免已删除的记录残留
    try:
        client.delete_collection(config.COLLECTION_NAME)
    except Exception:
        pass
    collection = client.create_collection(
        config.COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
    )
    collection.add(
        ids=[r.id for r in records],
        embeddings=embeddings,
        metadatas=[r.to_chroma_metadata() for r in records],
        documents=texts,
    )
    print(f"索引完成：{collection.count()} 条 → {config.CHROMA_DIR}")
    return collection.count()


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else None)
