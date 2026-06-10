"""Benchmark metrics: execution accuracy, percentiles, and aggregation.

`execution_accuracy` is the standard text-to-SQL metric — run the gold and
predicted queries and compare result sets (order-insensitive unless the gold
query has a top-level ORDER BY). `aggregate` rolls per-question records up into
the accuracy / speed / token figures the harness reports and plot.py charts.
"""
from __future__ import annotations

import math

from llm_sql_agent import db

_FLOAT_TOL = 6  # decimal places to round before comparing


def _normalize(rows: list[tuple]) -> list[tuple]:
    out = []
    for r in rows:
        out.append(tuple(round(v, _FLOAT_TOL) if isinstance(v, float) else v for v in r))
    return out


def _execute(db_path: str, sql: str) -> list[tuple] | None:
    try:
        res = db.run_query(db_path, sql, 100_000)
    except Exception:
        return None
    return _normalize(res.rows)


def execution_accuracy(db_path: str, gold_sql: str, pred_sql: str | None) -> bool:
    if not pred_sql:
        return False
    gold_rows = _execute(db_path, gold_sql)
    pred_rows = _execute(db_path, pred_sql)
    if gold_rows is None or pred_rows is None:
        return False
    if "order by" in gold_sql.lower():
        return gold_rows == pred_rows
    return sorted(map(repr, gold_rows)) == sorted(map(repr, pred_rows))


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    xs = sorted(values)
    k = (len(xs) - 1) * p / 100.0
    lo, hi = math.floor(k), math.ceil(k)
    if lo == hi:
        return float(xs[int(k)])
    return float(xs[lo] + (xs[hi] - xs[lo]) * (k - lo))


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _summarize(rows: list[dict], approach: str) -> dict:
    """rows are per-question records' sub-dicts for one approach."""
    if not rows:
        return {}
    latencies = [r["latency_s"] for r in rows]
    out = {
        "n": len(rows),
        "accuracy": round(_mean([1.0 if r["correct"] else 0.0 for r in rows]), 4),
        "avg_latency_s": round(_mean(latencies), 4),
        "p50_latency_s": round(percentile(latencies, 50), 4),
        "p95_latency_s": round(percentile(latencies, 95), 4),
        "avg_tokens": round(_mean([r["total_tokens"] for r in rows]), 1),
        "total_cost_usd": round(sum(r["cost_usd"] for r in rows), 6),
    }
    if approach == "agent":
        out["avg_steps"] = round(_mean([r["steps"] for r in rows]), 2)
        out["repair_rate"] = round(_mean([1.0 if r.get("repaired") else 0.0 for r in rows]), 4)
    return out


def aggregate(records: list[dict], provider: str, model: str) -> dict:
    tiers = ["easy", "medium", "hard"]
    summary = {"provider": provider, "model": model, "n": len(records)}
    for approach in ("naive", "agent"):
        rows = [r[approach] for r in records]
        by_tier = {}
        for tier in tiers:
            tier_rows = [r[approach] for r in records if r["difficulty"] == tier]
            if tier_rows:
                by_tier[tier] = _summarize(tier_rows, approach)
        summary[approach] = {"overall": _summarize(rows, approach), "by_tier": by_tier}
    return summary
