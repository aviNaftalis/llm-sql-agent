"""The production agent: a multi-step tool-calling loop with self-repair.

Reason -> call a tool -> observe the result (or error) -> repair -> until a
final answer or the step cap. Orchestration concerns live here: a hard step
cap, tracking of the last *successful* query as the prediction, and a
repaired-flag derived from observing an error followed by a recovery. Tool
errors are fed back to the model as tool_result errors so it can fix them.
"""
from __future__ import annotations

from dataclasses import dataclass

from .tools.registry import TOOL_SCHEMAS, dispatch

_SYSTEM = """You are a senior data analyst answering questions over a SQLite database.

Work step by step using the tools:
  - list_tables / describe_table to understand the schema,
  - run_sql to execute a single read-only SELECT.
If a query errors, read the error message and correct the query, then try again.
When you have the answer, reply with one short sentence stating it, and stop
calling tools."""


@dataclass
class AgentResult:
    final_text: str
    predicted_sql: str | None
    steps: int
    sql_errors: int
    repaired: bool


def run_agent(client, settings, question: str, tracer) -> AgentResult:
    messages = [{"role": "user", "content": question}]
    predicted_sql: str | None = None
    sql_errors = 0
    sql_successes = 0
    steps = 0

    for _ in range(settings.max_steps):
        resp = tracer.run_llm(
            "agent", lambda: client.chat(_SYSTEM, messages, TOOL_SCHEMAS)
        )
        steps += 1

        # Echo the assistant turn back (text + tool_use blocks) so the model
        # sees its own calls on the next turn.
        content: list[dict] = []
        if resp.text:
            content.append({"type": "text", "text": resp.text})
        for tc in resp.tool_calls:
            content.append({"type": "tool_use", "id": tc.id, "name": tc.name, "input": tc.arguments})
        messages.append({"role": "assistant", "content": content})

        if not resp.tool_calls:
            return AgentResult(
                final_text=resp.text, predicted_sql=predicted_sql, steps=steps,
                sql_errors=sql_errors, repaired=sql_errors > 0 and sql_successes > 0,
            )

        tool_results = []
        for tc in resp.tool_calls:
            text, is_error = tracer.run_tool(
                tc.name, lambda tc=tc: dispatch(tc.name, tc.arguments, settings)
            )
            if tc.name == "run_sql":
                if is_error:
                    sql_errors += 1
                else:
                    sql_successes += 1
                    predicted_sql = tc.arguments.get("query")
            tool_results.append({
                "type": "tool_result", "tool_use_id": tc.id,
                "content": text, "is_error": is_error,
            })
        messages.append({"role": "user", "content": tool_results})

    return AgentResult(
        final_text="(stopped: max steps reached)", predicted_sql=predicted_sql,
        steps=steps, sql_errors=sql_errors,
        repaired=sql_errors > 0 and sql_successes > 0,
    )
