"""代码沙盒执行器（D-13 §10.5 安全要求）。

用户贡献的代码一律视为不可信，先进沙盒执行：
    - 无网络：执行前注入 preamble，monkeypatch socket → 阻断出网
    - 限资源：resource.setrlimit 限 CPU 时间 / 文件大小 /（可选）地址空间（仅 POSIX）
    - 无凭证：清空环境变量，仅保留最小白名单（PATH/LANG…），绝不传 *_KEY/TOKEN/SECRET
    - 隔离目录：cwd 设为调用方给定的任务沙盒目录，HOME/TMPDIR 也指向它，禁止访问任务外
    - 墙钟超时：subprocess 墙钟超时，超时整组 kill（os.setsid 建新进程组）

特性开关 `IDW_SELF_EVOLVE_ENABLED`；未启用返回 SANDBOX_NOT_ENABLED（不阻塞平台启动）。

边界声明（v1，诚实）：这是进程级"软沙盒"。在 macOS/通用 POSIX 上没有内核级隔离
（无 namespace/seccomp/cgroup）。网络阻断为执行前 monkeypatch，理论上可被刻意 re-import
底层 C 接口绕过；内存硬限制（RLIMIT_AS）在 macOS 上会误杀解释器，默认关闭。
对"常规用户分析代码 + 限 CPU + 墙钟超时 + 去凭证 + 隔离 cwd + 文件大小上限"已是有效防线；
生产 Linux 应叠加容器/gVisor/firejail + cgroup 内存限制（IDW_SANDBOX_MEM_MB）。
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from app.core.config import get_settings

# 默认限额（可被环境变量覆盖）
DEFAULT_WALL_TIMEOUT = int(os.environ.get("IDW_SANDBOX_TIMEOUT_SEC", "15"))
DEFAULT_CPU_SECONDS = int(os.environ.get("IDW_SANDBOX_CPU_SEC", "10"))
# 内存硬限制（RLIMIT_AS）：0 = 不设（macOS 上设了会让解释器起不来）。Linux 生产可设 512+。
DEFAULT_MEM_MB = int(os.environ.get("IDW_SANDBOX_MEM_MB", "0"))
DEFAULT_FSIZE_MB = int(os.environ.get("IDW_SANDBOX_FSIZE_MB", "50"))
OUTPUT_LIMIT = 20000  # stdout/stderr 截断上限（字符）

# 环境白名单（绝不传任何凭证类变量 → 沙盒内无 key/token/secret）
_SAFE_ENV_KEYS = ("PATH", "LANG", "LC_ALL", "LC_CTYPE", "TZ")

# 网络阻断 + 入参注入 preamble（{params_literal} 由 run_python 用 replace 安全填充）
_PREAMBLE = '''\
# === IDW sandbox preamble (auto-injected) ===
import json as _json
def _idw_block_network():
    import socket as _s
    def _blocked(*a, **k):
        raise OSError("network access is disabled in sandbox")
    _s.socket = _blocked  # type: ignore
    _s.create_connection = _blocked  # type: ignore
    try:
        _s.SocketType = _blocked  # type: ignore
    except Exception:
        pass
_idw_block_network()
# 入参（由「贡献为 Skill」入参 schema 提供，运行时注入为变量 params）
params = _json.loads({params_literal})
# === end preamble ===
'''


def is_enabled() -> bool:
    """自演进/沙盒总开关。"""
    return get_settings().self_evolve_enabled


def _python_executable() -> str:
    """沙盒解释器：默认当前 venv；可用 IDW_SANDBOX_PYTHON 指向专用 venv（含 pandas/sklearn 等）。"""
    return os.environ.get("IDW_SANDBOX_PYTHON", "").strip() or sys.executable


def _disabled_result(runtime: str) -> dict:
    return {
        "ok": False, "error_code": "SANDBOX_NOT_ENABLED",
        "message": "自演进/沙盒未启用（设 IDW_SELF_EVOLVE_ENABLED=true 开启）",
        "runtime": runtime, "stdout": "", "stderr": "", "exit_code": None,
        "timed_out": False, "duration_ms": 0,
    }


def run_python(
    code: str, *, params: dict | None = None, workdir: str | Path,
    wall_timeout: int | None = None, cpu_seconds: int | None = None,
    mem_mb: int | None = None, fsize_mb: int | None = None,
) -> dict:
    """在隔离子进程中执行 Python 代码，返回结构化结果。

    返回：{ok, error_code, message, runtime, stdout, stderr, exit_code, timed_out, duration_ms}
    """
    if not is_enabled():
        return _disabled_result("python")

    work = Path(workdir)
    work.mkdir(parents=True, exist_ok=True)

    cpu_sec = cpu_seconds if cpu_seconds is not None else DEFAULT_CPU_SECONDS
    wall = wall_timeout if wall_timeout is not None else DEFAULT_WALL_TIMEOUT
    mem_bytes = (mem_mb if mem_mb is not None else DEFAULT_MEM_MB) * 1024 * 1024
    fsize_bytes = (fsize_mb if fsize_mb is not None else DEFAULT_FSIZE_MB) * 1024 * 1024

    preamble = _PREAMBLE.replace("{params_literal}", repr(json.dumps(params or {})))
    full_code = preamble + "\n" + (code or "")

    fd, code_path = tempfile.mkstemp(prefix="__idw_sandbox_", suffix=".py", dir=str(work))
    os.close(fd)
    Path(code_path).write_text(full_code, encoding="utf-8")

    # 最小环境：去凭证；HOME/TMPDIR 指向沙盒目录
    env = {k: os.environ[k] for k in _SAFE_ENV_KEYS if k in os.environ}
    env.update({
        "HOME": str(work), "TMPDIR": str(work),
        "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1",
    })

    preexec = _build_preexec(cpu_sec, mem_bytes, fsize_bytes) if os.name == "posix" else None

    start = time.monotonic()
    timed_out = False
    try:
        proc = subprocess.Popen(
            [_python_executable(), "-I", "-X", "utf8", "-B", code_path],
            cwd=str(work), env=env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            preexec_fn=preexec, text=True, encoding="utf-8", errors="replace",
        )
        try:
            stdout, stderr = proc.communicate(timeout=wall)
        except subprocess.TimeoutExpired:
            timed_out = True
            _kill_group(proc)
            try:
                stdout, stderr = proc.communicate(timeout=5)
            except Exception:
                stdout, stderr = "", ""
        exit_code = proc.returncode
    except Exception as e:  # 启动失败
        _safe_unlink(code_path)
        return {
            "ok": False, "error_code": "SANDBOX_ERROR",
            "message": f"沙盒启动失败: {e}", "runtime": "python",
            "stdout": "", "stderr": str(e), "exit_code": None,
            "timed_out": False, "duration_ms": int((time.monotonic() - start) * 1000),
        }
    finally:
        _safe_unlink(code_path)

    duration_ms = int((time.monotonic() - start) * 1000)
    ok = (exit_code == 0) and not timed_out
    if timed_out:
        error_code, message = "SANDBOX_TIMEOUT", f"执行超时（>{wall}s），已终止"
    elif ok:
        error_code, message = "OK", "执行完成"
    else:
        error_code, message = "SANDBOX_RUNTIME_ERROR", f"代码退出码 {exit_code}"

    return {
        "ok": ok, "error_code": error_code, "message": message, "runtime": "python",
        "stdout": _truncate(stdout), "stderr": _truncate(stderr),
        "exit_code": exit_code, "timed_out": timed_out, "duration_ms": duration_ms,
    }


# ─────────────────── 内部 ───────────────────

def _build_preexec(cpu_sec: int, mem_bytes: int, fsize_bytes: int):
    def _set_limits() -> None:  # pragma: no cover - 在子进程内执行
        import resource
        try:
            os.setsid()  # 新进程组，超时整组 kill
        except Exception:
            pass
        try:
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_sec, cpu_sec + 1))
        except Exception:
            pass
        if fsize_bytes > 0:
            try:
                resource.setrlimit(resource.RLIMIT_FSIZE, (fsize_bytes, fsize_bytes))
            except Exception:
                pass
        if mem_bytes > 0:  # macOS 默认 0（设了会误杀解释器）
            try:
                resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
            except Exception:
                pass
    return _set_limits


def _kill_group(proc: subprocess.Popen) -> None:
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def _safe_unlink(path: str) -> None:
    try:
        os.unlink(path)
    except Exception:
        pass


def _truncate(text: Any) -> str:
    s = text or ""
    if not isinstance(s, str):
        s = str(s)
    if len(s) > OUTPUT_LIMIT:
        return s[:OUTPUT_LIMIT] + f"\n…（输出已截断，共 {len(s)} 字符）"
    return s
