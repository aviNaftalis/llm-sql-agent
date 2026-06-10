"""Test-only LLM doubles.

These are NOT shipped backends (the only backends are Claude and the planned
Ollama one) — they're dependency-injected fakes that let the agent loop, naive
baseline, and metrics be tested deterministically and offline, with no API key.
`ScriptedLLM` drives the loop through a realistic trajectory: inspect schema,
run a (optionally broken) query, observe the error, and repair to the gold query.
"""
from __future__ import annotations

import re

from llm_sql_agent.llm.base import LLMResponse, ToolCall, Usage

_TABLES = ["order_items", "orders", "products", "reviews", "customers"]


def break_sql(gold: str) -> str:
    """Insert a reference to a non-existent column so the query fails to run."""
    m = re.search(r"(?i)\bselect\s+", gold)
    return gold[: m.end()] + "nonexistent_col, " + gold[m.end():] if m else gold


def _pick_table(gold: str) -> str:
    low = gold.lower()
    best, best_idx = "orders", len(low) + 1
    for t in _TABLES:
        i = low.find(t)
        if i != -1 and i < best_idx:
            best, best_idx = t, i
    return best


def _results(messages: list[dict]) -> list[tuple[str, bool]]:
    out = []
    for m in messages:
        if m.get("role") == "user" and isinstance(m.get("content"), list):
            for b in m["content"]:
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    out.append((str(b.get("content", "")), bool(b.get("is_error"))))
    return out


def _usage(messages, produced: str) -> Usage:
    inp = sum(len(str(m.get("content", ""))) for m in messages) // 4
    return Usage(max(inp, 1), max(len(produced) // 4, 1))


class ScriptedLLM:
    """A deterministic LLM double.

    repair=True       -> the agent's first query is broken, then repaired.
    naive_broken=True -> the naive one-shot returns a broken query.
    """

    def __init__(self, gold_sql: str, repair: bool = False, naive_broken: bool = False):
        self.model = "scripted"
        self.gold = gold_sql
        self.repair = repair
        self.naive_broken = naive_broken
        self._n = 0

    def chat(self, system, messages, tools=None) -> LLMResponse:
        # naive: one shot, no tools
        if not tools:
            sql = break_sql(self.gold) if self.naive_broken else self.gold
            return LLMResponse(text=sql, usage=_usage(messages, sql), stop_reason="end_turn")

        results = _results(messages)
        n = len(results)

        def tool_use(name, args, text):
            self._n += 1
            tc = ToolCall(id=f"toolu_fake_{self._n}", name=name, arguments=args)
            return LLMResponse(text=text, tool_calls=[tc],
                               usage=_usage(messages, text + str(args)), stop_reason="tool_use")

        if n == 0:
            return tool_use("list_tables", {}, "Inspecting the schema.")
        if n == 1:
            return tool_use("describe_table", {"table_name": _pick_table(self.gold)}, "Describing a table.")
        if n == 2:
            first = break_sql(self.gold) if self.repair else self.gold
            return tool_use("run_sql", {"query": first}, "Running my query.")

        if results[-1][1]:  # last was an error -> repair
            return tool_use("run_sql", {"query": self.gold}, "Fixing the query.")
        ans = "Here is the answer."
        return LLMResponse(text=ans, usage=_usage(messages, ans), stop_reason="end_turn")
