"""Re-score saved runs with the current metric — no new API calls.

Recomputes execution accuracy for every results/eval_results_*.json from the
stored predicted SQL, re-aggregates, and rewrites the per-model summaries. Handy
after changing metrics.py (you don't want to re-spend tokens to re-measure).

    python -m evals.rescore && python -m evals.tradeoff
"""
from __future__ import annotations

import glob
import json
import os

from llm_sql_agent.config import DEFAULT_DB_PATH, RESULTS_DIR

from . import metrics


def rescore_file(path: str, db_path: str) -> None:
    data = json.load(open(path))
    records = data["records"]
    for r in records:
        gold = r["gold_sql"]
        for approach in ("naive", "agent"):
            r[approach]["correct"] = metrics.execution_accuracy(db_path, gold, r[approach].get("sql"))
    summary = metrics.aggregate(records, data["summary"]["provider"], data["summary"]["model"])
    slug = summary["model"].replace("/", "-")
    json.dump({"summary": summary, "records": records}, open(path, "w"), indent=2)
    json.dump(summary, open(os.path.join(RESULTS_DIR, f"summary_{slug}.json"), "w"), indent=2)
    print(f"re-scored {os.path.basename(path)}: "
          f"naive {summary['naive']['overall']['accuracy']*100:.0f}%  "
          f"agent {summary['agent']['overall']['accuracy']*100:.0f}%")


def main() -> int:
    files = sorted(glob.glob(os.path.join(RESULTS_DIR, "eval_results_*.json")))
    for f in files:
        rescore_file(f, DEFAULT_DB_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
