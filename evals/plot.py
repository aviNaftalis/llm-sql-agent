"""Render the headline charts from results/benchmark_summary.json.

  results/accuracy.png         naive vs. agent execution accuracy per tier
  results/latency_tokens.png   agent speed (p95 latency) and cost (tokens) per tier

Run after the harness (the `chart` Make target does this automatically).
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


def _latency_tokens_chart(summary: dict, path: str) -> None:
    tiers = TIERS
    n_lat = [v * 1000 for v in _series(summary, "naive", "p95_latency_s")]
    a_lat = [v * 1000 for v in _series(summary, "agent", "p95_latency_s")]
    n_tok = _series(summary, "naive", "avg_tokens")
    a_tok = _series(summary, "agent", "avg_tokens")
    x = range(len(tiers))
    w = 0.38

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))
    ax1.bar([i - w / 2 for i in x], n_lat, w, label="naive", color="#c44e52")
    ax1.bar([i + w / 2 for i in x], a_lat, w, label="agent", color="#4c72b0")
    ax1.set_xticks(list(x)); ax1.set_xticklabels(tiers)
    ax1.set_ylabel("p95 latency (ms)")
    ax1.set_title("Speed (lower is better)")
    ax1.legend()

    ax2.bar([i - w / 2 for i in x], n_tok, w, label="naive", color="#c44e52")
    ax2.bar([i + w / 2 for i in x], a_tok, w, label="agent", color="#4c72b0")
    ax2.set_xticks(list(x)); ax2.set_xticklabels(tiers)
    ax2.set_ylabel("avg tokens / question")
    ax2.set_title("Cost in tokens (the agent trades tokens for accuracy)")
    ax2.legend()

    fig.suptitle(f"Speed & token cost — {summary['model']}")
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
    _latency_tokens_chart(summary, os.path.join(RESULTS_DIR, "latency_tokens.png"))
    print(f"Wrote {RESULTS_DIR}/accuracy.png and latency_tokens.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
