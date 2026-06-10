"""Read-only SQLite access.

Connections are opened in `mode=ro` with `PRAGMA query_only = ON`, so even if a
write somehow slips past the guardrails it cannot mutate the database. A progress
handler enforces a coarse statement-level interrupt as a runaway-query backstop.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass

# Progress handler fires every N VM ops; this bounds a pathological query.
_PROGRESS_OPS = 100_000
_MAX_PROGRESS_CALLS = 5_000  # ~5e8 VM ops before we abort


class QueryError(Exception):
    """A query failed to execute (SQL error, or hit the op-count backstop)."""


@dataclass
class QueryResult:
    columns: list[str]
    rows: list[tuple]
    truncated: bool


def connect_ro(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.execute("PRAGMA query_only = ON")
    return conn


def run_query(db_path: str, sql: str, max_rows: int) -> QueryResult:
    """Execute a read-only query and return at most `max_rows` rows."""
    conn = connect_ro(db_path)
    calls = {"n": 0}

    def _guard() -> int:
        calls["n"] += 1
        return 1 if calls["n"] > _MAX_PROGRESS_CALLS else 0

    conn.set_progress_handler(_guard, _PROGRESS_OPS)
    try:
        cur = conn.execute(sql)
        cols = [d[0] for d in cur.description] if cur.description else []
        rows = cur.fetchmany(max_rows + 1)
        truncated = len(rows) > max_rows
        return QueryResult(columns=cols, rows=rows[:max_rows], truncated=truncated)
    except sqlite3.Error as e:
        raise QueryError(str(e)) from e
    finally:
        conn.close()


def list_tables(db_path: str) -> list[str]:
    conn = connect_ro(db_path)
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        return [r[0] for r in rows]
    finally:
        conn.close()


def describe_table(db_path: str, table: str) -> list[tuple[str, str]]:
    """Return [(column_name, type), ...] for one table, or raise QueryError."""
    if table not in list_tables(db_path):
        raise QueryError(f"no such table: {table}")
    conn = connect_ro(db_path)
    try:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        return [(r[1], r[2]) for r in rows]
    finally:
        conn.close()


def schema_text(db_path: str) -> str:
    """A compact CREATE-statement dump, for the naive baseline's prompt."""
    conn = connect_ro(db_path)
    try:
        rows = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        return "\n\n".join(r[0] for r in rows if r[0])
    finally:
        conn.close()
