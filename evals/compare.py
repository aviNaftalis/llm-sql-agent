"""Compare models side by side from their per-model summaries.

Reads every results/summary_*.json (written by the harness, one per model) and
renders results/model_comparison.png:
  left  — overall naive vs. agent accuracy, grouped by model
  right — agent accuracy by difficulty tier, one bar group per model
Also prints a comparison table. Run after evaluating 2+ models (see `make compare`).
"""
from __future__ import annotations

import glob
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from llm_sql_agent.config import RESULTS_DIR  # noqa: E402

TIERS = ["easy", "medium", "hard"]


def _load_summaries() -> list[dict]:
    out = []
    for path in sorted(glob.glob(os.path.join(RESULTS_DIR, "summary_*.json"))):
        with open(path) as f:
            out.append(json.load(f))
    return out


def _print_table(summaries: list[dict]) -> None:
    from rich.console import Console
    from rich.table import Table

    t = Table(title="Model comparison")
    t.add_column("model")
    t.add_column("naive acc", justify="right")
    t.add_column("agent acc", justify="right")
    t.add_column("agent repair", justify="right")
    t.add_column("agent avg tokens", justify="right")
    t.add_column("agent cost", justify="right")
    for s in summaries:
        n, a = s["naive"]["overall"], s["agent"]["overall"]
        t.add_row(
            s["model"],
            f"{n['accuracy']*100:.0f}%",
            f"{a['accuracy']*100:.0f}%",
            f"{a.get('repair_rate', 0)*100:.0f}%",
            f"{a['avg_tokens']:.0f}",
            f"${a['total_cost_usd']:.4f}",
        )
    Console().print(t)


def _chart(summaries: list[dict], path: str) -> None:
    models = [s["model"] for s in summaries]
    x = range(len(models))
    w = 0.38

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

    naive = [s["naive"]["overall"]["accuracy"] * 100 for s in summaries]
    agent = [s["agent"]["overall"]["accuracy"] * 100 for s in summaries]
    ax1.bar([i - w / 2 for i in x], naive, w, label="naive", color="#c44e52")
    ax1.bar([i + w / 2 for i in x], agent, w, label="agent", color="#4c72b0")
    ax1.set_xticks(list(x)); ax1.set_xticklabels(models, rotation=10)
    ax1.set_ylabel("execution accuracy (%)"); ax1.set_ylim(0, 105)
    ax1.set_title("Overall accuracy: naive vs. agent, by model")
    for i, (nv, av) in enumerate(zip(naive, agent)):
        ax1.text(i - w / 2, nv + 1, f"{nv:.0f}", ha="center", fontsize=8)
        ax1.text(i + w / 2, av + 1, f"{av:.0f}", ha="center", fontsize=8)
    ax1.legend()

    nbar = len(models)
    group = 0.8
    bw = group / nbar
    palette = ["#4c72b0", "#dd8452", "#55a868", "#8172b3"]
    for mi, s in enumerate(summaries):
        vals = [s["agent"]["by_tier"].get(t, {}).get("accuracy", 0) * 100 for t in TIERS]
        offs = [ti - group / 2 + bw * (mi + 0.5) for ti in range(len(TIERS))]
        ax2.bar(offs, vals, bw, label=s["model"], color=palette[mi % len(palette)])
    ax2.set_xticks(range(len(TIERS))); ax2.set_xticklabels(TIERS)
    ax2.set_ylabel("agent execution accuracy (%)"); ax2.set_ylim(0, 105)
    ax2.set_title("Agent accuracy by difficulty, by model")
    ax2.legend()

    fig.suptitle("Model comparison — text-to-SQL agent")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def main() -> int:
    summaries = _load_summaries()
    if len(summaries) < 2:
        print(f"Need >=2 per-model summaries in {RESULTS_DIR} (found {len(summaries)}). "
              "Run the harness for two models first (see `make compare`).", file=sys.stderr)
        return 2
    _print_table(summaries)
    out = os.path.join(RESULTS_DIR, "model_comparison.png")
    _chart(summaries, out)
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
