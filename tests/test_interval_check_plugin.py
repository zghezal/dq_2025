import pandas as pd
import pytest

from src.plugins.discovery import discover_all_plugins, REGISTRY


class DummyContext:
    """Minimal context providing datasets and metric values for tests."""

    def __init__(self):
        self.datasets: dict[str, pd.DataFrame] = {}
        self.metrics_values: dict[str, float] = {}

    def load(self, alias: str) -> pd.DataFrame:
        if alias not in self.datasets:
            raise KeyError(f"Dataset '{alias}' not available in DummyContext")
        return self.datasets[alias].copy()


def get_interval_plugin():
    discover_all_plugins(verbose=False)
    plugin_cls = REGISTRY.get("test.interval_check")
    assert plugin_cls is not None, "Interval Check plugin should be registered"
    return plugin_cls()


def test_interval_check_metric_pass():
    plugin = get_interval_plugin()
    context = DummyContext()
    context.metrics_values["metric.ok"] = 0.52

    params = {
        "id": "interval-metric-pass",
        "specific": {
            "target_mode": "metric_value",
            "metric_id": "metric.ok",
            "lower_enabled": True,
            "lower_value": 0.5,
            "upper_enabled": True,
            "upper_value": 0.8,
        },
    }

    result = plugin.run(context, **params)

    assert result.passed is True
    assert result.value == pytest.approx(0.52)
    assert result.message == "OK"


def test_interval_check_metric_fail():
    plugin = get_interval_plugin()
    context = DummyContext()
    context.metrics_values["metric.ko"] = 1.4

    params = {
        "id": "interval-metric-fail",
        "specific": {
            "target_mode": "metric_value",
            "metric_id": "metric.ko",
            "lower_enabled": True,
            "lower_value": 0.2,
            "upper_enabled": True,
            "upper_value": 1.0,
        },
    }

    result = plugin.run(context, **params)

    assert result.passed is False
    assert "1.4 > max 1.0" in (result.message or "")


def test_interval_check_dataset_detects_outliers():
    plugin = get_interval_plugin()
    context = DummyContext()
    context.datasets["sales"] = pd.DataFrame(
        {
            "amount": [12.0, 15.5, 25.0, 60.0],
            "quantity": [11, 15, 5, 18],
        }
    )

    params = {
        "id": "interval-dataset",
        "specific": {
            "target_mode": "dataset_columns",
            "database": "sales",
            "columns": ["amount", "quantity"],
            "lower_enabled": True,
            "lower_value": 10.0,
            "upper_enabled": True,
            "upper_value": 50.0,
        },
    }

    result = plugin.run(context, **params)

    assert result.passed is False
    assert result.value == 2  # amount=60 and quantity=2 violate configured bounds
    assert "out of bounds" in (result.message or "")
    assert result.meta["violations"]["amount"]["violations"] == 1
    assert result.meta["violations"]["quantity"]["violations"] == 1


def test_interval_check_column_rules_override_bounds():
    plugin = get_interval_plugin()
    context = DummyContext()
    context.datasets["sales"] = pd.DataFrame(
        {
            "amount": [12.0, 15.5, 25.0, 60.0],
            "quantity": [11, 15, 5, 18],
        }
    )

    params = {
        "id": "interval-column-rules",
        "specific": {
            "target_mode": "dataset_columns",
            "database": "sales",
            "columns": [],
            "lower_enabled": False,
            "upper_enabled": False,
            "column_rules": [
                {"columns": ["amount"], "upper": 30.0},
                {"columns": ["quantity"], "lower": 10.0, "upper": 17.0},
            ],
        },
    }

    result = plugin.run(context, **params)

    assert result.passed is False
    assert result.value == 3
    assert result.meta["violations"]["amount"]["violations"] == 1
    assert result.meta["violations"]["quantity"]["violations"] == 2
    assert set(result.meta["violations"].keys()) == {"amount", "quantity"}
    assert result.meta["bounds"]["per_column"]["amount"]["upper"] == 30.0
    assert result.meta["skipped_columns"] == []
