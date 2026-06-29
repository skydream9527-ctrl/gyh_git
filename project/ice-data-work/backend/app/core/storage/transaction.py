"""file_transaction：多文件写入的原子边界（咨询锁 + 备份 + 失败回滚）。

用法：
    with file_transaction([p1, p2]) as tx:
        write_json(p1, ...)
        write_text(p2, ...)
    # 退出即提交；异常则把 p1/p2 回滚到进入前的内容
记忆/Skill 晋升等"文件 + 索引"操作应放在同一事务内完成（TDR-5）。
"""
from __future__ import annotations

import contextlib
import shutil
from pathlib import Path
from typing import Iterator, Sequence

from .locks import advisory_lock


@contextlib.contextmanager
def file_transaction(paths: Sequence[Path]) -> Iterator[None]:
    targets = [Path(p) for p in paths]
    backups: dict[Path, bytes | None] = {}

    # 串行加锁（按路径排序避免死锁）+ 记录原内容
    with contextlib.ExitStack() as stack:
        for p in sorted(set(targets), key=lambda x: str(x)):
            stack.enter_context(advisory_lock(p))
            backups[p] = p.read_bytes() if p.exists() else None
        try:
            yield
        except Exception:
            # 回滚到进入前状态
            for p, content in backups.items():
                if content is None:
                    if p.exists():
                        p.unlink()
                else:
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_bytes(content)
            raise


def atomic_move(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
