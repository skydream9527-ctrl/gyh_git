"""Application settings, sourced from .env at repo root."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT_DEFAULT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT_DEFAULT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Core
    DATA_ROOT: Path = REPO_ROOT_DEFAULT
    ICE_SECRET_KEY: str = "dev-secret-please-change-me-32bytes"
    ICE_ACCESS_TOKEN_TTL_MIN: int = 60
    ICE_REFRESH_TOKEN_TTL_DAYS: int = 14
    ICE_CORS_ORIGINS: str = "http://localhost:5173"

    # LLM gateway — OpenAI-compatible. Preferred path.
    MIFY_GATEWAY_BASE_URL: str = ""
    MIFY_GATEWAY_API_KEY: str = ""
    MIFY_DEFAULT_MODEL: str = "ppio/pa/claude-opus-4-7"

    # Mify RAG dataset API — separate from the LLM gateway. Used by
    # kb_svc to list/fetch documents in Mify-hosted knowledge bases.
    # API key format: `dataset-xxx`. Obtain from mify.mioffice.cn/datasets?category=api.
    MIFY_DATASET_BASE_URL: str = "https://mify.mioffice.cn/v1"
    MIFY_DATASET_API_KEY: str = ""

    # LLM (legacy native Anthropic SDK fallback)
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-opus-4-7"
    ANTHROPIC_BASE_URL: str = ""

    # Feishu OAuth (standard open platform OR Xiaomi internal Lark variant).
    # `FEISHU_HOST` lets you point at the internal domain when Xiaomi Lark
    # exposes the same OAuth endpoints under a different hostname.
    FEISHU_APP_ID: str = ""
    FEISHU_APP_SECRET: str = ""
    FEISHU_HOST: str = "https://open.feishu.cn"
    FEISHU_REDIRECT_URI: str = "http://localhost:5173/auth/feishu/callback"

    # Default location for `feishu_publish` — without this, the CLI drops every
    # generated doc into the app's *personal* my_library, where nobody else
    # has read perms (the "needs to apply for permission" complaint).
    # Setting either field makes feishu_publish create docs in a shared place
    # all space members can already see. wiki_space wins if both are set.
    # Default = 「内容生态数据产品知识库」(known agent's space).
    FEISHU_DEFAULT_WIKI_SPACE_ID: str = "7560912865739997187"
    FEISHU_DEFAULT_FOLDER_TOKEN: str = ""
    # Default IM target for Feishu bot message delivery. receive_id_type can be
    # chat_id/open_id/user_id/union_id/email. Agents may override per call.
    FEISHU_DEFAULT_RECEIVE_ID: str = ""
    FEISHU_DEFAULT_RECEIVE_ID_TYPE: str = "chat_id"
    # If non-empty, feishu_publish auto-grants this perm to:
    #   1. the task owner's xiaomi_email
    #   2. every active collaborator's xiaomi_email
    # one perm-add RPC per address. Errors are warnings, never block publish.
    FEISHU_AUTO_PERM_LEVEL: str = "edit"  # view | edit | full_access | "" (off)

    # Kyuubi (Xiaomi internal SQL gateway). Defaults bundled for chnbj/iceberg.
    KYUUBI_HOST: str = ""
    KYUUBI_PORT: int = 10009
    KYUUBI_USER: str = ""
    KYUUBI_PASSWORD: str = ""
    KYUUBI_REGION: str = "chnbj"
    KYUUBI_WORKSPACE: str = "11329"
    KYUUBI_CATALOG: str = "iceberg_zjyprc_hadoop"
    KYUUBI_ENGINE: str = "presto"
    KYUUBI_TOKEN: str = ""

    # Bootstrap admin
    ICE_BOOTSTRAP_ADMIN_EMAIL: str = "admin"
    ICE_BOOTSTRAP_ADMIN_PASSWORD: str = "admin123"
    ICE_BOOTSTRAP_ADMIN_NAME: str = "系统管理员"

    # Agent runtime v2 — Claude Code-style mechanisms. All default off so
    # existing conversations see zero behavior change; operators flip on
    # per-env after smoke test. Compaction defaults on because the current
    # history[-20:] truncation is strictly worse than a summary.
    ICE_TODO_ENABLED: bool = False
    ICE_SUBAGENT_ENABLED: bool = False
    ICE_PLAN_MODE_ENABLED: bool = False
    ICE_PARALLEL_TOOLS_ENABLED: bool = False
    ICE_COMPACTION_ENABLED: bool = True
    ICE_COMPACTION_THRESHOLD_MSGS: int = 40
    ICE_COMPACTION_KEEP_LAST: int = 20
    ICE_SUBAGENT_MAX_DEPTH: int = 2
    ICE_SUBAGENT_MAX_TOOL_ROUNDS: int = 3
    ICE_SUBAGENT_TIMEOUT_SEC: int = 120
    ICE_KYUUBI_CONCURRENCY: int = 3
    ICE_BG_TASK_ENABLED: bool = False
    # Max output tokens per assistant turn (streaming). The agent's preamble
    # text + tool_use input JSON share this budget — long markdown bodies
    # (e.g. feishu_publish 报告正文) can hit the cap and truncate the JSON
    # mid-string, which silently drops fields the runtime never sees. 16384
    # is the safe default for Claude Opus 4.7 / Sonnet 4.6; bump higher if
    # your provider supports it.
    ICE_LLM_MAX_OUTPUT_TOKENS: int = 16384
    # Python sandbox (data-analysis agent's execute_python tool)
    ICE_PYTHON_SANDBOX_ENABLED: bool = True
    ICE_PYTHON_SANDBOX_TIMEOUT_SEC: int = 60
    ICE_PYTHON_SANDBOX_MEMORY_MB: int = 1024
    ICE_PYTHON_SANDBOX_FSIZE_MB: int = 50
    ICE_PYTHON_SANDBOX_CONCURRENCY: int = 8

    # Voice (mobile PTT). Reuses MIFY_GATEWAY_BASE_URL + MIFY_GATEWAY_API_KEY;
    # zero new secret. Off by default — flip on after Mify rate-limit confirmed.
    # Both ASR and TTS go through Xiaomi MiMo's chat-completions API shape
    # (see services/voice_svc.py). Built-in TTS voice IDs:
    # mimo_default / Chloe / Mia / Milo / Dean / 冰糖 / 茉莉 / 苏打 / 白桦.
    ICE_VOICE_ENABLED: bool = False
    ICE_VOICE_ASR_MODEL: str = "mimo-v2.5"
    ICE_VOICE_TTS_MODEL: str = "mimo-v2.5-tts"
    ICE_VOICE_DEFAULT_TTS_VOICE: str = "Chloe"
    ICE_VOICE_AUDIO_MAX_MB: int = 5

    # 米盾 (Aegis) — production auth. When enabled, JWT is replaced by
    # X-Proxy-UserDetail header verification. Public key from the Aegis admin
    # console; multi-key is supported (comma-separated). Local dev can set
    # AEGIS_DEV_BYPASS_EMAIL to fake a user without going through the proxy.
    AEGIS_ENABLED: bool = True
    AEGIS_PUBLIC_KEY: str = ""           # comma-separated; PEM or base64 DER
    AEGIS_ADMIN_EMAILS: str = ""         # comma-separated → auth_role=super_admin
    AEGIS_DEV_BYPASS_EMAIL: str = ""     # local dev only; non-empty disables verification

    @field_validator("DATA_ROOT", mode="before")
    @classmethod
    def _resolve_data_root(cls, v):
        """Empty string / '.' / missing -> repo root. Makes the bundle
        portable: another machine can `unzip && make dev` without editing .env."""
        if v in ("", ".", None):
            return REPO_ROOT_DEFAULT
        # Relative path: resolve against the repo root, not cwd.
        from pathlib import Path as _P

        p = _P(str(v)).expanduser()
        if not p.is_absolute():
            p = (REPO_ROOT_DEFAULT / p).resolve()
        return p

    @property
    def cors_origins_list(self) -> list[str]:
        return [s.strip() for s in self.ICE_CORS_ORIGINS.split(",") if s.strip()]

    @property
    def aegis_public_keys(self) -> list[str]:
        return [s.strip() for s in self.AEGIS_PUBLIC_KEY.split(",") if s.strip()]

    @property
    def aegis_admin_emails(self) -> set[str]:
        return {s.strip().lower() for s in self.AEGIS_ADMIN_EMAILS.split(",") if s.strip()}

    @property
    def cache_dir(self) -> Path:
        d = self.DATA_ROOT / ".cache"
        d.mkdir(exist_ok=True)
        return d

    @property
    def cache_db_path(self) -> Path:
        return self.cache_dir / "index.db"

    @property
    def llm_enabled(self) -> bool:
        return bool(self.MIFY_GATEWAY_API_KEY) or bool(self.ANTHROPIC_API_KEY)

    @property
    def gateway_enabled(self) -> bool:
        return bool(self.MIFY_GATEWAY_BASE_URL and self.MIFY_GATEWAY_API_KEY)

    @property
    def feishu_enabled(self) -> bool:
        return bool(self.FEISHU_APP_ID and self.FEISHU_APP_SECRET)

    @property
    def feishu_cli_available(self) -> bool:
        """True when the `feishu` CLI exists on PATH (used as fallback when
        FEISHU_APP_ID/SECRET are not configured — the CLI carries its own
        OAuth token via `feishu auth login`)."""
        import shutil
        return shutil.which("feishu") is not None

    @property
    def mify_dataset_enabled(self) -> bool:
        return bool(self.MIFY_DATASET_BASE_URL and self.MIFY_DATASET_API_KEY)

    @property
    def voice_enabled(self) -> bool:
        """ASR/TTS routes only function when both the feature flag is on AND
        the Mify gateway is configured (voice reuses MIFY_GATEWAY_*)."""
        return bool(self.ICE_VOICE_ENABLED) and self.gateway_enabled

    @property
    def kyuubi_enabled(self) -> bool:
        import shutil
        return bool(self.KYUUBI_TOKEN) and shutil.which("kyuubi") is not None


@lru_cache
def get_settings() -> Settings:
    return Settings()
