"""Main sandbox API: run_python(code, *, task_dir, ...) -> SandboxResult."""
from __future__ import annotations

import asyncio
import json
import os
import platform
import signal
import sys
import tempfile
import time
import uuid
from pathlib import Path

from .preexec import make_preexec
from .types import SandboxFile, SandboxResult, SandboxStatus


STDOUT_MAX_BYTES = 8 * 1024
STDERR_MAX_BYTES = 8 * 1024

_SANDBOX_DIR = Path(__file__).resolve().parent
RUNNER_SCRIPT = _SANDBOX_DIR / "python_runner.py"

# Project root: backend/app/services/sandbox/ → ../../../../  → repo root
_REPO_ROOT = _SANDBOX_DIR.parents[3]
DEFAULT_VENV_PYTHON = _REPO_ROOT / "backend" / ".venv-sandbox" / "bin" / "python"


def _resolve_executable(custom: str | None = None) -> Path:
    # IMPORTANT: do NOT call `.resolve()` — that follows symlinks, and
    # `.venv-sandbox/bin/python` is a symlink chain to `/usr/bin/python3`.
    # If we resolve through the chain, subprocess ends up invoking system
    # Python directly, which can no longer locate the venv's pyvenv.cfg /
    # site-packages, and `import pandas` fails. Use `.absolute()` so we get
    # an absolute path without dereferencing symlinks.
    if custom:
        return Path(custom).absolute()
    if DEFAULT_VENV_PYTHON.exists():
        return DEFAULT_VENV_PYTHON
    # Fallback: parent's interpreter (development convenience; tests will
    # complain if pandas/prophet missing, but the sandbox itself works).
    return Path(sys.executable)


def _build_clean_env(*, venv_python: Path, task_dir: Path) -> dict[str, str]:
    """Strip the parent process env down to a minimal known set.

    Removed: HTTP_PROXY/HTTPS_PROXY/NO_PROXY, AWS_*, GCP_*, KYUUBI_*,
    ANTHROPIC_*, MIFY_*, OPENAI_*, FEISHU_*, anything containing TOKEN/KEY/
    SECRET/PASSWORD. The sandbox should never see service credentials.
    """
    venv_bin = str(venv_python.parent)
    minimal = {
        "PATH": f"{venv_bin}:/usr/bin:/bin",
        "HOME": str(task_dir),
        "TMPDIR": str(task_dir),
        "PYTHONUNBUFFERED": "1",
        # Force matplotlib non-interactive backend so it doesn't try to open
        # a GUI window in the sandbox (which would fail and waste time)
        "MPLBACKEND": "Agg",
        # Headless prophet
        "PROPHET_NO_PLOTLY": "1",
        # Pandas defaults
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        # BLAS single-thread: numpy / scipy / sklearn pull in OpenBLAS / MKL,
        # which by default spawn one worker thread per logical CPU on import.
        # Under RLIMIT_NPROC (or a busy machine where the per-UID thread count
        # is near limit), pthread_create fails repeatedly, the import path
        # raises a flood of warnings and eventually deadlocks. Forcing 1
        # thread keeps imports cheap and avoids the issue on every host.
        "OPENBLAS_NUM_THREADS": "1",
        "OMP_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1",
        "VECLIB_MAXIMUM_THREADS": "1",
    }
    # Carry over any safe vars the parent has explicitly opted in to
    return minimal


def _truncate(b: bytes, limit: int) -> tuple[str, bool]:
    if len(b) <= limit:
        return b.decode("utf-8", errors="replace"), False
    return b[:limit].decode("utf-8", errors="replace") + "\n…[truncated]", True


async def _read_capped(stream: asyncio.StreamReader, limit: int) -> bytes:
    """Read until EOF or limit+1024 bytes (so we can detect truncation)."""
    chunks: list[bytes] = []
    total = 0
    cap = limit + 1024
    while True:
        chunk = await stream.read(4096)
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
        if total >= cap:
            # drain rest to allow process to flush + exit cleanly
            try:
                while True:
                    rest = await stream.read(8192)
                    if not rest:
                        break
            except Exception:
                pass
            break
    return b"".join(chunks)


async def run_python(
    code: str,
    *,
    task_dir: Path | str,
    timeout_sec: int = 60,
    memory_mb: int = 1024,
    fsize_mb: int = 50,
    # RLIMIT_NPROC is per-UID, not per-process — it counts ALL threads/procs
    # owned by the same user, so on a shared dev box the user typically has
    # thousands of background processes already. A low cap (e.g. 32) makes
    # any subsequent fork()/pthread_create() inside the sandbox fail
    # immediately, breaking matplotlib's font-cache thread, BLAS, etc.
    # Setting it high prevents that hard fail; it's not real fork-bomb
    # defense (proper containment needs cgroups / pid namespaces) but it
    # caps a runaway code path at "many but bounded".
    nproc: int = 4096,
    # Same per-UID story for NOFILE; keep it generous for libs that open
    # many .so / data files at import.
    nofile: int = 1024,
    venv_python: str | None = None,
    description: str = "",
) -> SandboxResult:
    """Execute `code` in a sandboxed subprocess; return SandboxResult.

    Args:
        code: User Python code (raw source).
        task_dir: tasks/{tid}/ — the workspace root. cwd will be set to
                  task_dir/files/output/ so relative writes land there.
        timeout_sec: Wall-clock + RLIMIT_CPU. Hard SIGKILL on overrun.
        memory_mb: RLIMIT_AS in MB (Linux only; macOS skipped).
        fsize_mb: RLIMIT_FSIZE in MB.
        nproc: RLIMIT_NPROC.
        nofile: RLIMIT_NOFILE.
        venv_python: Override interpreter; defaults to .venv-sandbox/bin/python.
        description: Free-form context (audit only).

    Returns:
        SandboxResult with status, stdout, stderr, files_created list.
    """
    task_dir = Path(task_dir).resolve()
    if not task_dir.exists():
        return SandboxResult(
            status=SandboxStatus.SETUP_ERROR,
            stdout="", stderr="",
            error_message=f"task_dir does not exist: {task_dir}",
        )

    # cwd: tasks/{tid}/files/output/ — created if missing
    cwd = task_dir / "files" / "output"
    cwd.mkdir(parents=True, exist_ok=True)

    # Place user code inside .python_runs/, with a unique id
    runs_dir = task_dir / ".python_runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex[:12]
    code_path = runs_dir / f"{run_id}.py"
    code_path.write_text(code, encoding="utf-8")

    venv_py = _resolve_executable(venv_python)
    if not venv_py.exists():
        return SandboxResult(
            status=SandboxStatus.SETUP_ERROR,
            stdout="", stderr="",
            error_message=(
                f"sandbox python interpreter not found at {venv_py}. "
                f"Run `make install-sandbox` to bootstrap."
            ),
        )

    if not RUNNER_SCRIPT.exists():
        return SandboxResult(
            status=SandboxStatus.SETUP_ERROR,
            stdout="", stderr="",
            error_message=f"runner script missing at {RUNNER_SCRIPT}",
        )

    # pipe for the result inventory (separate from stdout/stderr)
    result_r, result_w = os.pipe()
    os.set_inheritable(result_w, True)

    env = _build_clean_env(venv_python=venv_py, task_dir=task_dir)

    preexec = make_preexec(
        cpu_sec=timeout_sec,
        memory_mb=memory_mb,
        fsize_mb=fsize_mb,
        nproc=nproc,
        nofile=nofile,
    ) if platform.system() in ("Linux", "Darwin") else None

    started = time.monotonic()
    proc: asyncio.subprocess.Process | None = None
    timed_out = False
    killed = False
    try:
        proc = await asyncio.create_subprocess_exec(
            str(venv_py),
            # Isolated mode: ignore PYTHON* env, no user site-packages, no sys.path[0]
            # injection, and (importantly) no PYTHONSTARTUP. We DO want site.py to run
            # though — without it, the venv's own site-packages/ never loads onto
            # sys.path, and pandas/numpy/prophet from .venv-sandbox become invisible.
            # That's why -S is intentionally NOT used; -I alone gives us the env-var
            # isolation we want without breaking the venv.
            "-I",
            str(RUNNER_SCRIPT),
            str(code_path),
            str(result_w),
            cwd=str(cwd),
            env=env,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            preexec_fn=preexec,
            pass_fds=(result_w,),
        )
    except FileNotFoundError as e:
        os.close(result_r)
        os.close(result_w)
        return SandboxResult(
            status=SandboxStatus.SETUP_ERROR,
            stdout="", stderr="",
            error_message=f"failed to spawn sandbox: {e}",
        )
    finally:
        # parent: close write end so EOF arrives when child exits
        os.close(result_w)

    # Read stdout/stderr concurrently with the wait
    stdout_task = asyncio.create_task(_read_capped(proc.stdout, STDOUT_MAX_BYTES))
    stderr_task = asyncio.create_task(_read_capped(proc.stderr, STDERR_MAX_BYTES))

    try:
        await asyncio.wait_for(proc.wait(), timeout=timeout_sec + 5)
    except asyncio.TimeoutError:
        timed_out = True
        # kill the whole process group
        try:
            if proc.pid:
                os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            try:
                proc.kill()
            except ProcessLookupError:
                pass
        try:
            await asyncio.wait_for(proc.wait(), timeout=2.0)
        except asyncio.TimeoutError:
            pass

    stdout_b = await stdout_task
    stderr_b = await stderr_task
    duration_ms = int((time.monotonic() - started) * 1000)

    # read result inventory from pipe (best-effort)
    inventory: dict | None = None
    try:
        with os.fdopen(result_r, "r", encoding="utf-8") as fh:
            raw = fh.read().strip()
        if raw:
            inventory = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        inventory = None
    finally:
        try:
            os.close(result_r)
        except OSError:
            pass

    stdout_s, stdout_trunc = _truncate(stdout_b, STDOUT_MAX_BYTES)
    stderr_s, stderr_trunc = _truncate(stderr_b, STDERR_MAX_BYTES)

    # Determine status
    exit_code = proc.returncode if proc else None
    if timed_out:
        status = SandboxStatus.TIMEOUT
        err_msg = f"sandbox exceeded {timeout_sec}s timeout (SIGKILL'd)"
    elif exit_code is not None and exit_code < 0:
        # killed by signal — usually SIGKILL from RLIMIT_AS or RLIMIT_CPU
        status = SandboxStatus.KILLED
        sig = -exit_code
        err_msg = f"sandbox killed by signal {sig} (likely OOM or CPU limit)"
        killed = True
    elif inventory and inventory.get("status") == "error":
        status = SandboxStatus.ERROR
        err_msg = inventory.get("error") or "user code raised"
    elif inventory and inventory.get("status") == "setup_error":
        status = SandboxStatus.SETUP_ERROR
        err_msg = inventory.get("error") or "sandbox setup error"
    elif inventory and inventory.get("status") == "ok":
        status = SandboxStatus.OK
        err_msg = None
    else:
        # No inventory at all — probably crashed before runner could write
        status = SandboxStatus.ERROR
        err_msg = "no inventory from runner (likely crash before exec)"

    files_created: list[SandboxFile] = []
    if inventory:
        for f in inventory.get("files_created") or []:
            files_created.append(SandboxFile(
                relpath=f["relpath"],
                size_bytes=int(f["size_bytes"]),
                kind=f.get("kind", "other"),
            ))

    return SandboxResult(
        status=status,
        stdout=stdout_s,
        stderr=stderr_s,
        files_created=files_created,
        duration_ms=duration_ms,
        exit_code=exit_code,
        error_message=err_msg,
        truncated=stdout_trunc or stderr_trunc,
    )
