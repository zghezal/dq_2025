"""
Test rapide de l'exécution du DQ refunds_quality
"""

import sys
import os

# Ajouter le répertoire racine au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import yaml
from pathlib import Path
from src.core.models_inventory import Inventory
from src.core.models_dq import DQDefinition
from src.core.parser import build_execution_plan
from src.core.executor import execute
from src.core.connectors import LocalReader

# Charger l'inventaire
inv_path = Path("config/inventory.yaml")
inv_data = yaml.safe_load(inv_path.read_text(encoding="utf-8"))
inv = Inventory(**inv_data)

# Charger la DQ refunds_quality
dq_path = Path("dq/definitions/refunds_quality.yaml")
dq_data = yaml.safe_load(dq_path.read_text(encoding="utf-8"))
dq = DQDefinition(**dq_data)

print(f"✓ DQ chargée: {dq.id}")
print(f"  - Métriques: {len(dq.metrics)}")
print(f"  - Tests: {len(dq.tests)}")

# Construire le plan
print("\n=== Construction du plan ===")
plan = build_execution_plan(inv, dq, overrides={})
print(f"✓ Plan construit avec {len(plan.steps)} étapes")

for step in plan.steps:
    print(f"  - {step.kind}: {step.id}")

# Exécuter
print("\n=== Exécution ===")
try:
    result = execute(plan, loader=LocalReader(plan.alias_map), investigate=False)
    print(f"✓ Exécution réussie: {result.run_id}")
    print(f"\nMétriques:")
    for metric_id, metric_result in result.metrics.items():
        print(f"  - {metric_id}: {metric_result.value} (passed={metric_result.passed})")
    
    print(f"\nTests:")
    for test_id, test_result in result.tests.items():
        status = "✓ PASS" if test_result.passed else "✗ FAIL"
        print(f"  - {test_id}: {status} - {test_result.message}")
    
except Exception as e:
    print(f"✗ Erreur lors de l'exécution: {e}")
    import traceback
    traceback.print_exc()
