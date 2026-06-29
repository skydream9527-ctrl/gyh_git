"""运行配置。

不依赖 pydantic-settings：直接读环境变量，DATA_ROOT 默认自解析到仓库根，
保证打包/换机器可移植（G3 文件优先存储所在）。
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path


def _truthy(v: str | None) -> bool:
    return (v or "").strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    def __init__(self) -> None:
        # backend/app/core/config.py -> parents[3] == 仓库根
        repo_root = Path(__file__).resolve().parents[3]
        env_root = os.environ.get("DATA_ROOT", "").strip()
        self.data_root: Path = Path(env_root).resolve() if env_root else repo_root

        self.secret_key: str = os.environ.get("IDW_SECRET_KEY", "dev-insecure-change-me")
        self.bind_host: str = os.environ.get("IDW_BIND_HOST", "0.0.0.0")
        self.bind_port: int = int(os.environ.get("IDW_BIND_PORT", "8000"))

        self.database_url: str = os.environ.get("DATABASE_URL", "")

        # 集成（缺省时相关能力降级，不阻塞启动）
        self.mify_base_url: str = os.environ.get("MIFY_GATEWAY_BASE_URL", "")
        self.mify_api_key: str = os.environ.get("MIFY_GATEWAY_API_KEY", "")
        self.feishu_app_id: str = os.environ.get("FEISHU_APP_ID", "")
        self.kyuubi_host: str = os.environ.get("KYUUBI_HOST", "")

        # 特性开关
        self.twin_enabled: bool = _truthy(os.environ.get("IDW_TWIN_ENABLED", "true"))
        self.pgvector_enabled: bool = _truthy(os.environ.get("IDW_PGVECTOR_ENABLED"))
        self.self_evolve_enabled: bool = _truthy(os.environ.get("IDW_SELF_EVOLVE_ENABLED"))
        self.daemon_enabled: bool = _truthy(os.environ.get("IDW_DAEMON_ENABLED"))
        self.cross_twin_enabled: bool = _truthy(os.environ.get("IDW_CROSS_TWIN_ENABLED"))

        # M7（v1.5 增强）特性开关：默认关，灰度上线
        self.a2a_enabled: bool = _truthy(os.environ.get("IDW_A2A_ENABLED"))
        self.autostep_enabled: bool = _truthy(os.environ.get("IDW_AUTOSTEP_ENABLED"))
        self.triggers_enabled: bool = _truthy(os.environ.get("IDW_TRIGGERS_ENABLED"))

        # M7 编排预算（防多 Agent 互相转交失控）
        self.a2a_max_hops: int = int(os.environ.get("IDW_A2A_MAX_HOPS", "3"))
        self.a2a_hard_cap: int = int(os.environ.get("IDW_A2A_HARD_CAP", "6"))
        # M7 主动性护栏：单任务每日主动动作上限 + 月度成本上限（与用量预算独立的主动性闸）
        self.autostep_daily_cap: int = int(os.environ.get("IDW_AUTOSTEP_DAILY_CAP", "20"))

    @property
    def llm_enabled(self) -> bool:
        return bool(self.mify_api_key) or bool(os.environ.get("ANTHROPIC_API_KEY"))

    @property
    def cache_dir(self) -> Path:
        return self.data_root / ".cache"


@lru_cache
def get_settings() -> Settings:
    return Settings()
