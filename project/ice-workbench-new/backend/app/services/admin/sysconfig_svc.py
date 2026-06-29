"""System configuration. Source of truth: .cache/system-config.json (cache-tier).

Settings are read-mostly; we keep them in a single JSON file for simplicity. The
file also persists across restarts (it lives next to the SQLite cache, not the
project root, since it's environment state — separate from the immutable repo).

Default values live in DEFAULTS; overrides are merged on read.
"""
from __future__ import annotations

import json
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from ...core.errors import APIError, ErrorCode
from ...core.storage import get_paths, read_json, write_json


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _config_path() -> Path:
    return get_paths().cache / "system-config.json"


DEFAULTS: dict = {
    "toggles": {
        # On by default — 注册接口写入的账号一律是 status=pending，必须管理员
        # 在 /admin/users 显式批准后才能登录，所以"开放注册"开关只控制"是否
        # 在登录页显示注册入口"，而非"任何人能直接登录"。如运营策略需要完全
        # 屏蔽自助注册渠道，改回 False 即可（admin 仍可代建账号）。
        "enable_open_register": True,
        "enable_public_task_review": False,
        "enable_feishu_strict_whitelist": False,
        # When true (default): a user logging in via Feishu for the first time
        # gets a fresh auth_role=user account auto-created. Set false to
        # require admin-side whitelisting before Feishu login works.
        "enable_feishu_auto_register": True,
    },
    "system_params": {
        "upload_max_size_mb": 20,
        "upload_max_size_hard_cap_mb": 50,
        "context_size": 20,
        # 单次用户对话允许的最大工具调用轮数。每轮 = 一次模型回复 + 这一轮里
        # 全部工具的并发执行。复杂数据分析任务（多次 SQL + Python + 画图 +
        # 飞书发布）很快会撞 5 轮上限，故默认 20。clamp 到 [1, 50]
        # 防止 admin 设过头打爆 token 预算（见 ws.py / bg_task_svc.py）。
        "tool_call_max_rounds": 20,
        "tool_call_timeout_s": 30,
    },
    "llm": {
        "budget_monthly_usd": 2000.0,
        "budget_alert_threshold": 0.8,
        # 默认模型（None = fallback 到 .env 的 MIFY_DEFAULT_MODEL）。在 admin
        # settings UI 配置；llm_gateway.resolve_model 优先读这里。
        "default_model_id": None,
        # visible_to_user：普通 user 在 workspace 模型下拉里能否看到这个模型；
        # admin/super_admin 不受此约束，能看到所有 enabled=true 的模型。
        # enabled 是系统级开关（false 全员都用不了），visible_to_user 是用户级。
        "models": [
            {"id": "ppio/pa/claude-opus-4-7", "label": "Claude Opus 4.7", "input_unit_price": 15.0, "output_unit_price": 75.0, "enabled": True, "visible_to_user": True},
            {"id": "ppio/pa/claude-opus-4-6", "label": "Claude Opus 4.6", "input_unit_price": 15.0, "output_unit_price": 75.0, "enabled": True, "visible_to_user": True},
            {"id": "ppio/pa/claude-sonnet-4-6", "label": "Claude Sonnet 4.6", "input_unit_price": 3.0, "output_unit_price": 15.0, "enabled": True, "visible_to_user": True},
            {"id": "azure_openai/gpt-5.4", "label": "GPT-5.4", "input_unit_price": 5.0, "output_unit_price": 25.0, "enabled": True, "visible_to_user": True},
            {"id": "azure_openai/gpt-5.3-codex", "label": "GPT-5.3 Codex", "input_unit_price": 5.0, "output_unit_price": 25.0, "enabled": True, "visible_to_user": True},
            {"id": "vertex_ai/gemini-3.1-pro-preview", "label": "Gemini 3.1 Pro", "input_unit_price": 2.5, "output_unit_price": 12.5, "enabled": True, "visible_to_user": True},
            {"id": "zhipuai/glm-5.2", "label": "GLM-5.2", "input_unit_price": 1.0, "output_unit_price": 4.0, "enabled": True, "visible_to_user": True},
            {"id": "xiaomi/glm-5", "label": "GLM-5 (Xiaomi)", "input_unit_price": 1.0, "output_unit_price": 4.0, "enabled": True, "visible_to_user": True},
            {"id": "xiaomi/mimo-v2.5-pro", "label": "MiMo v2.5 Pro (Xiaomi)", "input_unit_price": 1.0, "output_unit_price": 4.0, "enabled": True, "visible_to_user": True},
        ],
    },
    "announcements": [],
}


def _read() -> dict:
    p = _config_path()
    if not p.exists():
        write_json(p, DEFAULTS)
        return _deep_copy(DEFAULTS)
    saved = read_json(p, default={}) or {}
    merged = _merge(_deep_copy(DEFAULTS), saved)
    # Bump legacy installs that still carry the old $200 default to the new
    # $2000 ceiling. Idempotent: once the saved value is anything other than
    # 200 it's treated as an admin-set value and left alone.
    dirty = False
    llm_saved = saved.get("llm", {}) if isinstance(saved, dict) else {}
    if float(llm_saved.get("budget_monthly_usd", 2000.0)) == 200.0:
        merged["llm"]["budget_monthly_usd"] = 2000.0
        dirty = True
    # Remove the vestigial enforce_budget_cap key left behind by the earlier
    # hard-cap implementation — budget is now notification-only.
    if "enforce_budget_cap" in merged.get("llm", {}):
        merged["llm"].pop("enforce_budget_cap", None)
        dirty = True
    # Bump legacy 5-round tool-call ceiling to the new 20-round default.
    # The 5 was baked in before ws.py / bg_task_svc.py read this setting at
    # all, so any saved 5 is leftover stale state, never a deliberate admin
    # choice. Once the value is anything other than 5 we leave it alone.
    sp_saved = saved.get("system_params", {}) if isinstance(saved, dict) else {}
    if int(sp_saved.get("tool_call_max_rounds", 20)) == 5:
        merged["system_params"]["tool_call_max_rounds"] = 20
        dirty = True
    if dirty:
        write_json(p, merged)
    return merged


def _deep_copy(d: dict) -> dict:
    import copy

    return copy.deepcopy(d)


def _merge(base: dict, override: dict) -> dict:
    """Shallow merge dicts; lists are replaced (not appended)."""
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            base[k] = _merge(base[k], v)
        else:
            base[k] = v
    return base


def _save(cfg: dict) -> None:
    write_json(_config_path(), cfg)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


# ---- public API ----


def get_full_config() -> dict:
    return _read()


def get_toggles() -> dict:
    return _read()["toggles"]


def update_toggles(patch: dict) -> dict:
    cfg = _read()
    cfg["toggles"].update({k: bool(v) for k, v in patch.items() if k in cfg["toggles"]})
    _save(cfg)
    return cfg["toggles"]


def get_system_params() -> dict:
    return _read()["system_params"]


def update_system_params(patch: dict) -> dict:
    cfg = _read()
    for k in cfg["system_params"]:
        if k in patch:
            cfg["system_params"][k] = patch[k]
    _save(cfg)
    return cfg["system_params"]


def reset_system_params() -> dict:
    cfg = _read()
    cfg["system_params"] = _deep_copy(DEFAULTS["system_params"])
    _save(cfg)
    return cfg["system_params"]


# ---- LLM models / pricing ----


def get_llm_config() -> dict:
    cfg = _read()
    return {
        "budget_monthly_usd": cfg["llm"]["budget_monthly_usd"],
        "budget_alert_threshold": cfg["llm"]["budget_alert_threshold"],
        "default_model_id": cfg["llm"].get("default_model_id"),
        "models": cfg["llm"]["models"],
    }


def update_llm_budget(
    *, budget_monthly_usd: float, budget_alert_threshold: float
) -> dict:
    if budget_monthly_usd < 0:
        raise APIError(400, ErrorCode.VALIDATION_ERROR, "预算不能为负")
    if not 0 < budget_alert_threshold <= 1:
        raise APIError(400, ErrorCode.VALIDATION_ERROR, "告警阈值必须在 (0,1] 之间")
    cfg = _read()
    cfg["llm"]["budget_monthly_usd"] = float(budget_monthly_usd)
    cfg["llm"]["budget_alert_threshold"] = float(budget_alert_threshold)
    _save(cfg)
    return cfg["llm"]


def update_llm_model(model_id: str, patch: dict) -> dict:
    cfg = _read()
    found = False
    for m in cfg["llm"]["models"]:
        if m["id"] == model_id:
            for k in ("label", "input_unit_price", "output_unit_price", "enabled", "visible_to_user"):
                if k in patch:
                    m[k] = patch[k]
            found = True
            break
    if not found:
        # treat as upsert
        cfg["llm"]["models"].append(
            {
                "id": model_id,
                "label": patch.get("label", model_id),
                "input_unit_price": float(patch.get("input_unit_price", 0)),
                "output_unit_price": float(patch.get("output_unit_price", 0)),
                "enabled": bool(patch.get("enabled", True)),
                "visible_to_user": bool(patch.get("visible_to_user", True)),
            }
        )
    # 模型被禁用且它正好是当前默认 → 把 default_model_id 清掉，避免悬挂引用
    if cfg["llm"].get("default_model_id") == model_id:
        target = next((m for m in cfg["llm"]["models"] if m["id"] == model_id), None)
        if target and not target.get("enabled", True):
            cfg["llm"]["default_model_id"] = None
    _save(cfg)
    return next(m for m in cfg["llm"]["models"] if m["id"] == model_id)


def get_default_model_id() -> str | None:
    """Return the admin-configured default model id, or None to fall back to env."""
    cfg = _read()
    mid = cfg["llm"].get("default_model_id")
    if not mid:
        return None
    # 防御：如果默认模型已被禁用或删除，返回 None 让上游 fallback env
    for m in cfg["llm"]["models"]:
        if m["id"] == mid:
            return mid if m.get("enabled", True) else None
    return None


def update_llm_default_model(model_id: str | None) -> dict:
    """Set or clear the default model. None clears it (fallback to env).
    Non-None must reference an existing enabled model."""
    cfg = _read()
    if model_id is None or model_id == "":
        cfg["llm"]["default_model_id"] = None
    else:
        target = next((m for m in cfg["llm"]["models"] if m["id"] == model_id), None)
        if not target:
            raise APIError(400, ErrorCode.VALIDATION_ERROR, f"模型不存在：{model_id}")
        if not target.get("enabled", True):
            raise APIError(400, ErrorCode.VALIDATION_ERROR, f"模型已禁用，不能设为默认：{model_id}")
        cfg["llm"]["default_model_id"] = model_id
    _save(cfg)
    return {"default_model_id": cfg["llm"]["default_model_id"]}


def _list_mify_gateway_llm_models() -> list[dict]:
    script = _repo_root() / "skills" / "mify-model-gateway" / "scripts" / "list_models.py"
    if not script.exists():
        raise APIError(500, ErrorCode.INTERNAL_ERROR, "mify-model-gateway skill 未安装，无法刷新模型列表")
    try:
        proc = subprocess.run(
            [sys.executable, str(script), "--type", "llm", "--json"],
            cwd=str(_repo_root()),
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired as e:
        raise APIError(504, "MIFY_GATEWAY_TIMEOUT", "刷新 Mify 模型列表超时，请稍后重试") from e

    if proc.returncode != 0:
        msg = (proc.stderr or proc.stdout or "").strip()
        if "Missing $MIFY_API_KEY" in msg or "MIFY_API_KEY" in msg:
            msg = "MIFY_API_KEY 未配置，请先按 mify-model-gateway skill 配置网关 token"
        elif not msg:
            msg = "Mify 模型列表刷新失败"
        raise APIError(502, "MIFY_GATEWAY_ERROR", msg[:500])

    try:
        payload = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError as e:
        raise APIError(502, "MIFY_GATEWAY_ERROR", "Mify 模型列表返回了无法解析的 JSON") from e
    if not isinstance(payload, list):
        raise APIError(502, "MIFY_GATEWAY_ERROR", "Mify 模型列表返回格式异常")
    return payload


def _normalize_mify_model(row: dict) -> dict | None:
    raw_id = str(row.get("id") or "").strip()
    owner = str(row.get("owned_by") or "").strip()
    if not raw_id or not owner:
        return None
    return {
        "id": f"{owner}/{raw_id}",
        "label": f"{raw_id} ({owner})",
        "input_unit_price": 0.0,
        "output_unit_price": 0.0,
        "enabled": True,
        # New gateway models become admin-selectable first; admins decide what
        # to expose to normal users via the existing visibility switch.
        "visible_to_user": False,
    }


def _merge_mify_llm_models(existing_models: list[dict], rows: list[dict]) -> tuple[list[dict], dict]:
    by_id = {str(m.get("id")): dict(m) for m in existing_models if m.get("id")}
    ordered_ids = [str(m.get("id")) for m in existing_models if m.get("id")]
    fetched_ids: set[str] = set()
    inserted = 0
    updated = 0
    skipped_invalid = 0
    skipped_non_llm = 0

    for row in rows:
        if not isinstance(row, dict):
            skipped_invalid += 1
            continue
        if str(row.get("model_type") or "").lower() != "llm":
            skipped_non_llm += 1
            continue
        model = _normalize_mify_model(row)
        if not model:
            skipped_invalid += 1
            continue
        mid = model["id"]
        fetched_ids.add(mid)
        if mid not in by_id:
            by_id[mid] = model
            ordered_ids.append(mid)
            inserted += 1
            continue

        current = by_id[mid]
        before = dict(current)
        current.setdefault("label", model["label"])
        current.setdefault("input_unit_price", 0.0)
        current.setdefault("output_unit_price", 0.0)
        current.setdefault("enabled", True)
        current.setdefault("visible_to_user", False)
        if current != before:
            updated += 1

    merged = [by_id[mid] for mid in ordered_ids if mid in by_id]
    summary = {
        "fetched": len(rows),
        "llm": len(fetched_ids),
        "inserted": inserted,
        "updated": updated,
        "kept_existing": len([m for m in existing_models if str(m.get("id")) not in fetched_ids]),
        "skipped_non_llm": skipped_non_llm,
        "skipped_invalid": skipped_invalid,
    }
    return merged, summary


def refresh_llm_models_from_mify() -> dict:
    rows = _list_mify_gateway_llm_models()
    cfg = _read()
    merged, summary = _merge_mify_llm_models(cfg["llm"]["models"], rows)
    cfg["llm"]["models"] = merged
    _save(cfg)
    return {"llm": get_llm_config(), "summary": summary}


def get_model_pricing(model_id: str) -> tuple[float, float]:
    """Return (input_unit_price, output_unit_price) per 1M tokens."""
    cfg = _read()
    for m in cfg["llm"]["models"]:
        if m["id"] == model_id:
            return float(m["input_unit_price"]), float(m["output_unit_price"])
    return 0.0, 0.0


# ---- announcements ----


def list_announcements() -> list[dict]:
    cfg = _read()
    items = list(cfg.get("announcements") or [])
    items.sort(key=lambda a: a.get("created_at") or "", reverse=True)
    return items


def create_announcement(*, title: str, body: str, level: str, audience_scope: str, status: str) -> dict:
    if level not in {"info", "warning", "error"}:
        raise APIError(400, ErrorCode.VALIDATION_ERROR, "level 非法")
    cfg = _read()
    rec = {
        "id": uuid.uuid4().hex,
        "title": title,
        "body": body,
        "level": level,
        "audience_scope": audience_scope or "all",
        "status": status or "draft",
        "published_at": _now() if status == "published" else None,
        "created_at": _now(),
        "updated_at": _now(),
    }
    cfg.setdefault("announcements", []).append(rec)
    _save(cfg)
    return rec


def update_announcement(ann_id: str, patch: dict) -> dict:
    cfg = _read()
    items = cfg.get("announcements") or []
    for a in items:
        if a["id"] == ann_id:
            for k in ("title", "body", "level", "audience_scope", "status"):
                if k in patch:
                    a[k] = patch[k]
            if patch.get("status") == "published" and not a.get("published_at"):
                a["published_at"] = _now()
            a["updated_at"] = _now()
            cfg["announcements"] = items
            _save(cfg)
            return a
    raise APIError(404, ErrorCode.RESOURCE_NOT_FOUND, "公告不存在")


def delete_announcement(ann_id: str) -> None:
    cfg = _read()
    items = [a for a in (cfg.get("announcements") or []) if a["id"] != ann_id]
    cfg["announcements"] = items
    _save(cfg)


def list_active_announcements() -> list[dict]:
    return [a for a in list_announcements() if a.get("status") == "published"]
