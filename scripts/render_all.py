#!/usr/bin/env python3
"""Render a small demo GIF for every command the repo runs (`make tour`).

Keeps token use tiny: the LLM-touching demos run on just 1-2 questions (Haiku
where the model doesn't matter). The agent showcase GIFs (`make demos`) are
separate and reused as-is. Needs the `agg` binary on PATH.
"""
from __future__ import annotations

import os
import subprocess
import sys

from llm_sql_agent.config import RESULTS_DIR

PY = sys.executable  # the venv python running this script

# Tiny, hard-weighted slice so the demos stay cheap. Full set is 35 questions.
IDS = "e01,h02"

DEMOS = [
    # name        rows  last-frame  command
    ("db",        28,   "5",  [PY, "-m", "data.seed"]),
    ("test",      24,   "6",  [PY, "-m", "pytest", "-q", "--ignore=tests/test_smoke.py"]),
    ("eval",      36,   "12", [PY, "-m", "evals.harness", "--model", "claude-haiku-4-5", "--ids", IDS]),
    ("compare",   58,   "12", ["bash", "-lc",
        f"{PY} -m evals.harness --model claude-opus-4-8 --ids {IDS} && "
        f"{PY} -m evals.harness --model claude-haiku-4-5 --ids {IDS} && "
        f"{PY} -m evals.compare"]),
]


def main() -> int:
    os.makedirs(RESULTS_DIR, exist_ok=True)
    for name, rows, last, cmd in DEMOS:
        cast = os.path.join(RESULTS_DIR, f"demo_{name}.cast")
        gif = os.path.join(RESULTS_DIR, f"demo_{name}.gif")
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
