"""Smoke test against the real Claude backend (via the `claude` CLI).

Skipped unless the `claude` CLI is on PATH, so the offline suite stays green in
CI. When present it verifies the agent drives a real model to a valid, executing
query on a complex question.

    pytest tests/test_smoke.py -v
"""
import shutil

import pytest

from llm_sql_agent import db
from llm_sql_agent.agent import run_agent
from llm_sql_agent.config import load_settings
from llm_sql_agent.dataset import get_question, load_eval_set
from llm_sql_agent.llm import make_client
from llm_sql_agent.tracing import Tracer

pytestmark = pytest.mark.skipif(
    shutil.which("claude") is None,
    reason="`claude` CLI not on PATH — real-backend smoke test skipped",
)


def test_real_agent_produces_executing_sql(db_path):
    settings = load_settings(provider="anthropic", db_path=db_path)
    client = make_client(settings)
    q = get_question(load_eval_set(), "h02")  # profit per category — multi-join + arithmetic
    result = run_agent(client, settings, q["question"], Tracer(settings.model))

    assert result.predicted_sql, "agent produced no SQL"
    # The model's SQL must at least execute against the real schema.
    db.run_query(db_path, result.predicted_sql, settings.max_rows)
