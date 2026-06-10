"""Benchmark-as-tests: run the full harness on the deterministic mock backend
and assert on the measured metrics. This turns "we measure accuracy, speed, and
tokens" into a checked, regression-guarded property rather than a README claim.
"""
from evals import harness, metrics
from llm_sql_agent.dataset import build_oracle, load_eval_set
from llm_sql_agent.llm import make_client


def _run(settings):
    items = load_eval_set()
    client = make_client(settings, oracle=build_oracle(items))
    records = [harness.evaluate(client, settings, it) for it in items]
    summary = metrics.aggregate(records, "mock", "mock")
    return records, summary


def test_agent_beats_naive_on_accuracy(settings):
    _, summary = _run(settings)
    naive_acc = summary["naive"]["overall"]["accuracy"]
    agent_acc = summary["agent"]["overall"]["accuracy"]
    assert agent_acc >= naive_acc
    # The agent recovers from the errors that sink the naive baseline.
    assert agent_acc > naive_acc
    assert naive_acc < 1.0


def test_repair_rate_is_positive(settings):
    _, summary = _run(settings)
    assert summary["agent"]["overall"]["repair_rate"] > 0


def test_speed_and_token_metrics_recorded(settings):
    records, summary = _run(settings)
    overall = summary["agent"]["overall"]
    for key in ("avg_latency_s", "p50_latency_s", "p95_latency_s", "avg_tokens", "avg_steps"):
        assert key in overall
    assert overall["avg_tokens"] > 0
    assert overall["avg_steps"] >= 3  # inspect schema + run + (maybe) repair
    for r in records:
        assert r["agent"]["total_tokens"] > 0
        assert r["agent"]["latency_s"] >= 0


def test_every_tier_present(settings):
    _, summary = _run(settings)
    for tier in ("easy", "medium", "hard"):
        assert tier in summary["agent"]["by_tier"]
        assert tier in summary["naive"]["by_tier"]
