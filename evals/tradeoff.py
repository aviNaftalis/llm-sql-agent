"""The headline comparison: a small model + an agent vs. a big model one-shot.

Reads the saved Haiku and Opus summaries and charts three configurations across
the three axes that matter — **accuracy, latency, tokens**:

  * Haiku — naive      (cheap, fast, wrong)
  * Opus  — naive      (expensive one-shot, still wrong)
  * Haiku — agentic    (the sweet spot: right, and cheaper than Opus one-shot)

The point: the agent loop lets a small model beat a big model used naively, for
fewer tokens — paying only in latency (it makes several calls). No new API calls;
run the harness for both models first (`make compare`).
"""
from __future__ import annotations

import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from llm_sql_agent.config import RESULTS_DIR  # noqa: E402

HAIKU = os.path.join(RESULTS_DIR, "summary_claude-haiku-4-5.json")
OPUS = os.path.join(RESULTS_DIR, "summary_claude-opus-4-8.json")

RED = "#c44e52"
ORANGE = "#dd8452"
GREEN = "#55a868"


def main() -> int:
    if not (os.path.exists(HAIKU) and os.path.exists(OPUS)):
        print("Need both summary_claude-haiku-4-5.json and summary_claude-opus-4-8.json "
              "in results/. Run `make compare` first.", file=sys.stderr)
        return 2
    h = json.load(open(HAIKU))
    o = json.load(open(OPUS))

    # (label, node, color)
    configs = [
        ("Haiku\nnaive", h["naive"]["overall"], RED),
        ("Opus\nnaive", o["naive"]["overall"], ORANGE),
        ("Haiku\n+ agent", h["agent"]["overall"], GREEN),
    ]
    labels = [c[0] for c in configs]
    colors = [c[2] for c in configs]

    metrics = [
        ("Accuracy (%)", [c[1]["accuracy"] * 100 for c in configs], "higher is better", "{:.0f}"),
        ("p95 latency (s)", [c[1]["p95_latency_s"] for c in configs], "lower is better", "{:.1f}"),
        ("Tokens / question", [c[1]["avg_tokens"] for c in configs], "lower is better", "{:.0f}"),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(13, 4.6))
    for ax, (title, vals, hint, fmt) in zip(axes, metrics):
        bars = ax.bar(labels, vals, color=colors)
        ax.set_title(f"{title}\n({hint})", fontsize=11)
        top = max(vals) if max(vals) else 1
        ax.set_ylim(0, top * 1.18)
        for rect, v in zip(bars, vals):
            ax.text(rect.get_x() + rect.get_width() / 2, v + top * 0.02,
                    fmt.format(v), ha="center", va="bottom", fontsize=9)

    n = h.get("n", "?")
    fig.suptitle(f"Small model + agent  vs.  big model one-shot  (n={n})\n"
                 "Haiku+agent beats Opus-naive on accuracy AND tokens — paying only in latency",
                 fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    out = os.path.join(RESULTS_DIR, "tradeoff.png")
    fig.savefig(out, dpi=130)
    plt.close(fig)
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
