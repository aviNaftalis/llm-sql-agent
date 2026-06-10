"""The naive baseline: one prompt, one query, executed once.

The whole schema is dumped into the prompt, the model returns a single SQL
string, and we run it once with no introspection and no recovery. This is the
control the production agent is measured against — it captures the failure modes
(hallucinated columns, missed joins, no error recovery) that the agent fixes.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from . import db
from .tools.registry import dispatch

_SYSTEM = """You are a text-to-SQL assistant for a SQLite database.

Schema:
{schema}

Given the user's question, reply with EXACTLY ONE SQLite SELECT query that
answers it. Output only the SQL — no explanation, no markdown fences."""


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
    system = _SYSTEM.format(schema=db.schema_text(settings.db_path))
    messages = [{"role": "user", "content": question}]
    resp = tracer.run_llm("naive", lambda: client.chat(system, messages, tools=None))
    sql = _extract_sql(resp.text)
    text, is_error = tracer.run_tool(
        "run_sql", lambda: dispatch("run_sql", {"query": sql}, settings)
    )
    return NaiveResult(predicted_sql=sql, executed_ok=not is_error, final_text=text)
