"""
Tests du système de plugins complet.

Ce fichier teste l'intégration de tous les composants:
- Découverte automatique des plugins
- Catalogue de datasets virtuels
- Exécution des plugins
- Validation des schémas
"""

import os
import sys
import pytest
import pandas as pd

# Ensure workspace root is on sys.path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.plugins.discovery import discover_all_plugins, REGISTRY
from src.plugins.virtual_catalog import VirtualCatalog
from src.plugins.base import Result
from src.plugins.output_schema import OutputSchema


# Mock Context pour les tests
class MockContext:
    """Context factice pour tester les plugins sans vraie BDD."""
    
    def __init__(self):
        self.datasets = {}
    
    def load(self, alias: str) -> pd.DataFrame:
        """Retourne un DataFrame de test."""
        if alias not in self.datasets:
            # Créer un dataset de test par défaut
            if alias == "sales_2024":
                self.datasets[alias] = pd.DataFrame({
                    "date": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"],
                    "region": ["North", "South", "North", "East"],
                    "amount": [100.0, 200.0, None, 150.0],  # Une valeur manquante
                    "quantity": [10, 20, 15, 25]
                })
            else:
                # Dataset générique
                self.datasets[alias] = pd.DataFrame({
                    "col1": [1, 2, None, 4],
                    "col2": ["a", "b", "c", "d"]
                })
        return self.datasets[alias]


class TestPluginDiscovery:
    """Tests de découverte automatique des plugins."""
    
    def test_discovery_finds_plugins(self):
        """Vérifie que le système découvre les plugins."""
        plugins = discover_all_plugins(verbose=False)
        
        # On doit avoir au moins missing_rate et aggregation_by_column
        assert len(plugins) >= 2, f"Expected at least 2 plugins, found {len(plugins)}"
        
        # Vérifier que les plugins attendus sont présents
        plugin_ids = list(plugins.keys())
        assert "missing_rate" in plugin_ids, "missing_rate plugin not discovered"
        assert "aggregation_by_column" in plugin_ids, "aggregation_by_column not discovered"
    
    def test_registry_is_populated(self):
        """Vérifie que REGISTRY contient les plugins découverts."""
        discover_all_plugins(verbose=False)
        
        assert len(REGISTRY) > 0, "REGISTRY is empty"
        assert "missing_rate" in REGISTRY
        assert "aggregation_by_column" in REGISTRY
    
    def test_plugin_has_required_attributes(self):
        """Vérifie que les plugins respectent le contrat."""
        discover_all_plugins(verbose=False)
        
        for plugin_id, plugin_class in REGISTRY.items():
            # Attributs obligatoires
            assert hasattr(plugin_class, "plugin_id")
            assert hasattr(plugin_class, "label")
            assert hasattr(plugin_class, "group")
            assert hasattr(plugin_class, "ParamsModel")
            assert hasattr(plugin_class, "run")
            
            # Vérifier que plugin_id correspond
            assert plugin_class.plugin_id == plugin_id


class TestMissingRatePlugin:
    """Tests spécifiques au plugin missing_rate."""
    
    def test_missing_rate_on_column(self):
        """Test du calcul de missing rate sur une colonne."""
        discover_all_plugins(verbose=False)
        plugin = REGISTRY["missing_rate"]()
        
        context = MockContext()
        params = {
            "dataset": "sales_2024",
            "column": "amount"
        }
        
        result = plugin.run(context, **params)
        
        assert isinstance(result, Result)
        assert result.passed is None  # Métrique, pas test
        assert result.value is not None
        
        # Le dataset de test a 1 valeur manquante sur 4 = 0.25
        assert abs(result.value - 0.25) < 0.01
    
    def test_missing_rate_on_full_dataset(self):
        """Test du calcul de missing rate sur tout le dataset."""
        discover_all_plugins(verbose=False)
        plugin = REGISTRY["missing_rate"]()
        
        context = MockContext()
        params = {
            "dataset": "sales_2024",
            "column": None
        }
        
        result = plugin.run(context, **params)
        
        assert result.value is not None
        # 1 missing sur 16 cellules (4 rows x 4 cols) = 0.0625
        assert abs(result.value - 0.0625) < 0.01
    
    def test_missing_rate_has_no_output_schema(self):
        """Vérifie que missing_rate ne produit pas de colonnes."""
        discover_all_plugins(verbose=False)
        plugin_class = REGISTRY["missing_rate"]
        
        schema = plugin_class.output_schema({})
        assert schema is None, "missing_rate should not produce columns"


class TestAggregationPlugin:
    """Tests spécifiques au plugin aggregation_by_column."""
    
    def test_output_schema_is_declared(self):
        """Vérifie que le plugin déclare son schéma de sortie."""
        discover_all_plugins(verbose=False)
        plugin_class = REGISTRY["aggregation_by_column"]
        
        params = {
            "dataset": "sales_2024",
            "group_by": "region",
            "target": "amount"
        }
        
        schema = plugin_class.output_schema(params)
        
        assert schema is not None
        assert isinstance(schema, OutputSchema)
        
        # Vérifier les colonnes attendues
        column_names = schema.column_names()
        assert "region" in column_names
        assert "count" in column_names
        assert "sum_amount" in column_names
        assert "avg_amount" in column_names
        assert "min_amount" in column_names
        assert "max_amount" in column_names
    
    def test_aggregation_execution(self):
        """Test de l'exécution de l'agrégation."""
        discover_all_plugins(verbose=False)
        plugin = REGISTRY["aggregation_by_column"]()
        
        context = MockContext()
        params = {
            "dataset": "sales_2024",
            "group_by": "region",
            "target": "amount"
        }
        
        result = plugin.run(context, **params)
        
        assert isinstance(result, Result)
        assert result.dataframe is not None
        
        df = result.get_dataframe()
        assert df is not None
        assert len(df) > 0
        
        # Vérifier que les colonnes correspondent au schéma
        assert "region" in df.columns
        assert "count" in df.columns
        assert "sum_amount" in df.columns
    
    def test_schema_validation_passes(self):
        """Vérifie que le schéma produit correspond au schéma prédit."""
        discover_all_plugins(verbose=False)
        plugin = REGISTRY["aggregation_by_column"]()
        
        context = MockContext()
        params = {
            "dataset": "sales_2024",
            "group_by": "region",
            "target": "amount"
        }
        
        # Exécuter et vérifier qu'il n'y a pas d'erreur de validation
        result = plugin.run(context, **params)
        
        assert "schema_validation_failed" not in result.meta.get("error", "")


class TestVirtualCatalog:
    """Tests du catalogue de datasets virtuels."""
    
    def test_catalog_registration_from_config(self):
        """Test de l'enregistrement depuis une config DQ."""
        discover_all_plugins(verbose=False)
        
        config = {
            "metrics": [
                {
                    "id": "M-001",
                    "type": "aggregation_by_column",
                    "params": {
                        "dataset": "sales_2024",
                        "group_by": "region",
                        "target": "amount"
                    }
                },
                {
                    "id": "M-002",
                    "type": "missing_rate",
                    "params": {
                        "dataset": "sales_2024",
                        "column": "amount"
                    }
                }
            ]
        }
        
        catalog = VirtualCatalog()
        count = catalog.register_from_config(config)
        
        # Seul M-001 produit un virtual dataset (M-002 est scalaire)
        assert count == 1
        
        # Vérifier que virtual:M-001 existe
        assert catalog.exists("virtual:M-001")
        assert not catalog.exists("virtual:M-002")  # missing_rate ne produit pas de colonnes
    
    def test_catalog_get_columns(self):
        """Test de récupération des colonnes d'un virtual dataset."""
        discover_all_plugins(verbose=False)
        
        config = {
            "metrics": [
                {
                    "id": "M-001",
                    "type": "aggregation_by_column",
                    "params": {
                        "dataset": "sales_2024",
                        "group_by": "region",
                        "target": "amount"
                    }
                }
            ]
        }
        
        catalog = VirtualCatalog()
        catalog.register_from_config(config)
        
        columns = catalog.get_columns("virtual:M-001")
        
        assert "region" in columns
        assert "count" in columns
        assert "sum_amount" in columns
    
    def test_catalog_validates_test_references(self):
        """Test de validation des références de tests."""
        discover_all_plugins(verbose=False)
        
        config = {
            "metrics": [
                {
                    "id": "M-001",
                    "type": "aggregation_by_column",
                    "params": {
                        "dataset": "sales_2024",
                        "group_by": "region",
                        "target": "amount"
                    }
                }
            ]
        }
        
        catalog = VirtualCatalog()
        catalog.register_from_config(config)
        
        # Test valide
        test_valid = {
            "id": "T-001",
            "database": "virtual:M-001",
            "column": "sum_amount"
        }
        errors = catalog.validate_test_references(test_valid)
        assert len(errors) == 0
        
        # Test invalide: dataset virtuel inexistant
        test_bad_dataset = {
            "id": "T-002",
            "database": "virtual:M-999",
            "column": "foo"
        }
        errors = catalog.validate_test_references(test_bad_dataset)
        assert len(errors) > 0
        
        # Test invalide: colonne inexistante
        test_bad_column = {
            "id": "T-003",
            "database": "virtual:M-001",
            "column": "nonexistent_column"
        }
        errors = catalog.validate_test_references(test_bad_column)
        assert len(errors) > 0


class TestEndToEndFlow:
    """Tests du flux complet end-to-end."""
    
    def test_complete_workflow(self):
        """
        Test du workflow complet:
        1. Découverte des plugins
        2. Construction du catalogue virtuel
        3. Validation des tests
        4. Exécution
        """
        # 1. Découverte
        plugins = discover_all_plugins(verbose=False)
        assert len(plugins) >= 2
        
        # 2. Configuration DQ
        config = {
            "metrics": [
                {
                    "id": "M-001",
                    "type": "aggregation_by_column",
                    "params": {
                        "dataset": "sales_2024",
                        "group_by": "region",
                        "target": "amount"
                    }
                }
            ],
            "tests": [
                {
                    "id": "T-001",
                    "type": "range",
                    "database": "virtual:M-001",
                    "column": "sum_amount"
                }
            ]
        }
        
        # 3. Construction du catalogue
        catalog = VirtualCatalog()
        catalog.register_from_config(config)
        
        assert catalog.exists("virtual:M-001")
        
        # 4. Validation du test
        test = config["tests"][0]
        errors = catalog.validate_test_references(test)
        assert len(errors) == 0, f"Validation errors: {errors}"
        
        # 5. Exécution de la métrique
        context = MockContext()
        plugin = REGISTRY["aggregation_by_column"]()
        result = plugin.run(context, **config["metrics"][0]["params"])
        
        assert result.dataframe is not None
        print(f"\n✅ End-to-end test passed!")
        print(f"   Virtual catalog has {len(catalog.list_virtual_datasets())} datasets")
        print(f"   Aggregation produced {len(result.get_dataframe())} rows")


if __name__ == "__main__":
    # Permet de lancer les tests directement
    pytest.main([__file__, "-v", "-s"])
