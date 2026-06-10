"""`sql-agent ask "<question>"` — run the agent on one question and print a
live trace (reasoning -> tool calls -> repaired error -> final answer).
"""
from __future__ import annotations

import argparse
import os
import sys

from .agent import run_agent
from .config import load_settings
from .llm import make_client
from .tracing import Tracer


def _ask(question: str, provider: str | None, model: str | None) -> int:
    settings = load_settings(provider=provider, model=model)
    if not os.path.exists(settings.db_path):
        print(f"Database not found at {settings.db_path}. Run `make db` first.", file=sys.stderr)
        return 2

    client = make_client(settings)
    tracer = Tracer(settings.model)

    from rich.console import Console
    console = Console()
    console.print(f"[bold]Provider[/bold] {settings.provider}  "
                  f"[bold]Model[/bold] {settings.model}")
    console.print(f"[bold]Q:[/bold] {question}\n")

    result = run_agent(client, settings, question, tracer)
    tracer.render(console)
    console.print()
    if result.predicted_sql:
        console.print(f"[bold]SQL:[/bold] {result.predicted_sql}")
    console.print(f"[bold]Answer:[/bold] {result.final_text}")
    if result.repaired:
        console.print("[green](recovered from a SQL error via the repair loop)[/green]")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sql-agent")
    sub = parser.add_subparsers(dest="command", required=True)
    ask = sub.add_parser("ask", help="Ask the agent a question")
    ask.add_argument("question")
    ask.add_argument("--provider", default=None, help="anthropic (default) | ollama (roadmap)")
    ask.add_argument("--model", default=None)
    args = parser.parse_args(argv)

    if args.command == "ask":
        return _ask(args.question, args.provider, args.model)
    parser.error("unknown command")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
