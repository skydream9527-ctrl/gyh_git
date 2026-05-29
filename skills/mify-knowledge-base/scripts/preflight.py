#!/usr/bin/env python3
"""
Pre-flight check for Mify knowledge base operations.

Checks config, registry, and readiness in one shot.
Outputs a structured status summary so AI agents can parse
the result without needing file-search tools (which skip
git-ignored directories like .mify/).

Usage:
    python preflight.py                        # basic check
    python preflight.py --profile NAME         # check with specific profile
    python preflight.py --need-email           # also verify email is configured
    python preflight.py --need-email --verify-feishu  # verify Feishu binding
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from mify_client import (
    _global_state_dir,
    _mify_dir,
    _profile_state_dir,
    load_config,
    load_global_config,
    read_kb_state,
    refresh_registry,
    verify_feishu_auth,
)

MIFY_DIR = Path.cwd() / ".mify"
CONFIG_PATH = MIFY_DIR / "config.json"


def _scan_zombies(profile_name):
    """Scan state files for documents stuck in uploading/updating status."""
    state_dir = _profile_state_dir(profile_name)
    zombies = []
    if not state_dir.exists():
        return zombies
    for state_file in state_dir.glob("*.json"):
        if state_file.name == "kb-registry.json" or state_file.name.startswith("feishu-"):
            continue
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
            kb_id = state_file.stem
            for doc_name, doc_info in state.get("documents", {}).items():
                doc_status = doc_info.get("status", "")
                if doc_status in ("uploading", "updating"):
                    zombies.append({
                        "kb_id": kb_id,
                        "doc_name": doc_name,
                        "doc_id": doc_info.get("doc_id", ""),
                        "status": doc_status,
                    })
        except (json.JSONDecodeError, OSError):
            continue
    return zombies


def check():
    parser = argparse.ArgumentParser(description="Mify pre-flight check")
    parser.add_argument(
        "--need-email",
        action="store_true",
        help="Require email in config (for Feishu operations)",
    )
    parser.add_argument(
        "--verify-feishu",
        action="store_true",
        help="Verify Feishu data-source binding via test crawl (no URL needed)",
    )
    parser.add_argument(
        "--profile",
        default=None,
        help="Profile name (default: from config)",
    )
    args = parser.parse_args()

    status = {
        "config_exists": False,
        "api_key": False,
        "email": None,
        "profile_name": None,
        "profile_exists": False,
        "active_kbs": None,
        "registry_exists": False,
        "kb_count": 0,
        "kbs": [],
        "zombies": [],
        "ready": False,
        "errors": [],
        "warnings": [],
    }

    # 1. Load config using two-level merge (silent=True for pure JSON output)
    try:
        config = load_config(profile_name=args.profile, silent=True)
        if config is None:
            raise RuntimeError("Configuration not found or invalid")
        status["config_exists"] = True
        status["profile_name"] = config.get("profile_name")

        api_key = config.get("api_key", "").strip()
        if api_key:
            if not api_key.startswith("dataset-"):
                status["errors"].append(
                    "api_key format invalid: must start with 'dataset-' (e.g. dataset-xxx)"
                )
            else:
                status["api_key"] = True
        else:
            status["errors"].append("api_key not found — configure a profile or set api_key")

        email = config.get("email") or None
        status["email"] = email
        if email and not email.endswith("@xiaomi.com"):
            status["errors"].append(
                f"email format invalid: must be xxx@xiaomi.com, got '{email}'"
            )
        if args.need_email and not email:
            status["errors"].append(
                "email is required for Feishu operations — set it in ~/.mify/config.json"
            )

        # active_kbs for this profile
        active_kbs_map = config.get("active_kbs_map", {})
        profile_active = active_kbs_map.get(config.get("profile_name"))
        status["active_kbs"] = profile_active

        # Check if profile exists in global config (for non-legacy profiles)
        profile_name = config.get("profile_name")
        if profile_name and profile_name != "_legacy":
            global_cfg = load_global_config()
            profiles = global_cfg.get("profiles", {})
            status["profile_exists"] = profile_name in profiles
            if profile_name not in profiles:
                status["errors"].append(
                    f"Profile '{profile_name}' not found in ~/.mify/config.json. "
                    f"Add it: "
                    f'"profiles": {{"{profile_name}": {{"api_key": "dataset-xxx"}}}}'
                )
        else:
            # Legacy mode or no profile — check project config has api_key
            status["profile_exists"] = bool(api_key)

    except Exception as e:
        status["errors"].append(f"Failed to load config: {e}")

    # 2. Registry — always refresh from API when config is valid
    if status["api_key"]:
        try:
            registry = refresh_registry(config)
            status["registry_exists"] = True
            status["kb_count"] = len(registry)
            status["kbs"] = [
                {
                    "name": kb.get("name", "?"),
                    "id": kb.get("id", "?"),
                    "description": kb.get("description", ""),
                    "doc_count": kb.get("document_count", 0),
                }
                for kb in registry
            ]
        except Exception as e:
            # Fallback to local registry (check global, project, then legacy paths)
            profile_name = status.get("profile_name")
            global_reg_path = _global_state_dir(profile_name) / "kb-registry.json"
            project_reg_path = _profile_state_dir(profile_name) / "kb-registry.json"
            legacy_path = _mify_dir() / "kb-registry.json"
            fallback_path = None
            for p in (global_reg_path, project_reg_path, legacy_path):
                if p.exists():
                    fallback_path = p
                    break
            if fallback_path:
                status["registry_exists"] = True
                try:
                    with open(fallback_path, "r", encoding="utf-8") as f:
                        local_registry = json.load(f)
                    kbs = (
                        local_registry
                        if isinstance(local_registry, list)
                        else local_registry.get("data", [])
                    )
                    status["kb_count"] = len(kbs)
                    status["kbs"] = [
                        {
                            "name": kb.get("name", "?"),
                            "id": kb.get("id", "?"),
                            "description": kb.get("description", ""),
                            "doc_count": kb.get("document_count", 0),
                        }
                        for kb in kbs
                    ]
                except (json.JSONDecodeError, OSError):
                    status["errors"].append("Failed to parse local kb-registry.json")
            else:
                status["errors"].append(
                    f"Failed to refresh registry from API: {e}. "
                    "Run list_knowledge_bases.py list to create it."
                )

    # 3. Zombie scan
    if status["config_exists"]:
        zombies = _scan_zombies(status.get("profile_name"))
        if zombies:
            status["zombies"] = zombies
            status["warnings"].append(
                f"{len(zombies)} document(s) stuck in uploading/updating status. "
                "Run sync-state to reconcile or purge to clear local state."
            )

    # 4. Feishu binding check (via test crawl — the only reliable method)
    if args.verify_feishu and args.need_email and status["api_key"]:
        result = verify_feishu_auth(config)
        if result["bound"]:
            status["feishu_bound"] = True
        else:
            status["feishu_bound"] = False
            status["feishu_auth_url"] = result["auth_url"]
            status["feishu_auth_error"] = result["error"]
            status["errors"].append(
                "Feishu data source not bound (verified via test crawl). "
                "Open feishu_auth_url in browser, complete the FULL OAuth flow, "
                "then re-run preflight with --verify-feishu to confirm."
            )

    # 5. Overall readiness
    status["ready"] = status["api_key"] and len(status["errors"]) == 0

    # Output
    print(json.dumps(status, ensure_ascii=False, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    check()
