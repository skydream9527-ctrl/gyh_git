"""任务级运维事件流 — task/conv 粒度的"看日志"能力。

写入路径：`tasks/{task_id}/events/{YYYY-MM}.jsonl`，每条一行 JSON。
读取入口：管理端 /admin/diagnostics（admin.py 暴露的端点）。

核心约束：
  - filesystem 是 source of truth（G3）。不入 SQLite。
  - 大对象（完整 LLM payload、长 stdout）不写入 events——只放摘要 + 指针；
    完整数据继续写各自的 conversation.jsonl / tool_calls.jsonl。
  - emit() 永不抛异常：观测代码失败不能拖垮主路径。
  - request_id / ws_id 通过 contextvar 自动注入，调用方无需显式传。

事件 schema:
    {
      "ts": "2026-05-22T10:01:23.456Z",
      "level": "INFO" | "WARN" | "ERROR",
      "source": "api" | "ws" | "agent_runtime" | "tool_runner" | "llm_gateway"
                | "sandbox" | "scheduler" | "bg_task" | "auth",
      "task_id": "...",
      "conv_id": "..." | null,
      "run_id": "..." | null,        # subagent / scheduled run
      "request_id": "..." | null,    # HTTP / WS 请求维度
      "user_id": "..." | null,
      "event_type": "turn_start" | "turn_end" | "tool_call_start" | ...,
      "code": "TOOL_TIMEOUT_30s" | null,
      "message": "...",
      "payload": {...} | null         # 摘要，size 小
    }
"""
from __future__ import annotations

import contextvars
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Iterable

from ..core.storage import append_jsonl, get_paths, read_jsonl

log = logging.getLogger("event_log")

# 单线程 executor 序列化 emit 写盘——append_jsonl 走 portalocker 互斥锁，
# 让一个 worker 内部所有 events 走同一条线程就不会跟自己抢锁；跨 worker
# 仍由 portalocker 保护。重点是这不能阻塞 asyncio 事件循环（ws.py 的 streaming
# 主路径就在事件循环里），所以 submit + 立即返回，写失败也只 log.warning。
_writer = ThreadPoolExecutor(max_workers=1, thread_name_prefix="event_log")

# Per-request / per-WS 上下文。中间件 / WS 入口在拿到请求时 set，
# 业务代码 emit() 时自动读取。栈式 reset 不必，每个请求结束自动出作用域。
request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)
user_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "user_id", default=None
)


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat(timespec="milliseconds")


def _ym(ts_iso: str) -> str:
    return ts_iso[:7]  # "2026-05"


_VALID_LEVELS = {"INFO", "WARN", "ERROR"}


def emit(
    *,
    task_id: str | None,
    source: str,
    event_type: str,
    level: str = "INFO",
    conv_id: str | None = None,
    run_id: str | None = None,
    user_id: str | None = None,
    request_id: str | None = None,
    code: str | None = None,
    message: str = "",
    payload: dict | None = None,
) -> None:
    """同步追加一条事件。**永不抛异常**——观测失败不能阻断主流程。

    没有 task_id 的事件会被丢弃（events 是任务级流；非任务事件请用 logger）。
    level >= WARN 时同时通过标准 logger 输出一条，stdout 仍可看到。
    """
    if not task_id:
        return
    if level not in _VALID_LEVELS:
        level = "INFO"
    ts = _now_iso()
    rec: dict[str, Any] = {
        "ts": ts,
        "level": level,
        "source": source,
        "task_id": task_id,
        "conv_id": conv_id,
        "run_id": run_id,
        "request_id": request_id if request_id is not None else request_id_var.get(),
        "user_id": user_id if user_id is not None else user_id_var.get(),
        "event_type": event_type,
        "code": code,
        "message": (message or "")[:1000],
        "payload": _sanitize_payload(payload),
    }
    try:
        _writer.submit(_write_event, task_id, ts, rec)
    except Exception as exc:
        log.warning("event_log submit failed task=%s evt=%s: %s", task_id, event_type, exc)
    if level == "ERROR":
        log.error(
            "[event] task=%s conv=%s evt=%s code=%s msg=%s",
            task_id, conv_id, event_type, code, message,
        )
    elif level == "WARN":
        log.warning(
            "[event] task=%s conv=%s evt=%s code=%s msg=%s",
            task_id, conv_id, event_type, code, message,
        )


def _write_event(task_id: str, ts: str, rec: dict) -> None:
    try:
        append_jsonl(get_paths().task_events(task_id, _ym(ts)), rec)
    except Exception as exc:
        log.warning("event_log write failed task=%s evt=%s: %s",
                    task_id, rec.get("event_type"), exc)


# 防止 payload 把 events.jsonl 撑爆。LLM 完整 payload / 长 stdout 应该写
# tool_calls.jsonl / conversation.jsonl，events 只放摘要。
_PAYLOAD_MAX_BYTES = 4096


def _sanitize_payload(payload: dict | None) -> dict | None:
    if payload is None:
        return None
    if not isinstance(payload, dict):
        return {"_raw": str(payload)[:500]}
    # 估算大小并按需裁剪——对 string 字段截断，dict/list 转 repr 截断。
    out: dict[str, Any] = {}
    remaining = _PAYLOAD_MAX_BYTES
    for k, v in payload.items():
        if remaining <= 0:
            out["_truncated"] = True
            break
        if isinstance(v, str):
            cap = min(len(v), max(64, remaining))
            out[k] = v[:cap] + ("…" if len(v) > cap else "")
            remaining -= cap
        elif isinstance(v, (int, float, bool)) or v is None:
            out[k] = v
            remaining -= 16
        else:
            s = repr(v)
            cap = min(len(s), max(64, remaining))
            out[k] = s[:cap] + ("…" if len(s) > cap else "")
            remaining -= cap
    return out


# ---- read side（管理端诊断页用） ----


def _list_event_files(task_id: str, since_ym: str | None = None) -> list:
    """按月列出某任务的 events.jsonl 文件，按月份升序。"""
    d = get_paths().task_dir(task_id) / "events"
    if not d.is_dir():
        return []
    files = sorted(p for p in d.glob("*.jsonl") if p.is_file())
    if since_ym:
        files = [p for p in files if p.stem >= since_ym]
    return files


def read_task_events(
    task_id: str,
    *,
    conv_id: str | None = None,
    request_id: str | None = None,
    level: str | None = None,
    source: str | None = None,
    event_type: str | None = None,
    since_ym: str | None = None,
    limit: int = 500,
) -> list[dict]:
    """读取任务事件，支持过滤。返回时间倒序（最新在前），最多 limit 条。

    filesystem 直接读不入 SQLite——诊断页是冷查询，按需扫描即可。
    """
    files = _list_event_files(task_id, since_ym=since_ym)
    rows: list[dict] = []
    # 倒序读月份，找够 limit 条就停。
    for p in reversed(files):
        records = read_jsonl(p)
        for rec in records:
            if conv_id and rec.get("conv_id") != conv_id:
                continue
            if request_id and rec.get("request_id") != request_id:
                continue
            if level and rec.get("level") != level:
                continue
            if source and rec.get("source") != source:
                continue
            if event_type and rec.get("event_type") != event_type:
                continue
            rows.append(rec)
        if len(rows) >= limit * 2:
            break
    rows.sort(key=lambda r: r.get("ts") or "", reverse=True)
    return rows[:limit]


def lookup_by_request_id(request_id: str, *, limit: int = 200) -> list[dict]:
    """按 request_id 跨任务反查——用户只贴了一个错误请求 ID 时用。

    扫描所有任务的当月 events 文件；任务多时会慢，可后续按需加索引。
    """
    paths = get_paths()
    rows: list[dict] = []
    if not paths.tasks.exists():
        return rows
    ym_now = datetime.now(tz=timezone.utc).strftime("%Y-%m")
    for tdir in paths.tasks.iterdir():
        if not tdir.is_dir() or tdir.name.startswith("."):
            continue
        evt_dir = tdir / "events"
        if not evt_dir.is_dir():
            continue
        # 只扫当月 + 上月，避免全盘 IO
        for ym in (ym_now,):
            p = evt_dir / f"{ym}.jsonl"
            if not p.exists():
                continue
            for rec in read_jsonl(p):
                if rec.get("request_id") == request_id:
                    rows.append(rec)
        if len(rows) >= limit:
            break
    rows.sort(key=lambda r: r.get("ts") or "", reverse=True)
    return rows[:limit]


def list_tasks_with_events(limit: int = 50) -> list[dict]:
    """列出最近有事件写入的任务，给诊断页空状态时的入口。"""
    paths = get_paths()
    if not paths.tasks.exists():
        return []
    items: list[dict] = []
    for tdir in paths.tasks.iterdir():
        if not tdir.is_dir() or tdir.name.startswith("."):
            continue
        evt_dir = tdir / "events"
        if not evt_dir.is_dir():
            continue
        latest_mtime = 0.0
        files = list(evt_dir.glob("*.jsonl"))
        if not files:
            continue
        for f in files:
            try:
                m = f.stat().st_mtime
                if m > latest_mtime:
                    latest_mtime = m
            except OSError:
                continue
        # task name 从 meta.json 读
        meta_p = tdir / "meta.json"
        name = ""
        owner = ""
        try:
            import json as _json
            if meta_p.exists():
                meta = _json.loads(meta_p.read_text(encoding="utf-8"))
                name = meta.get("name") or ""
                owner = meta.get("owner_id") or ""
        except Exception:
            pass
        items.append(
            {
                "task_id": tdir.name,
                "task_name": name,
                "owner_id": owner,
                "last_event_at": datetime.fromtimestamp(latest_mtime, tz=timezone.utc).isoformat(timespec="seconds")
                if latest_mtime > 0
                else None,
            }
        )
    items.sort(key=lambda x: x.get("last_event_at") or "", reverse=True)
    return items[:limit]


def merge_with_other_streams(
    task_id: str, conv_id: str, *, limit: int = 500
) -> list[dict]:
    """把 events.jsonl 与同会话的 conversation.jsonl / tool_calls.jsonl 合并展示。

    用于诊断页"时间轴视图"——一屏看到运维事件、消息、工具调用。
    返回的统一形态：
      {ts, kind: 'event'|'message'|'tool_call', level?, summary, ref}
    """
    paths = get_paths()
    timeline: list[dict] = []
    for rec in read_task_events(task_id, conv_id=conv_id, limit=limit):
        ts = rec.get("ts") or ""
        timeline.append(
            {
                "ts": ts,
                "kind": "event",
                "level": rec.get("level"),
                "source": rec.get("source"),
                "event_type": rec.get("event_type"),
                "code": rec.get("code"),
                "summary": rec.get("message") or rec.get("event_type"),
                "ref": rec,
            }
        )
    # conversation.jsonl
    conv_path = paths.task_conversation(task_id, conv_id)
    if conv_path.exists():
        for rec in read_jsonl(conv_path):
            ts = rec.get("created_at") or ""
            content = rec.get("content")
            if isinstance(content, str):
                preview = content[:200]
            else:
                preview = str(content)[:200] if content else ""
            timeline.append(
                {
                    "ts": ts,
                    "kind": "message",
                    "role": rec.get("role"),
                    "summary": preview,
                    "ref": {"id": rec.get("id"), "stop_reason": rec.get("stop_reason")},
                }
            )
    # tool_calls.jsonl
    tool_path = paths.task_tool_calls(task_id, conv_id)
    if tool_path.exists():
        for rec in read_jsonl(tool_path):
            ts = rec.get("ended_at") or rec.get("started_at") or ""
            ok = rec.get("success")
            timeline.append(
                {
                    "ts": ts,
                    "kind": "tool_call",
                    "level": "INFO" if ok else "ERROR",
                    "summary": f"{rec.get('tool_name')} → {'ok' if ok else (rec.get('error') or {}).get('error_code') or 'failed'}",
                    "ref": rec,
                }
            )
    timeline.sort(key=lambda x: x.get("ts") or "")
    return timeline[-limit:] if len(timeline) > limit else timeline


def merge_for_request(request_id: str, *, limit: int = 200) -> list[dict]:
    rows = lookup_by_request_id(request_id, limit=limit)
    return [
        {
            "ts": r.get("ts"),
            "kind": "event",
            "level": r.get("level"),
            "source": r.get("source"),
            "event_type": r.get("event_type"),
            "task_id": r.get("task_id"),
            "conv_id": r.get("conv_id"),
            "code": r.get("code"),
            "summary": r.get("message") or r.get("event_type"),
            "ref": r,
        }
        for r in rows
    ]


__all__: Iterable[str] = [
    "emit",
    "read_task_events",
    "lookup_by_request_id",
    "list_tasks_with_events",
    "merge_with_other_streams",
    "merge_for_request",
    "request_id_var",
    "user_id_var",
]
