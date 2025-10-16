"""Petit runner DQ pour exécuter des métriques/tests simples à partir d'une configuration.

Le format de config attendu (extrait minimal):
{
  "metrics": [
    {"id": "m1", "type": "missing_rate", "database": "ds", "column": "col"}
  ],
  "tests": [
    {"id": "t1", "type": "range", "metric": "m1", "low": 0, "high": 0.1}
  ]
}

Le runner renvoie un dict avec résultats des métriques et des tests.
"""
from typing import Dict, Any

import pandas as pd

from .metrics import missing_rate, dq_test_range


def run_dq_config(df: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
    """Exécute les métriques et tests définis dans `config` sur `df`.

    Args:
        df: DataFrame à analyser.
        config: dict contenant keys 'metrics' et 'tests'.

    Returns:
        dict: {
            'metrics': {metric_id: {'value': ...}},
            'tests': {test_id: {'passed': bool, 'message': str, ...}}
        }
    """
    results = {"metrics": {}, "tests": {}}

    metrics_cfg = config.get("metrics", []) or []
    tests_cfg = config.get("tests", []) or []

    # Exécuter métriques
    for m in metrics_cfg:
        mid = m.get("id")
        mtype = m.get("type")
        if mtype == "missing_rate":
            col = m.get("column")
            try:
                val = missing_rate(df, column=col) if col else missing_rate(df)
            except Exception as e:
                results["metrics"][mid] = {"error": str(e)}
            else:
                results["metrics"][mid] = {"value": val}
        else:
            results["metrics"][mid] = {"error": f"Unknown metric type: {mtype}"}

    # Exécuter tests (référençant des métriques par id)
    for t in tests_cfg:
        tid = t.get("id")
        ttype = t.get("type")
        if ttype == "range":
            metric_ref = t.get("metric")
            if metric_ref not in results["metrics"]:
                results["tests"][tid] = {"passed": False, "message": f"Metric {metric_ref} not found"}
                continue

            metric_entry = results["metrics"][metric_ref]
            if "value" not in metric_entry:
                results["tests"][tid] = {"passed": False, "message": f"Metric {metric_ref} has error: {metric_entry.get('error')}"}
                continue

            val = metric_entry["value"]
            low = t.get("low")
            high = t.get("high")
            inclusive = t.get("inclusive", True)
            res = dq_test_range(val, low, high, inclusive=inclusive)
            results["tests"][tid] = res
        else:
            results["tests"][tid] = {"passed": False, "message": f"Unknown test type: {ttype}"}

    return results
