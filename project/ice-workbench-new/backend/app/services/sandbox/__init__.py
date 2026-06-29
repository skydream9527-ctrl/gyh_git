"""Python sandbox for the data-analysis agent.

Public API:
    run_python(code, *, task_dir, ...) -> SandboxResult

Sandbox model:
    - subprocess via asyncio.create_subprocess_exec
    - executable: backend/.venv-sandbox/bin/python  (separate venv with
      whitelisted analytics packages: pandas/numpy/scipy/sklearn/statsmodels/
      prophet/ruptures/matplotlib/seaborn/pyarrow)
    - cwd jail: tasks/{tid}/files/output/  (relative paths land here)
    - env scrub: minimal PATH, no proxies, no service credentials
    - resource limits (POSIX preexec_fn): CPU / AS / FSIZE / NPROC / NOFILE
    - hard timeout: SIGKILL after deadline
    - network: socket monkey-patch in runner wrapper

Not airtight against malicious code (LLM treated as untrusted-but-well-
intentioned). Hardens against:
    - runaway loops / OOM
    - accidental credential exfil via env
    - accidental network egress
    - filesystem writes outside task workspace (via relative-path discipline)
"""
from .python_sandbox import run_python
from .types import SandboxFile, SandboxResult, SandboxStatus

__all__ = ["run_python", "SandboxResult", "SandboxStatus", "SandboxFile"]
