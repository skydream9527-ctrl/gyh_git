"""Data monitor service — create and manage anomaly detection jobs.

A monitor rule is a thin wrapper around a scheduled task bound to the
data-monitor agent. It stores:
- A SQL query to run
- Threshold conditions (absolute, pct_change, consecutive_decline)
- Alert channels (in_app, feishu)
- A cron schedule

When the scheduler fires the job, the data-monitor agent executes the SQL,
evaluates thresholds, and pushes alerts through configured channels.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from ...core.errors import APIError, ErrorCode
from ...core.storage import file_transaction, get_paths, read_json, write_json


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _monitors_path(task_id: str):
    """Path to the task's monitor rules file."""
    return get_paths().task_dir(task_id) / "monitors.json"


# ─── CRUD ─────────────────────────────────────────────────────────────────────


def list_monitors(task_id: str) -> list[dict]:
    """List all monitor rules for a task."""
    return read_json(_monitors_path(task_id), default=[]) or []


def get_monitor(task_id: str, monitor_id: str) -> dict | None:
    """Get a single monitor rule."""
    for m in list_monitors(task_id):
        if m["id"] == monitor_id:
            return m
    return None


def create_monitor(
    *,
    task_id: str,
    owner_id: str,
    name: str,
    sql: str,
    cron: str,
    threshold: dict,
    channels: list[str] | None = None,
    feishu_chat_id: str | None = None,
    description: str | None = None,
) -> dict:
    """Create a new data monitor rule and its backing scheduled task.

    Args:
        task_id: the task this monitor belongs to
        owner_id: the user creating the monitor
        name: human-readable name (e.g. "CC 消费 UV 环比监控")
        sql: the SQL query to execute
        cron: 5-field cron expression for schedule
        threshold: dict with keys like:
            {"type": "pct_change", "value": 10, "direction": "decline"}
            {"type": "absolute", "upper_bound": 1000, "lower_bound": 100}
            {"type": "consecutive_decline", "periods": 3}
        channels: ["in_app", "feishu"] (default: ["in_app"])
        feishu_chat_id: optional chat_id for feishu alerts
        description: optional description
    """
    from ..storage import scheduler_svc

    monitor_id = _new_id()
    channels = channels or ["in_app"]

    # Build the prompt for the data-monitor agent
    prompt = _build_monitor_prompt(
        name=name,
        sql=sql,
        threshold=threshold,
        channels=channels,
        feishu_chat_id=feishu_chat_id,
    )

    # Create the backing scheduled task
    sched = scheduler_svc.create(
        task_id=task_id,
        owner_id=owner_id,
        body={
            "name": f"[Monitor] {name}",
            "cron": cron,
            "prompt": prompt,
            "enabled": True,
            "model": None,
            "channels": channels,
            "todo_list": [f"监控: {name}"],
        },
    )

    record = {
        "id": monitor_id,
        "task_id": task_id,
        "owner_id": owner_id,
        "name": name,
        "description": description,
        "sql": sql,
        "cron": cron,
        "threshold": threshold,
        "channels": channels,
        "feishu_chat_id": feishu_chat_id,
        "scheduled_id": sched["id"],
        "enabled": True,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "last_check_at": None,
        "last_alert_at": None,
        "alert_count": 0,
    }

    # Persist
    monitors = list_monitors(task_id)
    monitors.append(record)
    mpath = _monitors_path(task_id)
    mpath.parent.mkdir(parents=True, exist_ok=True)
    write_json(mpath, monitors)

    return record


def update_monitor(task_id: str, monitor_id: str, owner_id: str, patch: dict) -> dict:
    """Update a monitor rule."""
    from ..storage import scheduler_svc

    monitors = list_monitors(task_id)
    found_idx = None
    for i, m in enumerate(monitors):
        if m["id"] == monitor_id:
            found_idx = i
            break
    if found_idx is None:
        raise APIError(404, ErrorCode.RESOURCE_NOT_FOUND, "监控规则不存在")

    rec = monitors[found_idx]

    for k in ("name", "sql", "cron", "threshold", "channels", "feishu_chat_id", "enabled", "description"):
        if k in patch:
            rec[k] = patch[k]
    rec["updated_at"] = _now_iso()

    # If SQL/threshold/cron changed, update the scheduled task prompt
    if any(k in patch for k in ("sql", "threshold", "cron", "channels", "feishu_chat_id", "name")):
        prompt = _build_monitor_prompt(
            name=rec["name"],
            sql=rec["sql"],
            threshold=rec["threshold"],
            channels=rec["channels"],
            feishu_chat_id=rec.get("feishu_chat_id"),
        )
        sched_patch = {"prompt": prompt, "name": f"[Monitor] {rec['name']}"}
        if "cron" in patch:
            sched_patch["cron"] = patch["cron"]
        if "enabled" in patch:
            sched_patch["enabled"] = patch["enabled"]
        try:
            scheduler_svc.update(task_id, rec["scheduled_id"], owner_id, sched_patch)
        except Exception:
            pass  # best-effort sync

    monitors[found_idx] = rec
    write_json(_monitors_path(task_id), monitors)
    return rec


def delete_monitor(task_id: str, monitor_id: str, owner_id: str) -> None:
    """Delete a monitor rule and its backing scheduled task."""
    from ..storage import scheduler_svc

    monitors = list_monitors(task_id)
    target = None
    remaining = []
    for m in monitors:
        if m["id"] == monitor_id:
            target = m
        else:
            remaining.append(m)

    if not target:
        return

    # Remove the backing scheduled task
    try:
        scheduler_svc.remove(task_id, target["scheduled_id"], owner_id)
    except Exception:
        pass

    write_json(_monitors_path(task_id), remaining)


# ─── Prompt Builder ───────────────────────────────────────────────────────────


def _build_monitor_prompt(
    *,
    name: str,
    sql: str,
    threshold: dict,
    channels: list[str],
    feishu_chat_id: str | None,
) -> str:
    """Build the agent prompt that the scheduler will use."""
    threshold_desc = _describe_threshold(threshold)
    channel_desc = "、".join(channels)

    prompt = f"""你正在执行数据监控任务：**{name}**

## 监控 SQL

```sql
{sql}
```

## 阈值条件

{threshold_desc}

## 告警渠道

{channel_desc}

## 执行指令

1. 用 `kyuubi_query` 执行上述 SQL
2. 根据阈值条件判断是否异常
3. 如果异常：
   - 用 `write_file` 将告警详情写入 `alerts/` 目录
"""
    if "feishu" in channels and feishu_chat_id:
        prompt += f"""   - 用 `feishu_send_message` 发送告警到 chat_id="{feishu_chat_id}"
"""
    prompt += """4. 输出检测摘要（无论是否告警）

注意：如果 SQL 执行失败或返回空结果，记录异常但不发告警。
"""
    return prompt


def _describe_threshold(threshold: dict) -> str:
    """Convert threshold dict to human-readable description."""
    t = threshold.get("type", "pct_change")
    if t == "absolute":
        parts = []
        if "upper_bound" in threshold:
            parts.append(f"上限: {threshold['upper_bound']}")
        if "lower_bound" in threshold:
            parts.append(f"下限: {threshold['lower_bound']}")
        return f"绝对值阈值 — {', '.join(parts)}"
    elif t == "pct_change":
        direction = threshold.get("direction", "any")
        value = threshold.get("value", 10)
        dir_desc = {"decline": "下跌", "increase": "上涨", "any": "波动"}.get(direction, direction)
        return f"环比变化率阈值 — {dir_desc}超过 {value}% 时告警"
    elif t == "consecutive_decline":
        periods = threshold.get("periods", 3)
        return f"连续下跌阈值 — 连续 {periods} 个周期下跌时告警"
    else:
        return f"自定义阈值: {threshold}"
