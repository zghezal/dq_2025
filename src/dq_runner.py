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

Avec l'option investigate=True, génère automatiquement des échantillons de données
problématiques pour les tests qui échouent.
"""
from typing import Dict, Any, List, Optional

import pandas as pd

from .metrics import missing_rate, count_where, dq_test_range
from .investigation import DQInvestigator


def run_dq_config(
    df: pd.DataFrame, 
    config: Dict[str, Any],
    investigate: bool = False,
    investigation_dir: str = "reports/investigations"
) -> Dict[str, Any]:
    """Exécute les métriques et tests définis dans `config` sur `df`.

    Args:
        df: DataFrame à analyser.
        config: dict contenant keys 'metrics' et 'tests'.
        investigate: Si True, génère des échantillons pour les tests qui échouent.
        investigation_dir: Répertoire pour sauvegarder les investigations.

    Returns:
        dict: {
            'metrics': {metric_id: {'value': ...}},
            'tests': {test_id: {'passed': bool, 'message': str, ...}},
            'investigations': [...]  # Si investigate=True
        }
    """
    results = {"metrics": {}, "tests": {}}
    investigations = []
    
    # Initialiser l'investigator si nécessaire
    investigator = DQInvestigator(investigation_dir) if investigate else None

    metrics_cfg = config.get("metrics", []) or []
    tests_cfg = config.get("tests", []) or []
    
    # Créer un mapping metric_id -> metric_config pour investigation
    metrics_by_id = {m.get("id"): m for m in metrics_cfg}

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
        elif mtype == "count_where":
            filter_expr = m.get("filter")
            try:
                val = count_where(df, filter=filter_expr)
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
            
            # Si le test échoue et investigate=True, générer un échantillon
            if investigate and not res.get("passed", False):
                metric_config = metrics_by_id.get(metric_ref)
                if metric_config:
                    investigation = investigator.generate_investigation_samples(
                        df=df,
                        test_id=tid,
                        test_config=t,
                        metric_config=metric_config,
                        metric_value=val,
                        max_samples=100
                    )
                    if investigation:
                        investigations.append(investigation)
        else:
            results["tests"][tid] = {"passed": False, "message": f"Unknown test type: {ttype}"}
    
    # Ajouter les investigations au résultat
    if investigate and investigations:
        results["investigations"] = investigations
        
        # Générer un rapport consolidé
        report_path = investigator.generate_investigation_report(
            investigations,
            report_name=config.get("id", "dq_investigation")
        )
        results["investigation_report"] = str(report_path)

    return results
