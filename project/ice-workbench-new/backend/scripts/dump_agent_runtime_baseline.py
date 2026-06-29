"""Record the pre-refactor golden baseline for agent-runtime-consolidation.

Dumps, for every real on-disk agent:
  * tool_schemas.json  — get_anthropic_tools(...) output across 5 scenarios
  * agent_config.json  — every agents_svc.get_agent_* getter output

Run BEFORE the P1/P2 refactor so the comparison test
(tests/test_agent_runtime_baseline.py) can prove zero behavior drift after it.

    cd backend && . .venv/bin/activate && python scripts/dump_agent_runtime_baseline.py

The snapshot is computed in a throwaway temp DATA_ROOT seeded with a *copy* of
the real agents/ dir, so this never mutates the repo's agent files.

Design ref: agent-runtime-consolidation tasks.md Task 0.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

# Make `tests` package importable (backend/ on sys.path) and reuse the shared
# snapshot helpers so the dump and the test compute identically.
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="ice-baseline-"))
    for sub in ("agents", "skills", "files", "users", "tasks", ".cache"):
        (tmp / sub).mkdir(parents=True, exist_ok=True)
    os.environ["DATA_ROOT"] = str(tmp)
    os.environ.setdefault("ICE_SECRET_KEY", "baseline-secret-key-with-enough-length-32b")

    # Import after DATA_ROOT is set so cached settings/paths resolve to tmp.
    from app.core import config as cfg
    from app.core.storage import paths as p
    from tests.baseline_support import (
        AGENT_CONFIG_FILE,
        BASELINE_DIR,
        TOOL_SCHEMAS_FILE,
        compute_agent_config_snapshot,
        compute_tool_schema_snapshot,
        seed_real_agents,
    )

    cfg.get_settings.cache_clear()
    p.get_paths.cache_clear()
    seed_real_agents(tmp)

    BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    tool_snap = compute_tool_schema_snapshot()
    cfg_snap = compute_agent_config_snapshot()

    TOOL_SCHEMAS_FILE.write_text(
        json.dumps(tool_snap, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    AGENT_CONFIG_FILE.write_text(
        json.dumps(cfg_snap, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"  ✓ wrote {TOOL_SCHEMAS_FILE.relative_to(BACKEND_DIR)} "
          f"({len(tool_snap)} agents)")
    print(f"  ✓ wrote {AGENT_CONFIG_FILE.relative_to(BACKEND_DIR)} "
          f"({len(cfg_snap)} agents)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
