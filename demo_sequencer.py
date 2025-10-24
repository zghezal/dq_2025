#!/usr/bin/env python3
"""
Démonstration du séquenceur.

Ce script montre comment le séquenceur construit des plans d'exécution
avec détection automatique des dépendances.
"""

import sys
from pathlib import Path

# Ajouter src au path
sys.path.insert(0, str(Path(__file__).parent))

from src.plugins.sequencer import build_execution_plan, print_execution_plan


def demo_1_simple():
    """Demo 1: Plan simple sans dépendances."""
    print("\n" + "🔵 " * 35)
    print("DEMO 1: Plan simple sans dépendances")
    print("🔵 " * 35)
    
    config = {
        "metrics": [
            {"id": "M-001", "type": "missing_rate", "params": {"dataset": "sales", "column": "amount"}},
            {"id": "M-002", "type": "missing_rate", "params": {"dataset": "customers", "column": "email"}}
        ],
        "tests": [
            {"id": "T-001", "type": "range", "params": {"low": 0, "high": 0.1}}
        ]
    }
    
    plan = build_execution_plan(config)
    print_execution_plan(plan)
    
    print("💡 Observation:")
    print("   Toutes les métriques et le test sont au niveau 0 (pas de dépendances)")
    print("   L'ordre est: métriques d'abord, puis tests")


def demo_2_with_virtual_dataset():
    """Demo 2: Test dépendant d'un virtual dataset."""
    print("\n" + "🟢 " * 35)
    print("DEMO 2: Test dépendant d'un virtual dataset")
    print("🟢 " * 35)
    
    config = {
        "metrics": [
            {
                "id": "M-001",
                "type": "aggregation_by_column",
                "params": {
                    "dataset": "sales",
                    "group_by": "region",
                    "target": "amount"
                }
            },
            {
                "id": "M-002",
                "type": "missing_rate",
                "params": {"dataset": "customers", "column": "email"}
            }
        ],
        "tests": [
            {
                "id": "T-001",
                "type": "range",
                "database": "virtual:M-001",  # 👈 Dépendance sur M-001
                "column": "sum_amount",
                "params": {"low": 1000, "high": 100000}
            },
            {
                "id": "T-002",
                "type": "range",
                "metric": "M-002",  # 👈 Dépendance sur M-002
                "params": {"low": 0, "high": 0.05}
            }
        ]
    }
    
    plan = build_execution_plan(config)
    print_execution_plan(plan)
    
    print("💡 Observation:")
    print("   M-001 et M-002 sont au niveau 0 (pas de dépendances)")
    print("   T-001 est au niveau 1 (dépend de M-001 via virtual:M-001)")
    print("   T-002 est au niveau 1 (dépend de M-002 directement)")


def demo_3_complex():
    """Demo 3: Configuration complexe avec plusieurs niveaux."""
    print("\n" + "🟡 " * 35)
    print("DEMO 3: Configuration complexe")
    print("🟡 " * 35)
    
    config = {
        "metrics": [
            {
                "id": "M-001",
                "type": "aggregation_by_column",
                "params": {"dataset": "sales", "group_by": "region", "target": "amount"}
            },
            {
                "id": "M-002",
                "type": "aggregation_by_column",
                "params": {"dataset": "sales", "group_by": "product", "target": "quantity"}
            },
            {
                "id": "M-003",
                "type": "missing_rate",
                "params": {"dataset": "customers", "column": "email"}
            },
            {
                "id": "M-004",
                "type": "missing_rate",
                "params": {"dataset": "customers", "column": "phone"}
            }
        ],
        "tests": [
            {
                "id": "T-001",
                "type": "range",
                "database": "virtual:M-001",
                "column": "avg_amount",
                "params": {"low": 50, "high": 500}
            },
            {
                "id": "T-002",
                "type": "range",
                "database": "virtual:M-002",
                "column": "sum_quantity",
                "params": {"low": 100, "high": 10000}
            },
            {
                "id": "T-003",
                "type": "range",
                "metric": "M-003",
                "params": {"low": 0, "high": 0.02}
            },
            {
                "id": "T-004",
                "type": "range",
                "metric": "M-004",
                "params": {"low": 0, "high": 0.1}
            },
            {
                "id": "T-005",
                "type": "range",
                "params": {"low": 0, "high": 1}  # Pas de dépendances
            }
        ]
    }
    
    plan = build_execution_plan(config)
    print_execution_plan(plan)
    
    print("💡 Observation:")
    print("   Niveau 0: M-001, M-002, M-003, M-004, T-005 (5 steps)")
    print("   Niveau 1: T-001, T-002, T-003, T-004 (4 steps)")
    print("   Le séquenceur a détecté automatiquement toutes les dépendances")
    print("   Les tests sans dépendances (T-005) restent au niveau 0")


def demo_4_ordering():
    """Demo 4: L'ordre dans le JSON est préservé."""
    print("\n" + "🟣 " * 35)
    print("DEMO 4: Ordre préservé du JSON")
    print("🟣 " * 35)
    
    config = {
        "metrics": [
            {"id": "M-003", "type": "missing_rate", "params": {}},
            {"id": "M-001", "type": "missing_rate", "params": {}},
            {"id": "M-005", "type": "missing_rate", "params": {}},
            {"id": "M-002", "type": "missing_rate", "params": {}},
            {"id": "M-004", "type": "missing_rate", "params": {}}
        ],
        "tests": []
    }
    
    plan = build_execution_plan(config)
    print_execution_plan(plan)
    
    print("💡 Observation:")
    print("   L'ordre d'exécution suit exactement l'ordre du JSON")
    print("   M-003, M-001, M-005, M-002, M-004")
    print("   C'est stable et prévisible pour l'utilisateur")


def demo_5_validation():
    """Demo 5: Validation du plan."""
    print("\n" + "🔴 " * 35)
    print("DEMO 5: Validation et détection d'erreurs")
    print("🔴 " * 35)
    
    # Cas 1: IDs dupliqués
    print("\n[Test 1] IDs dupliqués:")
    config_dup = {
        "metrics": [
            {"id": "M-001", "type": "missing_rate", "params": {}},
            {"id": "M-001", "type": "aggregation_by_column", "params": {}}  # Duplicate!
        ],
        "tests": []
    }
    
    try:
        plan = build_execution_plan(config_dup)
        errors = plan.validate()
        if errors:
            print(f"   ❌ Erreurs détectées: {errors}")
        else:
            print("   ⚠️  Aucune erreur (pas normal!)")
    except ValueError as e:
        print(f"   ✅ Exception levée (attendu): {e}")
    
    # Cas 2: Configuration vide
    print("\n[Test 2] Configuration vide:")
    config_empty = {"metrics": [], "tests": []}
    
    try:
        plan = build_execution_plan(config_empty)
        print("   ⚠️  Plan créé (pas normal!)")
    except ValueError as e:
        print(f"   ✅ Exception levée (attendu): {e}")
    
    # Cas 3: Dépendance vers métrique inexistante
    print("\n[Test 3] Dépendance vers métrique inexistante:")
    config_missing = {
        "metrics": [
            {"id": "M-001", "type": "missing_rate", "params": {}}
        ],
        "tests": [
            {
                "id": "T-001",
                "type": "range",
                "database": "virtual:M-999"  # M-999 n'existe pas
            }
        ]
    }
    
    plan = build_execution_plan(config_missing)
    print(f"   ℹ️  Plan créé avec {len(plan.steps)} steps")
    t_step = next(s for s in plan.steps if s.id == "T-001")
    print(f"   ℹ️  T-001 dépendances: {t_step.depends_on}")
    print("   💡 Le séquenceur ne valide pas l'existence des métriques")
    print("      Cette validation est faite par le VirtualCatalog")


def main():
    print("\n" + "=" * 70)
    print(" 🚀 DÉMONSTRATION DU SÉQUENCEUR D'EXÉCUTION")
    print("=" * 70)
    print("\nLe séquenceur construit automatiquement l'ordre d'exécution")
    print("optimal en détectant les dépendances entre métriques et tests.")
    
    demos = [
        ("1", "Plan simple", demo_1_simple),
        ("2", "Virtual datasets", demo_2_with_virtual_dataset),
        ("3", "Configuration complexe", demo_3_complex),
        ("4", "Ordre préservé", demo_4_ordering),
        ("5", "Validation", demo_5_validation)
    ]
    
    print("\nDémos disponibles:")
    for num, title, _ in demos:
        print(f"  {num}. {title}")
    
    # Exécuter toutes les démos
    choice = input("\nExécuter toutes les démos? [Y/n] ").strip().lower()
    
    if choice in ("", "y", "yes", "o", "oui"):
        for num, title, func in demos:
            func()
            input("\nAppuyez sur Entrée pour continuer...")
    else:
        choice = input("Quelle démo? [1-5] ").strip()
        for num, title, func in demos:
            if num == choice:
                func()
                break
    
    print("\n" + "=" * 70)
    print("✅ Démonstration terminée!")
    print("=" * 70)
    print("\nPour tester avec vos propres configs:")
    print("  from src.plugins.sequencer import build_execution_plan")
    print("  plan = build_execution_plan(your_config)")
    print("  print_execution_plan(plan)")


if __name__ == "__main__":
    main()
