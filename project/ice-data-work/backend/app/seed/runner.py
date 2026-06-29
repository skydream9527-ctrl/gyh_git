"""启动种子：确保 G3 目录 + 管理员 + 测试用户 + Twin + 内置 Agent。

M1 增强：完整的种子数据用于开发/测试环境。
"""
from __future__ import annotations

from app.core.storage import paths
from app.core.storage.jsonio import read_json, write_json
from app.core.security import hash_password


def bootstrap() -> None:
    """应用启动时调用：确保目录 + 种子数据。"""
    paths.ensure_top_level()
    _seed_admin_user()
    _seed_test_user()
    _seed_sample_team()
    _seed_builtin_agents()


def _seed_admin_user() -> None:
    """创建管理员用户（admin / admin123）。"""
    uid = "admin"
    profile_path = paths.user_profile(uid)
    if read_json(profile_path) is not None:
        return

    paths.ensure(profile_path)
    write_json(profile_path, {
        "id": uid,
        "name": "系统管理员",
        "platform_role": "super_admin",
        "password_hash": hash_password("admin123"),
        "created_at": "2026-06-27T00:00:00+00:00",
    })

    # 管理员的 Twin
    twin_path = paths.twin_json(uid)
    paths.ensure(twin_path)
    write_json(twin_path, {
        "user_id": uid,
        "name": "管理员 Twin",
        "level": 4,  # L4: Bounded Autopilot
        "persona": "平台管理员，负责系统运维与团队管理",
        "preferences": {"language": "zh-CN", "theme": "system"},
        "goals": ["确保平台稳定运行", "管理用户和团队"],
        "created_at": "2026-06-27T00:00:00+00:00",
    })

    # 管理员的个人空间
    _ensure_personal_space(uid)


def _seed_test_user() -> None:
    """创建测试用户（test / test123）。"""
    uid = "test"
    profile_path = paths.user_profile(uid)
    if read_json(profile_path) is not None:
        return

    paths.ensure(profile_path)
    write_json(profile_path, {
        "id": uid,
        "name": "测试用户",
        "platform_role": "user",
        "password_hash": hash_password("test123"),
        "created_at": "2026-06-27T00:00:00+00:00",
    })

    # 测试用户的 Twin
    twin_path = paths.twin_json(uid)
    paths.ensure(twin_path)
    write_json(twin_path, {
        "user_id": uid,
        "name": "测试 Twin",
        "level": 2,  # L2: Delegate Draft
        "persona": "数据分析师，专注增长数据分析",
        "preferences": {"language": "zh-CN"},
        "goals": ["完成日常数据分析任务"],
        "created_at": "2026-06-27T00:00:00+00:00",
    })

    # 测试用户的个人空间
    _ensure_personal_space(uid)


def _seed_sample_team() -> None:
    """种子团队：增长数据团队 + 增长分析项目。"""
    tid, pid = "t_growth", "p_growth"
    tj = paths.team_json(tid)
    if read_json(tj) is None:
        paths.ensure(tj)
        write_json(tj, {
            "id": tid,
            "name": "增长数据团队",
            "type": "team",
            "members": [
                {"user_id": "admin", "role": "owner"},
                {"user_id": "test", "role": "member"},
            ],
            "created_at": "2026-06-27T00:00:00+00:00",
        })

    pj = paths.project_json(tid, pid)
    if read_json(pj) is None:
        paths.ensure(pj)
        write_json(pj, {
            "id": pid,
            "team_id": tid,
            "name": "增长分析",
            "type": "project",
            "members": [
                {"user_id": "admin", "role": "owner"},
                {"user_id": "test", "role": "member"},
            ],
            "created_at": "2026-06-27T00:00:00+00:00",
        })


def _seed_builtin_agents() -> None:
    """内置 Agent（系统级工具 Agent）。"""
    agents = [
        {
            "id": "data-analysis",
            "name": "数据分析 Agent",
            "description": "通用数据分析助手，支持 SQL 查询、数据清洗、可视化",
            "type": "builtin",
            "skills": ["kyuubi_query", "data_viz", "csv_export"],
        },
        {
            "id": "report-writer",
            "name": "报告撰写 Agent",
            "description": "基于数据产出分析报告、周报、项目总结",
            "type": "builtin",
            "skills": ["write_file", "template_render"],
        },
        {
            "id": "code-runner",
            "name": "代码执行 Agent",
            "description": "在沙盒中运行 Python 数据脚本（pandas/sklearn/prophet）",
            "type": "builtin",
            "skills": ["run_user_code", "pip_install"],
        },
    ]

    for agent in agents:
        aj = paths.agent_json(agent["id"])
        if read_json(aj) is not None:
            continue
        paths.ensure(aj)
        write_json(aj, {
            **agent,
            "version": 1,
            "created_at": "2026-06-27T00:00:00+00:00",
        })

        # agent.md（系统提示词占位）
        md_path = paths.agent_md(agent["id"])
        paths.ensure(md_path)
        md_path.write_text(
            f"# {agent['name']}\n\n{agent['description']}\n\n"
            f"## 可用技能\n\n" + "\n".join(f"- {s}" for s in agent["skills"]) + "\n",
            encoding="utf-8",
        )


def _ensure_personal_space(uid: str) -> None:
    """为用户创建个人团队 + 个人项目。"""
    personal_team_id = f"personal_{uid}"
    personal_project_id = f"p_personal_{uid}"

    tj = paths.team_json(personal_team_id)
    if read_json(tj) is None:
        paths.ensure(tj)
        write_json(tj, {
            "id": personal_team_id,
            "name": f"{uid} 的个人空间",
            "type": "personal",
            "members": [{"user_id": uid, "role": "owner"}],
            "created_at": "2026-06-27T00:00:00+00:00",
        })

    pj = paths.project_json(personal_team_id, personal_project_id)
    if read_json(pj) is None:
        paths.ensure(pj)
        write_json(pj, {
            "id": personal_project_id,
            "team_id": personal_team_id,
            "name": "个人项目",
            "type": "personal",
            "members": [{"user_id": uid, "role": "owner"}],
            "created_at": "2026-06-27T00:00:00+00:00",
        })


if __name__ == "__main__":
    bootstrap()
    print("seed: ok")
