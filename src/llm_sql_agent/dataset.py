"""Loading the eval set and selecting showcase questions."""
from __future__ import annotations

import json

from .config import EVAL_SET_PATH

# Three complex questions used for the demo GIFs (`make demos`): a profit
# aggregation, a windowed per-group ranking, and a CTE + subquery comparison.
SHOWCASE_IDS = ["h02", "h13", "h06"]


def load_eval_set(path: str | None = None) -> list[dict]:
    path = path or EVAL_SET_PATH
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def get_question(items: list[dict], qid: str) -> dict:
    for it in items:
        if it["id"] == qid:
            return it
    raise KeyError(f"no eval question with id {qid!r}")
