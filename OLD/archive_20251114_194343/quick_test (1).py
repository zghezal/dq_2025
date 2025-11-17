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


class TestRunner:
    """Gestionnaire d'état des tests avec vraie validation."""
    
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failure_messages = []
    
    def run_test(self, name: str, test_func):
        """
        Exécute un test et enregistre le résultat.
        
        Args:
            name: Nom du test
            test_func: Fonction qui retourne (bool, message)
        """
        self.tests_run += 1
        try:
            success, message = test_func()
            if success:
                self.tests_passed += 1
                print(f"✅ {name}")
            else:
                self.tests_failed += 1
                self.failure_messages.append(f"{name}: {message}")
                print(f"❌ {name}")
                print(f"   Raison: {message}")
        except Exception as e:
            self.tests_failed += 1
            self.failure_messages.append(f"{name}: Exception - {str(e)}")
            print(f"❌ {name}")
            print(f"   Exception: {e}")
    
    def print_summary(self):
        """Affiche le résumé final."""
        print("\n" + "=" * 70)
        print("RÉSUMÉ DES TESTS")
        print("=" * 70)
        print(f"Tests exécutés: {self.tests_run}")
        print(f"Tests réussis:  {self.tests_passed} ✅")
        print(f"Tests échoués:  {self.tests_failed} ❌")
        
        if self.tests_failed > 0:
            print("\n⚠️  ÉCHECS DÉTECTÉS:")
            for msg in self.failure_messages:
                print(f"  • {msg}")
            print("\n" + "=" * 70)
            print("❌ CERTAINS TESTS ONT ÉCHOUÉ")
            print("=" * 70)
            return False
        else:
            print("\n" + "=" * 70)
            print("🎉 TOUS LES TESTS SONT PASSÉS !")
            print("=" * 70)
            return True


def test_plugin_discovery():
    """Test 1: Découverte des plugins."""
    plugins = discover_all_plugins(verbose=False)
    if len(plugins) < 2:
        return False, f"Seulement {len(plugins)} plugin(s) trouvé(s), attendu >= 2"
    if "missing_rate" not in plugins:
        return False, "missing_rate non découvert"
    if "aggregation_by_column" not in plugins:
        return False, "aggregation_by_column non découvert"
    return True, f"{len(plugins)} plugins découverts"


def test_registry_populated():
    """Test 2: REGISTRY est peuplé."""
    if len(REGISTRY) == 0:
        return False, "REGISTRY est vide"
    if "missing_rate" not in REGISTRY:
        return False, "missing_rate absent du REGISTRY"
    return True, f"REGISTRY contient {len(REGISTRY)} plugins"


def test_missing_rate_execution():
    """Test 3: Exécution de missing_rate."""
    plugin = REGISTRY["missing_rate"]()
    ctx = SimpleContext()
    result = plugin.run(ctx, dataset="test", column="amount")
    
    if result.value is None:
        return False, "missing_rate n'a pas produit de valeur"
    
    # Vérifier que la valeur est cohérente (1 missing sur 4 = 0.25)
    if abs(result.value - 0.25) > 0.01:
        return False, f"Valeur incorrecte: {result.value}, attendu ~0.25"
    
    return True, f"missing_rate = {result.value:.2%}"


def test_missing_rate_no_output_schema():
    """Test 4: missing_rate ne produit pas de schéma."""
    plugin_class = REGISTRY["missing_rate"]
    schema = plugin_class.output_schema({})
    
    if schema is not None:
        return False, "missing_rate ne devrait pas produire de schéma"
    
    return True, "missing_rate est bien scalaire"


def test_aggregation_has_output_schema():
    """Test 5: aggregation déclare son schéma."""
    plugin_class = REGISTRY["aggregation_by_column"]
    params = {
        "dataset": "test",
        "group_by": "region",
        "target": "amount"
    }
    
    schema = plugin_class.output_schema(params)
    
    if schema is None:
        return False, "aggregation devrait produire un schéma"
    
    columns = schema.column_names()
    expected = ["region", "count", "sum_amount", "avg_amount", "min_amount", "max_amount"]
    
    for col in expected:
        if col not in columns:
            return False, f"Colonne manquante: {col}"
    
    return True, f"Schéma avec {len(columns)} colonnes"


def test_aggregation_execution():
    """Test 6: Exécution de aggregation."""
    plugin = REGISTRY["aggregation_by_column"]()
    ctx = SimpleContext()
    params = {
        "dataset": "test",
        "group_by": "region",
        "target": "amount"
    }
    
    result = plugin.run(ctx, **params)
    
    if result.dataframe is None:
        return False, "aggregation n'a pas produit de DataFrame"
    
    df = result.get_dataframe()
    if df is None or len(df) == 0:
        return False, "DataFrame vide"
    
    # Vérifier les colonnes
    expected_cols = ["region", "count", "sum_amount", "avg_amount", "min_amount", "max_amount"]
    for col in expected_cols:
        if col not in df.columns:
            return False, f"Colonne manquante dans le DataFrame: {col}"
    
    return True, f"DataFrame avec {len(df)} lignes et {len(df.columns)} colonnes"


def test_virtual_catalog_creation():
    """Test 7: Création du catalogue virtuel."""
    config = {
        "metrics": [
            {
                "id": "M-001",
                "type": "aggregation_by_column",
                "params": {
                    "dataset": "test",
                    "group_by": "region",
                    "target": "amount"
                }
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
    
    # Seul M-001 devrait créer un virtual dataset
    if count != 1:
        return False, f"Attendu 1 virtual dataset, obtenu {count}"
    
    if not catalog.exists("virtual:M-001"):
        return False, "virtual:M-001 devrait exister"
    
    if catalog.exists("virtual:M-002"):
        return False, "virtual:M-002 ne devrait PAS exister (métrique scalaire)"
    
    return True, f"{count} virtual dataset créé"


def test_virtual_catalog_columns():
    """Test 8: Récupération des colonnes virtuelles."""
    config = {
        "metrics": [
            {
                "id": "M-001",
                "type": "aggregation_by_column",
                "params": {
                    "dataset": "test",
                    "group_by": "region",
                    "target": "amount"
                }
            }
        ]
    }
    
    catalog = VirtualCatalog()
    catalog.register_from_config(config)
    
    try:
        columns = catalog.get_columns("virtual:M-001")
    except Exception as e:
        return False, f"Impossible de récupérer les colonnes: {e}"
    
    if "sum_amount" not in columns:
        return False, "Colonne sum_amount manquante"
    
    return True, f"{len(columns)} colonnes récupérées"


def test_validation_valid_test():
    """Test 9: Validation d'un test valide."""
    config = {
        "metrics": [
            {
                "id": "M-001",
                "type": "aggregation_by_column",
                "params": {
                    "dataset": "test",
                    "group_by": "region",
                    "target": "amount"
                }
            }
        ]
    }
    
    catalog = VirtualCatalog()
    catalog.register_from_config(config)
    
    test_config = {
        "id": "T-001",
        "database": "virtual:M-001",
        "column": "sum_amount"
    }
    
    errors = catalog.validate_test_references(test_config)
    
    if errors:
        return False, f"Test valide rejeté: {errors}"
    
    return True, "Test valide accepté"


def test_validation_invalid_dataset():
    """Test 10: Validation rejette dataset invalide."""
    config = {
        "metrics": [
            {
                "id": "M-001",
                "type": "aggregation_by_column",
                "params": {
                    "dataset": "test",
                    "group_by": "region",
                    "target": "amount"
                }
            }
        ]
    }
    
    catalog = VirtualCatalog()
    catalog.register_from_config(config)
    
    test_config = {
        "id": "T-BAD",
        "database": "virtual:M-999",  # N'existe pas
        "column": "foo"
    }
    
    errors = catalog.validate_test_references(test_config)
    
    if not errors:
        return False, "Test invalide devrait être rejeté"
    
    return True, "Test invalide correctement rejeté"


def test_validation_invalid_column():
    """Test 11: Validation rejette colonne invalide."""
    config = {
        "metrics": [
            {
                "id": "M-001",
                "type": "aggregation_by_column",
                "params": {
                    "dataset": "test",
                    "group_by": "region",
                    "target": "amount"
                }
            }
        ]
    }
    
    catalog = VirtualCatalog()
    catalog.register_from_config(config)
    
    test_config = {
        "id": "T-BAD",
        "database": "virtual:M-001",
        "column": "colonne_inexistante"  # N'existe pas
    }
    
    errors = catalog.validate_test_references(test_config)
    
    if not errors:
        return False, "Colonne invalide devrait être rejetée"
    
    return True, "Colonne invalide correctement rejetée"


def main():
    print("=" * 70)
    print("TEST RAPIDE DU SYSTÈME DE PLUGINS")
    print("=" * 70)
    
    runner = TestRunner()
    
    # Section 1: Découverte
    print("\n[SECTION 1] DÉCOUVERTE DES PLUGINS")
    print("-" * 70)
    discover_all_plugins(verbose=True)  # Afficher les détails de découverte
    
    runner.run_test("1.1 - Plugins découverts", test_plugin_discovery)
    runner.run_test("1.2 - REGISTRY peuplé", test_registry_populated)
    
    # Section 2: Missing Rate
    print("\n[SECTION 2] PLUGIN MISSING_RATE")
    print("-" * 70)
    runner.run_test("2.1 - Exécution missing_rate", test_missing_rate_execution)
    runner.run_test("2.2 - missing_rate sans output_schema", test_missing_rate_no_output_schema)
    
    # Section 3: Aggregation
    print("\n[SECTION 3] PLUGIN AGGREGATION")
    print("-" * 70)
    runner.run_test("3.1 - output_schema déclaré", test_aggregation_has_output_schema)
    runner.run_test("3.2 - Exécution aggregation", test_aggregation_execution)
    
    # Section 4: Catalogue Virtuel
    print("\n[SECTION 4] CATALOGUE VIRTUEL")
    print("-" * 70)
    runner.run_test("4.1 - Création catalogue", test_virtual_catalog_creation)
    runner.run_test("4.2 - Récupération colonnes", test_virtual_catalog_columns)
    
    # Section 5: Validation
    print("\n[SECTION 5] VALIDATION DES TESTS")
    print("-" * 70)
    runner.run_test("5.1 - Test valide accepté", test_validation_valid_test)
    runner.run_test("5.2 - Dataset invalide rejeté", test_validation_invalid_dataset)
    runner.run_test("5.3 - Colonne invalide rejetée", test_validation_invalid_column)
    
    # Résumé final
    all_passed = runner.print_summary()
    
    if all_passed:
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
    else:
        print("\n⚠️  Corrigez les erreurs ci-dessus avant de continuer.")
        return 1


if __name__ == "__main__":
    sys.exit(main())