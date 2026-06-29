"""IndexBackend — abstract interface for the derived cache index.

The filesystem remains the sole source of truth (G3). The index backend is a
*derived, rebuildable* acceleration layer for listings, search, and counts.

This Protocol decouples callers from the concrete implementation (currently
SQLite via aiosqlite). Future implementations (e.g., Postgres for multi-machine
deployments) can be swapped in by setting ICE_INDEX_BACKEND without touching
any business code.

Method signatures mirror IndexDB's existing public API exactly so the
extraction is zero-breaking.
"""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class IndexBackend(Protocol):
    """Minimal contract for a rebuildable index store."""

    async def init(self) -> None:
        """Initialize schema / tables. Idempotent."""
        ...

    async def execute(self, sql: str, params: Iterable[Any] | None = None) -> None:
        """Execute a write statement (INSERT/UPDATE/DELETE) and commit."""
        ...

    async def executescript(self, script: str) -> None:
        """Execute a multi-statement script (DDL, bulk ops) and commit."""
        ...

    async def executemany(self, sql: str, rows: Iterable[Iterable[Any]]) -> None:
        """Execute a parameterized statement for each row and commit."""
        ...

    async def fetchone(self, sql: str, params: Iterable[Any] | None = None) -> dict | None:
        """Fetch a single row as dict, or None if not found."""
        ...

    async def fetchall(self, sql: str, params: Iterable[Any] | None = None) -> list[dict]:
        """Fetch all matching rows as list of dicts."""
        ...

    async def upsert(self, table: str, row: dict, key: str = "id") -> None:
        """Insert or update a row by primary key."""
        ...
