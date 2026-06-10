"""Loading the eval set and selecting showcase questions."""
from __future__ import annotations

import json

from .config import EVAL_SET_PATH


def load_eval_set(path: str | None = None) -> list[dict]:
    path = path or EVAL_SET_PATH
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def get_question(items: list[dict], qid: str) -> dict:
    for it in items:
        if it["id"] == qid:
            return it
    raise KeyError(f"no eval question with id {qid!r}")
