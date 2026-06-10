"""Deterministic tests of the agent loop, naive baseline, and tracing, driven by
a scripted LLM double (no API key). Complex multi-join / CTE / window questions
from the eval set are used so the loop is exercised on realistic SQL.
"""
import pytest

from evals import metrics
from llm_sql_agent.agent import run_agent
from llm_sql_agent.dataset import get_question, load_eval_set
from llm_sql_agent.naive import run_naive
from llm_sql_agent.tracing import Tracer

from fakes import ScriptedLLM

COMPLEX_IDS = ["h02", "h06", "h09", "h11", "h13"]  # joins, CTE+subquery, window funcs


@pytest.fixture
def items():
    return load_eval_set()


@pytest.mark.parametrize("qid", COMPLEX_IDS)
def test_agent_repairs_and_lands_on_correct_sql(settings, items, qid):
    q = get_question(items, qid)
    client = ScriptedLLM(q["gold_sql"], repair=True)
    tracer = Tracer(settings.model)
    result = run_agent(client, settings, q["question"], tracer)

    assert result.repaired is True
    assert result.sql_errors == 1
    assert metrics.execution_accuracy(settings.db_path, q["gold_sql"], result.predicted_sql)

    # tracing recorded speed + tokens
    s = tracer.summary()
    assert s["total_tokens"] > 0
    assert s["latency_s"] >= 0
    assert s["llm_calls"] >= 4  # inspect -> describe -> broken -> repair -> answer


@pytest.mark.parametrize("qid", COMPLEX_IDS)
def test_agent_without_error_does_not_flag_repair(settings, items, qid):
    q = get_question(items, qid)
    client = ScriptedLLM(q["gold_sql"], repair=False)
    result = run_agent(client, settings, q["question"], Tracer(settings.model))
    assert result.repaired is False
    assert result.sql_errors == 0
    assert metrics.execution_accuracy(settings.db_path, q["gold_sql"], result.predicted_sql)


def test_naive_correct_executes(settings, items):
    q = get_question(items, "h02")
    nr = run_naive(ScriptedLLM(q["gold_sql"]), settings, q["question"], Tracer(settings.model))
    assert nr.executed_ok
    assert metrics.execution_accuracy(settings.db_path, q["gold_sql"], nr.predicted_sql)


def test_naive_broken_fails(settings, items):
    q = get_question(items, "h02")
    nr = run_naive(ScriptedLLM(q["gold_sql"], naive_broken=True), settings,
                   q["question"], Tracer(settings.model))
    assert nr.executed_ok is False
    assert not metrics.execution_accuracy(settings.db_path, q["gold_sql"], nr.predicted_sql)
