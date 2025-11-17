"""
Test complet simulation submission_processor
"""
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.core.dq_parser import load_dq_config
from src.core.models_dq import DQDefinition
from src.core.parser import build_execution_plan
from src.core.models_inventory import Inventory
from src.core.executor import execute
from src.core.script_executor import execute_scripts

print("="*80)
print("TEST SIMULATION SUBMISSION_PROCESSOR")
print("="*80)

# Charger les données
datasets = {
    'sales_data': pd.read_csv('data/sales_invalid_upload.csv')
}

print(f"\n[1] Données chargées: {len(datasets['sales_data'])} lignes")
print(f"    NaN dans customer_id: {datasets['sales_data']['customer_id'].isna().sum()}")

# Charger la config DQ
config = load_dq_config('dq/definitions/sales_strict_validation.yaml')
print(f"\n[2] Config DQ chargée:")
print(f"    ID: {config.id}")
print(f"    Metrics: {len(config.metrics)}")
print(f"    Tests: {len(config.tests)}")
print(f"    Scripts: {len(config.scripts)}")

# Convertir DQConfig en DQDefinition
dq_def_data = {
    'id': config.id,
    'label': config.label,
    'databases': [{'alias': alias} for alias in datasets.keys()],
    'metrics': {},
    'tests': {},
    'scripts': [s.model_dump() for s in config.scripts]
}

# Convertir metrics
for metric_id, metric_obj in config.metrics.items():
    dq_def_data['metrics'][metric_id] = {
        'id': metric_id,
        'type': metric_obj.type,
        'specific': metric_obj.specific
    }

# Convertir tests
for test_id, test_obj in config.tests.items():
    dq_def_data['tests'][test_id] = {
        'id': test_id,
        'type': test_obj.type,
        'specific': test_obj.specific
    }

dq_definition = DQDefinition(**dq_def_data)

print(f"\n[3] DQDefinition créée:")
print(f"    Metrics: {list(dq_definition.metrics.keys())}")
print(f"    Tests: {list(dq_definition.tests.keys())}")

# Créer loader
def loader(alias: str):
    if alias in datasets:
        return datasets[alias]
    raise ValueError(f"Dataset {alias} non trouvé")

# Créer inventaire et plan
inv_data = {
    'streams': [],
    'datasets': [{'alias': alias, 'path': f'memory://{alias}'} for alias in datasets.keys()]
}
inv = Inventory(**inv_data)

overrides = {alias: f'memory://{alias}' for alias in datasets.keys()}
plan = build_execution_plan(inv, dq_definition, overrides=overrides)

print(f"\n[4] Plan d'exécution: {len(plan.steps)} étapes")

# Exécuter
run_result = execute(plan, loader, investigate=False)

print(f"\n[5] Résultats DQ:")
print(f"    Métriques: {len(run_result.metrics)}")
for mid, mres in run_result.metrics.items():
    print(f"      - {mid}: {mres.value}")

print(f"    Tests: {len(run_result.tests)}")
for tid, tres in run_result.tests.items():
    status = "✓ PASS" if tres.passed else "✗ FAIL"
    print(f"      {status} {tid}: {tres.message}")

# Exécuter scripts
class ScriptContext:
    def __init__(self, loader_func):
        self.loader_func = loader_func
    
    def load(self, alias):
        return self.loader_func(alias)

script_ctx = ScriptContext(loader)
script_results = execute_scripts(config.scripts, script_ctx, execute_phase="post_dq")

print(f"\n[6] Résultats Scripts: {len(script_results)}")
for sres in script_results:
    print(f"    Script: {sres.script_id} - Status: {sres.status}")
    for tid, tdata in sres.tests.items():
        status = "✓ PASS" if tdata['status'] == 'passed' else "✗ FAIL"
        print(f"      {status} {tid}: {tdata['message']}")

# Compter
total_passed = sum(1 for t in run_result.tests.values() if t.passed)
total_failed = sum(1 for t in run_result.tests.values() if not t.passed)
script_passed = sum(1 for s in script_results for t in s.tests.values() if t.get('status') == 'passed')
script_failed = sum(1 for s in script_results for t in s.tests.values() if t.get('status') != 'passed')

print(f"\n{'='*80}")
print("RÉSUMÉ")
print(f"{'='*80}")
print(f"DQ Tests: {total_passed} PASS, {total_failed} FAIL")
print(f"Script Tests: {script_passed} PASS, {script_failed} FAIL")
print(f"TOTAL: {total_passed + script_passed} PASS, {total_failed + script_failed} FAIL")

if total_failed + script_failed > 0:
    print(f"\n✓ SUCCÈS: {total_failed + script_failed} erreurs détectées (données invalides)")
else:
    print(f"\n✗ ÉCHEC: Aucune erreur détectée (attendu: 4 erreurs)")
