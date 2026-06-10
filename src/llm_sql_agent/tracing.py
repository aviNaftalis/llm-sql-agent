"""Lightweight span tracing with token + cost accounting.

Wrap each LLM call and tool call so every step is timed and its token usage
recorded. `summary()` rolls the spans up into the metrics the benchmark reports
(latency, steps, tokens, estimated cost); `render()` prints a readable trace for
the CLI demo.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Callable

from .config import price_for


@dataclass
class Span:
    kind: str           # "llm" | "tool"
    label: str
    latency_s: float
    input_tokens: int = 0
    output_tokens: int = 0
    is_error: bool = False
    detail: str = ""


class Tracer:
    def __init__(self, model: str):
        self.model = model
        self.spans: list[Span] = []

    def run_llm(self, label: str, fn: Callable):
        t0 = perf_counter()
        resp = fn()
        dt = perf_counter() - t0
        self.spans.append(Span(
            kind="llm", label=label, latency_s=dt,
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
            detail=(resp.text or "").strip()[:120],
        ))
        return resp

    def run_tool(self, label: str, fn: Callable):
        t0 = perf_counter()
        text, is_error = fn()
        dt = perf_counter() - t0
        self.spans.append(Span(
            kind="tool", label=label, latency_s=dt,
            is_error=is_error, detail=text.strip()[:120],
        ))
        return text, is_error

    # --- rollups -----------------------------------------------------------
    def summary(self) -> dict:
        in_tok = sum(s.input_tokens for s in self.spans)
        out_tok = sum(s.output_tokens for s in self.spans)
        p_in, p_out = price_for(self.model)
        cost = in_tok / 1e6 * p_in + out_tok / 1e6 * p_out
        return {
            "llm_calls": sum(1 for s in self.spans if s.kind == "llm"),
            "tool_calls": sum(1 for s in self.spans if s.kind == "tool"),
            "tool_errors": sum(1 for s in self.spans if s.kind == "tool" and s.is_error),
            "input_tokens": in_tok,
            "output_tokens": out_tok,
            "total_tokens": in_tok + out_tok,
            "cost_usd": round(cost, 6),
            "latency_s": round(sum(s.latency_s for s in self.spans), 4),
        }

    def render(self, console=None) -> None:
        """Pretty-print the trace (used by the CLI demo)."""
        from rich.console import Console
        from rich.table import Table

        console = console or Console()
        table = Table(title="Agent trace", show_lines=False)
        table.add_column("#", justify="right", style="dim")
        table.add_column("step")
        table.add_column("latency", justify="right")
        table.add_column("tokens", justify="right")
        table.add_column("detail", overflow="fold", max_width=70)
        for i, s in enumerate(self.spans, 1):
            tok = f"{s.input_tokens}+{s.output_tokens}" if s.kind == "llm" else ""
            label = s.label if s.kind == "llm" else f"tool:{s.label}"
            style = "red" if s.is_error else None
            table.add_row(str(i), label, f"{s.latency_s*1000:.0f}ms", tok,
                          s.detail, style=style)
        console.print(table)
        s = self.summary()
        console.print(
            f"[bold]steps[/bold] {s['llm_calls']}  "
            f"[bold]tool calls[/bold] {s['tool_calls']} "
            f"([red]{s['tool_errors']} error(s)[/red])  "
            f"[bold]tokens[/bold] {s['total_tokens']}  "
            f"[bold]cost[/bold] ${s['cost_usd']:.4f}  "
            f"[bold]latency[/bold] {s['latency_s']:.2f}s"
        )
