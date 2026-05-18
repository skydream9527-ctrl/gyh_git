"""Knowledge bases (D54-D58 / D119).

Source of truth: .cache/knowledge-bases.json (admin-only configuration).
Sync with feishu / mify happens via background scheduler or the 立即同步 button;
logs in .cache/kb_sync_logs/{kb_id}.jsonl; article snapshots in
.cache/kb_articles/{kb_id}.json (for 浏览文档 view + agent read_kb_article).

Connection strategy:
- feishu_wiki  — tries backend OAuth (FEISHU_APP_ID/SECRET) first; if those
                 are empty but the `feishu` CLI is authenticated
                 (`feishu auth status`), falls back to shelling out to the CLI.
                 Field `config.use_cli_fallback: true` forces the CLI path.
- mify_rag     — requires MIFY_DATASET_API_KEY (+ MIFY_DATASET_BASE_URL); uses
                 the dataset REST API: GET /datasets/{id}/documents.
"""
from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx

from ..core.config import get_settings
from ..core.errors import APIError, ErrorCode
from ..core.storage import append_jsonl, get_paths, read_json, read_jsonl, write_json


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _kb_config_path() -> Path:
    return get_paths().cache / "knowledge-bases.json"


def _kb_sync_log_path(kb_id: str) -> Path:
    return get_paths().cache / "kb_sync_logs" / f"{kb_id}.jsonl"


def _kb_articles_path(kb_id: str) -> Path:
    return get_paths().cache / "kb_articles" / f"{kb_id}.json"


def list_kbs() -> list[dict]:
    items = read_json(_kb_config_path(), default=[]) or []
    items.sort(key=lambda x: x.get("created_at") or "", reverse=False)
    return items


def get_kb(kb_id: str) -> dict | None:
    for k in list_kbs():
        if k["id"] == kb_id:
            return k
    return None


def create_kb(body: dict) -> dict:
    source_type = body.get("source_type")
    if source_type not in {"feishu_wiki", "mify_rag"}:
        raise APIError(400, ErrorCode.VALIDATION_ERROR, "source_type 必须为 feishu_wiki 或 mify_rag")
    rec = {
        "id": uuid.uuid4().hex,
        "name": body.get("name") or "未命名知识库",
        "description": body.get("description"),
        "source_type": source_type,
        "config": body.get("config") or {},  # space_id / dataset_id 等
        "sync_frequency": body.get("sync_frequency", "daily"),  # manual / hourly / daily / weekly
        "visibility": body.get("visibility", "all"),
        "status": "idle",
        "last_sync_at": None,
        "last_sync_summary": None,
        "doc_count": 0,
        "enabled": body.get("enabled", True),
        "created_at": _now(),
        "updated_at": _now(),
    }
    items = list_kbs()
    items.append(rec)
    write_json(_kb_config_path(), items)
    return rec


def update_kb(kb_id: str, patch: dict) -> dict:
    items = list_kbs()
    for k in items:
        if k["id"] == kb_id:
            for field in (
                "name",
                "description",
                "config",
                "sync_frequency",
                "visibility",
                "enabled",
            ):
                if field in patch:
                    k[field] = patch[field]
            k["updated_at"] = _now()
            write_json(_kb_config_path(), items)
            return k
    raise APIError(404, ErrorCode.RESOURCE_NOT_FOUND, "知识库不存在")


def delete_kb(kb_id: str) -> None:
    items = [k for k in list_kbs() if k["id"] != kb_id]
    write_json(_kb_config_path(), items)
    # Best-effort cleanup of cached snapshot.
    try:
        _kb_articles_path(kb_id).unlink(missing_ok=True)
    except OSError:
        pass


def list_sync_logs(kb_id: str, limit: int = 50) -> list[dict]:
    rows = read_jsonl(_kb_sync_log_path(kb_id))
    return rows[-limit:][::-1]


# ---------------------------------------------------------------------------
# Article snapshot — used by 浏览文档 modal + file_svc `attach kb article`
# ---------------------------------------------------------------------------


def _load_articles_snapshot(kb_id: str) -> dict:
    return read_json(_kb_articles_path(kb_id), default={"articles": [], "fetched_at": None}) or {
        "articles": [],
        "fetched_at": None,
    }


def _save_articles_snapshot(kb_id: str, articles: list[dict]) -> None:
    write_json(
        _kb_articles_path(kb_id),
        {"articles": articles, "fetched_at": _now()},
    )


def list_articles(kb_id: str, *, limit: int = 200) -> list[dict]:
    kb = get_kb(kb_id)
    if not kb:
        raise APIError(404, ErrorCode.RESOURCE_NOT_FOUND, "知识库不存在")
    snap = _load_articles_snapshot(kb_id)
    return (snap.get("articles") or [])[:limit]


async def get_article(kb_id: str, article_id: str) -> dict:
    kb = get_kb(kb_id)
    if not kb:
        raise APIError(404, ErrorCode.RESOURCE_NOT_FOUND, "知识库不存在")
    snap = _load_articles_snapshot(kb_id)
    for a in snap.get("articles") or []:
        if a.get("id") == article_id or a.get("article_id") == article_id:
            # Lazy fetch body if not cached
            if not a.get("content"):
                try:
                    a["content"] = await _fetch_article_body(kb, a)
                except APIError:
                    raise
                except Exception as e:  # noqa: BLE001
                    a["content"] = f"[获取正文失败] {e}"
            return a
    raise APIError(404, ErrorCode.RESOURCE_NOT_FOUND, "文档不存在（可能需要先同步）")


# ---------------------------------------------------------------------------
# Test connection
# ---------------------------------------------------------------------------


async def test_connection(kb_id: str) -> dict:
    s = get_settings()
    kb = get_kb(kb_id)
    if not kb:
        raise APIError(404, ErrorCode.RESOURCE_NOT_FOUND, "知识库不存在")
    if kb["source_type"] == "feishu_wiki":
        if s.feishu_enabled:
            return {"ok": True, "message": "飞书 OAuth 凭证已配置"}
        if s.feishu_cli_available:
            try:
                proc = await asyncio.create_subprocess_exec(
                    "feishu",
                    "auth",
                    "status",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                out, _err = await asyncio.wait_for(proc.communicate(), timeout=10)
                info = json.loads(out.decode("utf-8"))
                if info.get("logged_in") and not info.get("access_token_expired"):
                    return {"ok": True, "message": "飞书 CLI 已登录（OAuth 回落）"}
                return {
                    "ok": False,
                    "error_code": "FEISHU_CLI_NOT_AUTHED",
                    "message": "feishu CLI 未登录，请在服务器运行 `feishu auth login`",
                }
            except asyncio.TimeoutError:
                return {"ok": False, "error_code": "FEISHU_CLI_TIMEOUT", "message": "feishu CLI 超时"}
            except Exception as e:  # noqa: BLE001
                return {"ok": False, "error_code": "FEISHU_CLI_ERROR", "message": str(e)[:200]}
        return {
            "ok": False,
            "error_code": ErrorCode.FEISHU_NOT_CONFIGURED,
            "message": "飞书既未配置 APP_ID/SECRET，也未检测到 feishu CLI",
        }
    if kb["source_type"] == "mify_rag":
        if not s.mify_dataset_enabled:
            return {
                "ok": False,
                "error_code": "MIFY_DATASET_NOT_CONFIGURED",
                "message": "请在 .env 配置 MIFY_DATASET_API_KEY（dataset-xxx 格式）",
            }
        # Probe /datasets to verify key validity
        try:
            async with httpx.AsyncClient(timeout=15) as cli:
                r = await cli.get(
                    f"{s.MIFY_DATASET_BASE_URL.rstrip('/')}/datasets",
                    headers={"Authorization": f"Bearer {s.MIFY_DATASET_API_KEY}"},
                    params={"page": 1, "limit": 1},
                )
            if r.status_code == 200:
                return {"ok": True, "message": "Mify dataset API 连通"}
            return {
                "ok": False,
                "error_code": "MIFY_DATASET_ERROR",
                "message": f"Mify 返回 HTTP {r.status_code}: {r.text[:200]}",
            }
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error_code": "MIFY_DATASET_ERROR", "message": str(e)[:200]}
    return {"ok": False, "error_code": "UNKNOWN", "message": "未知 source_type"}


# ---------------------------------------------------------------------------
# Sync — writes articles snapshot + sync log
# ---------------------------------------------------------------------------


async def sync_kb(kb_id: str, *, trigger: str = "manual") -> dict:
    """Sync once. Append a record to .cache/kb_sync_logs/{kb}.jsonl."""
    kb = get_kb(kb_id)
    if not kb:
        raise APIError(404, ErrorCode.RESOURCE_NOT_FOUND, "知识库不存在")
    started = _now()
    log: dict = {
        "id": uuid.uuid4().hex,
        "kb_id": kb_id,
        "trigger": trigger,
        "started_at": started,
        "ended_at": None,
        "status": "running",
        "added": 0,
        "updated": 0,
        "failed": 0,
        "error": None,
    }
    articles: list[dict] = []
    try:
        if kb["source_type"] == "feishu_wiki":
            articles, res = await _sync_feishu(kb)
        elif kb["source_type"] == "mify_rag":
            articles, res = await _sync_mify(kb)
        else:
            raise APIError(400, ErrorCode.VALIDATION_ERROR, "未知 source_type")
        log.update(res)
        log["status"] = "success"
        # Merge with previous snapshot: keep existing content where possible.
        prev = _load_articles_snapshot(kb_id).get("articles") or []
        prev_by_id = {a.get("id"): a for a in prev if a.get("id")}
        for a in articles:
            if a["id"] in prev_by_id and prev_by_id[a["id"]].get("content") and not a.get("content"):
                a["content"] = prev_by_id[a["id"]]["content"]
        _save_articles_snapshot(kb_id, articles)
    except APIError as e:
        log["status"] = "failed"
        log["error"] = {"code": e.error_code, "message": e.message}
    except Exception as e:
        log["status"] = "failed"
        log["error"] = {"code": ErrorCode.KB_SYNC_FAILED, "message": str(e)[:500]}
    log["ended_at"] = _now()
    append_jsonl(_kb_sync_log_path(kb_id), log)
    # update KB last sync
    items = list_kbs()
    for k in items:
        if k["id"] == kb_id:
            k["last_sync_at"] = log["ended_at"]
            k["last_sync_summary"] = {
                "status": log["status"],
                "added": log["added"],
                "updated": log["updated"],
                "failed": log["failed"],
            }
            k["status"] = "idle"
            if log["status"] == "success":
                k["doc_count"] = len(articles)
            break
    write_json(_kb_config_path(), items)
    return log


# ---------------------------------------------------------------------------
# Feishu — backend OAuth first, then CLI fallback
# ---------------------------------------------------------------------------


async def _sync_feishu(kb: dict) -> tuple[list[dict], dict]:
    """Returns (articles, counts). Raises APIError on unrecoverable error."""
    s = get_settings()
    space_id = (kb.get("config") or {}).get("space_id")
    if not space_id:
        raise APIError(400, ErrorCode.VALIDATION_ERROR, "config.space_id 必填")
    use_cli = (kb.get("config") or {}).get("use_cli_fallback", False)

    # Path 1: backend OAuth (preferred when app credentials configured and CLI is not forced)
    if s.feishu_enabled and not use_cli:
        return await _sync_feishu_oauth(kb, space_id, s)

    # Path 2: feishu CLI fallback (user-level OAuth; CLI already authenticated)
    if s.feishu_cli_available:
        return await _sync_feishu_cli(kb, space_id)

    raise APIError(503, ErrorCode.KB_SYNC_FAILED, "飞书未配置 APP_ID/SECRET 且无可用 feishu CLI")


async def _sync_feishu_oauth(kb: dict, space_id: str, s) -> tuple[list[dict], dict]:
    async with httpx.AsyncClient(timeout=20) as cli:
        r = await cli.post(
            f"{s.FEISHU_HOST.rstrip('/')}/open-apis/auth/v3/app_access_token/internal",
            json={"app_id": s.FEISHU_APP_ID, "app_secret": s.FEISHU_APP_SECRET},
        )
        r.raise_for_status()
        token = r.json().get("app_access_token")
        if not token:
            raise APIError(502, ErrorCode.KB_SYNC_FAILED, "飞书 token 获取失败")
        items: list[dict] = []
        page_token = None
        while True:
            params = {"page_size": 50}
            if page_token:
                params["page_token"] = page_token
            nodes_resp = await cli.get(
                f"{s.FEISHU_HOST.rstrip('/')}/open-apis/wiki/v2/spaces/{space_id}/nodes",
                headers={"Authorization": f"Bearer {token}"},
                params=params,
            )
            if nodes_resp.status_code != 200:
                raise APIError(502, ErrorCode.KB_SYNC_FAILED, f"飞书 wiki 拉取失败 ({nodes_resp.status_code})")
            data = nodes_resp.json().get("data", {}) or {}
            items.extend(data.get("items", []) or [])
            if not data.get("has_more"):
                break
            page_token = data.get("page_token")
            if not page_token:
                break
    articles = [_feishu_item_to_article(it, space_id) for it in items]
    return articles, {"added": len(articles), "updated": 0, "failed": 0}


async def _sync_feishu_cli(kb: dict, space_id: str) -> tuple[list[dict], dict]:
    """Recursively walk the space via `feishu wiki nodes <space> [--parent]`."""

    async def run(*args: str) -> dict:
        proc = await asyncio.create_subprocess_exec(
            "feishu", *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        try:
            out, err = await asyncio.wait_for(proc.communicate(), timeout=30)
        except asyncio.TimeoutError:
            proc.kill()
            raise APIError(504, ErrorCode.KB_SYNC_FAILED, f"feishu CLI 超时: {' '.join(args)}")
        if proc.returncode != 0:
            msg = (err or b"").decode("utf-8", errors="replace")[:300]
            raise APIError(502, ErrorCode.KB_SYNC_FAILED, f"feishu CLI 失败: {msg}")
        try:
            return json.loads(out.decode("utf-8"))
        except json.JSONDecodeError as e:
            raise APIError(502, ErrorCode.KB_SYNC_FAILED, f"feishu CLI 返回非 JSON: {e}")

    async def walk(parent: str | None, depth: int = 0) -> list[dict]:
        if depth > 3:  # safety bound
            return []
        args = ["wiki", "nodes", space_id]
        if parent:
            args += ["--parent", parent]
        data = await run(*args)
        items = data.get("nodes") or data.get("items") or []
        out: list[dict] = list(items)
        for it in items:
            if it.get("has_child"):
                out.extend(await walk(it.get("node_token"), depth + 1))
        return out

    nodes = await walk(None)
    articles = [_feishu_item_to_article(n, space_id) for n in nodes]
    return articles, {"added": len(articles), "updated": 0, "failed": 0}


def _feishu_item_to_article(item: dict, space_id: str) -> dict:
    node_token = item.get("node_token") or item.get("nodeToken") or ""
    obj_token = item.get("obj_token") or item.get("objToken") or ""
    obj_type = item.get("obj_type") or item.get("objType") or "docx"
    return {
        "id": node_token or obj_token,
        "title": item.get("title") or "(无标题)",
        "url": f"https://mi.feishu.cn/wiki/{node_token}" if node_token else None,
        "source_type": "feishu_wiki",
        "meta": {
            "space_id": space_id,
            "node_token": node_token,
            "obj_token": obj_token,
            "obj_type": obj_type,
            "has_child": bool(item.get("has_child")),
        },
        "content": None,  # lazy-fetched on demand
    }


# ---------------------------------------------------------------------------
# Mify — dataset REST API
# ---------------------------------------------------------------------------


async def _sync_mify(kb: dict) -> tuple[list[dict], dict]:
    s = get_settings()
    if not s.mify_dataset_enabled:
        raise APIError(503, "MIFY_DATASET_NOT_CONFIGURED", "请在 .env 配置 MIFY_DATASET_API_KEY")
    dataset_id = (kb.get("config") or {}).get("dataset_id")
    if not dataset_id:
        raise APIError(400, ErrorCode.VALIDATION_ERROR, "config.dataset_id 必填")
    base = s.MIFY_DATASET_BASE_URL.rstrip("/")
    headers = {"Authorization": f"Bearer {s.MIFY_DATASET_API_KEY}"}
    articles: list[dict] = []
    async with httpx.AsyncClient(timeout=30) as cli:
        page = 1
        while True:
            r = await cli.get(
                f"{base}/datasets/{dataset_id}/documents",
                headers=headers,
                params={"page": page, "limit": 100},
            )
            if r.status_code != 200:
                raise APIError(502, ErrorCode.KB_SYNC_FAILED, f"Mify 返回 HTTP {r.status_code}: {r.text[:300]}")
            data = r.json() or {}
            for doc in data.get("data", []) or []:
                articles.append(_mify_doc_to_article(doc, dataset_id))
            if not data.get("has_more"):
                break
            page += 1
            if page > 20:  # safety bound
                break
    return articles, {"added": len(articles), "updated": 0, "failed": 0}


def _mify_doc_to_article(doc: dict, dataset_id: str) -> dict:
    return {
        "id": doc.get("id") or doc.get("document_id") or uuid.uuid4().hex,
        "title": doc.get("name") or doc.get("title") or "(无标题)",
        "url": None,
        "source_type": "mify_rag",
        "meta": {
            "dataset_id": dataset_id,
            "indexing_status": doc.get("indexing_status"),
            "word_count": doc.get("word_count"),
            "created_at": doc.get("created_at"),
            "enabled": doc.get("enabled", True),
        },
        "content": None,
    }


# ---------------------------------------------------------------------------
# Article body — lazy fetch
# ---------------------------------------------------------------------------


async def _fetch_article_body(kb: dict, article: dict) -> str:
    if kb["source_type"] == "feishu_wiki":
        return await _fetch_feishu_doc_body(article)
    if kb["source_type"] == "mify_rag":
        return await _fetch_mify_doc_body(kb, article)
    return ""


async def _fetch_feishu_doc_body(article: dict) -> str:
    """Use the CLI's `feishu fetch` when available (it already handles OAuth
    + markdown conversion). Falls back to the URL."""
    s = get_settings()
    url = article.get("url")
    if not url:
        return "(无法构造飞书 URL)"
    if s.feishu_cli_available:
        try:
            proc = await asyncio.create_subprocess_exec(
                "feishu",
                "fetch",
                url,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            out, err = await asyncio.wait_for(proc.communicate(), timeout=30)
            if proc.returncode == 0 and out:
                return out.decode("utf-8", errors="replace")
            return f"[feishu fetch 失败] {(err or b'').decode('utf-8', errors='replace')[:300]}"
        except asyncio.TimeoutError:
            return "[feishu fetch 超时（30s）]"
        except Exception as e:  # noqa: BLE001
            return f"[feishu fetch 异常] {e}"
    return f"[请在服务器安装 feishu CLI 后访问] {url}"


async def _fetch_mify_doc_body(kb: dict, article: dict) -> str:
    s = get_settings()
    if not s.mify_dataset_enabled:
        return "[Mify dataset API 未配置]"
    dataset_id = (kb.get("config") or {}).get("dataset_id")
    doc_id = article.get("id")
    if not dataset_id or not doc_id:
        return "[缺少 dataset_id / document_id]"
    base = s.MIFY_DATASET_BASE_URL.rstrip("/")
    headers = {"Authorization": f"Bearer {s.MIFY_DATASET_API_KEY}"}
    async with httpx.AsyncClient(timeout=30) as cli:
        r = await cli.get(
            f"{base}/datasets/{dataset_id}/documents/{doc_id}/segments",
            headers=headers,
            params={"limit": 100},
        )
        if r.status_code != 200:
            return f"[Mify 返回 HTTP {r.status_code}] {r.text[:200]}"
        data = r.json() or {}
        segs = data.get("data") or []
        if not segs:
            return "(此文档尚无可读取的分段)"
        return "\n\n---\n\n".join(s.get("content") or "" for s in segs)
