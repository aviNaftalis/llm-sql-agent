from evals import metrics


def test_identical_query_is_accurate(settings):
    gold = "SELECT category FROM products ORDER BY category"
    assert metrics.execution_accuracy(settings.db_path, gold, gold) is True


def test_broken_prediction_is_inaccurate(settings):
    gold = "SELECT COUNT(*) FROM customers"
    broken = "SELECT nonexistent_col, COUNT(*) FROM customers"
    assert metrics.execution_accuracy(settings.db_path, gold, broken) is False


def test_none_prediction_is_inaccurate(settings):
    assert metrics.execution_accuracy(settings.db_path, "SELECT 1", None) is False


def test_unordered_comparison_is_order_insensitive(settings):
    # No ORDER BY in gold -> compared as a multiset, so row order must not matter.
    gold = "SELECT country FROM customers"
    pred = "SELECT country FROM customers ORDER BY country DESC"
    assert metrics.execution_accuracy(settings.db_path, gold, pred) is True


def test_ordered_comparison_is_order_sensitive(settings):
    gold = "SELECT name FROM products ORDER BY price ASC LIMIT 5"
    pred = "SELECT name FROM products ORDER BY price DESC LIMIT 5"
    assert metrics.execution_accuracy(settings.db_path, gold, pred) is False


def test_percentile():
    assert metrics.percentile([1, 2, 3, 4], 50) == 2.5
    assert metrics.percentile([10], 95) == 10
    assert metrics.percentile([], 50) == 0.0
