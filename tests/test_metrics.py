import os
import sys
import pandas as pd
import pytest

# Ensure workspace root is on sys.path so `src` package can be imported when running tests
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.metrics import missing_rate, dq_test_range


def test_missing_rate_column():
    df = pd.DataFrame({"a": [1, None, 3], "b": [None, None, 2]})
    assert abs(missing_rate(df, "a") - (1/3)) < 1e-9
    assert abs(missing_rate(df, "b") - (2/3)) < 1e-9


def test_missing_rate_global():
    df = pd.DataFrame({"a": [1, None], "b": [None, 2]})
    # total cells 4, missing 2 -> 0.5
    assert missing_rate(df) == 0.5


def test_missing_rate_empty_df():
    df = pd.DataFrame(columns=["a", "b"])  # 0 rows
    assert missing_rate(df, "a") == 0.0
    assert missing_rate(df) == 0.0


def test_missing_rate_wrong_inputs():
    with pytest.raises(TypeError):
        missing_rate(123)
    df = pd.DataFrame({"x": [1, 2]})
    with pytest.raises(KeyError):
        missing_rate(df, "y")


def test_range_inclusive_pass():
    res = dq_test_range(5, 1, 10)
    assert res["passed"] is True


def test_range_inclusive_fail():
    res = dq_test_range(0, 1, 10)
    assert res["passed"] is False
    assert "out of range" in res["message"]


def test_range_exclusive():
    assert dq_test_range(5, 5, 10, inclusive=False)["passed"] is False
    assert dq_test_range(6, 5, 10, inclusive=False)["passed"] is True


def test_range_incomparable_types():
    res = dq_test_range("a", 1, 10)
    assert res["passed"] is False
    assert "Incomparable types" in res["message"]
