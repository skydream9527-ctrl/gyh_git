"""Seed runner. Idempotent — safe to call on every startup."""
from __future__ import annotations

import asyncio
import logging
import os
import secrets
import string
import uuid
from datetime import datetime, timezone

from ..core.config import get_settings
from ..core.security import hash_password
from ..core.storage import file_transaction, get_index_db, get_paths, read_json
from ..core.storage.paths import ensure_layout
from ..services import agents_svc

log = logging.getLogger(__name__)

# Passwords that must never be silently seeded — these are documented public
# defaults (see CLAUDE.md / .env.example) and any deployment that lands on
# them is a fresh out-of-the-box install. We refuse to bake them into the
# password hash and instead generate a random one (printed to logs + saved
# to .cache/initial_admin_password.txt with 0600 perms for one-time recovery).
_KNOWN_DEFAULT_PASSWORDS = {"admin123", "test123", "password", "changeme"}


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex


async def bootstrap() -> None:
    ensure_layout()
    db = get_index_db()
    await db.init()
    agents_svc._ensure_seed_agents()
    await _ensure_admin()
    if os.getenv("ICE_SEED_TEST_USERS", "").lower() in ("1", "true", "yes"):
        await _ensure_test_users()
    await _reindex_users_and_agents()


def _random_password(length: int = 24) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*-_=+"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _resolve_admin_password(configured: str) -> tuple[str, bool]:
    """Return (password, was_generated). If `configured` is a known default,
    generate a random one and persist it to .cache/initial_admin_password.txt
    so the operator can recover it once."""
    if configured and configured not in _KNOWN_DEFAULT_PASSWORDS and len(configured) >= 12:
        return configured, False
    pwd = _random_password()
    paths = get_paths()
    out = paths.cache / "initial_admin_password.txt"
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(pwd, encoding="utf-8")
        try:
            os.chmod(out, 0o600)
        except OSError:
            pass
    except OSError as e:
        log.warning("could not persist initial admin password: %s", e)
    log.warning(
        "================================================================\n"
        " 已生成一次性的 super_admin 密码（首次登录后请立即修改）：\n"
        "   %s\n"
        " 同时写入 %s（0600）。请妥善保存后删除该文件。\n"
        " 配置 .env 中的 ICE_BOOTSTRAP_ADMIN_PASSWORD 为强密码可避免随机生成。\n"
        "================================================================",
        pwd,
        out,
    )
    return pwd, True


async def _ensure_admin() -> None:
    s = get_settings()
    paths = get_paths()
    db = get_index_db()
    row = await db.fetchone(
        "SELECT id FROM users_index WHERE auth_role = 'super_admin' LIMIT 1"
    )
    if row:
        return
    pwd, generated = _resolve_admin_password(s.ICE_BOOTSTRAP_ADMIN_PASSWORD)
    uid = _new_id()
    profile = {
        "id": uid,
        "email": s.ICE_BOOTSTRAP_ADMIN_EMAIL,
        "name": s.ICE_BOOTSTRAP_ADMIN_NAME,
        "auth_role": "super_admin",
        "status": "active",
        "password_hash": hash_password(pwd),
        "feishu_user_id": None,
        "feishu_bound_at": None,
        "team": "platform",
        "title": "管理员",
        "avatar_url": None,
        "created_at": _now(),
        "last_login_at": None,
        "must_change_password": generated,
    }
    p = paths.user_profile(uid)
    with file_transaction([p, paths.user_tasks_index(uid)]) as tx:
        tx.makedirs(
            [
                paths.user_dir(uid) / "tasks",
                paths.user_dir(uid) / "notifications",
                paths.user_dir(uid) / "audit",
            ]
        )
        tx.write_json(p, profile)
        tx.write_json(paths.user_tasks_index(uid), [])
        tx.write_json(paths.user_settings(uid), {"theme": "dark"})
    await db.upsert(
        "users_index",
        {
            "id": uid,
            "email": profile["email"],
            "name": profile["name"],
            "auth_role": "super_admin",
            "status": "active",
            "feishu_user_id": None,
            "last_login_at": None,
            "password_hash": profile["password_hash"],
            "created_at": profile["created_at"],
        },
    )


async def _ensure_test_users() -> None:
    """Demo seed accounts. Off by default — set ICE_SEED_TEST_USERS=true.

    Each test user gets a freshly generated random password persisted under
    .cache/test_user_passwords.json (0600). Never seed a documented public
    password — internal pentests have repeatedly used the old `test123`.
    """
    paths = get_paths()
    db = get_index_db()
    test_users = [
        {"email": "zhangmingyuan", "name": "张明远", "team": "growth", "title": "产品经理"},
        {"email": "lisihan", "name": "李思涵", "team": "biz", "title": "数据分析师"},
    ]
    pw_log: dict[str, str] = {}
    for u in test_users:
        row = await db.fetchone("SELECT id FROM users_index WHERE email = ?", [u["email"]])
        if row:
            continue
        pwd = _random_password(16)
        pw_log[u["email"]] = pwd
        uid = _new_id()
        profile = {
            "id": uid,
            "email": u["email"],
            "name": u["name"],
            "auth_role": "user",
            "status": "active",
            "password_hash": hash_password(pwd),
            "feishu_user_id": None,
            "team": u["team"],
            "title": u["title"],
            "created_at": _now(),
            "last_login_at": None,
        }
        with file_transaction([paths.user_profile(uid), paths.user_tasks_index(uid)]) as tx:
            tx.makedirs(
                [
                    paths.user_dir(uid) / "tasks",
                    paths.user_dir(uid) / "notifications",
                    paths.user_dir(uid) / "audit",
                ]
            )
            tx.write_json(paths.user_profile(uid), profile)
            tx.write_json(paths.user_tasks_index(uid), [])
            tx.write_json(paths.user_settings(uid), {"theme": "dark"})
        await db.upsert(
            "users_index",
            {
                "id": uid,
                "email": profile["email"],
                "name": profile["name"],
                "auth_role": "user",
                "status": "active",
                "feishu_user_id": None,
                "last_login_at": None,
                "password_hash": profile["password_hash"],
                "created_at": profile["created_at"],
            },
        )
    if pw_log:
        out = paths.cache / "test_user_passwords.json"
        try:
            import json as _json
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(_json.dumps(pw_log, ensure_ascii=False, indent=2), encoding="utf-8")
            try:
                os.chmod(out, 0o600)
            except OSError:
                pass
            log.warning(
                "已生成测试账号一次性密码，保存在 %s（0600）。请使用后删除。",
                out,
            )
        except OSError as e:
            log.warning("could not persist test user passwords: %s", e)


async def _reindex_users_and_agents() -> None:
    """Sweep users/ and agents/ trees back into cache index (idempotent)."""
    paths = get_paths()
    db = get_index_db()
    if paths.users.exists():
        for d in paths.users.iterdir():
            if not d.is_dir():
                continue
            profile = read_json(d / "profile.json")
            if not profile:
                continue
            await db.upsert(
                "users_index",
                {
                    "id": profile["id"],
                    "email": profile.get("email", ""),
                    "name": profile.get("name", ""),
                    "auth_role": profile.get("auth_role", "user"),
                    "status": profile.get("status", "active"),
                    "feishu_user_id": profile.get("feishu_user_id"),
                    "last_login_at": profile.get("last_login_at"),
                    "password_hash": profile.get("password_hash"),
                    "created_at": profile.get("created_at"),
                },
            )
            tasks_idx = d / "tasks" / "index.json"
            for entry in read_json(tasks_idx, default=[]) or []:
                tid = entry.get("task_id")
                if not tid:
                    continue
                meta = read_json(paths.task_meta(tid))
                if not meta:
                    continue
                await db.upsert(
                    "tasks_index",
                    {
                        "id": meta["id"],
                        "owner_id": meta["owner_id"],
                        "name": meta.get("name", ""),
                        "paradigm": meta.get("paradigm", ""),
                        "agent_id": meta.get("agent_id"),
                        "status": meta.get("status", "active"),
                        "visibility": meta.get("visibility", "private"),
                        "publish_status": meta.get("publish_status", "draft"),
                        "file_count": int(meta.get("file_count", 0)),
                        "last_message_preview": meta.get("last_message_preview"),
                        "updated_at": meta.get("updated_at"),
                        "created_at": meta.get("created_at"),
                    },
                )
    for a in agents_svc.list_agents():
        await db.upsert(
            "agents_index",
            {
                "id": a["id"],
                "name": a.get("name"),
                "paradigm": a.get("paradigm"),
                "icon": a.get("icon"),
                "color": a.get("color"),
                "publish_status": a.get("publish_status", "published"),
                "description": a.get("description"),
                "updated_at": _now(),
            },
        )


def main() -> None:
    asyncio.run(bootstrap())
    print("seed: ok")


if __name__ == "__main__":
    main()
