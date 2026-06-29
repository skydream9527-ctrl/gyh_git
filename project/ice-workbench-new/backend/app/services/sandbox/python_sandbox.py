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


def _count_uid_tasks() -> int:
    """Count tasks (procs + threads) owned by current UID via /proc.

    RLIMIT_NPROC on Linux counts tasks (each thread is a task), so a sandbox
    nproc cap below the parent UID's current task count makes pthread_create
    fail immediately — breaks matplotlib's font-cache thread, BLAS imports.
    Returning 0 disables the dynamic bump (caller falls back to absolute nproc).
    """
    if platform.system() != "Linux":
        return 0
    try:
        my_uid = os.getuid()
    except AttributeError:
        return 0
    count = 0
    try:
        for entry in os.listdir("/proc"):
            if not entry.isdigit():
                continue
            try:
                if os.stat(f"/proc/{entry}").st_uid != my_uid:
                    continue
                # add this proc's thread count
                count += len(os.listdir(f"/proc/{entry}/task"))
            except (FileNotFoundError, PermissionError, NotADirectoryError):
                continue
    except (FileNotFoundError, PermissionError):
        return 0
    return count


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


# Vars the sandboxed code must never see, even when allow_cli=True. We
# intentionally use both an explicit set (for full names that don't match the
# generic *_TOKEN/_KEY/_SECRET pattern) and substring/prefix rules so a
# future credential exported into the parent shell defaults to "blocked".
_BLOCKED_ENV_KEYS = {
    "ANTHROPIC_BASE_URL",
    "MIFY_GATEWAY_BASE_URL",
    "OPENAI_BASE_URL",
    "ICE_SECRET_KEY",
    "AEGIS_DEV_BYPASS_EMAIL",
    "AEGIS_PUBLIC_KEYS",
    "KUBECONFIG",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "DOCKER_AUTH_CONFIG",
}
_BLOCKED_PREFIXES = ("SUDO_", "SSH_", "GPG_")
_BLOCKED_SUBSTRINGS = ("TOKEN", "SECRET", "KEY", "PASSWORD", "PASSWD", "API_KEY")


def _is_blocked_env_key(k: str) -> bool:
    if k in _BLOCKED_ENV_KEYS:
        return True
    if any(k.startswith(p) for p in _BLOCKED_PREFIXES):
        return True
    up = k.upper()
    return any(s in up for s in _BLOCKED_SUBSTRINGS)


def _build_clean_env(
    *, venv_python: Path, task_dir: Path, allow_cli: bool = False
) -> dict[str, str]:
    """Build env for the sandbox subprocess.

    Default (allow_cli=False): minimal whitelist — original isolation. Used by
    pure data-analysis Python that should never reach the network or read
    service credentials.

    allow_cli=True: inherit the parent env minus LLM-gateway secrets, so the
    sandboxed Python can subprocess.run() CLI tools (feishu / kyuubi / datum)
    that need their auth files (under real HOME) and service env vars. PATH is
    widened to common install locations for those CLIs (npm-global / pipx /
    /usr/local/bin). The sandbox still enforces CPU / memory / fsize / nproc
    via RLIMIT — only the env-strip and network-block layers are relaxed.
    """
    venv_bin = str(venv_python.parent)
    common_overrides = {
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

    if not allow_cli:
        return {
            "PATH": f"{venv_bin}:/usr/bin:/bin",
            "HOME": str(task_dir),
            "TMPDIR": str(task_dir),
            **common_overrides,
        }

    parent = {k: v for k, v in os.environ.items() if not _is_blocked_env_key(k)}
    parent_path = parent.get("PATH", "/usr/bin:/bin")
    parent_home = parent.get("HOME") or str(task_dir)
    from ...core.cli_path import cli_path_extras

    seen: set[str] = set()
    merged_path_parts: list[str] = []
    for p in [venv_bin, *cli_path_extras(home=parent_home), *parent_path.split(":")]:
        if not p or p in seen:
            continue
        seen.add(p)
        merged_path_parts.append(p)
    parent["PATH"] = ":".join(merged_path_parts)
    parent["HOME"] = parent_home
    parent["TMPDIR"] = parent.get("TMPDIR") or str(task_dir)
    parent["SANDBOX_NETWORK_ALLOWED"] = "1"
    parent.update(common_overrides)
    return parent


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
    allow_cli: bool = False,
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

    env = _build_clean_env(
        venv_python=venv_py, task_dir=task_dir, allow_cli=allow_cli
    )

    # RLIMIT_NPROC is shared per-UID — on a busy host the parent UID may
    # already have more tasks than the requested nproc cap, which makes any
    # pthread_create() in the child (matplotlib font cache, BLAS) fail with
    # "can't start new thread". Bump the cap to (current_tasks + nproc) so
    # the sandbox always has `nproc` headroom regardless of what else the
    # user is running. Falls back to absolute nproc if /proc is unreadable.
    current_tasks = _count_uid_tasks()
    effective_nproc = nproc if current_tasks == 0 else current_tasks + nproc

    preexec = make_preexec(
        cpu_sec=timeout_sec,
        memory_mb=memory_mb,
        fsize_mb=fsize_mb,
        nproc=effective_nproc,
        nofile=nofile,
        apply_as=not allow_cli,
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
