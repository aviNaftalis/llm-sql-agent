import pytest

from llm_sql_agent.guardrails import GuardrailError, enforce_limit, validate_select


def test_select_is_allowed():
    assert validate_select("SELECT 1") == "SELECT 1"
    assert validate_select("  SELECT * FROM orders;  ") == "SELECT * FROM orders"


def test_with_cte_is_allowed():
    sql = "WITH t AS (SELECT 1 AS x) SELECT x FROM t"
    assert validate_select(sql) == sql


@pytest.mark.parametrize("sql", [
    "DROP TABLE customers",
    "DELETE FROM orders",
    "INSERT INTO products VALUES (1)",
    "UPDATE orders SET status='x'",
    "PRAGMA writable_schema = ON",
])
def test_write_statements_rejected(sql):
    with pytest.raises(GuardrailError):
        validate_select(sql)


def test_multiple_statements_rejected():
    with pytest.raises(GuardrailError):
        validate_select("SELECT 1; SELECT 2")


def test_limit_injected_when_absent():
    out = enforce_limit("SELECT * FROM orders", 100)
    assert out.endswith("LIMIT 100")


def test_limit_not_double_injected():
    sql = "SELECT * FROM orders LIMIT 5"
    assert enforce_limit(sql, 100) == sql


def test_inner_limit_still_gets_outer_cap():
    sql = "SELECT * FROM (SELECT * FROM orders LIMIT 5) ORDER BY order_id"
    assert enforce_limit(sql, 100).endswith("LIMIT 100")
