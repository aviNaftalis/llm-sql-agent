from llm_sql_agent.tools.registry import dispatch


def test_list_tables(settings):
    text, is_error = dispatch("list_tables", {}, settings)
    assert not is_error
    for t in ("customers", "products", "orders", "order_items", "reviews"):
        assert t in text


def test_describe_table(settings):
    text, is_error = dispatch("describe_table", {"table_name": "orders"}, settings)
    assert not is_error
    assert "status" in text and "customer_id" in text


def test_describe_unknown_table_errors(settings):
    text, is_error = dispatch("describe_table", {"table_name": "nope"}, settings)
    assert is_error


def test_run_sql_ok(settings):
    text, is_error = dispatch("run_sql", {"query": "SELECT COUNT(*) FROM customers"}, settings)
    assert not is_error
    assert "60" in text  # seed creates 60 customers


def test_run_sql_write_blocked(settings):
    text, is_error = dispatch("run_sql", {"query": "DELETE FROM customers"}, settings)
    assert is_error
    assert "guardrail" in text.lower()


def test_run_sql_bad_column_errors(settings):
    text, is_error = dispatch("run_sql", {"query": "SELECT nonesuch FROM customers"}, settings)
    assert is_error
    assert "error" in text.lower()
