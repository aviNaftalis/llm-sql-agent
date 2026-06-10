"""Render the headline accuracy chart from results/benchmark_summary.json.

  results/accuracy.png   naive vs. agent execution accuracy per tier

Run after the harness (the `chart` Make target does this automatically). Token/
latency figures aren't charted: via the `claude` CLI they carry context overhead
and aren't representative — accuracy is the meaningful axis.
"""
from __future__ import annotations

import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from llm_sql_agent.config import RESULTS_DIR  # noqa: E402

TIERS = ["easy", "medium", "hard", "overall"]


def _series(summary: dict, approach: str, key: str) -> list[float]:
    vals = []
    for tier in TIERS:
        node = (summary[approach]["overall"] if tier == "overall"
                else summary[approach]["by_tier"].get(tier, {}))
        vals.append(node.get(key, 0) or 0)
    return vals


def _accuracy_chart(summary: dict, path: str) -> None:
    naive = [v * 100 for v in _series(summary, "naive", "accuracy")]
    agent = [v * 100 for v in _series(summary, "agent", "accuracy")]
    x = range(len(TIERS))
    w = 0.38
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar([i - w / 2 for i in x], naive, w, label="naive (one-shot)", color="#c44e52")
    ax.bar([i + w / 2 for i in x], agent, w, label="agent (tools + repair)", color="#4c72b0")
    ax.set_xticks(list(x))
    ax.set_xticklabels(TIERS)
    ax.set_ylabel("execution accuracy (%)")
    ax.set_ylim(0, 105)
    ax.set_title(f"Text-to-SQL accuracy: naive vs. agent\n{summary['model']}")
    for i, (n, a) in enumerate(zip(naive, agent)):
        ax.text(i - w / 2, n + 1, f"{n:.0f}", ha="center", fontsize=8)
        ax.text(i + w / 2, a + 1, f"{a:.0f}", ha="center", fontsize=8)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def main() -> int:
    summary_path = os.path.join(RESULTS_DIR, "benchmark_summary.json")
    if not os.path.exists(summary_path):
        print("No benchmark_summary.json — run `make eval` first.", file=sys.stderr)
        return 2
    with open(summary_path) as f:
        summary = json.load(f)
    os.makedirs(RESULTS_DIR, exist_ok=True)
    _accuracy_chart(summary, os.path.join(RESULTS_DIR, "accuracy.png"))
    print(f"Wrote {RESULTS_DIR}/accuracy.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
