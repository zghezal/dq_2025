#!/usr/bin/env python3
"""
Script de test rapide du système de plugins.

Ce script peut être exécuté directement pour vérifier que:
- Les plugins sont découverts
- Le catalogue virtuel fonctionne
- Les métriques s'exécutent
- La validation des schémas fonctionne

Usage:
    python test_plugin_quick.py
"""

import sys
import pandas as pd
from pathlib import Path

# Ajouter src au path
sys.path.insert(0, str(Path(__file__).parent))

from src.plugins.discovery import discover_all_plugins, REGISTRY
from src.plugins.virtual_catalog import VirtualCatalog


class SimpleContext:
    """Context minimal pour tester."""
    def __init__(self):
        self.data = pd.DataFrame({
            "region": ["North", "South", "North", "East"],
            "amount": [100.0, 200.0, None, 150.0],
        })
    
    def load(self, alias):
        return self.data


def main():
    print("=" * 70)
    print("TEST RAPIDE DU SYSTÈME DE PLUGINS")
    print("=" * 70)
    
    # 1. Découverte
    print("\n[1] DÉCOUVERTE DES PLUGINS")
    print("-" * 70)
    plugins = discover_all_plugins(verbose=True)
    
    if len(plugins) == 0:
        print("❌ ERREUR: Aucun plugin découvert!")
        return 1
    
    print(f"\n✅ Découverte OK: {len(plugins)} plugin(s)")
    
    # 2. Vérifier missing_rate
    print("\n[2] TEST MISSING_RATE")
    print("-" * 70)
    
    if "missing_rate" not in REGISTRY:
        print("❌ ERREUR: missing_rate non trouvé dans REGISTRY!")
        return 1
    
    plugin = REGISTRY["missing_rate"]()
    ctx = SimpleContext()
    result = plugin.run(ctx, dataset="test", column="amount")
    
    print(f"Missing rate calculé: {result.value:.2%}")
    print(f"Message: {result.message}")
    
    if result.value is None:
        print("❌ ERREUR: missing_rate n'a pas produit de valeur!")
        return 1
    
    print("✅ missing_rate fonctionne")
    
    # 3. Vérifier aggregation_by_column
    print("\n[3] TEST AGGREGATION_BY_COLUMN")
    print("-" * 70)
    
    if "aggregation_by_column" not in REGISTRY:
        print("❌ ERREUR: aggregation_by_column non trouvé!")
        return 1
    
    # Vérifier le schéma
    plugin_class = REGISTRY["aggregation_by_column"]
    params = {
        "dataset": "test",
        "group_by": "region",
        "target": "amount"
    }
    
    schema = plugin_class.output_schema(params)
    if schema is None:
        print("❌ ERREUR: aggregation devrait produire un schéma!")
        return 1
    
    print(f"Schéma de sortie: {schema.column_names()}")
    
    # Exécuter
    plugin = plugin_class()
    result = plugin.run(ctx, **params)
    
    if result.dataframe is None:
        print("❌ ERREUR: aggregation n'a pas produit de DataFrame!")
        return 1
    
    df = result.get_dataframe()
    print(f"DataFrame produit: {len(df)} lignes")
    print(f"Colonnes: {list(df.columns)}")
    
    print("✅ aggregation_by_column fonctionne")
    
    # 4. Test du catalogue virtuel
    print("\n[4] TEST CATALOGUE VIRTUEL")
    print("-" * 70)
    
    config = {
        "metrics": [
            {
                "id": "M-001",
                "type": "aggregation_by_column",
                "params": params
            },
            {
                "id": "M-002",
                "type": "missing_rate",
                "params": {"dataset": "test", "column": "amount"}
            }
        ]
    }
    
    catalog = VirtualCatalog()
    count = catalog.register_from_config(config)
    
    print(f"Datasets virtuels créés: {count}")
    print(f"Aliases: {catalog.list_virtual_datasets()}")
    
    if not catalog.exists("virtual:M-001"):
        print("❌ ERREUR: virtual:M-001 devrait exister!")
        return 1
    
    if catalog.exists("virtual:M-002"):
        print("❌ ERREUR: virtual:M-002 ne devrait PAS exister (métrique scalaire)!")
        return 1
    
    columns = catalog.get_columns("virtual:M-001")
    print(f"Colonnes de virtual:M-001: {columns}")
    
    print("✅ Catalogue virtuel fonctionne")
    
    # 5. Validation de test
    print("\n[5] TEST VALIDATION")
    print("-" * 70)
    
    # Test valide
    test_ok = {
        "id": "T-001",
        "database": "virtual:M-001",
        "column": "sum_amount"
    }
    errors = catalog.validate_test_references(test_ok)
    
    if errors:
        print(f"❌ ERREUR: Test valide rejeté: {errors}")
        return 1
    
    print("✅ Test valide accepté")
    
    # Test invalide
    test_bad = {
        "id": "T-002",
        "database": "virtual:M-001",
        "column": "colonne_inexistante"
    }
    errors = catalog.validate_test_references(test_bad)
    
    if not errors:
        print("❌ ERREUR: Test invalide devrait être rejeté!")
        return 1
    
    print(f"✅ Test invalide rejeté: {errors[0]}")
    
    # SUCCESS
    print("\n" + "=" * 70)
    print("🎉 TOUS LES TESTS SONT PASSÉS !")
    print("=" * 70)
    print("\nLe système de plugins fonctionne correctement:")
    print("  ✓ Découverte automatique")
    print("  ✓ Exécution des métriques")
    print("  ✓ Schémas de sortie")
    print("  ✓ Catalogue virtuel")
    print("  ✓ Validation des tests")
    print("\nVous pouvez maintenant:")
    print("  1. Ajouter de nouveaux plugins dans src/plugins/metrics/ ou /tests/")
    print("  2. Lancer les tests complets: pytest tests/test_plugin_system.py -v")
    print("  3. Commencer l'intégration avec l'UI")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
