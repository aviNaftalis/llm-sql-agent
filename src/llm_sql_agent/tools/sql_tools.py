"""The three tools the agent calls, plus result formatting.

Each returns (text, is_error). `is_error=True` is fed back to the model as a
tool_result error so it can observe the failure and repair — this is the
mechanism the production agent uses that the naive baseline lacks.
"""
from __future__ import annotations

from .. import db
from ..guardrails import GuardrailError, enforce_limit, validate_select


def _format_rows(result: db.QueryResult, max_display: int = 50) -> str:
    if not result.columns:
        return "(no columns)"
    lines = [" | ".join(result.columns)]
    for row in result.rows[:max_display]:
        lines.append(" | ".join("NULL" if v is None else str(v) for v in row))
    out = "\n".join(lines)
    note = f"\n({len(result.rows)} row(s)"
    if result.truncated:
        note += ", truncated to the row cap"
    if len(result.rows) > max_display:
        note += f"; showing first {max_display}"
    note += ")"
    return out + note


def tool_list_tables(settings) -> tuple[str, bool]:
    tables = db.list_tables(settings.db_path)
    return "Tables: " + ", ".join(tables), False


def tool_describe_table(settings, table_name: str) -> tuple[str, bool]:
    try:
        cols = db.describe_table(settings.db_path, table_name)
    except db.QueryError as e:
        return f"Error: {e}", True
    body = "\n".join(f"  {name} {typ}" for name, typ in cols)
    return f"{table_name}:\n{body}", False


def tool_run_sql(settings, query: str) -> tuple[str, bool]:
    try:
        cleaned = validate_select(query)
    except GuardrailError as e:
        return f"Rejected by guardrail: {e}", True
    capped = enforce_limit(cleaned, settings.max_rows)
    try:
        result = db.run_query(settings.db_path, capped, settings.max_rows)
    except db.QueryError as e:
        return f"SQL error: {e}", True
    return _format_rows(result), False
