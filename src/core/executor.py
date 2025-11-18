import pandas as pd
import subprocess
import json
import os
from typing import Dict, Any, List
from pydantic import BaseModel, ConfigDict
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
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    run_id: str
    metrics: Dict[str, Result]
    tests: Dict[str, Result]
    scripts: Dict[str, Dict[str, Any]] = {}  # Résultats des scripts
    artifacts: Dict[str, Any] = {}
    investigations: Dict[str, pd.DataFrame] = {}  # Investigations par test_id (DataFrame pandas)
    investigation_report: str = ""

def _make_run_id():
    import time, uuid
    return f"{time.strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:8]}"

def _execute_script(script_path: str, params: Dict[str, Any], ctx: Context) -> Dict[str, Any]:
    """
    Exécute un script Python et capture sa sortie JSON.
    
    Le script doit produire un JSON avec la structure (même format que les tests DQ):
    {
        "tests": [
            {
                "id": "TEST_001",
                "value": 0.95,
                "passed": true,
                "message": "Test description",
                "meta": {...}  # optionnel
            }
        ]
    }
    """
    # Préparer les paramètres en JSON
    params_json = json.dumps({
        "params": params,
        "datasets": {alias: alias for alias in ctx.datasets.keys()},
        "metrics": {k: v for k, v in ctx.metrics_values.items()}
    })
    
    # Exécuter le script
    try:
        result = subprocess.run(
            ["python", script_path],
            input=params_json,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minutes max
            cwd=os.getcwd()
        )
        
        if result.returncode != 0:
            return {
                "success": False,
                "error": f"Script failed with code {result.returncode}",
                "stderr": result.stderr,
                "stdout": result.stdout
            }
        
        # Parser la sortie JSON
        try:
            output = json.loads(result.stdout)
            return {
                "success": True,
                "tests": output.get("tests", []),
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"Invalid JSON output: {e}",
                "stdout": result.stdout,
                "stderr": result.stderr
            }
    
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Script execution timeout (5 minutes)"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Script execution error: {e}"
        }

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
    scripts: Dict[str, Dict[str, Any]] = {}
    investigations: Dict[str, pd.DataFrame] = {}  # Changé en Dict
    
    for step in plan.steps:
        if step.kind == "load":
            ctx.load(step.id)
        elif step.kind == "script":
            # Exécuter le script
            script_result = _execute_script(
                step.params.get("path"),
                step.params.get("params", {}),
                ctx
            )
            scripts[step.id] = script_result
            
            # Intégrer les tests du script dans les résultats globaux
            if script_result.get("success") and script_result.get("tests"):
                for test_data in script_result["tests"]:
                    test_id = test_data.get("id", f"{step.id}_test_{len(tests)}")
                    # Convertir en Result avec les mêmes champs que les tests DQ
                    tests[test_id] = Result(
                        value=test_data.get("value"),
                        passed=test_data.get("passed", False),
                        message=test_data.get("message", f"From script {step.id}"),
                        meta=test_data.get("meta", {})
                    )
        elif step.kind == "metric":
            plugin = REGISTRY[step.id]()
            res = plugin.run(ctx, **step.params)
            # Utiliser l'ID unique du paramètre au lieu du plugin type
            metric_id = step.params.get('id', step.id)
            metrics[metric_id] = res
            if res.value is not None:
                ctx.metrics_values[metric_id] = res.value
            # Stocker aussi le résultat complet pour les investigations
            if not hasattr(ctx, 'metrics_results'):
                ctx.metrics_results = {}
            ctx.metrics_results[metric_id] = res
        elif step.kind == "test":
            plugin = REGISTRY[step.id]()
            res = plugin.run(ctx, **step.params)
            # Utiliser l'ID unique du paramètre au lieu du plugin type
            test_id = step.params.get('id', step.id)
            tests[test_id] = res
            
            # Investigation automatique si le test échoue (exclure les scripts de type)
            if investigate and res.passed is False:
                # Exclure les tests de type "script"
                test_type = step.id  # Le type de test (range, missing_rate, etc.)
                is_script = test_type.lower() == 'script' or 'script' in test_type.lower()
                
                if not is_script:
                    print(f"🔍 Investigation pour test échoué: {test_id}")
                    
                    # Stratégie 1: Dataset direct dans specific.database ou params
                    dataset_alias = step.params.get('specific', {}).get('database')
                    if not dataset_alias:
                        dataset_alias = step.params.get('database')
                    
                    # Stratégie 2: Si c'est un test basé sur une métrique, récupérer le dataset de la métrique
                    if not dataset_alias:
                        metric_id = step.params.get('specific', {}).get('metric_id')
                        if metric_id and metric_id in metrics:
                            # Récupérer le dataset depuis la métrique
                            metric_result = metrics[metric_id]
                            if hasattr(metric_result, 'meta') and metric_result.meta:
                                dataset_alias = metric_result.meta.get('dataset')
                    
                    # Stratégie 3: Si un seul dataset dans le contexte, l'utiliser
                    if not dataset_alias and len(ctx.datasets) == 1:
                        dataset_alias = list(ctx.datasets.keys())[0]
                        print(f"   Dataset unique détecté, utilisation de: {dataset_alias}")
                    
                    print(f"   Dataset alias: {dataset_alias}")
                    print(f"   Datasets disponibles: {list(ctx.datasets.keys())}")
                    
                    if dataset_alias and dataset_alias in ctx.datasets:
                        df = ctx.datasets[dataset_alias]
                        print(f"   DataFrame trouvé: {len(df)} lignes")
                        
                        # Appeler investigate() si le plugin le supporte
                        if hasattr(plugin, 'investigate'):
                            print(f"   Plugin {step.id} a une méthode investigate()")
                            inv_result = plugin.investigate(ctx, df, step.params, max_samples=100)
                            
                            if inv_result and 'sample' in inv_result:
                                # Stocker le DataFrame d'investigation avec test_id comme clé
                                sample_df = inv_result['sample']
                                if isinstance(sample_df, pd.DataFrame) and not sample_df.empty:
                                    investigations[test_id] = sample_df
                                    print(f"   ✅ Investigation ajoutée: {len(sample_df)} lignes")
                                    
                                    # Marquer que ce test a une investigation
                                    res.investigation = True
                                else:
                                    print(f"   ⚠️ Investigation vide ou invalide")
                            else:
                                print(f"   ⚠️ investigate() n'a pas retourné de sample")
                        else:
                            print(f"   ⚠️ Plugin {step.id} n'a pas de méthode investigate()")
                    else:
                        print(f"   ⚠️ Dataset '{dataset_alias}' non trouvé dans le contexte")
        else:
            raise ValueError(f"Unknown step kind: {step.kind}")
    
    # Générer un rapport consolidé si des investigations existent
    investigation_report = ""
    if investigations:
        print(f"📊 {len(investigations)} investigation(s) générée(s): {list(investigations.keys())}")
        # Convertir le dict en list pour generate_consolidated_report
        inv_list = [{'test_id': k, 'sample': v} for k, v in investigations.items()]
        report_path = generate_consolidated_report(
            inv_list,
            report_name=f"run_{_make_run_id()}",
            output_dir=investigation_dir
        )
        investigation_report = str(report_path)
    else:
        print("⚠️ Aucune investigation générée")
    
    return RunResult(
        run_id=_make_run_id(), 
        metrics=metrics, 
        tests=tests,
        scripts=scripts,
        investigations=investigations,
        investigation_report=investigation_report
    )
