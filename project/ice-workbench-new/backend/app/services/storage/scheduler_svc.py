"""Scheduled tasks. Cron parsing + run history. Source of truth: tasks/{tid}/scheduled.json."""
from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import IO

import portalocker

from ...core.config import get_settings
from ...core.errors import APIError, ErrorCode
from ...core.storage import append_jsonl, get_paths, read_json, read_jsonl, write_json

log = logging.getLogger("scheduler")


def _now() -> datetime:
    # Cron expressions are authored from the product UI and prompts in the
    # server's local timezone (Asia/Shanghai in this deployment), so compute
    # next_fire_at against local time rather than UTC wall-clock hours.
    return datetime.now().astimezone()


def _now_iso() -> str:
    return _now().isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex


# ---- cron parsing (minute hour dom month dow) ----

def _expand(field: str, lo: int, hi: int) -> set[int]:
    out: set[int] = set()
    for part in field.split(","):
        step = 1
        if "/" in part:
            base, s = part.split("/", 1)
            step = int(s)
            part = base
        if part == "*":
            rng = range(lo, hi + 1, step)
        elif "-" in part:
            a, b = part.split("-", 1)
            rng = range(int(a), int(b) + 1, step)
        else:
            rng = [int(part)]
        out.update(rng)
    return out


def _next_fire(expr: str, *, after: datetime) -> datetime | None:
    parts = expr.split()
    if len(parts) != 5:
        return None
    try:
        minutes = _expand(parts[0], 0, 59)
        hours = _expand(parts[1], 0, 23)
        doms = _expand(parts[2], 1, 31)
        months = _expand(parts[3], 1, 12)
        dows = _expand(parts[4], 0, 6)
    except ValueError:
        return None
    cur = after.replace(second=0, microsecond=0) + timedelta(minutes=1)
    for _ in range(60 * 24 * 366):
        if (
            cur.minute in minutes
            and cur.hour in hours
            and cur.day in doms
            and cur.month in months
            and (cur.weekday() + 1) % 7 in dows
        ):
            return cur
        cur += timedelta(minutes=1)
    return None


# ---- storage helpers ----


def _sched_path(tid: str) -> Path:
    return get_paths().task_dir(tid) / "scheduled.json"


def _runs_path(tid: str, sid: str) -> Path:
    return get_paths().task_dir(tid) / "scheduled_runs" / f"{sid}.jsonl"


def _transcript_path(tid: str, sid: str, run_id: str) -> Path:
    return get_paths().task_dir(tid) / "scheduled_runs" / f"{sid}.{run_id}.transcript.jsonl"


def list_for_task(tid: str) -> list[dict]:
    return read_json(_sched_path(tid), default=[]) or []


def list_for_user(user_id: str) -> list[dict]:
    """Aggregate scheduled tasks across user's tasks."""
    paths = get_paths()
    out: list[dict] = []
    user_index = read_json(paths.user_tasks_index(user_id), default=[]) or []
    for entry in user_index:
        tid = entry.get("task_id")
        if not tid:
            continue
        for s in list_for_task(tid):
            out.append({**s, "task_id": tid, "task_name": entry.get("name")})
    if paths.tasks.exists():
        for d in paths.tasks.iterdir():
            if not d.is_dir():
                continue
            meta = read_json(d / "meta.json")
            if meta and meta.get("owner_id") == user_id:
                for s in list_for_task(meta["id"]):
                    if not any(o["id"] == s["id"] for o in out):
                        out.append({**s, "task_id": meta["id"], "task_name": meta.get("name")})
    return out


def get_one(tid: str, sid: str) -> dict | None:
    for s in list_for_task(tid):
        if s.get("id") == sid:
            return s
    return None


def create(*, task_id: str, owner_id: str, body: dict) -> dict:
    cron = (body.get("cron") or "").strip()
    if not cron or _next_fire(cron, after=_now()) is None:
        raise APIError(400, ErrorCode.VALIDATION_ERROR, "cron 表达式无效")
    sid = _new_id()
    record = {
        "id": sid,
        "task_id": task_id,
        "name": body.get("name") or f"Schedule {sid[:6]}",
        "owner_id": owner_id,
        "cron": cron,
        "prompt": body.get("prompt") or "",
        "channels": body.get("channels") or ["in_app"],
        "enabled": body.get("enabled", True),
        "model": body.get("model") or None,
        "todo_list": body.get("todo_list") or [],
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "next_fire_at": _next_fire(cron, after=_now()).isoformat(),
        "last_fire_at": None,
    }
    items = list_for_task(task_id)
    items.append(record)
    write_json(_sched_path(task_id), items)
    return record


def update(task_id: str, sid: str, owner_id: str, patch: dict) -> dict:
    items = list_for_task(task_id)
    found = None
    for i, s in enumerate(items):
        if s["id"] == sid:
            found = i
            break
    if found is None:
        raise APIError(404, ErrorCode.RESOURCE_NOT_FOUND, "定时任务不存在")
    rec = items[found]
    if rec.get("owner_id") not in (owner_id, None):
        raise APIError(403, ErrorCode.PERMISSION_DENIED, "无权修改")
    if "cron" in patch:
        if _next_fire(patch["cron"], after=_now()) is None:
            raise APIError(400, ErrorCode.VALIDATION_ERROR, "cron 表达式无效")
        rec["cron"] = patch["cron"]
        rec["next_fire_at"] = _next_fire(patch["cron"], after=_now()).isoformat()
    for k in ("name", "prompt", "channels", "enabled", "model", "todo_list"):
        if k in patch:
            rec[k] = patch[k]
    rec["updated_at"] = _now_iso()
    items[found] = rec
    write_json(_sched_path(task_id), items)
    return rec


def remove(task_id: str, sid: str, owner_id: str) -> None:
    items = list_for_task(task_id)
    items2 = [s for s in items if s["id"] != sid]
    if len(items2) == len(items):
        return
    write_json(_sched_path(task_id), items2)


def list_runs(task_id: str, sid: str, *, limit: int = 50) -> list[dict]:
    rows = read_jsonl(_runs_path(task_id, sid))
    latest: dict[str, dict] = {}
    order: list[str] = []
    for row in rows:
        rid = row.get("id")
        if not rid:
            continue
        if rid not in latest:
            order.append(rid)
        latest[rid] = _normalize_run_status(task_id, sid, row)
    compact = [latest[rid] for rid in order]
    return compact[-limit:][::-1]


def _normalize_run_status(task_id: str, sid: str, row: dict) -> dict:
    """Decorate legacy successful Feishu runs that never actually sent."""
    if row.get("status") != "success":
        return row
    prompt = row.get("prompt") or ""
    if "feishu_send_message" not in prompt:
        return row
    if _tool_calls_include_feishu_sent(row.get("tool_calls") or []):
        return row
    run_id = row.get("id")
    transcript = read_jsonl(_transcript_path(task_id, sid, run_id)) if run_id else []
    if _transcript_include_feishu_sent(transcript):
        return row
    fixed = dict(row)
    fixed["status"] = "failed"
    fixed["error"] = fixed.get("error") or {
        "code": "FEISHU_NOT_SENT",
        "message": "历史执行记录显示成功，但未找到 feishu_send_message 的真实成功发送结果。",
    }
    return fixed


def _tool_calls_include_feishu_sent(tool_calls: list) -> bool:
    for call in tool_calls:
        if not isinstance(call, dict) or call.get("name") != "feishu_send_message":
            continue
        result = call.get("result") or {}
        if isinstance(result, dict) and result.get("sent"):
            return True
    return False


def _transcript_include_feishu_sent(transcript: list[dict]) -> bool:
    for event in transcript:
        if event.get("event") != "tool_call" or event.get("name") != "feishu_send_message":
            continue
        result = event.get("result") or {}
        if isinstance(result, dict) and result.get("sent"):
            return True
    return False


def get_run_detail(task_id: str, sid: str, run_id: str) -> dict | None:
    run = next((r for r in list_runs(task_id, sid, limit=500) if r.get("id") == run_id), None)
    if not run:
        return None
    transcript_path = _transcript_path(task_id, sid, run_id)
    transcript = read_jsonl(transcript_path) if transcript_path.exists() else []
    return {
        "run": _redact_sensitive(run),
        "transcript": [_redact_sensitive(e) for e in transcript[-200:]],
        "transcript_path": str(transcript_path) if transcript_path.exists() else None,
    }


def _redact_sensitive(value):
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            lk = str(k).lower()
            if lk in {"webhook_url", "sign_secret", "app_secret", "secret", "token", "authorization"}:
                out[k] = "***"
            else:
                out[k] = _redact_sensitive(v)
        return out
    if isinstance(value, list):
        return [_redact_sensitive(v) for v in value]
    return value


def summary_for_user(user_id: str) -> dict:
    items = list_for_user(user_id)
    now = _now()
    today = now.date()
    week_ago = now - timedelta(days=7)
    today_runs = 0
    failed_7d = 0
    last_runs: list[dict] = []
    for s in items:
        for run in list_runs(s["task_id"], s["id"], limit=100):
            started_raw = run.get("started_at") or run.get("ended_at")
            try:
                started = datetime.fromisoformat(started_raw) if started_raw else None
            except ValueError:
                started = None
            if started and started.date() == today:
                today_runs += 1
            if run.get("status") == "failed" and started and started >= week_ago:
                failed_7d += 1
            last_runs.append({**run, "schedule_name": s.get("name"), "task_name": s.get("task_name")})
    last_runs.sort(key=lambda r: r.get("started_at") or "", reverse=True)
    return {
        "total": len(items),
        "enabled": sum(1 for s in items if s.get("enabled")),
        "paused": sum(1 for s in items if not s.get("enabled")),
        "today_runs": today_runs,
        "failed_7d": failed_7d,
        "last_runs": last_runs[:10],
    }


async def run_now(task_id: str, sid: str, owner_id: str) -> dict:
    rec = get_one(task_id, sid)
    if not rec:
        raise APIError(404, ErrorCode.RESOURCE_NOT_FOUND, "定时任务不存在")
    run_id = _new_id()
    started = _now_iso()
    run = {
        "id": run_id,
        "scheduled_id": sid,
        "task_id": task_id,
        "trigger": "manual",
        "status": "running",
        "started_at": started,
        "ended_at": None,
        "prompt": rec.get("prompt"),
        "output": None,
        "error": None,
        "tokens": None,
    }
    append_jsonl(_runs_path(task_id, sid), run)
    task = asyncio.create_task(
        _execute_run(
            task_id,
            rec,
            trigger="manual",
            run_id=run_id,
            started_at=started,
            append_running=False,
        )
    )
    _manual_run_tasks.add(task)
    task.add_done_callback(_manual_run_tasks.discard)
    return run


async def _execute_run(
    task_id: str,
    rec: dict,
    *,
    trigger: str,
    run_id: str | None = None,
    started_at: str | None = None,
    append_running: bool = True,
) -> dict:
    from ...core.config import get_settings
    from ...core.storage import get_paths, read_json
    from . import (
        agent_runtime,
        agents_svc,
        experience_card_svc,
        llm_gateway,
        sysconfig_svc,
        tool_runner,
        usage_svc,
    )

    sid = rec["id"]
    started = started_at or _now_iso()
    run = {
        "id": run_id or _new_id(),
        "scheduled_id": sid,
        "task_id": task_id,
        "trigger": trigger,
        "status": "running",
        "started_at": started,
        "ended_at": None,
        "prompt": rec.get("prompt"),
        "output": None,
        "error": None,
        "tokens": None,
    }
    if append_running:
        append_jsonl(_runs_path(task_id, sid), run)
    try:
        if not get_settings().llm_enabled:
            run["status"] = "skipped"
            run["error"] = {
                "code": ErrorCode.LLM_KEY_MISSING,
                "message": "LLM 未配置，跳过执行",
            }
        else:
            meta = read_json(get_paths().task_meta(task_id), default={}) or {}
            ws_cfg = read_json(get_paths().task_workspace(task_id), default={}) or {}
            agent_id = meta.get("agent_id") or "biz-insight"
            owner_id = rec.get("owner_id") or meta.get("owner_id")
            model_id = rec.get("model") or ws_cfg.get("model") or llm_gateway.resolve_model(None)
            skill_ids = list(meta.get("skill_ids") or [])
            tools = tool_runner.get_anthropic_tools(
                feature_flags={
                    "todo_write": agents_svc.get_agent_feature(agent_id, "todo_write", True),
                    "exit_plan_mode": False,
                    "spawn_subagent": False,
                    "run_background": False,
                },
                tool_whitelist=agents_svc.get_agent_tools(agent_id),
                disallowed_tools=agents_svc.get_agent_disallowed_tools(agent_id),
                task_skill_ids=skill_ids,
            )
            system_prompt = experience_card_svc.merged_system_prompt(
                agent_id,
                task_skill_ids=skill_ids,
                callable_tool_names=[t["name"] for t in tools],
                user_id=owner_id,
                task_id=task_id,
                query=rec.get("prompt") or "",
            )
            system_prompt = (
                f"{system_prompt}\n\n---\n\n"
                "你正在执行无人值守的定时任务。必须真实调用工具完成查询、文件生成、截图和外部发送；"
                "不要把 `<tool_call>`、Python 代码块或计划当作执行结果输出。"
                "如果 prompt 要求飞书推送，最终必须以 `feishu_send_message` 的真实工具结果为准。"
            )
            ctx = {
                "user_id": owner_id,
                "agent_id": agent_id,
                "task_id": task_id,
                "conversation_id": f"schedule::{sid}",
                "run_id": run["id"],
                "plan_mode": False,
                "subagent_depth": 0,
            }
            sys_params = sysconfig_svc.get_system_params()
            max_rounds = max(
                1,
                min(
                    llm_gateway.MAX_TOOL_ROUNDS,
                    int(sys_params.get("tool_call_max_rounds") or 20),
                ),
            )
            agent_max_turns = agents_svc.get_agent_max_turns(agent_id)
            if agent_max_turns is not None:
                max_rounds = min(max_rounds, agent_max_turns)
            initial_prompt = agents_svc.get_agent_initial_prompt(agent_id)
            scheduled_prompt = rec.get("prompt") or ""
            user_prompt = f"{initial_prompt}\n\n{scheduled_prompt}" if initial_prompt else scheduled_prompt
            transcript = (
                get_paths().task_dir(task_id)
                / "scheduled_runs"
                / f"{sid}.{run['id']}.transcript.jsonl"
            )
            result = await agent_runtime.run_agent_turn(
                system_prompt=system_prompt,
                initial_messages=[{"role": "user", "content": user_prompt}],
                tools=tools,
                ctx=ctx,
                max_rounds=max_rounds,
                model=model_id,
                max_tokens=4096,
                transcript_sink=transcript,
            )
            final_text = result.get("final_text") or ""
            tool_uses = result.get("tool_uses_log") or []
            required_feishu = "feishu_send_message" in scheduled_prompt
            feishu_calls = [t for t in tool_uses if t.get("name") == "feishu_send_message"]
            feishu_sent = any(
                bool((t.get("result") or {}).get("sent"))
                for t in feishu_calls
                if isinstance(t.get("result"), dict)
            )
            if required_feishu and not feishu_sent:
                run["status"] = "failed"
                last_error = next(
                    (
                        t.get("error") or t.get("result")
                        for t in reversed(feishu_calls)
                        if t.get("error") or isinstance(t.get("result"), dict)
                    ),
                    None,
                )
                run["error"] = {
                    "code": "FEISHU_NOT_SENT",
                    "message": (
                        "定时任务要求飞书推送，但没有真实成功发送。"
                        f"工具结果：{str(last_error)[:300]}" if last_error else "定时任务要求飞书推送，但本次执行没有调用 feishu_send_message。"
                    ),
                }
            elif required_feishu and not tool_uses:
                run["status"] = "failed"
                run["error"] = {
                    "code": "NO_TOOLS_EXECUTED",
                    "message": "定时任务只生成了文本，没有执行任何工具，因此没有完成日报发送。",
                }
            elif result.get("stop_reason") == "llm_error":
                run["status"] = "failed"
                run["error"] = {"code": "LLM_ERROR", "message": "定时任务 LLM 执行失败"}
            else:
                run["status"] = "success"
            run["output"] = final_text[:4000]
            run["tool_calls"] = [
                {
                    "name": t.get("name"),
                    "success": t.get("success"),
                    "status": t.get("status"),
                    "error": t.get("error"),
                    "result": t.get("result"),
                }
                for t in tool_uses[-20:]
            ]
            run["rounds"] = result.get("rounds")
            run["stop_reason"] = result.get("stop_reason")
            usage = result.get("usage_total") or {}
            run["tokens"] = {
                "input": int(usage.get("input_tokens") or 0),
                "output": int(usage.get("output_tokens") or 0),
            }
            run["model"] = model_id
            try:
                await usage_svc.record_usage(
                    user_id=owner_id,
                    agent_id=agent_id,
                    task_id=task_id,
                    conversation_id=None,
                    model=model_id,
                    input_tokens=int(usage.get("input_tokens") or 0),
                    output_tokens=int(usage.get("output_tokens") or 0),
                    success=run["status"] == "success",
                )
            except Exception as exc:
                log.warning("scheduler record_usage failed: %s", exc)
    except Exception as e:
        run["status"] = "failed"
        run["error"] = {"code": "RUN_ERROR", "message": str(e)[:500]}
    finally:
        run["ended_at"] = _now_iso()
        append_jsonl(_runs_path(task_id, sid), run)
        # update last_fire_at + next_fire_at
        items = list_for_task(task_id)
        for i, s in enumerate(items):
            if s["id"] == sid:
                items[i]["last_fire_at"] = run["ended_at"]
                nf = _next_fire(s["cron"], after=_now())
                items[i]["next_fire_at"] = nf.isoformat() if nf else None
                break
        write_json(_sched_path(task_id), items)
    return run


# ---- background loop ----

_loop_task: asyncio.Task | None = None
_manual_run_tasks: set[asyncio.Task] = set()
# Leader-election state. With uvicorn --workers=N each worker calls start_loop()
# at lifespan startup; without coordination the same scheduled task fires N
# times. We use a non-blocking flock on .cache/scheduler.leader.lock — only the
# worker that grabs it runs the loop. The lock is held for the worker's
# lifetime; if that process dies, the kernel releases it and another worker
# takes over on its next start_loop() call (today: only at restart).
_leader_fh: IO | None = None


def _try_become_leader() -> bool:
    """Acquire the cross-process scheduler lock. True = this worker leads."""
    global _leader_fh
    if _leader_fh is not None:
        return True
    lock_path = get_settings().cache_dir / "scheduler.leader.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fh = open(lock_path, "a+")
    try:
        portalocker.lock(fh, portalocker.LOCK_EX | portalocker.LOCK_NB)
    except portalocker.LockException:
        fh.close()
        return False
    try:
        fh.seek(0)
        fh.truncate()
        fh.write(f"{os.getpid()}\n")
        fh.flush()
    except Exception:
        pass
    _leader_fh = fh
    return True


def _release_leader() -> None:
    global _leader_fh
    if _leader_fh is None:
        return
    try:
        portalocker.unlock(_leader_fh)
    finally:
        _leader_fh.close()
        _leader_fh = None


async def scheduler_loop() -> None:
    log.info("scheduler loop started")
    while True:
        try:
            await asyncio.sleep(20)
            now = _now()
            paths = get_paths()
            if not paths.tasks.exists():
                continue
            for d in paths.tasks.iterdir():
                if not d.is_dir() or d.name.startswith("."):
                    continue
                items = read_json(d / "scheduled.json", default=[]) or []
                for s in items:
                    if not s.get("enabled"):
                        continue
                    nf_iso = s.get("next_fire_at")
                    if not nf_iso:
                        continue
                    try:
                        nf = datetime.fromisoformat(nf_iso)
                    except ValueError:
                        continue
                    if nf <= now:
                        try:
                            await _execute_run(d.name, s, trigger="cron")
                        except Exception as e:
                            log.warning("scheduler run failed task=%s sid=%s: %s", d.name, s["id"], e)
        except asyncio.CancelledError:
            break
        except Exception as e:
            log.exception("scheduler loop error: %s", e)


def start_loop() -> None:
    global _loop_task
    if _loop_task is not None:
        return
    if not _try_become_leader():
        log.info("scheduler: another worker holds the leader lock; this worker stays follower")
        return
    log.info("scheduler: acquired leader lock pid=%s", os.getpid())
    _loop_task = asyncio.create_task(scheduler_loop(), name="scheduler-loop")


def stop_loop() -> None:
    global _loop_task
    if _loop_task:
        _loop_task.cancel()
        _loop_task = None
    _release_leader()
