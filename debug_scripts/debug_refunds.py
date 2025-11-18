"""Test d'exécution refunds_quality avec debug"""

import sys
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import yaml
from src.core.models_inventory import Inventory
from src.core.models_dq import DQDefinition
from src.core.parser import build_execution_plan
from src.core.executor import execute
from src.core.connectors import LocalReader
from src.plugins.base import REGISTRY

print("=" * 60)
print("DEBUG: Contenu du REGISTRY avant exécution")
print("=" * 60)
print(f"Plugins enregistrés: {list(REGISTRY.keys())}")
print()

# Charger l'inventaire
inv_path = Path("config/inventory.yaml")
inv_data = yaml.safe_load(inv_path.read_text(encoding="utf-8"))
inv = Inventory(**inv_data)
print("✓ Inventaire chargé")

# Charger la DQ refunds_quality
dq_path = Path("dq/definitions/refunds_quality.yaml")
dq_data = yaml.safe_load(dq_path.read_text(encoding="utf-8"))
dq = DQDefinition(**dq_data)
print(f"✓ DQ chargée: {dq.id}")

print(f"\nTests dans la DQ:")
for test_id, test_data in dq.tests.items():
    print(f"  - {test_id}: type={test_data.get('type')}")

# Construire le plan
print("\n" + "=" * 60)
print("Construction du plan d'exécution")
print("=" * 60)
try:
    plan = build_execution_plan(inv, dq, overrides={})
    print(f"✓ Plan construit avec {len(plan.steps)} étapes")
    
    for step in plan.steps:
        print(f"  - {step.kind}: {step.id}")
        if step.kind == "test":
            print(f"    -> Cherche dans REGISTRY: {step.id in REGISTRY}")
except Exception as e:
    print(f"✗ Erreur: {e}")
    import traceback
    traceback.print_exc()
