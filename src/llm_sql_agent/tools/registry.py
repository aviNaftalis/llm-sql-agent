"""Tool schemas (Anthropic tool-use format) and a name -> implementation dispatch.

Every LLM backend consumes the same schemas, and the agent loop
routes every tool call through `dispatch`. Adding a tool here is the only change
needed for the agent and every backend to use it.
"""
from __future__ import annotations

from . import sql_tools

TOOL_SCHEMAS = [
    {
        "name": "list_tables",
        "description": "List the names of all tables in the database.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "describe_table",
        "description": "Show the columns and types of one table.",
        "input_schema": {
            "type": "object",
            "properties": {
                "table_name": {"type": "string", "description": "Name of the table"}
            },
            "required": ["table_name"],
        },
    },
    {
        "name": "run_sql",
        "description": (
            "Run a single read-only SELECT query and return the rows. "
            "Use this to answer the question; if it errors, read the error and try again."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "A single SQLite SELECT query"}
            },
            "required": ["query"],
        },
    },
]


def dispatch(name: str, args: dict, settings) -> tuple[str, bool]:
    """Run a tool by name. Returns (text, is_error)."""
    if name == "list_tables":
        return sql_tools.tool_list_tables(settings)
    if name == "describe_table":
        return sql_tools.tool_describe_table(settings, args.get("table_name", ""))
    if name == "run_sql":
        return sql_tools.tool_run_sql(settings, args.get("query", ""))
    return f"Unknown tool: {name}", True
