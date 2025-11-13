#!/usr/bin/env python
import argparse, sys, yaml
from pathlib import Path

# Ajouter le répertoire parent au path pour pouvoir importer src
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.models_inventory import Inventory
from src.core.models_dq import DQDefinition
from src.core.parser import build_execution_plan
from src.core.executor import execute
from src.core.connectors import LocalReader

def load_yaml_model(path, model):
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return model(**data)

def main():
    ap = argparse.ArgumentParser(description="Run a DQ definition using the inventory")
    ap.add_argument("--inventory", default="config/inventory.yaml")
    ap.add_argument("--dq", required=True, help="Path to dq definition yaml")
    ap.add_argument("--override", action="append", default=[], help="alias=local_path override (optional)")
    ap.add_argument("--investigate", action="store_true", help="Generate investigation samples for failed tests")
    args = ap.parse_args()

    inv = load_yaml_model(args.inventory, Inventory)
    dq = load_yaml_model(args.dq, DQDefinition)

    overrides = {}
    for ov in args.override:
        if "=" not in ov:
            print(f"Invalid override '{ov}', expected alias=path", file=sys.stderr)
            return 2
        alias, path = ov.split("=", 1)
        overrides[alias] = path

    plan = build_execution_plan(inv, dq, overrides=overrides)
    rr = execute(plan, loader=LocalReader(plan.alias_map), investigate=args.investigate)

    print("Run:", rr.run_id)
    print("Metrics:")
    for k, v in rr.metrics.items():
        print("  -", k, v.model_dump())
    print("Tests:")
    for k, v in rr.tests.items():
        print("  -", k, v.model_dump())
    
    # Afficher les investigations si présentes
    if hasattr(rr, 'investigations') and rr.investigations:
        print("\nInvestigations:")
        for inv_item in rr.investigations:
            print(f"  - Test: {inv_item.get('test_id')}")
            print(f"    Sample: {inv_item.get('sample_file')}")
            print(f"    Rows: {inv_item.get('total_problematic_rows', inv_item.get('total_matching_rows', 'N/A'))}")
        
        if hasattr(rr, 'investigation_report'):
            print(f"\nConsolidated report: {rr.investigation_report}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
