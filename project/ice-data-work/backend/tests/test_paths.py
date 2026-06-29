"""四层空间 paths 的单测：防穿越 + 结构正确 + 顶层目录创建。"""
from __future__ import annotations

import os

import pytest


@pytest.fixture
def tmp_root(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_ROOT", str(tmp_path))
    from app.core.config import get_settings

    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


def test_paths_under_root(tmp_root):
    from app.core.storage import paths

    assert paths.root() == tmp_root
    assert str(paths.task_json("t1")).startswith(str(tmp_root))
    assert paths.twin_memory("u1", "preferences").name == "preferences.memory.md"


def test_four_layer_structure(tmp_root):
    from app.core.storage import paths

    # Agent 情景记忆按用户分区 / 团队共享分区（D-06）
    assert paths.agent_user_memory("data-analysis", "u1").as_posix().endswith(
        "agents/data-analysis/memory/by-user/u1/usage.memory.md"
    )
    assert paths.agent_team_memory("data-analysis", "t1").as_posix().endswith(
        "agents/data-analysis/memory/by-team/t1/shared.memory.md"
    )
    # 项目共享 / 任务参与者叠加层
    assert paths.project_shared("t1", "p1", "files").as_posix().endswith(
        "teams/t1/projects/p1/shared/files"
    )
    assert paths.task_participant_notes("tk1", "twin-u1").as_posix().endswith(
        "tasks/tk1/participants/twin-u1/notes.md"
    )


def test_segment_guard_blocks_traversal(tmp_root):
    from app.core.storage import paths

    for bad in ["../etc", "a/b", "..", "", "/abs"]:
        with pytest.raises(ValueError):
            paths.task_dir(bad)


def test_ensure_top_level(tmp_root):
    from app.core.storage import paths

    paths.ensure_top_level()
    for d in ("agents", "skills", "teams", "users", "tasks", "files", ".cache"):
        assert (tmp_root / d).is_dir()


def test_files_kind_validation(tmp_root):
    from app.core.storage import paths

    assert paths.task_files("tk1", "input").as_posix().endswith("tasks/tk1/files/input")
    with pytest.raises(ValueError):
        paths.task_files("tk1", "weird")
