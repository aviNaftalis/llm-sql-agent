"""The naive baseline: one blind prompt, one query, executed once.

Apples-to-apples with the agent: both start with only the question. The agent
earns the schema by calling tools (`list_tables` / `describe_table`) and verifies
by executing; the naive baseline gets neither — it writes one query from the
question alone and runs it once, with no introspection and no recovery. So this
isolates exactly what the agentic loop buys: schema discovery + execution
feedback. It captures the failure modes (guessed table/column names, missed
joins, no error recovery) that the agent fixes.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .tools.registry import dispatch

_SYSTEM = """You are a text-to-SQL assistant for a SQLite database. You are not
given the schema — infer reasonable table and column names from the question.

Reply with EXACTLY ONE SQLite SELECT query that answers the question. Output only
the SQL — no explanation, no markdown fences."""


@dataclass
class NaiveResult:
    predicted_sql: str
    executed_ok: bool
    final_text: str


def _extract_sql(text: str) -> str:
    t = text.strip()
    # Strip ```sql ... ``` fences if the model added them.
    fence = re.search(r"```(?:sql)?\s*(.+?)```", t, flags=re.S | re.I)
    if fence:
        t = fence.group(1).strip()
    return t


def run_naive(client, settings, question: str, tracer) -> NaiveResult:
    messages = [{"role": "user", "content": question}]
    resp = tracer.run_llm("naive", lambda: client.chat(_SYSTEM, messages, tools=None))
    sql = _extract_sql(resp.text)
    text, is_error = tracer.run_tool(
        "run_sql", lambda: dispatch("run_sql", {"query": sql}, settings)
    )
    return NaiveResult(predicted_sql=sql, executed_ok=not is_error, final_text=text)
