"""用量与成本：LLM 调用统计 + 月度预算 + CSV 导出（材料二 §10 复用 ICE）。

每次 LLM 调用记一条 usage（model/tokens/估价/task/user）到 .cache/usage.jsonl（派生）。
单价表近似（USD/1K tokens）；mock 调用记 0 成本但计次，保证看板有数据。
"""
from __future__ import annotations

import csv
import io
from datetime import datetime, timezone

from app.core.config import get_settings
from app.core.storage.jsonio import append_jsonl, read_jsonl

# 近似单价（USD / 1K tokens）：input, output
_PRICING: dict[str, tuple[float, float]] = {
    "claude-sonnet-4": (0.003, 0.015),
    "claude-opus-4": (0.015, 0.075),
    "gpt-4o": (0.005, 0.015),
    "mock": (0.0, 0.0),
}


def _usage_path():
    return get_settings().cache_dir / "usage.jsonl"


def record_usage(
    *, model: str, input_tokens: int = 0, output_tokens: int = 0,
    task_id: str = "", user_id: str = "", mock: bool = False,
) -> dict:
    """记录一次 LLM 用量。"""
    key = "mock" if mock else _normalize(model)
    in_price, out_price = _PRICING.get(key, _PRICING["claude-sonnet-4"])
    cost = (input_tokens / 1000.0) * in_price + (output_tokens / 1000.0) * out_price
    rec = {
        "ts": _now_iso(),
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": round(cost, 6),
        "task_id": task_id,
        "user_id": user_id,
        "mock": mock,
    }
    p = _usage_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    append_jsonl(p, rec)
    return rec


def summary(*, month: str | None = None) -> dict:
    """用量汇总。month 形如 '2026-06'，缺省全部。"""
    records = read_jsonl(_usage_path())
    if month:
        records = [r for r in records if (r.get("ts", "")[:7] == month)]
    total_calls = len(records)
    total_in = sum(r.get("input_tokens", 0) for r in records)
    total_out = sum(r.get("output_tokens", 0) for r in records)
    total_cost = round(sum(r.get("cost_usd", 0.0) for r in records), 4)

    by_model: dict[str, dict] = {}
    for r in records:
        m = r.get("model", "?")
        agg = by_model.setdefault(m, {"calls": 0, "tokens": 0, "cost_usd": 0.0})
        agg["calls"] += 1
        agg["tokens"] += r.get("input_tokens", 0) + r.get("output_tokens", 0)
        agg["cost_usd"] = round(agg["cost_usd"] + r.get("cost_usd", 0.0), 6)

    budget = _monthly_budget()
    return {
        "month": month or "all",
        "total_calls": total_calls,
        "total_tokens": total_in + total_out,
        "total_cost_usd": total_cost,
        "by_model": by_model,
        "monthly_budget_usd": budget,
        "budget_used_pct": round(total_cost / budget * 100, 1) if budget else None,
    }


def export_csv(*, month: str | None = None) -> str:
    """导出用量明细 CSV。"""
    records = read_jsonl(_usage_path())
    if month:
        records = [r for r in records if (r.get("ts", "")[:7] == month)]
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["ts", "model", "input_tokens", "output_tokens", "cost_usd", "task_id", "user_id", "mock"])
    for r in records:
        writer.writerow([
            r.get("ts", ""), r.get("model", ""), r.get("input_tokens", 0),
            r.get("output_tokens", 0), r.get("cost_usd", 0.0),
            r.get("task_id", ""), r.get("user_id", ""), r.get("mock", False),
        ])
    return buf.getvalue()


def _monthly_budget() -> float:
    import os
    try:
        return float(os.environ.get("IDW_MONTHLY_BUDGET_USD", "100"))
    except ValueError:
        return 100.0


def _normalize(model: str) -> str:
    m = model.removeprefix("mify/")
    for key in _PRICING:
        if m.startswith(key):
            return key
    return m


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
