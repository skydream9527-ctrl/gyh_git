"""M1 测试：认证 + 权限 gate + 成员资格 + 个人项目。"""
from __future__ import annotations

import os
import tempfile

import pytest

# 使用临时目录避免污染真实数据
_tmp = tempfile.mkdtemp()
os.environ["DATA_ROOT"] = _tmp

from app.core.config import get_settings  # noqa: E402

# 清除 lru_cache 使新 DATA_ROOT 生效
get_settings.cache_clear()

from app.core.security import (  # noqa: E402
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.core.storage import paths  # noqa: E402
from app.core.storage.jsonio import read_json, write_json  # noqa: E402
from app.services import auth_svc, team_svc, twin_svc, user_svc  # noqa: E402


@pytest.fixture(autouse=True)
def setup_env():
    """确保顶层目录存在。"""
    paths.ensure_top_level()
    yield


class TestSecurity:
    def test_password_hash_verify(self):
        hashed = hash_password("hello123")
        assert verify_password("hello123", hashed)
        assert not verify_password("wrong", hashed)

    def test_jwt_roundtrip(self):
        token = create_access_token("user1", extra={"role": "user"})
        payload = decode_access_token(token)
        assert payload["sub"] == "user1"
        assert payload["role"] == "user"

    def test_jwt_expired(self):
        from datetime import timedelta

        from jose import JWTError

        token = create_access_token("x", expires_delta=timedelta(seconds=-1))
        with pytest.raises(JWTError):
            decode_access_token(token)


class TestAuthSvc:
    def test_register_and_login(self):
        result = auth_svc.register("alice", "pw123", "Alice")
        assert result["token"]
        assert result["user"]["id"] == "alice"

        login_result = auth_svc.login("alice", "pw123")
        assert login_result["token"]

    def test_login_wrong_password(self):
        from app.core.errors import APIError

        auth_svc.register("bob", "correct", "Bob")
        with pytest.raises(APIError) as exc_info:
            auth_svc.login("bob", "wrong")
        assert exc_info.value.status == 401

    def test_register_duplicate(self):
        from app.core.errors import APIError

        auth_svc.register("dup", "pw", "Dup")
        with pytest.raises(APIError) as exc_info:
            auth_svc.register("dup", "pw2", "Dup2")
        assert exc_info.value.status == 409


class TestUserSvc:
    def test_create_user_auto_personal_project(self):
        user = user_svc.create_user("charlie", name="Charlie", password="pw")
        assert user["id"] == "charlie"

        # 个人团队应已创建
        personal_team = read_json(paths.team_json("personal_charlie"))
        assert personal_team is not None
        assert personal_team["type"] == "personal"

        # 个人项目应已创建
        personal_proj = read_json(paths.project_json("personal_charlie", "p_personal_charlie"))
        assert personal_proj is not None
        assert personal_proj["type"] == "personal"

    def test_ensure_user_idempotent(self):
        u1 = user_svc.ensure_user("dave", name="Dave")
        u2 = user_svc.ensure_user("dave", name="Should Not Change")
        assert u1["name"] == u2["name"] == "Dave"

    def test_update_user(self):
        user_svc.create_user("eve", name="Eve", password="pw")
        updated = user_svc.update_user("eve", name="Eve Updated")
        assert updated["name"] == "Eve Updated"

    def test_list_users(self):
        user_svc.create_user("frank", name="Frank", password="pw")
        users = user_svc.list_users()
        ids = [u["id"] for u in users]
        assert "frank" in ids


class TestTeamSvc:
    def test_create_team(self):
        team = team_svc.create_team("t_test1", name="测试团队", owner_id="admin")
        assert team["id"] == "t_test1"
        assert team["members"][0]["role"] == "owner"

    def test_add_remove_member(self):
        team_svc.create_team("t_test2", name="T2", owner_id="admin")
        team_svc.add_member("t_test2", "user1", "member")

        meta = team_svc.get_team("t_test2")
        assert len(meta["members"]) == 2

        team_svc.remove_member("t_test2", "user1")
        meta = team_svc.get_team("t_test2")
        assert len(meta["members"]) == 1

    def test_cannot_remove_owner(self):
        from app.core.errors import APIError

        team_svc.create_team("t_test3", name="T3", owner_id="admin")
        with pytest.raises(APIError) as exc_info:
            team_svc.remove_member("t_test3", "admin")
        assert exc_info.value.status == 400

    def test_change_role(self):
        team_svc.create_team("t_test4", name="T4", owner_id="admin")
        team_svc.add_member("t_test4", "user2", "member")
        team_svc.change_role("t_test4", "user2", "admin")

        meta = team_svc.get_team("t_test4")
        u2 = next(m for m in meta["members"] if m["user_id"] == "user2")
        assert u2["role"] == "admin"

    def test_list_teams_by_user(self):
        team_svc.create_team("t_test5", name="T5", owner_id="userX")
        teams = team_svc.list_teams(user_id="userX")
        ids = [t["id"] for t in teams]
        assert "t_test5" in ids

        teams_other = team_svc.list_teams(user_id="nobody")
        ids_other = [t["id"] for t in teams_other]
        assert "t_test5" not in ids_other


class TestTwinSvc:
    def test_ensure_twin(self):
        twin = twin_svc.ensure_twin("twin_user", name="Twin User")
        assert twin["user_id"] == "twin_user"
        assert twin["level"] == 2  # 默认 L2

    def test_update_twin_level(self):
        twin_svc.ensure_twin("twin_user2")
        updated = twin_svc.set_level("twin_user2", 4)
        assert updated["level"] == 4

    def test_invalid_level(self):
        from app.core.errors import APIError

        twin_svc.ensure_twin("twin_user3")
        with pytest.raises(APIError):
            twin_svc.set_level("twin_user3", 6)

    def test_update_twin_persona(self):
        twin_svc.ensure_twin("twin_user4")
        updated = twin_svc.update_twin("twin_user4", persona="数据分析专家")
        assert updated["persona"] == "数据分析专家"
