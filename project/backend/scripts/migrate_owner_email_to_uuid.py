"""One-shot migration: remap any task whose ``owner_id`` is an email/login to
the canonical UUID stored in the users registry.

Background: the dev_bypass / Aegis auth paths used to set ``user["id"] =
email`` while password-login set it to the registered uuid. Tasks created
under each path got siloed into different ``users/{id}/`` directories, so
admins saw a "split" Dashboard depending on how they authenticated.

After deps.py is fixed to always canonicalize to the UUID, this script
brings historical data in line:

* SQLite ``tasks_index.owner_id`` rewritten to the canonical id
* ``tasks/{tid}/meta.json#owner_id`` rewritten
* ``tasks/{tid}/collaborators.json`` entries rewritten
* per-user task index merged (``users/{email}/tasks/index.json`` →
  ``users/{uuid}/tasks/index.json``)
* per-user audit log appended (kept for traceability)
* The ``users/{email}/`` directory is left in place but emptied of duplicated
  data; you can ``rm -rf`` it manually after eyeballing the result.

Run from the repo root:

    cd backend && . .venv/bin/activate && python scripts/migrate_owner_email_to_uuid.py
"""
from __future__ import annotations

import asyncio
import json
import re
import shutil
from pathlib import Path

# Make `app` importable when running directly.
import sys

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from app.core.storage import get_index_db, get_paths, read_json, write_json  # noqa: E402
from app.services.auth_svc import load_user_by_email  # noqa: E402

UUID_HEX = re.compile(r"^[0-9a-f]{32}$")


def looks_like_uuid(s: str) -> bool:
    return bool(s) and bool(UUID_HEX.match(s))


async def main() -> None:
    paths = get_paths()
    db = get_index_db()

    # 1. Discover non-uuid owner_ids in tasks_index.
    rows = await db.fetchall(
        "SELECT id, name, owner_id FROM tasks_index ORDER BY updated_at DESC", []
    )
    if not rows:
        print("tasks_index empty — nothing to do.")
        return

    bad: dict[str, list[dict]] = {}
    for r in rows:
        oid = r["owner_id"] or ""
        if not looks_like_uuid(oid):
            bad.setdefault(oid, []).append(dict(r))
    if not bad:
        print("✓ All tasks already keyed on canonical UUID owner_id. No migration needed.")
        return

    print(f"Found {sum(len(v) for v in bad.values())} task(s) under non-canonical owner_id:")
    for oid, items in bad.items():
        print(f"  • '{oid}'  ×{len(items)}")
    print()

    # 2. For each suspicious owner_id, look up the canonical uuid via email.
    remap: dict[str, str] = {}
    for oid in bad:
        canon = await load_user_by_email(oid)
        if not canon:
            print(f"  ! '{oid}' has no matching user in the registry — skipping ({len(bad[oid])} tasks)")
            continue
        canon_id = canon["id"]
        if canon_id == oid:
            print(f"  - '{oid}' already canonical, skipping")
            continue
        remap[oid] = canon_id
        print(f"  → '{oid}'  =>  '{canon_id}'  ({canon.get('name')})")
    if not remap:
        print("Nothing to remap.")
        return
    print()

    # 3. SQLite tasks_index update.
    for old_id, new_id in remap.items():
        n = await db.execute(
            "UPDATE tasks_index SET owner_id = ? WHERE owner_id = ?",
            [new_id, old_id],
        )
        print(f"sqlite: tasks_index '{old_id}' → '{new_id}': {n} row(s)")

    # 4. Update each task's meta.json + collaborators.json.
    for old_id, new_id in remap.items():
        for r in bad[old_id]:
            tid = r["id"]
            meta_path = paths.task_meta(tid)
            meta = read_json(meta_path)
            if meta and meta.get("owner_id") == old_id:
                meta["owner_id"] = new_id
                if meta.get("created_by") == old_id:
                    meta["created_by"] = new_id
                write_json(meta_path, meta)
                print(f"meta: tasks/{tid}/meta.json owner_id → {new_id}")
            collab_path = paths.task_collaborators(tid)
            collabs = read_json(collab_path, default=[]) or []
            changed = False
            for c in collabs:
                if c.get("user_id") == old_id:
                    c["user_id"] = new_id
                    changed = True
            if changed:
                write_json(collab_path, collabs)
                print(f"collab: tasks/{tid}/collaborators.json updated")

    # 5. Merge per-user tasks index files.
    for old_id, new_id in remap.items():
        old_idx_path = paths.user_tasks_index(old_id)
        new_idx_path = paths.user_tasks_index(new_id)
        old_entries = read_json(old_idx_path, default=[]) or []
        if not old_entries:
            continue
        # Ensure the new user dir exists (auto-provisioned by ensure_user_for_email).
        new_idx_path.parent.mkdir(parents=True, exist_ok=True)
        new_entries = read_json(new_idx_path, default=[]) or []
        seen_tids = {e.get("task_id") for e in new_entries}
        added = 0
        for e in old_entries:
            tid = e.get("task_id")
            if not tid or tid in seen_tids:
                continue
            new_entries.append(e)
            seen_tids.add(tid)
            added += 1
        # Sort by added_at DESC to keep the recently-created on top.
        new_entries.sort(key=lambda x: x.get("added_at") or "", reverse=True)
        write_json(new_idx_path, new_entries)
        # Empty out the old per-user index to prevent stale reads.
        write_json(old_idx_path, [])
        print(f"index merge: users/{old_id}/tasks/index.json → users/{new_id}/tasks/index.json (+{added})")

    # 6. Move audit log if any (append rather than truncate).
    for old_id, new_id in remap.items():
        old_audit = paths.user_dir(old_id) / "audit"
        new_audit = paths.user_dir(new_id) / "audit"
        if old_audit.exists():
            new_audit.mkdir(parents=True, exist_ok=True)
            for f in sorted(old_audit.glob("*.jsonl")):
                target = new_audit / f.name
                if target.exists():
                    target.write_bytes(target.read_bytes() + f.read_bytes())
                else:
                    shutil.copyfile(f, target)
                f.unlink()
                print(f"audit: merged {f.relative_to(paths.root)} → {target.relative_to(paths.root)}")

    print()
    print("✓ Migration done.")
    print()
    print("Stale directories (safe to remove after eyeballing):")
    for old_id in remap:
        d = paths.user_dir(old_id)
        if d.exists():
            print(f"  rm -rf {d.relative_to(paths.root)}")


if __name__ == "__main__":
    asyncio.run(main())
