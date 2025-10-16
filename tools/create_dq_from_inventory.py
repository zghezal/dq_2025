#!/usr/bin/env python
import argparse, sys, yaml
from pathlib import Path
from src.core.models_inventory import Inventory
from src.core.models_dq import DQDefinition

def load_inventory(path: str) -> Inventory:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return Inventory(**data)

def main():
    ap = argparse.ArgumentParser(description="Create a DQ definition based on inventory aliases")
    ap.add_argument("--inventory", default="config/inventory.yaml")
    ap.add_argument("--id", required=True, help="DQ id")
    ap.add_argument("--aliases", nargs="+", required=True, help="Dataset aliases to include as databases")
    ap.add_argument("--out", default="dq/definitions/generated.yaml")
    args = ap.parse_args()

    inv = load_inventory(args.inventory)
    # Validate that aliases exist
    found = {d.alias for s in inv.streams for p in s.projects for z in p.zones for d in z.datasets}
    missing = [a for a in args.aliases if a not in found]
    if missing:
        print(f"Error: aliases not found in inventory: {missing}", file=sys.stderr)
        sys.exit(2)

    dq = DQDefinition(id=args.id, databases=[{"alias": a} for a in args.aliases], metrics=[], tests=[])
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(yaml.safe_dump(dq.model_dump(), sort_keys=False), encoding="utf-8")
    print(f"Wrote {out}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
