"""SQL guardrails: read-only enforcement + a row cap.

These run before any query reaches the database. They reject anything that
isn't a single read-only SELECT/WITH statement and inject a LIMIT when the
query has none — a reusable safety layer the `run_sql` tool routes through.
"""
from __future__ import annotations

import re

import sqlparse

# Keywords that mutate state or escape the read-only sandbox.
_FORBIDDEN = {
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "REPLACE",
    "TRUNCATE", "ATTACH", "DETACH", "PRAGMA", "VACUUM", "REINDEX", "GRANT",
    "MERGE", "UPSERT",
}


class GuardrailError(Exception):
    """A query was rejected before execution."""


def _first_keyword(statement: sqlparse.sql.Statement) -> str:
    for tok in statement.flatten():
        if tok.ttype in sqlparse.tokens.Keyword or tok.ttype in sqlparse.tokens.DML:
            return tok.value.upper()
    return ""


def validate_select(sql: str) -> str:
    """Return a cleaned single-statement SELECT, or raise GuardrailError."""
    cleaned = sql.strip().rstrip(";").strip()
    if not cleaned:
        raise GuardrailError("empty query")

    statements = [s for s in sqlparse.parse(cleaned) if str(s).strip()]
    if len(statements) != 1:
        raise GuardrailError(
            f"expected exactly one statement, got {len(statements)}"
        )

    stmt = statements[0]
    first = _first_keyword(stmt)
    if first not in ("SELECT", "WITH"):
        raise GuardrailError(f"only SELECT/WITH queries are allowed (got {first or '?'})")

    # Reject any forbidden keyword appearing as an actual keyword token.
    for tok in stmt.flatten():
        if tok.ttype in (sqlparse.tokens.Keyword, sqlparse.tokens.DDL,
                         sqlparse.tokens.DML, sqlparse.tokens.Keyword.DML,
                         sqlparse.tokens.Keyword.DDL):
            if tok.value.upper() in _FORBIDDEN:
                raise GuardrailError(f"forbidden keyword: {tok.value.upper()}")

    return cleaned


def enforce_limit(sql: str, max_rows: int) -> str:
    """Append `LIMIT max_rows` unless a trailing LIMIT already bounds the result.

    Only a *trailing* LIMIT counts — a LIMIT inside a subquery or CTE leaves the
    outer result set unbounded, so we still add an outer cap in that case.
    """
    if re.search(r"(?is)\blimit\b\s+\d+(\s+offset\s+\d+)?\s*$", sql.rstrip()):
        return sql
    return f"{sql}\nLIMIT {max_rows}"
