"""Strongly-typed view over an agent's ``agent.json``.

This is P1 of the agent-runtime-consolidation refactor (design.md §6). It
collapses the dozen tolerant getters that used to live in ``agents_svc`` into a
single normalization pass, so the "what does this field default to / which
camelCase aliases do we accept / when is a value invalid" rules live in exactly
one place.

Behavior is intentionally **byte-for-byte identical** to the pre-refactor
getters — every rule below was lifted verbatim from ``agents_svc``:

    - ``tools``           : list[str] only if every item is a str, else None
    - ``disallowed_tools``: accepts ``disallowedTools`` alias, drops non-str, [] default
    - ``model``           : stripped; empty → None
    - ``effort``          : positive int, or one of {low, medium, high}; else None
    - ``max_turns``       : accepts ``maxTurns``; positive int only; else None
    - ``permission_mode`` : accepts ``permissionMode``; one of the 4 modes; else "default"
    - ``initial_prompt``  : accepts ``initialPrompt``; stripped; empty → None
    - ``spawn_targets``   : list[str]; ``["*"]`` → None (no restriction); invalid → None
    - ``skills``          : drops non-str; [] default
    - ``hooks``           : dict only; else {}
    - ``features``        : raw dict; queried via :meth:`feature`

Normalization happens in a ``mode="before"`` validator so the declared field
types already hold post-validation and Pydantic never has to coerce.
``extra="allow"`` keeps untouched fields (id / name / icon / color / …) so the
model round-trips agent.json without data loss (G3).
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Mirror agents_svc constants exactly.
FEATURE_KEYS = ("spawn_subagent", "run_background", "todo_write", "exit_plan_mode")
PERMISSION_MODES = {"default", "read_only", "confirm_write", "confirm_network"}
EFFORT_VALUES = {"low", "medium", "high"}


class AgentConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str = ""
    tools: list[str] | None = None
    disallowed_tools: list[str] = Field(default_factory=list)
    model: str | None = None
    effort: str | int | None = None
    max_turns: int | None = None
    permission_mode: str = "default"
    initial_prompt: str | None = None
    spawn_targets: list[str] | None = None
    skills: list[str] = Field(default_factory=list)
    hooks: dict = Field(default_factory=dict)
    features: dict = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _normalize(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        raw = data
        out = dict(raw)  # preserve extras (id/name/icon/color/description/...)

        # tools — list[str] only if homogeneous, else None (no restriction)
        tools = raw.get("tools")
        out["tools"] = (
            list(tools)
            if isinstance(tools, list) and all(isinstance(t, str) for t in tools)
            else None
        )

        # disallowed_tools — camelCase fallback, drop non-str, [] default
        dis = raw.get("disallowed_tools")
        if dis is None:
            dis = raw.get("disallowedTools")
        out["disallowed_tools"] = (
            [t for t in dis if isinstance(t, str)] if isinstance(dis, list) else []
        )

        # model — strip, empty → None
        model = raw.get("model")
        out["model"] = model.strip() if isinstance(model, str) and model.strip() else None

        # effort — positive int OR a known level string, else None
        effort = raw.get("effort")
        if isinstance(effort, int) and not isinstance(effort, bool) and effort > 0:
            out["effort"] = effort
        elif isinstance(effort, str) and effort.strip().lower() in EFFORT_VALUES:
            out["effort"] = effort.strip().lower()
        else:
            out["effort"] = None

        # max_turns — camelCase fallback, positive int only
        mt = raw.get("max_turns")
        if mt is None:
            mt = raw.get("maxTurns")
        out["max_turns"] = (
            mt if isinstance(mt, int) and not isinstance(mt, bool) and mt > 0 else None
        )

        # permission_mode — camelCase fallback, known mode only, else "default"
        pm = raw.get("permission_mode")
        if pm is None:
            pm = raw.get("permissionMode")
        out["permission_mode"] = (
            pm.strip() if isinstance(pm, str) and pm.strip() in PERMISSION_MODES else "default"
        )

        # initial_prompt — camelCase fallback, strip, empty → None
        ip = raw.get("initial_prompt")
        if ip is None:
            ip = raw.get("initialPrompt")
        out["initial_prompt"] = ip.strip() if isinstance(ip, str) and ip.strip() else None

        # spawn_targets — list[str]; ["*"] → None; invalid → None
        st = raw.get("spawn_targets")
        if isinstance(st, list) and all(isinstance(t, str) for t in st):
            out["spawn_targets"] = None if st == ["*"] else list(st)
        else:
            out["spawn_targets"] = None

        # skills — drop non-str, [] default
        skills = raw.get("skills")
        out["skills"] = (
            [s for s in skills if isinstance(s, str)] if isinstance(skills, list) else []
        )

        # hooks — dict only, else {}
        hooks = raw.get("hooks")
        out["hooks"] = hooks if isinstance(hooks, dict) else {}

        # features — raw dict kept for feature() lookups
        feats = raw.get("features")
        out["features"] = feats if isinstance(feats, dict) else {}

        return out

    def feature(self, name: str, default: bool) -> bool:
        """Per-agent feature flag resolution (mirrors agents_svc.get_agent_feature).

        Only the 4 known runtime feature keys are honored; any other name
        returns ``default`` untouched. A present ``features.<name>`` wins as a
        bool; absence falls back to ``default`` (typically a global ICE_* flag).
        """
        if name not in FEATURE_KEYS:
            return default
        if name in self.features:
            return bool(self.features[name])
        return default

    @classmethod
    def load(cls, agent_id: str) -> AgentConfig | None:
        """Direct read of ``agents/<id>/agent.json`` → AgentConfig, or None if
        the file is absent. Does NOT trigger seed creation — for runtime config
        reads that must preserve the seeding side-effect, go through
        ``agents_svc`` getters (which read via ``get_agent``).
        """
        from ...core.storage import get_paths, read_json

        raw = read_json(get_paths().agents / agent_id / "agent.json")
        if not raw:
            return None
        return cls.model_validate(raw)
