"""Run the benchmark: naive vs. agent over the eval set, measured three ways.

Measures accuracy (execution accuracy + agent repair rate), speed (latency
percentiles, steps), and cost (tokens, USD) per difficulty tier. Writes
results/eval_results.json (full per-question records) and
results/benchmark_summary.json, then prints a comparison table.

    python -m evals.harness --provider anthropic
    python -m evals.harness --provider anthropic --model claude-sonnet-4-6
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from llm_sql_agent.agent import run_agent
from llm_sql_agent.config import RESULTS_DIR, load_settings
from llm_sql_agent.dataset import load_eval_set
from llm_sql_agent.llm import make_client
from llm_sql_agent.naive import run_naive
from llm_sql_agent.tracing import Tracer

from . import metrics


def evaluate(client, settings, item: dict) -> dict:
    q, gold = item["question"], item["gold_sql"]

    nt = Tracer(settings.model)
    nr = run_naive(client, settings, q, nt)
    naive = {**nt.summary(), "sql": nr.predicted_sql,
             "correct": metrics.execution_accuracy(settings.db_path, gold, nr.predicted_sql)}

    at = Tracer(settings.model)
    ar = run_agent(client, settings, q, at)
    agent = {**at.summary(), "sql": ar.predicted_sql, "steps": ar.steps,
             "repaired": ar.repaired,
             "correct": metrics.execution_accuracy(settings.db_path, gold, ar.predicted_sql)}

    return {"id": item["id"], "difficulty": item["difficulty"],
            "question": q, "gold_sql": gold, "naive": naive, "agent": agent}


def _print_table(summary: dict) -> None:
    from rich.console import Console
    from rich.table import Table

    console = Console()
    title = f"{summary['provider']} / {summary['model']}  (n={summary['n']})"
    table = Table(title=title)
    table.add_column("tier")
    table.add_column("naive acc", justify="right")
    table.add_column("agent acc", justify="right")
    table.add_column("repair rate", justify="right")
    table.add_column("agent steps", justify="right")
    table.add_column("agent p95 lat", justify="right")
    table.add_column("agent tokens", justify="right")

    def row(label, n, a):
        table.add_row(
            label,
            f"{n['accuracy']*100:.0f}%",
            f"{a['accuracy']*100:.0f}%",
            f"{a.get('repair_rate', 0)*100:.0f}%",
            f"{a.get('avg_steps', 0):.1f}",
            f"{a['p95_latency_s']*1000:.0f}ms",
            f"{a['avg_tokens']:.0f}",
        )

    for tier in ("easy", "medium", "hard"):
        if tier in summary["naive"]["by_tier"]:
            row(tier, summary["naive"]["by_tier"][tier], summary["agent"]["by_tier"][tier])
    row("[bold]overall[/bold]", summary["naive"]["overall"], summary["agent"]["overall"])
    console.print(table)

    no = summary["naive"]["overall"]
    ao = summary["agent"]["overall"]
    console.print(
        f"naive cost ${no['total_cost_usd']:.4f}  |  agent cost ${ao['total_cost_usd']:.4f}  "
        f"(across {summary['n']} questions)"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="evals.harness")
    parser.add_argument("--provider", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--limit", type=int, default=None, help="run only the first N questions")
    parser.add_argument("--ids", default=None, help="comma-separated question ids to run")
    args = parser.parse_args(argv)

    settings = load_settings(provider=args.provider, model=args.model)
    if not os.path.exists(settings.db_path):
        print(f"Database not found at {settings.db_path}. Run `make db` first.", file=sys.stderr)
        return 2

    all_items = load_eval_set()
    if args.ids:
        wanted = [s.strip() for s in args.ids.split(",")]
        items = [it for it in all_items if it["id"] in wanted]
    elif args.limit:
        items = all_items[: args.limit]
    else:
        items = all_items
    client = make_client(settings)

    print(f"Running {len(items)} questions on provider={settings.provider} "
          f"model={settings.model} ...")
    records = []
    for i, item in enumerate(items, 1):
        records.append(evaluate(client, settings, item))
        print(f"  [{i}/{len(items)}] {item['id']}", end="\r", flush=True)
    print()

    summary = metrics.aggregate(records, settings.provider, settings.model)

    os.makedirs(RESULTS_DIR, exist_ok=True)
    slug = settings.model.replace("/", "-")
    payload = {"summary": summary, "records": records}
    # Latest run (consumed by plot.py) + a per-model copy (consumed by compare.py).
    for path in ("eval_results.json", f"eval_results_{slug}.json"):
        with open(os.path.join(RESULTS_DIR, path), "w") as f:
            json.dump(payload, f, indent=2)
    for path in ("benchmark_summary.json", f"summary_{slug}.json"):
        with open(os.path.join(RESULTS_DIR, path), "w") as f:
            json.dump(summary, f, indent=2)

    _print_table(summary)
    print(f"\nWrote {RESULTS_DIR}/summary_{slug}.json (+ benchmark_summary.json)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
