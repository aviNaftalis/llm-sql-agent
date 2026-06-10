"""The Anthropic (Claude) backend — via the local `claude` CLI, no API key.

There's one backend: Claude. We reach it through the authenticated `claude` CLI
(`claude -p`) rather than the Messages API, so it runs on your Claude Code login
with no ANTHROPIC_API_KEY anywhere. The CLI returns text, not native `tool_use`
blocks, so the agent is driven with a small JSON-action protocol: each turn the
model emits one JSON object — a tool call or a final answer — which we parse back
into the normalized `LLMResponse`.

Model is selectable via `--model` (LLM_MODEL), e.g. claude-opus-4-8 (default) or
claude-haiku-4-5 for the model comparison.
"""
from __future__ import annotations

import json
import shutil
import subprocess

from .base import LLMResponse, ToolCall, Usage

_TOOL_PROTOCOL = """You are a senior data analyst answering a question over a SQLite database.

You have these tools:
  - list_tables()                      list all table names
  - describe_table(table_name)         show a table's columns and types
  - run_sql(query)                     run ONE read-only SELECT and get rows

Do NOT use any of your own tools or the filesystem. Respond with EXACTLY ONE
JSON object and nothing else (no prose, no markdown fences):

  to call a tool:   {"action": "tool", "tool": "run_sql", "args": {"query": "SELECT ..."}}
  when finished:    {"action": "final", "answer": "<one sentence>"}

If a run_sql call returns an error, read it and try a corrected query."""

_NAIVE_PROTOCOL = """Reply with EXACTLY ONE SQLite SELECT query that answers the question,
and nothing else — no explanation, no markdown, no JSON."""


def _render(messages: list[dict]) -> str:
    lines = []
    for m in messages:
        role, content = m.get("role"), m.get("content")
        if isinstance(content, str):
            lines.append(f"{role.upper()}: {content}")
        elif isinstance(content, list):
            for b in content:
                t = b.get("type")
                if t == "text" and b.get("text"):
                    lines.append(f"ASSISTANT: {b['text']}")
                elif t == "tool_use":
                    lines.append(f"ASSISTANT called {b['name']}({json.dumps(b.get('input', {}))})")
                elif t == "tool_result":
                    tag = "TOOL ERROR" if b.get("is_error") else "TOOL RESULT"
                    lines.append(f"{tag}: {b.get('content', '')}")
    return "\n".join(lines)


def _extract_json(text: str) -> dict | None:
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    start, depth = text.find("{"), 0
    if start == -1:
        return None
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i + 1])
                except Exception:
                    return None
    return None


def _extract_sql(text: str) -> str:
    import re
    t = text.strip()
    fence = re.search(r"```(?:sql)?\s*(.+?)```", t, flags=re.S | re.I)
    return fence.group(1).strip() if fence else t


class AnthropicClient:
    def __init__(self, model: str, settings):
        if shutil.which("claude") is None:
            raise RuntimeError(
                "The `claude` CLI was not found on PATH. Install and log in to "
                "Claude Code (https://docs.claude.com/en/docs/claude-code); this "
                "backend uses `claude -p` and needs no API key."
            )
        self.model = model
        self._timeout = max(settings.request_timeout, 180)
        self._n = 0

    def _run(self, prompt: str) -> tuple[str, Usage]:
        proc = subprocess.run(
            ["claude", "-p", prompt, "--model", self.model, "--output-format", "json"],
            capture_output=True, text=True, timeout=self._timeout,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"claude CLI failed ({proc.returncode}): {proc.stderr[:400]}")
        data = json.loads(proc.stdout)
        if data.get("is_error"):
            raise RuntimeError(f"claude CLI error: {data.get('result', '')[:400]}")
        u = data.get("usage", {})
        # Uncached input + output only — excludes the CLI's cached system prompt.
        usage = Usage(int(u.get("input_tokens", 0)), int(u.get("output_tokens", 0)))
        return data.get("result", ""), usage

    def chat(self, system, messages, tools=None) -> LLMResponse:
        if tools:
            prompt = (f"{_TOOL_PROTOCOL}\n\n=== conversation so far ===\n"
                      f"{_render(messages)}\n\n=== respond with the next JSON object ===")
            text, usage = self._run(prompt)
            action = _extract_json(text)
            if action and action.get("action") == "tool" and action.get("tool"):
                self._n += 1
                tc = ToolCall(id=f"toolu_{self._n}", name=action["tool"],
                              arguments=action.get("args", {}) or {})
                return LLMResponse(tool_calls=[tc], usage=usage, stop_reason="tool_use")
            answer = (action or {}).get("answer") or text
            return LLMResponse(text=answer, usage=usage, stop_reason="end_turn")

        # naive: one SQL string. The schema lives in `system`.
        prompt = f"{system}\n\n{_NAIVE_PROTOCOL}\n\n=== context ===\n{_render(messages)}\n\nSQL:"
        text, usage = self._run(prompt)
        return LLMResponse(text=_extract_sql(text), usage=usage, stop_reason="end_turn")
