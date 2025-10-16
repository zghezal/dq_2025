import os
import sys
import pandas as pd

# Ensure workspace root is on sys.path for imports
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.dq_runner import run_dq_config


def test_run_dq_config_success():
    df = pd.DataFrame({"a": [1, None, 3], "b": [None, 2, 3]})
    cfg = {
        "metrics": [
            {"id": "m_missing_a", "type": "missing_rate", "column": "a"},
            {"id": "m_missing_all", "type": "missing_rate"}
        ],
        "tests": [
            {"id": "t1", "type": "range", "metric": "m_missing_a", "low": 0.0, "high": 0.5}
        ]
    }

    res = run_dq_config(df, cfg)
    assert "metrics" in res and "tests" in res
    assert "m_missing_a" in res["metrics"]
    assert abs(res["metrics"]["m_missing_a"]["value"] - (1/3)) < 1e-9
    assert res["tests"]["t1"]["passed"] is True


def test_run_dq_config_missing_metric_ref():
    df = pd.DataFrame({"x": [1, 2]})
    cfg = {
        "metrics": [],
        "tests": [{"id": "t_missing", "type": "range", "metric": "no_such_metric", "low": 0, "high": 1}]
    }
    res = run_dq_config(df, cfg)
    assert res["tests"]["t_missing"]["passed"] is False
    assert "not found" in res["tests"]["t_missing"]["message"]
