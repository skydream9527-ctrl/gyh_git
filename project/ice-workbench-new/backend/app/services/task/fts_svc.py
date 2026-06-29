"""Full-Text Search service — FTS5-backed content search across conversations and files.

Provides search over:
- Conversation messages (user + assistant text)
- Task output files (text/markdown/csv content)

The FTS index is a **derived cache** (G3 compliant) — it can be rebuilt from
the filesystem at any time. It lives alongside the main index.db.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from ...core.storage import get_index_db

log = logging.getLogger("fts")

# ─── Schema ───────────────────────────────────────────────────────────────────

FTS_SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS content_fts USING fts5(
    content,
    task_id UNINDEXED,
    conversation_id UNINDEXED,
    message_id UNINDEXED,
    role UNINDEXED,
    source_type UNINDEXED,
    file_name UNINDEXED,
    created_at UNINDEXED,
    tokenize='unicode61'
);
"""


# ─── Init ─────────────────────────────────────────────────────────────────────


async def ensure_fts_table() -> None:
    """Create the FTS5 table if it doesn't exist."""
    db = get_index_db()
    await db.executescript(FTS_SCHEMA)


# ─── Indexing ─────────────────────────────────────────────────────────────────


async def index_message(
    *,
    task_id: str,
    conversation_id: str,
    message_id: str,
    role: str,
    content: str,
    created_at: str | None = None,
) -> None:
    """Index a single conversation message into FTS."""
    if not content or len(content.strip()) < 5:
        return
    db = get_index_db()
    # Truncate very long messages to keep index reasonable
    text = content[:5000]
    await db.execute(
        "INSERT OR IGNORE INTO content_fts (content, task_id, conversation_id, message_id, role, source_type, file_name, created_at) "
        "VALUES (?, ?, ?, ?, ?, 'message', NULL, ?)",
        [text, task_id, conversation_id, message_id, role, created_at],
    )


async def index_file(
    *,
    task_id: str,
    file_name: str,
    content: str,
    file_id: str | None = None,
    created_at: str | None = None,
) -> None:
    """Index a task output file into FTS."""
    if not content or len(content.strip()) < 10:
        return
    db = get_index_db()
    text = content[:10000]
    await db.execute(
        "INSERT OR IGNORE INTO content_fts (content, task_id, conversation_id, message_id, role, source_type, file_name, created_at) "
        "VALUES (?, ?, NULL, ?, NULL, 'file', ?, ?)",
        [text, task_id, file_id, file_name, created_at],
    )


async def index_task_conversations(task_id: str) -> int:
    """Re-index all conversations for a given task. Returns count indexed."""
    from ...core.storage import get_paths, read_jsonl

    paths = get_paths()
    conv_dir = paths.task_dir(task_id) / "conversations"
    if not conv_dir.exists():
        return 0

    count = 0
    for jsonl_file in conv_dir.glob("*.jsonl"):
        conv_id = jsonl_file.stem
        for record in read_jsonl(jsonl_file):
            content = record.get("content") or ""
            msg_id = record.get("id") or ""
            role = record.get("role") or ""
            created_at = record.get("created_at")
            if content and len(content) >= 5:
                await index_message(
                    task_id=task_id,
                    conversation_id=conv_id,
                    message_id=msg_id,
                    role=role,
                    content=content,
                    created_at=created_at,
                )
                count += 1
    return count


async def index_task_files(task_id: str) -> int:
    """Index text output files for a task. Returns count indexed."""
    from ...core.storage import get_paths

    paths = get_paths()
    output_dir = paths.task_files_output(task_id)
    if not output_dir.exists():
        return 0

    TEXT_EXTS = {".md", ".txt", ".csv", ".sql", ".json", ".html", ".log"}
    count = 0
    for f in output_dir.rglob("*"):
        if not f.is_file() or f.suffix.lower() not in TEXT_EXTS:
            continue
        if f.stat().st_size > 500_000:  # Skip files > 500KB
            continue
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
            await index_file(
                task_id=task_id,
                file_name=f.name,
                content=content,
                file_id=f.stem,
            )
            count += 1
        except Exception:
            continue
    return count


async def rebuild_all() -> dict:
    """Rebuild the entire FTS index from filesystem. Admin operation."""
    from ...core.storage import get_paths

    db = get_index_db()
    # Drop and recreate
    await db.executescript("DROP TABLE IF EXISTS content_fts;")
    await db.executescript(FTS_SCHEMA)

    paths = get_paths()
    tasks_dir = paths.tasks
    if not tasks_dir.exists():
        return {"tasks": 0, "messages": 0, "files": 0}

    task_count = 0
    msg_count = 0
    file_count = 0

    for task_dir in tasks_dir.iterdir():
        if not task_dir.is_dir() or task_dir.name.startswith("."):
            continue
        task_id = task_dir.name
        try:
            mc = await index_task_conversations(task_id)
            fc = await index_task_files(task_id)
            msg_count += mc
            file_count += fc
            task_count += 1
        except Exception as exc:
            log.warning("FTS rebuild skip task %s: %s", task_id, exc)
            continue

    return {"tasks": task_count, "messages": msg_count, "files": file_count}


# ─── Search ───────────────────────────────────────────────────────────────────


async def search(
    query: str,
    *,
    task_id: str | None = None,
    source_type: str | None = None,
    limit: int = 30,
) -> list[dict]:
    """Full-text search across indexed content.

    Args:
        query: the search query (supports FTS5 match syntax)
        task_id: optional filter to search within a specific task
        source_type: 'message' or 'file' filter
        limit: max results

    Returns:
        List of dicts with: content (snippet), task_id, conversation_id,
        message_id, role, source_type, file_name, created_at, rank
    """
    db = get_index_db()

    # Build FTS5 MATCH query — escape user input for safety
    safe_query = query.replace('"', '""')
    where_parts = ['content_fts MATCH ?']
    params: list[Any] = [f'"{safe_query}"']

    if task_id:
        where_parts.append("task_id = ?")
        params.append(task_id)
    if source_type:
        where_parts.append("source_type = ?")
        params.append(source_type)

    where_clause = " AND ".join(where_parts)
    params.append(limit)

    sql = (
        f"SELECT snippet(content_fts, 0, '<mark>', '</mark>', '…', 40) AS snippet, "
        f"task_id, conversation_id, message_id, role, source_type, file_name, created_at, "
        f"rank "
        f"FROM content_fts "
        f"WHERE {where_clause} "
        f"ORDER BY rank "
        f"LIMIT ?"
    )

    try:
        rows = await db.fetchall(sql, params)
    except Exception as exc:
        # FTS table might not exist yet
        log.warning("FTS search failed: %s", exc)
        return []

    return rows
