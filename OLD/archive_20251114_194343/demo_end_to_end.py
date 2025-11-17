#!/usr/bin/env python3
"""
Démonstration end-to-end du système complet.

Ce script montre l'intégration complète:
1. Découverte des plugins
2. Construction du catalogue virtuel
3. Séquençage automatique
4. Exécution avec résultats

C'est la démonstration ultime que tout fonctionne ! 🚀
"""

import sys
from pathlib import Path
import pandas as pd

# Ajouter src au path
sys.path.insert(0, str(Path(__file__).parent))

from src.plugins.discovery import discover_all_plugins
from src.plugins.virtual_catalog import VirtualCatalog
from src.plugins.sequencer import build_execution_plan, print_execution_plan
from src.plugins.executor import Executor, ExecutionContext, print_execution_result


class DemoContext:
    """Context de démo avec données réalistes."""
    
    def __init__(self):
        # Créer des datasets de démo
        self.sales_data = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=20, freq="D"),
            "region": ["North", "South", "East", "West"] * 5,
            "product": ["Laptop", "Phone", "Tablet", "Watch"] * 5,
            "amount": [1500, 800, 600, 300, 1200, 900, 550, 250,
                      1800, 850, 650, 350, 1100, 750, 500, 280,
                      1600, 820, 580, 320],
            "quantity": [2, 3, 4, 5, 1, 2, 3, 4, 2, 3, 1, 2, 3, 4, 5, 1, 2, 3, 4, 5]
        })
        
        # Ajouter quelques valeurs manquantes
        self.sales_data.loc[2, "amount"] = None
        self.sales_data.loc[7, "amount"] = None
        self.sales_data.loc[15, "quantity"] = None
    
    def load(self, alias: str):
        """Charge un dataset par alias."""
        if alias == "sales":
            return self.sales_data
        raise ValueError(f"Dataset '{alias}' inconnu")


def demo_1_full_workflow():
    """Démo 1: Workflow complet simple."""
    print("\n" + "🔵 " * 35)
    print("DEMO 1: Workflow complet - Métriques + Tests")
    print("🔵 " * 35)
    
    # Configuration DQ
    config = {
        "metrics": [
            {
                "id": "M-001",
                "type": "missing_rate",
                "params": {
                    "dataset": "sales",
                    "column": "amount"
                }
            },
            {
                "id": "M-002",
                "type": "missing_rate",
                "params": {
                    "dataset": "sales",
                    "column": "quantity"
                }
            }
        ],
        "tests": [
            {
                "id": "T-001",
                "type": "range",
                "params": {
                    "value_from_metric": "M-001",
                    "low": 0.0,
                    "high": 0.15,
                    "inclusive": True
                }
            },
            {
                "id": "T-002",
                "type": "range",
                "params": {
                    "value_from_metric": "M-002",
                    "low": 0.0,
                    "high": 0.1,
                    "inclusive": True
                }
            }
        ]
    }
    
    print("\n📋 Configuration DQ:")
    print(f"  - {len(config['metrics'])} métriques")
    print(f"  - {len(config['tests'])} tests")
    
    # Étape 1: Découverte
    print("\n[1/4] 🔍 Découverte des plugins...")
    plugins = discover_all_plugins(verbose=False)
    print(f"      ✅ {len(plugins)} plugins découverts")
    
    # Étape 2: Catalogue virtuel
    print("\n[2/4] 📚 Construction du catalogue virtuel...")
    catalog = VirtualCatalog()
    virtual_count = catalog.register_from_config(config)
    print(f"      ✅ {virtual_count} virtual datasets créés")
    
    # Étape 3: Séquençage
    print("\n[3/4] 🔀 Séquençage automatique...")
    plan = build_execution_plan(config, catalog)
    print(f"      ✅ Plan avec {len(plan.steps)} steps, {plan.max_level + 1} niveaux")
    print_execution_plan(plan)
    
    # Étape 4: Exécution
    print("\n[4/4] ▶️  Exécution du plan...")
    demo_ctx = DemoContext()
    executor = Executor(ExecutionContext(demo_ctx.load))
    result = executor.execute(plan)
    
    # Résultats détaillés
    print_execution_result(result)
    
    # Analyse
    print("\n💡 Analyse:")
    print(f"   M-001 (missing_rate sur amount): {result.metrics['M-001']:.2%}")
    print(f"   M-002 (missing_rate sur quantity): {result.metrics['M-002']:.2%}")
    print(f"   T-001 (test sur M-001): {'✅ PASS' if result.tests['T-001']['passed'] else '❌ FAIL'}")
    print(f"   T-002 (test sur M-002): {'✅ PASS' if result.tests['T-002']['passed'] else '❌ FAIL'}")


def demo_2_with_aggregation():
    """Démo 2: Avec agrégation et virtual datasets."""
    print("\n" + "🟢 " * 35)
    print("DEMO 2: Agrégation + Virtual Datasets")
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
            }
        ],
        "tests": []
    }
    
    print("\n📋 Configuration DQ:")
    print("  - Agrégation des ventes par région")
    print("  - Calcul de sum, avg, min, max pour chaque région")
    
    # Pipeline complet
    print("\n[1/4] Découverte...")
    discover_all_plugins(verbose=False)
    
    print("[2/4] Catalogue virtuel...")
    catalog = VirtualCatalog()
    catalog.register_from_config(config)
    print(f"      ✅ Virtual dataset 'virtual:M-001' créé")
    print(f"      ✅ Colonnes disponibles: {catalog.get_columns('virtual:M-001')}")
    
    print("\n[3/4] Séquençage...")
    plan = build_execution_plan(config, catalog)
    
    print("\n[4/4] Exécution...")
    demo_ctx = DemoContext()
    executor = Executor(ExecutionContext(demo_ctx.load))
    result = executor.execute(plan)
    
    # Afficher le DataFrame résultant
    if "M-001" in result.dataframes:
        df = result.dataframes["M-001"]
        print("\n📊 Résultat de l'agrégation:")
        print(df.to_string(index=False))
        
        print("\n💡 Observations:")
        print(f"   - {len(df)} régions analysées")
        print(f"   - Total des ventes: {df['sum_amount'].sum():.2f}€")
        print(f"   - Région avec plus de ventes: {df.loc[df['sum_amount'].idxmax(), 'region']}")


def demo_3_complex_workflow():
    """Démo 3: Workflow complexe avec dépendances."""
    print("\n" + "🟡 " * 35)
    print("DEMO 3: Workflow complexe avec dépendances")
    print("🟡 " * 35)
    
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
                "params": {
                    "dataset": "sales",
                    "column": "amount"
                }
            },
            {
                "id": "M-003",
                "type": "missing_rate",
                "params": {
                    "dataset": "sales",
                    "column": "quantity"
                }
            }
        ],
        "tests": [
            # Test sur le missing rate
            {
                "id": "T-001",
                "type": "range",
                "params": {
                    "value_from_metric": "M-002",
                    "low": 0.0,
                    "high": 0.2,
                    "inclusive": True
                }
            },
            # Test sur un autre missing rate
            {
                "id": "T-002",
                "type": "range",
                "params": {
                    "value_from_metric": "M-003",
                    "low": 0.0,
                    "high": 0.1,
                    "inclusive": True
                }
            }
        ]
    }
    
    print("\n📋 Configuration DQ:")
    print("  - 3 métriques (1 agrégation + 2 missing rates)")
    print("  - 2 tests (validation des missing rates)")
    
    # Pipeline complet
    discover_all_plugins(verbose=False)
    
    catalog = VirtualCatalog()
    catalog.register_from_config(config)
    
    plan = build_execution_plan(config, catalog)
    print_execution_plan(plan)
    
    demo_ctx = DemoContext()
    executor = Executor(ExecutionContext(demo_ctx.load))
    result = executor.execute(plan)
    
    print_execution_result(result)
    
    # Afficher le DataFrame d'agrégation
    if "M-001" in result.dataframes:
        df = result.dataframes["M-001"]
        print("\n📊 Agrégation par région:")
        print(df.to_string(index=False))
    
    print("\n💡 Résumé:")
    print(f"   ✅ {len(result.get_successful_steps())} steps réussis")
    print(f"   ⏱️  Durée totale: {result.total_duration_ms:.0f}ms")
    print(f"   📈 Données: {len(demo_ctx.sales_data)} lignes analysées")


def demo_4_virtual_dataset_usage():
    """Démo 4: Utilisation réelle d'un virtual dataset dans un test."""
    print("\n" + "🟣 " * 35)
    print("DEMO 4: Tests utilisant des virtual datasets")
    print("🟣 " * 35)
    
    print("\n⚠️  Note: Cette démo nécessite un plugin de test qui peut")
    print("   lire des colonnes de virtual datasets. Pour l'instant,")
    print("   nous montrons la mécanique sans l'exécution complète.")
    
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
            }
        ],
        "tests": []
    }
    
    # Montrer la mécanique
    discover_all_plugins(verbose=False)
    
    catalog = VirtualCatalog()
    catalog.register_from_config(config)
    
    print("\n📚 Catalogue virtuel créé:")
    print(f"   Dataset: virtual:M-001")
    print(f"   Colonnes: {catalog.get_columns('virtual:M-001')}")
    
    plan = build_execution_plan(config, catalog)
    
    demo_ctx = DemoContext()
    exec_context = ExecutionContext(demo_ctx.load)
    executor = Executor(exec_context)
    result = executor.execute(plan)
    
    # Montrer qu'on peut charger le virtual dataset
    print("\n🔍 Test du virtual dataset:")
    virtual_df = exec_context.load("virtual:M-001")
    print(f"   ✅ Chargement réussi: {len(virtual_df)} lignes")
    print("\n   Aperçu du virtual dataset:")
    print(virtual_df.to_string(index=False))
    
    print("\n💡 Un test pourrait maintenant:")
    print("   1. Sélectionner la colonne 'sum_amount'")
    print("   2. Vérifier que sum_amount > 1000 pour chaque région")
    print("   3. Valider la cohérence des données agrégées")


def main():
    print("\n" + "=" * 70)
    print(" 🚀 DÉMONSTRATION END-TO-END DU SYSTÈME COMPLET")
    print("=" * 70)
    print("\nCe script démontre l'intégration complète:")
    print("  1️⃣  Découverte automatique des plugins")
    print("  2️⃣  Construction du catalogue de virtual datasets")
    print("  3️⃣  Séquençage automatique avec détection de dépendances")
    print("  4️⃣  Exécution avec gestion d'erreurs et validation")
    
    demos = [
        ("1", "Workflow complet simple", demo_1_full_workflow),
        ("2", "Agrégation + Virtual Datasets", demo_2_with_aggregation),
        ("3", "Workflow complexe", demo_3_complex_workflow),
        ("4", "Virtual datasets en action", demo_4_virtual_dataset_usage)
    ]
    
    print("\nDémos disponibles:")
    for num, title, _ in demos:
        print(f"  {num}. {title}")
    
    choice = input("\nExécuter toutes les démos? [Y/n] ").strip().lower()
    
    if choice in ("", "y", "yes", "o", "oui"):
        for num, title, func in demos:
            func()
            input("\nAppuyez sur Entrée pour continuer...")
    else:
        choice = input("Quelle démo? [1-4] ").strip()
        for num, title, func in demos:
            if num == choice:
                func()
                break
    
    print("\n" + "=" * 70)
    print("✅ Démonstration terminée!")
    print("=" * 70)
    print("\n🎉 Le système complet fonctionne:")
    print("  ✓ Plugins auto-découverts")
    print("  ✓ Virtual datasets créés automatiquement")
    print("  ✓ Plans d'exécution optimaux")
    print("  ✓ Exécution avec résultats stockés")
    print("\nVous êtes prêt pour:")
    print("  • Créer le vrai Context (inventory.yaml)")
    print("  • Construire l'API FastAPI")
    print("  • Adapter l'UI Dash")


if __name__ == "__main__":
    main()
