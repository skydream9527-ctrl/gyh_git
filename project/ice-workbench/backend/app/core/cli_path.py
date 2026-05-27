"""Resolve common CLI install locations into PATH.

Daemons started outside an interactive shell (uvicorn under systemd, `make
dev` from a fresh shell, etc.) miss the nvm / volta / homebrew shellenv
that puts node-based CLIs like `feishu` / `npx` on PATH. This module gives
us one place to merge those locations in: the backend calls it once at
lifespan-startup so `shutil.which()` in every tool wrapper finds the CLI;
the Python sandbox uses the same logic to widen its own subprocess PATH.
"""
from __future__ import annotations

import functools
import glob
import os


@functools.lru_cache(maxsize=8)
def cli_path_extras(home: str | None = None) -> tuple[str, ...]:
    """Return the directories we want prepended to PATH so node / pip / brew
    CLIs are reachable. Order: dynamic per-version dirs first (newest nvm
    install wins via sort-desc), then static well-known prefixes.

    Cached: results are stable for a process lifetime; the sandbox calls this
    on every execute_python and the glob isn't free under cold filesystem cache.
    Returns a tuple so callers can splat-iterate without aliasing the cache.
    """
    h = home or os.environ.get("HOME") or "/root"
    nvm_bins = sorted(
        glob.glob(f"{h}/.nvm/versions/node/*/bin"), reverse=True
    )
    return (
        *nvm_bins,
        f"{h}/.npm-global/bin",
        f"{h}/.local/bin",
        f"{h}/.volta/bin",
        f"{h}/bin",
        "/usr/local/bin",
        "/opt/homebrew/bin",
    )


def widen_path_in_place() -> None:
    """Mutate os.environ['PATH'] to include cli_path_extras() entries that
    actually exist on disk. Idempotent: re-running is a no-op since dedup
    drops already-present segments. Called from lifespan so subprocess /
    shutil.which from any tool wrapper picks up feishu / kyuubi / datum
    even when uvicorn was started without sourcing nvm."""
    cur = os.environ.get("PATH", "/usr/bin:/bin").split(":")
    seen = {p for p in cur if p}
    extras = [p for p in cli_path_extras() if p and p not in seen and os.path.isdir(p)]
    if extras:
        os.environ["PATH"] = ":".join(extras + cur)
