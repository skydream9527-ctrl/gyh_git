#!/usr/bin/env python3
"""
List and create Mify knowledge bases.

Usage:
    python list_knowledge_bases.py list [--hide-empty] [--profile NAME]
    python list_knowledge_bases.py docs --kb "My KB" [--feishu-only] [--profile NAME]
    python list_knowledge_bases.py create --name "My KB" [--provider vendor|mibrag] [--permission only_me|all_team_members] [--profile NAME]
    python list_knowledge_bases.py search-config [--set KB ...] [--add KB ...] [--remove KB ...] [--clear] [--disable] [--profile NAME]
    python list_knowledge_bases.py sync-state --kb "My KB" [--profile NAME]
    python list_knowledge_bases.py purge --kb "My KB" [--profile NAME]
"""

import argparse
import json
import sys
from pathlib import Path

# Import shared client
sys.path.insert(0, str(Path(__file__).parent))
from mify_client import (
    _mify_dir,
    _profile_state_dir,
    list_remote_documents,
    load_config,
    mify_request,
    read_kb_registry,
    read_kb_state,
    refresh_registry,
    remove_config_field,
    resolve_kb,
    save_config_field,
    write_kb_state,
)

# ---------------------------------------------------------------------------
# Default KB configuration
# ---------------------------------------------------------------------------

RETRIEVAL_MODEL_CONFIG = {
    "search_method": "hybrid_search",
    "reranking_enable": True,
    "reranking_mode": "reranking_model",
    "reranking_model": {
        "reranking_provider_name": "langgenius/siliconflow/siliconflow",
        "reranking_model_name": "BAAI/bge-reranker-v2-m3_mi_sys",
    },
    "top_k": 5,
    "score_threshold_enabled": True,
    "score_threshold": 0.1,
}

PROCESS_RULE_CUSTOM = {
    "mode": "custom",
    "rules": {
        "pre_processing_rules": [],
        "segmentation": {
            "separator": '["#", "##", "###", "```\\n", "\\n---\\n", "\\n\\n", "\\n"]',
            "max_tokens": 1024,
        },
    },
}


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------


def cmd_list(args, config):
    """List all knowledge bases."""
    print("Fetching knowledge bases...\n")

    datasets = refresh_registry(config)

    if args.hide_empty:
        datasets = [ds for ds in datasets if ds.get("document_count", 0) > 0]

    if not datasets:
        print("No knowledge bases found.")
        return

    # Print table
    print(f"{'Name':<35} {'ID':<40} {'Provider':<10} {'Docs':>5} {'Words':>8}")
    print("-" * 100)
    for ds in datasets:
        name = ds.get("name", "N/A")[:34]
        kb_id = ds.get("id", "N/A")[:39]
        provider = ds.get("provider", "?")[:9]
        docs = ds.get("document_count", 0)
        words = ds.get("word_count", 0)
        desc = ds.get("description", "")
        print(f"{name:<35} {kb_id:<40} {provider:<10} {docs:>5} {words:>8}")
        if desc:
            print(f"  {desc[:90]}")

    print(f"\nTotal: {len(datasets)} knowledge base(s)")


# ---------------------------------------------------------------------------
# Docs — list documents in a KB
# ---------------------------------------------------------------------------


def cmd_docs(args, config):
    """List all documents in a knowledge base."""
    profile_name = config.get("profile_name")
    kb = resolve_kb(args.kb, profile_name)
    if kb is None:
        return

    try:
        docs = list_remote_documents(kb["id"], config)
    except Exception as e:
        print(f"[ERROR] Failed to fetch documents: {e}")
        return

    if args.feishu_only:
        docs = [d for d in docs if d.get("data_source_type") == "feishu_import"]

    if not docs:
        label = "Feishu documents" if args.feishu_only else "documents"
        print(f"No {label} found in KB '{kb['name']}'.")
        return

    source_label = {"feishu_import": "feishu", "upload_file": "upload"}
    print(f"KB: {kb['name']}  ({len(docs)} document(s))\n")
    for i, d in enumerate(docs, 1):
        src = source_label.get(d.get("data_source_type", ""), d.get("data_source_type", "?"))
        status = d.get("indexing_status", "?")
        print(f"{i:3}. [{src}] {d['name']}")
        if status not in ("completed", "available"):
            print(f"       status: {status}")


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


def cmd_create(args, config):
    """Create a new empty knowledge base."""
    body = {
        "name": args.name,
        "description": args.description or "",
        "permission": args.permission,
        "provider": args.provider,
        "retrieval_model": RETRIEVAL_MODEL_CONFIG,
        "process_rule": PROCESS_RULE_CUSTOM,
    }

    desc_info = f", description: {args.description}" if args.description else ""
    perm_label = "team" if args.permission == "all_team_members" else "personal"
    print(
        f"Creating knowledge base '{args.name}' (provider: {args.provider}, permission: {perm_label}{desc_info})..."
    )

    try:
        result = mify_request("POST", "/datasets", config, body=body)
    except Exception as e:
        print(f"[ERROR] Failed to create knowledge base: {e}")
        return

    if result is None:
        return

    kb_id = result.get("id", "")
    kb_name = result.get("name", args.name)
    print(f"Created: {kb_name} (ID: {kb_id})")
    refresh_registry(config)

    # Auto-add to active_kbs if whitelist is in use for this profile
    profile_name = config.get("profile_name")
    active_kbs_map = config.get("active_kbs_map", {})
    profile_active = active_kbs_map.get(profile_name)  # None = all allowed
    if isinstance(profile_active, list) and kb_name not in profile_active and kb_id not in profile_active:
        profile_active.append(kb_name)
        active_kbs_map[profile_name] = profile_active
        save_config_field("active_kbs", active_kbs_map)
        print(f"Auto-added '{kb_name}' to active_kbs for profile '{profile_name}'.")


# ---------------------------------------------------------------------------
# Search config (manage active_kbs whitelist, per-profile)
# ---------------------------------------------------------------------------


def cmd_search_config(args, config):
    """View or modify the search KB whitelist for the active profile.

    active_kbs is stored as a per-profile map in project config:
      { "profile-name": ["KB-A"] | null }
    null = all KBs searchable, [] = disabled, [...] = whitelist
    """
    profile_name = config.get("profile_name", "_legacy")
    active_kbs_map = config.get("active_kbs_map", {})
    current = active_kbs_map.get(profile_name)  # None = not set (all allowed)

    def _save_active(new_val):
        """Save updated active_kbs_map to project config."""
        # Read fresh copy to avoid overwriting other profiles' data
        config_path = _mify_dir() / "config.json"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        else:
            raw = {}
        existing_map = raw.get("active_kbs", {})
        if isinstance(existing_map, list):
            # Legacy list: convert first
            existing_map = {profile_name: existing_map}
        existing_map[profile_name] = new_val
        save_config_field("active_kbs", existing_map)

    if args.clear:
        _save_active(None)
        print(f"Cleared active_kbs for profile '{profile_name}'. All KBs are now searchable.")
        return

    if args.disable:
        _save_active([])
        print(f"Set active_kbs to empty list for profile '{profile_name}'. Search disabled.")
        return

    if args.set:
        names = _validate_kb_names(args.set, profile_name)
        _save_active(names)
        print(f"Set active_kbs for profile '{profile_name}': {', '.join(names)}")
        return

    if args.add:
        names = _validate_kb_names(args.add, profile_name)
        base = current if current is not None else []
        updated = list(dict.fromkeys(base + names))
        _save_active(updated)
        print(f"Added to active_kbs [{profile_name}]: {', '.join(names)}")
        print(f"Current whitelist: {', '.join(updated)}")
        return

    if args.remove:
        if current is None:
            print(f"active_kbs for profile '{profile_name}' is not set. Nothing to remove.")
            return
        remove_set = set(args.remove)
        updated = [n for n in current if n not in remove_set]
        removed = remove_set & set(current)
        if removed:
            print(f"Removed from active_kbs [{profile_name}]: {', '.join(removed)}")
        else:
            print("No matching entries found to remove.")
        _save_active(updated)
        if updated:
            print(f"Current whitelist: {', '.join(updated)}")
        else:
            print(
                "Whitelist is now empty — search is disabled.\n"
                "  To allow all KBs: search-config --clear\n"
                '  To add specific KBs: search-config --add "KB Name"'
            )
        return

    # Default: show current config
    if current is None:
        print(f"[Profile: {profile_name}] active_kbs not set — all KBs searchable.")
    elif not current:
        print(
            f"[Profile: {profile_name}] active_kbs is empty — search disabled.\n"
            "  To allow all KBs: search-config --clear\n"
            '  To add specific KBs: search-config --add "KB Name"'
        )
    else:
        print(f"[Profile: {profile_name}] Searchable KBs ({len(current)}):")
        registry = read_kb_registry(profile_name)
        registry_map = {kb["name"]: kb for kb in registry}
        registry_map.update({kb["id"]: kb for kb in registry})
        for name in current:
            kb = registry_map.get(name)
            if kb:
                doc_count = kb.get("document_count", 0)
                print(f"  - {name} ({doc_count} docs)")
            else:
                print(f"  - {name} (not found in registry)")


def _validate_kb_names(names, profile_name=None):
    """Return cleaned list of KB names/IDs, checking they exist in registry."""
    registry = read_kb_registry(profile_name)
    known = {kb["name"] for kb in registry} | {kb["id"] for kb in registry}
    result = []
    for n in names:
        n = n.strip()
        if not n:
            continue
        if n not in known:
            print(
                f"  [WARN] '{n}' not found in registry — adding anyway", file=sys.stderr
            )
        result.append(n)
    return result


# ---------------------------------------------------------------------------
# sync-state — reconcile local state with remote
# ---------------------------------------------------------------------------


def cmd_sync_state(args, config):
    """Sync local KB state file with the remote document list."""
    profile_name = config.get("profile_name")
    kb = resolve_kb(args.kb, profile_name)
    if kb is None:
        return
    kb_id = kb["id"]

    print(f"Syncing state for KB '{kb['name']}' (profile: {profile_name})...")

    try:
        remote_docs = list_remote_documents(kb_id, config)
    except Exception as e:
        print(f"[ERROR] Failed to fetch remote documents: {e}")
        return

    remote_by_id = {d["id"]: d for d in remote_docs}
    state = read_kb_state(kb_id, profile_name)
    local_docs = state.get("documents", {})

    synced = 0
    added = 0
    orphaned = 0
    orphaned_docs = []

    # Update existing local records and mark orphans
    for doc_name, doc_info in list(local_docs.items()):
        doc_id = doc_info.get("doc_id")
        if doc_id in remote_by_id:
            remote = remote_by_id[doc_id]
            doc_info["status"] = remote.get("indexing_status", doc_info.get("status"))
            synced += 1
        else:
            doc_info["status"] = "orphaned"
            orphaned += 1
            orphaned_docs.append({"name": doc_name, "doc_id": doc_id})

    # Add remote docs not tracked locally
    local_doc_ids = {v.get("doc_id") for v in local_docs.values()}
    for remote_doc in remote_docs:
        if remote_doc["id"] not in local_doc_ids:
            doc_name = remote_doc.get("name", remote_doc["id"])
            local_docs[doc_name] = {
                "doc_id": remote_doc["id"],
                "source_type": "unknown",
                "status": remote_doc.get("indexing_status", "synced"),
            }
            added += 1

    state["documents"] = local_docs
    write_kb_state(kb_id, state, profile_name)

    summary = {"synced": synced, "added": added, "orphaned": orphaned, "orphaned_docs": orphaned_docs}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if orphaned_docs:
        print(
            f"\n[WARN] {orphaned} document(s) in local state no longer exist remotely.\n"
            "  They are marked 'orphaned' but NOT deleted from local state.\n"
            "  Run 'purge --kb ...' to clear state and start fresh.",
            file=sys.stderr,
        )


# ---------------------------------------------------------------------------
# purge — clear local KB state
# ---------------------------------------------------------------------------


def cmd_purge(args, config):
    """Delete local state file for a KB."""
    profile_name = config.get("profile_name")
    kb = resolve_kb(args.kb, profile_name)
    if kb is None:
        return
    kb_id = kb["id"]

    state_path = _profile_state_dir(profile_name) / f"{kb_id}.json"
    if not state_path.exists():
        print(f"No local state found for KB '{kb['name']}' (profile: {profile_name}). Nothing to purge.")
        return

    state_path.unlink()
    print(f"Purged local state for KB '{kb['name']}' (profile: {profile_name}).")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _add_profile_arg(parser):
    """Add --profile optional argument to a subparser."""
    parser.add_argument(
        "--profile", default=None, help="Profile name (default: from config)"
    )


def main():
    parser = argparse.ArgumentParser(description="Manage Mify knowledge bases")
    sub = parser.add_subparsers(dest="command", required=True)

    # list
    p_list = sub.add_parser("list", help="List all knowledge bases")
    p_list.add_argument(
        "--hide-empty", action="store_true", help="Hide KBs with no documents"
    )
    _add_profile_arg(p_list)

    # docs
    p_docs = sub.add_parser("docs", help="List documents in a knowledge base")
    p_docs.add_argument("--kb", required=True, help="Knowledge base name or ID")
    p_docs.add_argument(
        "--feishu-only", action="store_true", help="Show only Feishu-imported documents"
    )
    _add_profile_arg(p_docs)

    # create
    p_create = sub.add_parser("create", help="Create a new knowledge base")
    p_create.add_argument("--name", required=True, help="Knowledge base name")
    p_create.add_argument(
        "--description", default="", help="Knowledge base description"
    )
    p_create.add_argument(
        "--provider",
        default="vendor",
        choices=["vendor", "mibrag"],
        help="Provider type (default: vendor)",
    )
    p_create.add_argument(
        "--permission",
        default="only_me",
        choices=["only_me", "all_team_members"],
        help="Visibility: only_me (default) or all_team_members",
    )
    _add_profile_arg(p_create)

    # search-config
    p_sc = sub.add_parser("search-config", help="Manage searchable KB whitelist")
    sc_group = p_sc.add_mutually_exclusive_group()
    sc_group.add_argument(
        "--set", nargs="+", metavar="KB", help="Set search whitelist (replace)"
    )
    sc_group.add_argument("--add", nargs="+", metavar="KB", help="Add KBs to whitelist")
    sc_group.add_argument(
        "--remove", nargs="+", metavar="KB", help="Remove KBs from whitelist"
    )
    sc_group.add_argument(
        "--clear", action="store_true", help="Remove active_kbs (all KBs searchable)"
    )
    sc_group.add_argument(
        "--disable",
        action="store_true",
        help="Set active_kbs to empty list (disable search)",
    )
    _add_profile_arg(p_sc)

    # sync-state
    p_sync = sub.add_parser("sync-state", help="Sync local state with remote KB")
    p_sync.add_argument("--kb", required=True, help="Knowledge base name or ID")
    _add_profile_arg(p_sync)

    # purge
    p_purge = sub.add_parser("purge", help="Delete local state file for a KB")
    p_purge.add_argument("--kb", required=True, help="Knowledge base name or ID")
    _add_profile_arg(p_purge)

    args = parser.parse_args()
    config = load_config(profile_name=args.profile)
    if config is None:
        return

    if args.command == "list":
        cmd_list(args, config)
    elif args.command == "docs":
        cmd_docs(args, config)
    elif args.command == "create":
        cmd_create(args, config)
    elif args.command == "search-config":
        cmd_search_config(args, config)
    elif args.command == "sync-state":
        cmd_sync_state(args, config)
    elif args.command == "purge":
        cmd_purge(args, config)


if __name__ == "__main__":
    main()
