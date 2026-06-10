#!/usr/bin/env python3
"""Render one demo GIF per showcase question (`make demos`).

For each complex question in dataset.SHOWCASE_IDS, records the live agent trace
to results/demo_<id>.cast and converts it to results/demo_<id>.gif with `agg`.
Needs the `agg` binary and an ANTHROPIC_API_KEY (the trace runs the real agent).
"""
from __future__ import annotations

import os
import subprocess
import sys

from llm_sql_agent.config import RESULTS_DIR
from llm_sql_agent.dataset import SHOWCASE_IDS, get_question, load_eval_set

REC_ROWS = os.environ.get("REC_ROWS", "46")  # complex traces are long
# There's a lot to read in the final trace, so hold it on screen.
IDLE = os.environ.get("AGG_IDLE", "3")
LAST_FRAME = os.environ.get("AGG_LAST_FRAME", "14")


def main() -> int:
    os.makedirs(RESULTS_DIR, exist_ok=True)
    items = load_eval_set()
    env = {**os.environ, "REC_ROWS": REC_ROWS}
    for qid in SHOWCASE_IDS:
        question = get_question(items, qid)["question"]
        cast = os.path.join(RESULTS_DIR, f"demo_{qid}.cast")
        gif = os.path.join(RESULTS_DIR, f"demo_{qid}.gif")
        subprocess.run(
            [sys.executable, "scripts/record_demo.py", cast,
             sys.executable, "-m", "llm_sql_agent.cli", "ask", question],
            check=True, env=env,
        )
        subprocess.run(
            ["agg", "--theme", "monokai", "--font-size", "16",
             "--idle-time-limit", IDLE, "--last-frame-duration", LAST_FRAME, cast, gif],
            check=True,
        )
        print(f"wrote {gif}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
