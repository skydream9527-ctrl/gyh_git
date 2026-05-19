"""Python sandbox tests.

Covers:
    - happy path: code executes, stdout captured, files registered
    - exception in user code → status=ERROR with traceback in stderr
    - timeout (busy loop) → status=TIMEOUT, killed within deadline
    - network blocked → AF_INET socket raises OSError
    - file inventory: only NEW files reported, not pre-existing ones
    - missing venv → SETUP_ERROR (not crash)
    - stdout truncation
    - validation: empty code → VALIDATION_ERROR (via tool layer)

Most tests use the parent's interpreter (sys.executable) as fallback
because the .venv-sandbox isn't installed in CI by default. The flag
ICE_PYTHON_SANDBOX_E2E_VENV=1 enables full venv tests (Prophet etc.).
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import pytest

from app.services.sandbox import run_python
from app.services.sandbox.types import SandboxStatus


# ---- helpers ---------------------------------------------------------------

def _make_task_dir(root: Path, task_id: str = "t-test") -> Path:
    """Layout matches paths.task_dir(task_id)."""
    td = root / "tasks" / task_id
    (td / "files" / "output").mkdir(parents=True, exist_ok=True)
    return td


def _run(code: str, task_dir: Path, **kw):
    """Sync wrapper for the async sandbox API."""
    return asyncio.run(run_python(
        code,
        task_dir=task_dir,
        venv_python=kw.pop("venv_python", sys.executable),
        **kw,
    ))


# ---- happy path -----------------------------------------------------------

def test_happy_path_print_and_write(isolated_data_root):
    td = _make_task_dir(isolated_data_root)
    code = (
        "print('hello')\n"
        "with open('data.csv', 'w') as f:\n"
        "    f.write('a,b\\n1,2\\n')\n"
    )
    r = _run(code, td)
    assert r.status == SandboxStatus.OK, r.error_message
    assert "hello" in r.stdout
    assert any(f.relpath == "data.csv" and f.kind == "csv"
               for f in r.files_created)
    # the file actually exists on disk
    assert (td / "files" / "output" / "data.csv").read_text() == "a,b\n1,2\n"


def test_inventory_excludes_preexisting(isolated_data_root):
    td = _make_task_dir(isolated_data_root)
    out = td / "files" / "output"
    (out / "preexisting.txt").write_text("old")
    code = (
        "with open('new.txt', 'w') as f:\n"
        "    f.write('new')\n"
    )
    r = _run(code, td)
    assert r.status == SandboxStatus.OK
    rels = [f.relpath for f in r.files_created]
    assert "new.txt" in rels
    assert "preexisting.txt" not in rels


# ---- exceptions ------------------------------------------------------------

def test_user_exception_yields_error_status(isolated_data_root):
    td = _make_task_dir(isolated_data_root)
    code = "raise ValueError('boom')"
    r = _run(code, td)
    assert r.status == SandboxStatus.ERROR
    assert "ValueError" in (r.error_message or "")
    assert "boom" in r.stderr


def test_syntax_error(isolated_data_root):
    td = _make_task_dir(isolated_data_root)
    code = "def(:\n"  # invalid
    r = _run(code, td)
    assert r.status == SandboxStatus.ERROR
    assert "SyntaxError" in (r.error_message or "") or "SyntaxError" in r.stderr


# ---- timeout ---------------------------------------------------------------

def test_timeout_kills_busy_loop(isolated_data_root):
    td = _make_task_dir(isolated_data_root)
    code = "while True: pass"
    r = _run(code, td, timeout_sec=2)
    # RLIMIT_CPU usually kills the child at cpu_sec exactly (status=KILLED).
    # asyncio.wait_for is a backstop (status=TIMEOUT). Either is correct.
    assert r.status in (SandboxStatus.KILLED, SandboxStatus.TIMEOUT)
    assert r.duration_ms < 8000


# ---- network block ---------------------------------------------------------

def test_inet_socket_blocked(isolated_data_root):
    td = _make_task_dir(isolated_data_root)
    code = (
        "import socket\n"
        "try:\n"
        "    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)\n"
        "    print('NETWORK_LEAK')\n"
        "except OSError as e:\n"
        "    print('blocked:', str(e))\n"
    )
    r = _run(code, td)
    assert r.status == SandboxStatus.OK
    assert "blocked" in r.stdout
    assert "NETWORK_LEAK" not in r.stdout


def test_dns_blocked(isolated_data_root):
    td = _make_task_dir(isolated_data_root)
    code = (
        "import socket\n"
        "try:\n"
        "    socket.getaddrinfo('example.com', 80)\n"
        "    print('DNS_LEAK')\n"
        "except OSError as e:\n"
        "    print('dns blocked:', str(e))\n"
    )
    r = _run(code, td)
    assert r.status == SandboxStatus.OK
    assert "dns blocked" in r.stdout
    assert "DNS_LEAK" not in r.stdout


# ---- env scrub -------------------------------------------------------------

def test_credentials_not_in_env(isolated_data_root, monkeypatch):
    """Parent has KYUUBI_TOKEN; child must not see it."""
    monkeypatch.setenv("KYUUBI_TOKEN", "secret-token")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "ant-secret")
    monkeypatch.setenv("MIFY_GATEWAY_API_KEY", "mify-secret")
    td = _make_task_dir(isolated_data_root)
    code = (
        "import os\n"
        "leaks = [k for k in os.environ "
        "         if 'TOKEN' in k or 'KEY' in k or 'SECRET' in k]\n"
        "print('LEAKS:', leaks)\n"
    )
    r = _run(code, td)
    assert r.status == SandboxStatus.OK
    assert "KYUUBI_TOKEN" not in r.stdout
    assert "ANTHROPIC_API_KEY" not in r.stdout
    assert "MIFY_GATEWAY_API_KEY" not in r.stdout


# ---- cwd jail (relative) ---------------------------------------------------

def test_cwd_is_task_output(isolated_data_root):
    td = _make_task_dir(isolated_data_root)
    code = "import os; print('cwd:', os.getcwd())"
    r = _run(code, td)
    assert r.status == SandboxStatus.OK
    assert str(td / "files" / "output") in r.stdout


# ---- output truncation -----------------------------------------------------

def test_stdout_truncation(isolated_data_root):
    td = _make_task_dir(isolated_data_root)
    # 16KB of output, sandbox limit is 8KB
    code = "print('x' * 16384)"
    r = _run(code, td)
    assert r.status == SandboxStatus.OK
    assert r.truncated
    assert len(r.stdout.encode("utf-8")) < 16 * 1024


# ---- setup error -----------------------------------------------------------

def test_missing_venv_python_returns_setup_error(isolated_data_root):
    td = _make_task_dir(isolated_data_root)
    r = _run("print('x')", td, venv_python="/nope/no/python")
    assert r.status == SandboxStatus.SETUP_ERROR


def test_missing_task_dir_returns_setup_error(isolated_data_root):
    r = asyncio.run(run_python(
        "print('x')",
        task_dir=isolated_data_root / "tasks" / "does-not-exist",
        venv_python=sys.executable,
    ))
    assert r.status == SandboxStatus.SETUP_ERROR


# ---- validation (tool-layer) -----------------------------------------------

def test_tool_layer_empty_code():
    """Verify the tool wrapper rejects empty code without spawning."""
    from app.services.tool_runner import _tool_execute_python
    res = asyncio.run(_tool_execute_python({"code": ""}, ctx={"task_id": "x", "user_id": "y"}))
    assert res.get("error_code") == "VALIDATION_ERROR"


def test_tool_layer_no_task_context():
    from app.services.tool_runner import _tool_execute_python
    res = asyncio.run(_tool_execute_python({"code": "print(1)"}, ctx={}))
    assert res.get("error_code") == "VALIDATION_ERROR"
    assert "task context" in res.get("message", "")


# ---- imports work ----------------------------------------------------------

def test_basic_stdlib_imports(isolated_data_root):
    td = _make_task_dir(isolated_data_root)
    code = (
        "import json, math, statistics, csv\n"
        "print(math.pi, json.dumps([1, 2]))\n"
    )
    r = _run(code, td)
    assert r.status == SandboxStatus.OK
    assert "3.14159" in r.stdout


# ---- venv-only smoke (skipped unless venv installed) -----------------------

VENV_PY = Path(__file__).resolve().parents[2] / "backend" / ".venv-sandbox" / "bin" / "python"


@pytest.mark.skipif(not VENV_PY.exists(),
                    reason="sandbox venv not bootstrapped (run `make install-sandbox`)")
def test_venv_pandas_numpy_smoke(isolated_data_root):
    """End-to-end: load pandas, write a CSV via DataFrame, matplotlib PNG."""
    td = _make_task_dir(isolated_data_root)
    code = (
        "import pandas as pd\n"
        "import numpy as np\n"
        "import matplotlib\n"
        "matplotlib.use('Agg')\n"
        "import matplotlib.pyplot as plt\n"
        "df = pd.DataFrame({'x': np.arange(10), 'y': np.arange(10)**2})\n"
        "df.to_csv('out.csv', index=False)\n"
        "fig, ax = plt.subplots()\n"
        "ax.plot(df['x'], df['y']); ax.set_title('smoke')\n"
        "fig.savefig('chart.png'); plt.close(fig)\n"
        "print('rows:', len(df))\n"
    )
    r = _run(code, td, venv_python=str(VENV_PY))
    assert r.status == SandboxStatus.OK, r.error_message or r.stderr
    rels = {f.relpath: f for f in r.files_created}
    assert "out.csv" in rels and rels["out.csv"].kind == "csv"
    assert "chart.png" in rels and rels["chart.png"].kind == "png"
    assert rels["chart.png"].size_bytes > 1000   # actual PNG
