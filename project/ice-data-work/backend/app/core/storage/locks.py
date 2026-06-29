"""文件咨询锁。优先 portalocker；未安装时降级为进程内锁（仅保证骨架可运行）。"""
from __future__ import annotations

import contextlib
import threading
from pathlib import Path
from typing import Iterator

try:
    import portalocker  # type: ignore

    _HAS_PORTALOCKER = True
except Exception:  # pragma: no cover - 依赖未装时降级
    _HAS_PORTALOCKER = False

_fallback_locks: dict[str, threading.Lock] = {}
_registry_lock = threading.Lock()


@contextlib.contextmanager
def advisory_lock(target: Path) -> Iterator[None]:
    """对 <target>.lock 加排他锁；缺 portalocker 时退化为进程内互斥。"""
    target.parent.mkdir(parents=True, exist_ok=True)
    lock_path = target.with_suffix(target.suffix + ".lock")

    if _HAS_PORTALOCKER:
        with open(lock_path, "a+") as fh:
            portalocker.lock(fh, portalocker.LOCK_EX)
            try:
                yield
            finally:
                portalocker.unlock(fh)
        return

    key = str(lock_path)
    with _registry_lock:
        lk = _fallback_locks.setdefault(key, threading.Lock())
    with lk:
        yield
