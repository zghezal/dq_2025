"""
Test avec données VALIDES - doivent passer
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
print("TEST AVEC DONNÉES VALIDES")
print("="*80)

# Charger les données VALIDES
datasets = {
    'sales_data': pd.read_csv('data/sales_valid_upload.csv')
}

print(f"\n[1] Données chargées: {len(datasets['sales_data'])} lignes")
print(datasets['sales_data'])

# Charger et convertir config
config = load_dq_config('dq/definitions/sales_strict_validation.yaml')

dq_def_data = {
    'id': config.id,
    'label': config.label,
    'databases': [{'alias': alias} for alias in datasets.keys()],
    'metrics': {},
    'tests': {},
    'scripts': [s.model_dump() for s in config.scripts]
}

for metric_id, metric_obj in config.metrics.items():
    dq_def_data['metrics'][metric_id] = {
        'id': metric_id,
        'type': metric_obj.type,
        'specific': metric_obj.specific
    }

for test_id, test_obj in config.tests.items():
    dq_def_data['tests'][test_id] = {
        'id': test_id,
        'type': test_obj.type,
        'specific': test_obj.specific
    }

dq_definition = DQDefinition(**dq_def_data)

def loader(alias: str):
    return datasets[alias]

inv_data = {
    'streams': [],
    'datasets': [{'alias': alias, 'path': f'memory://{alias}'} for alias in datasets.keys()]
}
inv = Inventory(**inv_data)
overrides = {alias: f'memory://{alias}' for alias in datasets.keys()}
plan = build_execution_plan(inv, dq_definition, overrides=overrides)

# Exécuter
run_result = execute(plan, loader, investigate=False)

print(f"\n[2] Résultats DQ:")
for tid, tres in run_result.tests.items():
    status = "✓ PASS" if tres.passed else "✗ FAIL"
    print(f"      {status} {tid}: {tres.message}")

# Scripts
class ScriptContext:
    def __init__(self, loader_func):
        self.loader_func = loader_func
    def load(self, alias):
        return self.loader_func(alias)

script_ctx = ScriptContext(loader)
script_results = execute_scripts(config.scripts, script_ctx, execute_phase="post_dq")

print(f"\n[3] Résultats Scripts:")
for sres in script_results:
    print(f"    Script: {sres.script_id} - Status: {sres.status}")
    for tid, tdata in sres.tests.items():
        status = "✓ PASS" if tdata['status'] == 'passed' else "✗ FAIL"
        print(f"      {status} {tid}: {tdata['message']}")

total_failed = sum(1 for t in run_result.tests.values() if not t.passed)
script_failed = sum(1 for s in script_results for t in s.tests.values() if t.get('status') != 'passed')

print(f"\n{'='*80}")
if total_failed + script_failed == 0:
    print("✓ SUCCÈS: Toutes les données valides PASSENT les tests")
else:
    print(f"✗ ÉCHEC: {total_failed + script_failed} erreurs détectées (attendu: 0)")
print(f"{'='*80}")
