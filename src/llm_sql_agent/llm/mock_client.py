"""Deterministic, keyless mock backend.

This is a TEST DOUBLE, not a model. It exists so `make eval`, `make demo`, and
the test suite run end-to-end with zero API keys and produce identical results
every time — exercising the full agent loop, guardrails, tracing, and metrics.

It simulates *outcomes* from the gold SQL it is handed via an `oracle`:

  * Naive (no tools): emits one SQL string — a deliberately broken query for
    `hard` questions (no recovery), the gold query otherwise.
  * Agent (tools present): inspects the schema, runs a first query that is
    broken for `medium`/`hard` questions, observes the error, and repairs to
    the gold query — exercising the self-repair loop.

Because it simulates rather than reasons, keyless numbers are ILLUSTRATIVE.
Real headline numbers come from a real backend (`make eval-real`). The README
says so plainly.
"""
from __future__ import annotations

import re

from .base import LLMResponse, ToolCall, Usage

_KNOWN_TABLES = ["order_items", "orders", "products", "reviews", "customers"]
_BROKEN_MARKER = "nonexistent_col"


def break_sql(gold: str) -> str:
    """Insert a reference to a non-existent column so the query fails to run."""
    m = re.search(r"(?i)\bselect\s+", gold)
    if not m:
        return f"SELECT {_BROKEN_MARKER} -- {gold}"
    return gold[: m.end()] + f"{_BROKEN_MARKER}, " + gold[m.end():]


def _pick_table(gold: str) -> str:
    low = gold.lower()
    best, best_idx = "orders", len(low) + 1
    for t in _KNOWN_TABLES:
        idx = low.find(t)
        if idx != -1 and idx < best_idx:
            best, best_idx = t, idx
    return best


def _extract_question(messages: list[dict]) -> str:
    for m in messages:
        if m.get("role") == "user" and isinstance(m.get("content"), str):
            return m["content"].strip()
    return ""


def _tool_results(messages: list[dict]) -> list[tuple[str, bool]]:
    out = []
    for m in messages:
        if m.get("role") == "user" and isinstance(m.get("content"), list):
            for b in m["content"]:
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    out.append((str(b.get("content", "")), bool(b.get("is_error"))))
    return out


def _usage(messages, produced: str) -> Usage:
    inp = sum(len(str(m.get("content", ""))) for m in messages) // 4
    return Usage(input_tokens=max(inp, 1), output_tokens=max(len(produced) // 4, 1))


class MockClient:
    def __init__(self, model: str = "mock", oracle: dict | None = None):
        self.model = model
        self.oracle = oracle or {}
        self._n = 0  # tool-call counter, for unique ids

    def _info(self, question: str) -> dict | None:
        return self.oracle.get(question)

    def chat(self, system, messages, tools=None) -> LLMResponse:
        question = _extract_question(messages)
        info = self._info(question)

        if info is None:
            txt = ("Mock backend has no script for this question. Use one of the "
                   "eval-set questions, or run with a real provider.")
            return LLMResponse(text=txt, usage=_usage(messages, txt), stop_reason="end_turn")

        gold = info["gold_sql"]
        difficulty = info.get("difficulty", "easy")
        broken = break_sql(gold)

        # ---- naive path: one shot, no tools --------------------------------
        if not tools:
            sql = broken if difficulty == "hard" else gold
            return LLMResponse(text=sql, usage=_usage(messages, sql), stop_reason="end_turn")

        # ---- agent path: scripted tool loop --------------------------------
        results = _tool_results(messages)
        n = len(results)
        repair_first = difficulty in ("medium", "hard")

        def tool_use(name, args, preamble):
            self._n += 1
            tc = ToolCall(id=f"toolu_mock_{self._n}", name=name, arguments=args)
            return LLMResponse(
                text=preamble, tool_calls=[tc],
                usage=_usage(messages, preamble + str(args)), stop_reason="tool_use",
            )

        if n == 0:
            return tool_use("list_tables", {}, "Let me look at the schema first.")
        if n == 1:
            table = _pick_table(gold)
            return tool_use("describe_table", {"table_name": table},
                            f"Now I'll inspect the `{table}` table.")
        if n == 2:
            first = broken if repair_first else gold
            return tool_use("run_sql", {"query": first}, "Running my query.")

        # n >= 3: either we just hit an error (repair) or we have rows (finish).
        last_text, last_error = results[-1]
        if last_error:
            return tool_use("run_sql", {"query": gold},
                            "That column doesn't exist — fixing the query.")
        answer = "Based on the query results, here is the answer to your question."
        return LLMResponse(text=answer, usage=_usage(messages, answer), stop_reason="end_turn")
