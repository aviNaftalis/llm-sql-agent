"""Loading the eval set and building the mock oracle."""
from __future__ import annotations

import json

from .config import EVAL_SET_PATH


def load_eval_set(path: str | None = None) -> list[dict]:
    path = path or EVAL_SET_PATH
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def build_oracle(items: list[dict]) -> dict:
    """question -> {gold_sql, difficulty}, consumed only by the mock backend."""
    return {
        it["question"]: {"gold_sql": it["gold_sql"], "difficulty": it["difficulty"]}
        for it in items
    }


def _norm(q: str) -> str:
    return q.strip().rstrip(".").lower()


def resolve_question(question: str, items: list[dict]) -> str:
    """Map a user-typed question to the exact eval-set text (for mock mode)."""
    by_exact = {it["question"] for it in items}
    if question in by_exact:
        return question
    target = _norm(question)
    for it in items:
        if _norm(it["question"]) == target:
            return it["question"]
    return question
