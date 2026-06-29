#!/usr/bin/env python3
"""
Update documents in a Mify knowledge base.

Usage:
    python update_documents.py local --kb "My KB" --dir ./docs
    python update_documents.py feishu-sync --kb "My KB" --all
    python update_documents.py feishu-sync --kb "My KB" --doc-ids DOC_ID_1 DOC_ID_2
    python update_documents.py set-frequency --kb "My KB" --frequency 3
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from mify_client import (
    SUPPORTED_EXTENSIONS,
    compute_file_hash,
    list_remote_documents,
    load_config,
    mify_request,
    read_kb_state,
    refresh_registry,
    resolve_kb,
    upload_file,
    write_kb_state,
)

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
# Local update by hash comparison
# ---------------------------------------------------------------------------


def cmd_local(args, config):
    """Update local documents by comparing SHA256 hashes."""
    profile_name = config.get("profile_name")
    kb = resolve_kb(args.kb, profile_name)
    if kb is None:
        return
    kb_id = kb["id"]
    dir_path = Path(args.dir)

    if not dir_path.is_dir():
        print(f"[ERROR] Directory not found: {dir_path}")
        return

    state = read_kb_state(kb_id, profile_name)
    if not state.get("documents"):
        print(
            f"[ERROR] No documents tracked for KB '{kb['name']}'.\n"
            f"  Use create_documents.py to add documents first."
        )
        return

    # Scan local files
    local_files = sorted(
        f
        for f in dir_path.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    )

    tracked_docs = state.get("documents", {})
    updated = 0
    unchanged = 0
    untracked = []
    missing = []

    for f in local_files:
        if f.name not in tracked_docs:
            untracked.append(f.name)
            continue

        doc_info = tracked_docs[f.name]
        current_hash = compute_file_hash(f)
        stored_hash = doc_info.get("file_hash", "")

        if current_hash == stored_hash:
            unchanged += 1
            continue

        # File changed — update via API
        doc_id = doc_info.get("doc_id", "")
        print(f"Updating: {f.name} (hash changed)...")
        data_json = json.dumps(
            {
                "indexing_technique": "high_quality",
                "process_rule": PROCESS_RULE_CUSTOM,
            }
        )

        try:
            upload_file(
                f"/datasets/{kb_id}/documents/{doc_id}/update-by-file",
                f,
                config,
                data_json=data_json,
            )
            state["documents"][f.name]["file_hash"] = current_hash
            state["documents"][f.name]["status"] = "updated"
            write_kb_state(kb_id, state, profile_name)
            print("  Updated successfully")
            updated += 1
        except Exception as e:
            print(f"  [ERROR] {e}")

    # Check for tracked files that are missing locally
    for name in tracked_docs:
        if tracked_docs[name].get("source_type") == "local":
            local_path = dir_path / name
            if not local_path.exists() and name not in [f.name for f in local_files]:
                missing.append(name)

    # Summary
    print(f"\nSummary: {updated} updated, {unchanged} unchanged")

    if untracked:
        print(
            f"\n[WARN] {len(untracked)} untracked file(s) — use create_documents.py to add them:"
        )
        for name in untracked:
            print(f"  - {name}")

    if missing:
        print(f"\n[WARN] {len(missing)} tracked file(s) missing locally (skipped):")
        for name in missing:
            print(f"  - {name}")

    if updated == 0 and unchanged > 0 and not untracked:
        print("\nAll files up to date, nothing to update.")
    elif updated > 0:
        refresh_registry(config)


# ---------------------------------------------------------------------------
# Feishu sync
# ---------------------------------------------------------------------------


def cmd_feishu_sync(args, config):
    """Sync Feishu documents in a KB."""
    kb = resolve_kb(args.kb, config.get("profile_name"))
    if kb is None:
        return
    kb_id = kb["id"]

    if args.all:
        # Auto-discover all feishu_import documents in the KB
        print(f"Fetching all Feishu documents in KB '{kb['name']}'...")
        try:
            remote_docs = list_remote_documents(kb_id, config)
        except Exception as e:
            print(f"[ERROR] Failed to fetch remote documents: {e}")
            return
        doc_ids = [d["id"] for d in remote_docs if d.get("data_source_type") == "feishu_import"]
        if not doc_ids:
            print("No Feishu documents found in this KB.")
            return
        print(f"Found {len(doc_ids)} Feishu document(s).")
    else:
        doc_ids = args.doc_ids if args.doc_ids else []
        if not doc_ids:
            print(
                "[ERROR] Specify --all to sync all Feishu documents, or --doc-ids DOC_ID ..."
            )
            return

    print(f"Syncing {len(doc_ids)} Feishu document(s) in KB '{kb['name']}'...")

    try:
        result = mify_request(
            "POST",
            f"/datasets/{kb_id}/documents/feishu/sync",
            config,
            body={"document_ids": doc_ids},
            require_email=True,
        )
    except Exception as e:
        print(f"[ERROR] Feishu sync failed: {e}")
        return

    if result is None:
        return

    if result.get("result") == "success":
        print("Sync initiated successfully.")
        refresh_registry(config)
    else:
        print(f"Sync response: {result}")


# ---------------------------------------------------------------------------
# Set frequency
# ---------------------------------------------------------------------------


def cmd_set_frequency(args, config):
    """Set Feishu document sync frequency."""
    kb = resolve_kb(args.kb, config.get("profile_name"))
    if kb is None:
        return
    kb_id = kb["id"]

    frequency = int(args.frequency)
    doc_ids = args.doc_ids

    if not doc_ids:
        print(
            "[ERROR] --doc-ids is required. Specify one or more document IDs."
        )
        return

    documents = [{"document_id": d, "frequency": frequency} for d in doc_ids]

    print(
        f"Setting sync frequency to {frequency} for {len(documents)} document(s) in KB '{kb['name']}'..."
    )

    try:
        mify_request(
            "POST",
            f"/datasets/{kb_id}/documents/update-frequency",
            config,
            body={"documents": documents},
            require_email=True,
        )
        print(f"Sync frequency set to: {frequency}")
    except Exception as e:
        print(f"[ERROR] {e}")
        return


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _add_profile_arg(parser):
    """Add --profile optional argument to a subparser."""
    parser.add_argument(
        "--profile", default=None, help="Profile name (default: from config)"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Update documents in a Mify knowledge base"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # local
    p_local = sub.add_parser("local", help="Update local files by hash comparison")
    p_local.add_argument("--kb", required=True, help="KB name or ID")
    p_local.add_argument("--dir", required=True, help="Local directory path")
    _add_profile_arg(p_local)

    # feishu-sync
    p_sync = sub.add_parser("feishu-sync", help="Sync Feishu documents")
    p_sync.add_argument("--kb", required=True, help="KB name or ID")
    sync_group = p_sync.add_mutually_exclusive_group()
    sync_group.add_argument(
        "--all", action="store_true", help="Sync all Feishu documents in the KB"
    )
    sync_group.add_argument(
        "--doc-ids", nargs="+", help="Specific document IDs to sync"
    )
    _add_profile_arg(p_sync)

    # set-frequency
    p_freq = sub.add_parser("set-frequency", help="Set Feishu sync frequency")
    p_freq.add_argument("--kb", required=True, help="KB name or ID")
    p_freq.add_argument("--frequency", required=True, help="Sync frequency value")
    p_freq.add_argument(
        "--doc-ids", required=True, nargs="+", help="Document IDs to update"
    )
    _add_profile_arg(p_freq)

    args = parser.parse_args()
    config = load_config(profile_name=args.profile)
    if config is None:
        return

    if args.command == "local":
        cmd_local(args, config)
    elif args.command == "feishu-sync":
        cmd_feishu_sync(args, config)
    elif args.command == "set-frequency":
        cmd_set_frequency(args, config)


if __name__ == "__main__":
    main()
