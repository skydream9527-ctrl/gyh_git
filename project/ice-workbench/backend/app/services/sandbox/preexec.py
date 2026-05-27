"""POSIX preexec_fn for the sandbox child process.

Linux: full set of resource limits (CPU / AS / FSIZE / NPROC / NOFILE).
macOS: skip RLIMIT_AS (Darwin's RLIMIT_AS is unreliable for Python because
       the interpreter mmap-reserves more than it commits). We still apply
       CPU / FSIZE / NOFILE which gives partial protection — enough for dev.

Always:
    - os.setpgrp(): own process group so we can kill the whole tree on timeout

This module is imported by the parent backend process. The actual
preexec_fn callable is invoked in the *child* between fork() and exec().
"""
from __future__ import annotations

import os
import platform
import resource


def _is_linux() -> bool:
    return platform.system() == "Linux"


def make_preexec(*, cpu_sec: int, memory_mb: int, fsize_mb: int,
                 nproc: int, nofile: int, apply_as: bool = True):
    """Return a preexec_fn closure with the given limits baked in.

    Called in the forked child *before* exec(). Must be small and not
    touch async / asyncio internals.

    `apply_as=False` skips RLIMIT_AS entirely. Use this when the sandboxed
    code drives a Node-based CLI (V8 / Wasm pre-reserve multi-GB virtual
    address space; even a generous RLIMIT_AS = 4 GB makes `feishu fetch`
    crash with "Cannot allocate Wasm memory"). RLIMIT_CPU + wall-clock
    timeout still bound runaway resource use.
    """
    cpu_hard = max(1, int(cpu_sec))
    mem_bytes = max(64, int(memory_mb)) * 1024 * 1024
    fsize_bytes = max(1, int(fsize_mb)) * 1024 * 1024
    nproc_v = max(8, int(nproc))
    nofile_v = max(16, int(nofile))
    use_as = _is_linux() and apply_as

    def _apply():
        # New process group → easy to kill the whole tree later
        try:
            os.setpgrp()
        except OSError:
            pass

        # CPU time hard cap (SIGXCPU then SIGKILL)
        try:
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_hard, cpu_hard))
        except (ValueError, OSError):
            pass

        # Address space (Linux only — macOS RLIMIT_AS is unreliable for Python)
        if use_as:
            try:
                resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
            except (ValueError, OSError):
                pass

        # File size cap (matplotlib output, csv dumps)
        try:
            resource.setrlimit(resource.RLIMIT_FSIZE, (fsize_bytes, fsize_bytes))
        except (ValueError, OSError):
            pass

        # Process count (block fork bombs)
        try:
            resource.setrlimit(resource.RLIMIT_NPROC, (nproc_v, nproc_v))
        except (ValueError, OSError):
            pass

        # Open files
        try:
            resource.setrlimit(resource.RLIMIT_NOFILE, (nofile_v, nofile_v))
        except (ValueError, OSError):
            pass

    return _apply
