#!/usr/bin/env bash
# Bootstrap the Python sandbox venv at backend/.venv-sandbox/.
# Idempotent: re-running upgrades the packages in place.
#
# Used by:
#   - Makefile install-sandbox target
#   - deploy.sh --prod (one-shot during deploy)
#   - manual: bash backend/scripts/bootstrap_sandbox_venv.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV="${BACKEND_DIR}/.venv-sandbox"
REQ="${BACKEND_DIR}/requirements.sandbox.txt"

PY_BIN="${PYTHON_BIN:-python3}"

if [[ ! -d "${VENV}" ]]; then
  echo "→ creating sandbox venv at ${VENV}"
  "${PY_BIN}" -m venv "${VENV}"
fi

# pip install with --upgrade so re-running picks up requirements.sandbox.txt changes
echo "→ installing sandbox requirements (this can take 1-2 minutes; prophet is heavy)"
"${VENV}/bin/python" -m pip install --upgrade pip wheel >/dev/null
"${VENV}/bin/python" -m pip install --upgrade -r "${REQ}"

echo "→ verifying critical imports"
"${VENV}/bin/python" - <<'PY'
import importlib
for mod in ("numpy", "pandas", "scipy", "sklearn", "statsmodels",
            "prophet", "ruptures", "matplotlib", "seaborn", "pyarrow"):
    importlib.import_module(mod)
    print(f"  ok  {mod}")
PY

echo "✓ sandbox venv ready: ${VENV}"
