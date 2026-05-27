"""Sandbox result types."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class SandboxStatus(str, Enum):
    OK = "ok"
    ERROR = "error"           # user code raised
    TIMEOUT = "timeout"       # exceeded wall-clock limit
    KILLED = "killed"         # OS killed (likely OOM / RLIMIT_CPU)
    SETUP_ERROR = "setup_error"   # venv missing, runner script missing, etc.


@dataclass
class SandboxFile:
    """Artifact written to the task workspace by the sandboxed code."""
    relpath: str          # path relative to task_dir, e.g. "files/output/charts/T1.png"
    size_bytes: int
    kind: str             # "csv" | "png" | "json" | "txt" | "model" | "other"


@dataclass
class SandboxResult:
    status: SandboxStatus
    stdout: str           # truncated to STDOUT_MAX_BYTES
    stderr: str           # truncated to STDERR_MAX_BYTES
    files_created: list[SandboxFile] = field(default_factory=list)
    duration_ms: int = 0
    exit_code: int | None = None
    error_message: str | None = None    # populated when status != OK
    truncated: bool = False              # stdout/stderr exceeded limits

    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "files_created": [
                {"relpath": f.relpath, "size_bytes": f.size_bytes, "kind": f.kind}
                for f in self.files_created
            ],
            "duration_ms": self.duration_ms,
            "exit_code": self.exit_code,
            "error_message": self.error_message,
            "truncated": self.truncated,
        }
