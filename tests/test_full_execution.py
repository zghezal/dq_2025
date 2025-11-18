"""
Test complet: DQ + Scripts avec données invalides
"""
import pandas as pd
import sys
from pathlib import Path

# Ajouter repo root au path
repo_root = Path(__file__).parent
sys.path.insert(0, str(repo_root))

from src.core.dq_parser import load_dq_config
from src.core.parser import build_execution_plan
from src.core.models_inventory import Inventory
from src.core.executor import execute
from src.core.script_executor import execute_scripts

print("=" * 80)
print("TEST COMPLET: DQ + SCRIPTS AVEC DONNÉES INVALIDES")
print("=" * 80)

# 1. Charger les données invalides
print("\n[1] Chargement des données invalides...")
df_invalid = pd.read_csv('data/sales_invalid_upload.csv')
print(f"    ✓ {len(df_invalid)} lignes chargées")
print(f"    Colonnes: {list(df_invalid.columns)}")
print(f"    customer_id NaN count: {df_invalid['customer_id'].isna().sum()}")
print("\nPremières lignes:")
print(df_invalid.head())

# 2. Charger la config DQ
print("\n[2] Chargement de la config DQ...")
config = load_dq_config('dq/definitions/sales_strict_validation.yaml')
print(f"    ✓ DQ: {config.id}")
print(f"    ✓ Metrics: {len(config.metrics)}")
print(f"    ✓ Tests: {len(config.tests)}")
print(f"    ✓ Scripts: {len(config.scripts)}")

# 3. Préparer le loader
datasets = {'sales_data': df_invalid}

def loader(alias: str):
    if alias in datasets:
        return datasets[alias]
    raise ValueError(f"Dataset {alias} non trouvé")

# 4. Préparer l'exécution comme dans submission_processor
print("\n[3] Préparation de l'exécution...")

# Créer un inventaire minimal
inv_data = {
    'streams': [],
    'datasets': [{'alias': alias, 'path': f'memory://{alias}'} for alias in datasets.keys()]
}
inv = Inventory(**inv_data)

# Construire le plan avec les overrides
overrides = {alias: f'memory://{alias}' for alias in datasets.keys()}

# Importer et utiliser le parser comme submission_processor
from src.core.parser import build_execution_plan

# Le parser attend un DQDefinition, donc on doit convertir DQConfig en DQDefinition
# ou utiliser directement les dicts
from src.core.models_dq import DQDefinition

# Créer un DQDefinition compatible
dq_def_data = {
    'id': config.id,
    'label': config.label,
    'context': config.context.__dict__ if config.context else None,
    'databases': [{'alias': 'sales_data', 'path': 'memory://sales_data'}],
    'metrics': {mid: {'id': mid, 'type': m.type, 'specific': m.specific} for mid, m in config.metrics.items()},
    'tests': {tid: {'id': tid, 'type': t.type, 'specific': t.specific} for tid, t in config.tests.items()},
    'scripts': [s.model_dump() for s in config.scripts]
}

dq_def = DQDefinition(**dq_def_data)

plan = build_execution_plan(inv, dq_def, overrides=overrides)
print(f"    ✓ Plan construit: {len(plan.steps)} étapes")
print("\n    Détail des étapes:")
for i, step in enumerate(plan.steps):
    print(f"      {i+1}. {step.kind}: {step.id}")

# 5. Exécuter le plan DQ
print("\n[4] Exécution des tests DQ...")
run_result = execute(plan, loader, investigate=False)

print(f"\n    Métriques calculées: {len(run_result.metrics)}")
for metric_id, metric_result in run_result.metrics.items():
    print(f"      - {metric_id}: {metric_result.value} (passed: {metric_result.passed})")

print(f"\n    Tests exécutés: {len(run_result.tests)}")
for test_id, test_result in run_result.tests.items():
    status = "✓ PASS" if test_result.passed else "✗ FAIL"
    print(f"      {status} {test_id}: {test_result.message}")

# 6. Exécuter les scripts
print("\n[5] Exécution des scripts...")

class ScriptContext:
    def __init__(self, loader_func):
        self.loader_func = loader_func
    
    def load(self, alias):
        return self.loader_func(alias)

script_ctx = ScriptContext(loader)
script_results = execute_scripts(config.scripts, script_ctx, execute_phase="post_dq")

print(f"\n    Scripts exécutés: {len(script_results)}")
for script_result in script_results:
    print(f"\n    Script: {script_result.script_id}")
    print(f"      Status: {script_result.status}")
    print(f"      Durée: {script_result.duration:.2f}s")
    
    if script_result.metrics:
        print(f"      Métriques:")
        for metric_name, metric_value in script_result.metrics.items():
            print(f"        - {metric_name}: {metric_value}")
    
    if script_result.tests:
        print(f"      Tests:")
        for test_id, test_data in script_result.tests.items():
            status = "✓ PASS" if test_data['status'] == 'passed' else "✗ FAIL"
            print(f"        {status} {test_id}: {test_data['message']}")
    
    if script_result.error:
        print(f"      ✗ Erreur: {script_result.error}")

# 7. Résumé final
print("\n" + "=" * 80)
print("RÉSUMÉ")
print("=" * 80)

dq_passed = sum(1 for t in run_result.tests.values() if t.passed)
dq_failed = sum(1 for t in run_result.tests.values() if not t.passed)

script_passed = sum(1 for s in script_results for t in s.tests.values() if t.get('status') == 'passed')
script_failed = sum(1 for s in script_results for t in s.tests.values() if t.get('status') != 'passed')

total_passed = dq_passed + script_passed
total_failed = dq_failed + script_failed

print(f"\nTests DQ:")
print(f"  ✓ Réussis: {dq_passed}")
print(f"  ✗ Échoués: {dq_failed}")

print(f"\nTests Scripts:")
print(f"  ✓ Réussis: {script_passed}")
print(f"  ✗ Échoués: {script_failed}")

print(f"\nTOTAL:")
print(f"  ✓ Réussis: {total_passed}")
print(f"  ✗ Échoués: {total_failed}")

if total_failed > 0:
    print(f"\n🎯 RÉSULTAT ATTENDU: ÉCHEC (données invalides détectées)")
    print(f"   ✓ {total_failed} test(s) ont échoué comme prévu")
else:
    print(f"\n❌ PROBLÈME: Aucun test n'a échoué (attendu: au moins 4 échecs)")

print("=" * 80)
