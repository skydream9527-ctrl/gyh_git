from __future__ import annotations

import os
import shutil
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

    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)
