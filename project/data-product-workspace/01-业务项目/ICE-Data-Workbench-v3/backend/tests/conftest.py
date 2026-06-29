from __future__ import annotations

import os
import shutil
import sqlite3
import tempfile
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_data_root(monkeypatch):
    tmp = Path(tempfile.mkdtemp(prefix="ice-test-"))
    for sub in ("agents", "skills", "files", "users", "tasks", ".cache"):
        (tmp / sub).mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("DATA_ROOT", str(tmp))
    monkeypatch.setenv("ICE_SECRET_KEY", "test-secret-key-with-enough-length-32b")
    # Tests pin a known strong admin password. Without this the seed runner
    # generates a random one on every test run and the login fixtures can't
    # log in. Strong enough to satisfy the security validator (>=12 chars,
    # not in the documented-default list).
    monkeypatch.setenv("ICE_BOOTSTRAP_ADMIN_PASSWORD", "Test-Admin-Pw-2026!")

    # purge cached settings/paths
    from app.core import config as cfg
    from app.core.storage import index_db, paths as p

    cfg.get_settings.cache_clear()
    p.get_paths.cache_clear()
    index_db.get_index_db.cache_clear()

    # Apply IndexDB schema so services that hit the cache (e.g. conversation_svc
    # → user._name_map → users_index) don't trip on a missing table. In prod
    # this is done via `await db.init()` from app/seed/runner.py; here we run
    # the same SCHEMA via stdlib sqlite3 so the fixture stays sync.
    db_path = cfg.get_settings().cache_db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.executescript(index_db.SCHEMA)
        conn.commit()

    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)
