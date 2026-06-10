#!/usr/bin/env python3
"""The one example that justifies the repo: one-shot vs. agentic on one question.

Runs the SAME question through the naive one-shot baseline and the agentic loop,
then prints a side-by-side verdict — the one-shot returns a plausible-but-wrong
answer, while the agent runs its query, sees the result, and returns the correct
one. This is the whole point: execution feedback beats guessing once.

    python scripts/showcase.py --id h15 --model claude-haiku-4-5
"""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from evals import metrics  # noqa: E402
from llm_sql_agent import db  # noqa: E402
from llm_sql_agent.agent import run_agent  # noqa: E402
from llm_sql_agent.config import load_settings  # noqa: E402
from llm_sql_agent.dataset import get_question, load_eval_set  # noqa: E402
from llm_sql_agent.llm import make_client  # noqa: E402
from llm_sql_agent.naive import run_naive  # noqa: E402
from llm_sql_agent.tracing import Tracer  # noqa: E402


def _rowcount(db_path: str, sql: str | None) -> str:
    if not sql:
        return "—"
    try:
        return f"{len(db.run_query(db_path, sql, 100_000).rows)} rows"
    except Exception as e:
        return f"ERROR: {str(e)[:50]}"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--id", default="h15")
    p.add_argument("--model", default="claude-haiku-4-5")
    args = p.parse_args()

    from rich.console import Console
    from rich.panel import Panel
    console = Console()

    settings = load_settings(provider="anthropic", model=args.model)
    item = get_question(load_eval_set(), args.id)
    q, gold = item["question"], item["gold_sql"]
    client = make_client(settings)

    console.print(Panel(f"[bold]{q}[/bold]", title=f"Question ({args.id}, {args.model})",
                        border_style="white"))

    # --- one-shot ----------------------------------------------------------
    nr = run_naive(client, settings, q, Tracer(settings.model))
    naive_ok = metrics.execution_accuracy(settings.db_path, gold, nr.predicted_sql)
    verdict = "[green]✓ correct[/green]" if naive_ok else "[red]✗ WRONG[/red]"
    console.print(Panel(
        f"[dim]single prompt, one query, no feedback[/dim]\n\n"
        f"{nr.predicted_sql}\n\n"
        f"returned {_rowcount(settings.db_path, nr.predicted_sql)} → {verdict}",
        title="ONE-SHOT (naive)", border_style="red" if not naive_ok else "green"))

    # --- agentic -----------------------------------------------------------
    at = Tracer(settings.model)
    ar = run_agent(client, settings, q, at)
    agent_ok = metrics.execution_accuracy(settings.db_path, gold, ar.predicted_sql)
    at.render(console)
    verdict = "[green]✓ correct[/green]" if agent_ok else "[red]✗ WRONG[/red]"
    recovered = "  [yellow](recovered from a SQL error)[/yellow]" if ar.repaired else ""
    console.print(Panel(
        f"[dim]inspect schema → run → observe → repair → answer[/dim]\n\n"
        f"{ar.predicted_sql}\n\n"
        f"returned {_rowcount(settings.db_path, ar.predicted_sql)} → {verdict}{recovered}",
        title="AGENTIC (tools + execution + repair)",
        border_style="green" if agent_ok else "red"))

    if agent_ok and not naive_ok:
        console.print("\n[bold green]The agent ran its query and corrected the mistake "
                      "the one-shot committed.[/bold green]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
