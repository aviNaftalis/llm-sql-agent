#!/usr/bin/env python3
"""Render the demo GIFs (`make tour`). Focused on the repo's reason for existing.

  demo_showcase  one-shot vs. agentic on one question (one-shot wrong, agent right)
  demo_recovery  the agent hitting a real SQL error and repairing it
  demo_eval      the naive-vs-agent benchmark (tiny run)
  demo_compare   Opus 4.8 vs Haiku 4.5 (tiny run)

Token-cheap by design: everything runs on Haiku and 1-2 questions. Already-rendered
GIFs are skipped unless FORCE=1. Needs the `agg` binary on PATH.
"""
from __future__ import annotations

import os
import subprocess
import sys

from llm_sql_agent.config import RESULTS_DIR
from llm_sql_agent.dataset import get_question, load_eval_set

PY = sys.executable
IDS = "e01,h02"  # tiny, hard-weighted slice for the benchmark demos
H04 = get_question(load_eval_set(), "h04")["question"]

DEMOS = [
    # name        rows  last  command
    ("showcase",  46,   "14", [PY, "scripts/showcase.py", "--id", "h15", "--model", "claude-haiku-4-5"]),
    ("recovery",  40,   "12", [PY, "-m", "llm_sql_agent.cli", "ask", H04, "--model", "claude-haiku-4-5"]),
    ("eval",      36,   "12", [PY, "-m", "evals.harness", "--model", "claude-haiku-4-5", "--ids", IDS]),
    ("compare",   58,   "12", ["bash", "-lc",
        f"{PY} -m evals.harness --model claude-opus-4-8 --ids {IDS} && "
        f"{PY} -m evals.harness --model claude-haiku-4-5 --ids {IDS} && "
        f"{PY} -m evals.compare"]),
]


def main() -> int:
    os.makedirs(RESULTS_DIR, exist_ok=True)
    force = os.environ.get("FORCE")
    for name, rows, last, cmd in DEMOS:
        gif = os.path.join(RESULTS_DIR, f"demo_{name}.gif")
        if os.path.exists(gif) and not force:
            print(f"skip {gif} (exists; FORCE=1 to re-render)")
            continue
        cast = os.path.join(RESULTS_DIR, f"demo_{name}.cast")
        env = {**os.environ, "REC_ROWS": str(rows)}
        subprocess.run([PY, "scripts/record_demo.py", cast, *cmd], check=True, env=env)
        subprocess.run(
            ["agg", "--theme", "monokai", "--font-size", "16",
             "--idle-time-limit", "2", "--last-frame-duration", last, cast, gif],
            check=True,
        )
        print(f"wrote {gif}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
