"""ICE services layer — backward-compatible lazy re-exports.

Services are organized into subdirectories by domain:
  agent/       — agent configuration, runtime, kernel, prompt building
  auth/        — authentication, rate limiting
  task/        — task CRUD, conversations, context, compaction, bg tasks
  llm/         — LLM gateway, tool runner, error classification
  integration/ — feishu, KB, voice, skills
  admin/       — admin operations, usage, SQL audit, system config
  notification/— notifications, invitations, join requests, HITL
  storage/     — file service, event log, scheduler, builtin docs
  sandbox/     — Python sandbox execution (unchanged)

This __init__.py provides lazy re-exports so existing imports like
`from app.services import task_svc` continue to work without triggering
circular imports at module load time.
"""
from __future__ import annotations

import importlib
from typing import Any

# Map module name → subpackage containing it
_MODULE_MAP: dict[str, str] = {
    # agent/
    "agent_config": "agent",
    "agent_runtime": "agent",
    "agent_kernel": "agent",
    "agent_prompt_builder": "agent",
    "agent_snapshot_svc": "agent",
    "agent_workflow_svc": "agent",
    "agent_inspection_svc": "agent",
    "agent_event_sinks": "agent",
    "agents_svc": "agent",
    # auth/
    "auth_svc": "auth",
    "rate_limit_svc": "auth",
    # task/
    "task_svc": "task",
    "task_intent_svc": "task",
    "conversation_svc": "task",
    "inflight_svc": "task",
    "context_svc": "task",
    "compaction_svc": "task",
    "bg_task_svc": "task",
    # llm/
    "llm_gateway": "llm",
    "tool_runner": "llm",
    "error_classifier": "llm",
    # integration/
    "feishu": "integration",
    "feishu_import_svc": "integration",
    "kb_svc": "integration",
    "voice_svc": "integration",
    "skill_svc": "integration",
    # admin/
    "admin_svc": "admin",
    "usage_svc": "admin",
    "sql_audit_svc": "admin",
    "sysconfig_svc": "admin",
    "experience_card_svc": "admin",
    "public_task_svc": "admin",
    "template_svc": "admin",
    # notification/
    "notification_svc": "notification",
    "invitation_svc": "notification",
    "join_request_svc": "notification",
    "hitl_svc": "notification",
    # storage/
    "file_svc": "storage",
    "event_log": "storage",
    "scheduler_svc": "storage",
    "builtin_docs_svc": "storage",
}


def __getattr__(name: str) -> Any:
    subpkg = _MODULE_MAP.get(name)
    if subpkg is not None:
        mod = importlib.import_module(f".{subpkg}.{name}", __name__)
        # Cache in the package namespace so subsequent access is O(1)
        globals()[name] = mod
        return mod
    raise AttributeError(f"module 'app.services' has no attribute {name!r}")
