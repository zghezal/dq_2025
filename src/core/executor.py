import pandas as pd
from typing import Dict, Any, List
from pydantic import BaseModel
from src.plugins.base import REGISTRY, Result
from src.plugins.investigation_helpers import generate_consolidated_report
from src.plugins.discovery import ensure_plugins_discovered

class Context:
    def __init__(self, alias_map, loader):
        self.alias_map = alias_map
        self.loader = loader
        self.datasets: Dict[str, pd.DataFrame] = {}
        self.metrics_values: Dict[str, Any] = {}

    def load(self, alias: str) -> pd.DataFrame:
        if alias not in self.datasets:
            self.datasets[alias] = self.loader(alias)
        return self.datasets[alias]

class RunResult(BaseModel):
    run_id: str
    metrics: Dict[str, Result]
    tests: Dict[str, Result]
    artifacts: Dict[str, Any] = {}
    investigations: List[Dict[str, Any]] = []
    investigation_report: str = ""

def _make_run_id():
    import time, uuid
    return f"{time.strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:8]}"

def execute(plan, loader, investigate: bool = False, investigation_dir: str = "reports/investigations") -> RunResult:
    """
    Exécute un plan DQ (métriques + tests).
    
    Args:
        plan: Plan d'exécution (liste de steps)
        loader: Fonction de chargement des datasets
        investigate: Si True, génère des investigations pour les tests échoués
        investigation_dir: Répertoire pour sauvegarder les investigations
    
    Returns:
        RunResult avec métriques, tests, et investigations (si investigate=True)
    """
    # S'assurer que les plugins sont découverts AVANT d'utiliser REGISTRY
    ensure_plugins_discovered()
    
    ctx = Context(plan.alias_map, loader)
    metrics: Dict[str, Result] = {}
    tests: Dict[str, Result] = {}
    investigations: List[Dict[str, Any]] = []
    
    for step in plan.steps:
        if step.kind == "load":
            ctx.load(step.id)
        elif step.kind == "metric":
            plugin = REGISTRY[step.id]()
            res = plugin.run(ctx, **step.params)
            metrics[step.id] = res
            if res.value is not None:
                ctx.metrics_values[step.id] = res.value
        elif step.kind == "test":
            plugin = REGISTRY[step.id]()
            res = plugin.run(ctx, **step.params)
            tests[step.id] = res
            
            # Investigation automatique si le test échoue
            if investigate and res.passed is False:
                # Récupérer le DataFrame source
                dataset_alias = step.params.get('specific', {}).get('database')
                if dataset_alias and dataset_alias in ctx.datasets:
                    df = ctx.datasets[dataset_alias]
                    
                    # Appeler investigate() si le plugin le supporte
                    inv_result = plugin.investigate(ctx, df, step.params, max_samples=100)
                    
                    if inv_result:
                        # Enrichir avec test_id et test_type
                        inv_result['test_id'] = step.id
                        inv_result['test_type'] = plugin.plugin_id
                        investigations.append(inv_result)
                        
                        # Ajouter à Result.investigation
                        res.investigation = inv_result
        else:
            raise ValueError(f"Unknown step kind: {step.kind}")
    
    # Générer un rapport consolidé si des investigations existent
    investigation_report = ""
    if investigations:
        report_path = generate_consolidated_report(
            investigations,
            report_name=f"run_{_make_run_id()}",
            output_dir=investigation_dir
        )
        investigation_report = str(report_path)
    
    return RunResult(
        run_id=_make_run_id(), 
        metrics=metrics, 
        tests=tests,
        investigations=investigations,
        investigation_report=investigation_report
    )
