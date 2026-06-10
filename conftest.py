"""Shared pytest fixtures. Living at the repo root also puts `data` and `evals`
on the import path for the test session.
"""
import pytest

from data.seed import build_database
from llm_sql_agent.config import Settings


@pytest.fixture(scope="session")
def db_path(tmp_path_factory) -> str:
    path = tmp_path_factory.mktemp("db") / "shop.db"
    build_database(str(path))
    return str(path)


@pytest.fixture
def settings(db_path) -> Settings:
    return Settings(
        provider="anthropic", model="claude-opus-4-8", db_path=db_path,
        max_steps=10, max_rows=1000, request_timeout=60, max_retries=3,
    )
