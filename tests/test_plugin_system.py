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
            # Supporter à la fois 'sales' et 'sales_2024' comme alias courants
            if alias in ("sales_2024", "sales"):
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


class TestSequencer:
    """Tests du séquenceur d'exécution."""
    
    def test_simple_sequence(self):
        """Test d'un séquençage simple sans dépendances."""
        from src.plugins.sequencer import build_execution_plan, StepKind
        
        config = {
            "metrics": [
                {"id": "M-001", "type": "missing_rate", "params": {}},
                {"id": "M-002", "type": "missing_rate", "params": {}}
            ],
            "tests": [
                {"id": "T-001", "type": "range", "params": {}}
            ]
        }
        
        plan = build_execution_plan(config)
        
        assert len(plan.steps) == 3
        assert plan.metrics_count == 2
        assert plan.tests_count == 1
        
        # Les métriques doivent être au niveau 0
        metrics = plan.get_steps_by_kind(StepKind.METRIC)
        assert all(m.level == 0 for m in metrics)
        
        # Le test doit être au niveau 0 aussi (pas de dépendances)
        tests = plan.get_steps_by_kind(StepKind.TEST)
        assert all(t.level == 0 for t in tests)
    
    def test_sequence_with_virtual_dataset_dependency(self):
        """Test avec un test qui dépend d'un virtual dataset."""
        from src.plugins.sequencer import build_execution_plan
        
        config = {
            "metrics": [
                {"id": "M-001", "type": "aggregation_by_column", "params": {}}
            ],
            "tests": [
                {
                    "id": "T-001",
                    "type": "range",
                    "database": "virtual:M-001",  # Dépendance !
                    "column": "sum_amount"
                }
            ]
        }
        
        plan = build_execution_plan(config)
        
        # La métrique doit être niveau 0
        m_step = next(s for s in plan.steps if s.id == "M-001")
        assert m_step.level == 0
        
        # Le test doit être niveau 1 (dépend de M-001)
        t_step = next(s for s in plan.steps if s.id == "T-001")
        assert t_step.level == 1
        assert "M-001" in t_step.depends_on
    
    def test_sequence_with_metric_reference(self):
        """Test avec un test qui référence directement une métrique."""
        from src.plugins.sequencer import build_execution_plan
        
        config = {
            "metrics": [
                {"id": "M-002", "type": "missing_rate", "params": {}}
            ],
            "tests": [
                {
                    "id": "T-002",
                    "type": "range",
                    "metric": "M-002",  # Référence directe
                    "params": {}
                }
            ]
        }
        
        plan = build_execution_plan(config)
        
        # Le test doit dépendre de la métrique
        t_step = next(s for s in plan.steps if s.id == "T-002")
        assert t_step.level == 1
        assert "M-002" in t_step.depends_on
    
    def test_sequence_multiple_levels(self):
        """Test avec plusieurs niveaux de dépendances."""
        from src.plugins.sequencer import build_execution_plan
        
        config = {
            "metrics": [
                {"id": "M-001", "type": "aggregation_by_column", "params": {}},
                {"id": "M-002", "type": "missing_rate", "params": {}}
            ],
            "tests": [
                {
                    "id": "T-001",
                    "type": "range",
                    "database": "virtual:M-001"
                },
                {
                    "id": "T-002",
                    "type": "range",
                    "metric": "M-002"
                },
                {
                    "id": "T-003",
                    "type": "range",
                    "params": {}  # Pas de dépendances
                }
            ]
        }
        
        plan = build_execution_plan(config)
        
        assert plan.max_level == 1
        
        # Niveau 0: M-001, M-002, T-003
        level_0 = plan.get_steps_by_level(0)
        assert len(level_0) == 3
        assert all(s.id in ["M-001", "M-002", "T-003"] for s in level_0)
        
        # Niveau 1: T-001, T-002
        level_1 = plan.get_steps_by_level(1)
        assert len(level_1) == 2
        assert all(s.id in ["T-001", "T-002"] for s in level_1)
    
    def test_sequence_validation_duplicate_ids(self):
        """Test de validation: détection des IDs dupliqués."""
        from src.plugins.sequencer import build_execution_plan
        
        config = {
            "metrics": [
                {"id": "M-001", "type": "missing_rate", "params": {}},
                {"id": "M-001", "type": "aggregation_by_column", "params": {}}  # Duplicate!
            ],
            "tests": []
        }
        
        try:
            plan = build_execution_plan(config)
            errors = plan.validate()
            assert len(errors) > 0
            assert any("dupliqué" in e.lower() for e in errors)
        except ValueError:
            # C'est aussi acceptable de lever une exception
            pass
    
    def test_sequence_validation_missing_dependency(self):
        """Test de validation: détection des dépendances manquantes."""
        from src.plugins.sequencer import build_execution_plan
        
        config = {
            "metrics": [],
            "tests": [
                {
                    "id": "T-001",
                    "type": "range",
                    "database": "virtual:M-999"  # N'existe pas!
                }
            ]
        }
        
        plan = build_execution_plan(config)
        
        # Le plan se construit mais la dépendance est notée
        t_step = next(s for s in plan.steps if s.id == "T-001")
        # La dépendance est ajoutée même si la métrique n'existe pas
        # (la validation côté catalog détectera l'erreur)
        assert len(t_step.depends_on) == 0  # M-999 n'est pas dans metric_ids
    
    def test_sequence_ordering(self):
        """Test que l'ordre dans le JSON est préservé à niveau égal."""
        from src.plugins.sequencer import build_execution_plan
        
        config = {
            "metrics": [
                {"id": "M-003", "type": "missing_rate", "params": {}},
                {"id": "M-001", "type": "missing_rate", "params": {}},
                {"id": "M-002", "type": "missing_rate", "params": {}}
            ],
            "tests": []
        }
        
        plan = build_execution_plan(config)
        
        # L'ordre devrait être préservé (M-003, M-001, M-002)
        metric_ids = [s.id for s in plan.get_steps_by_kind("metric")]
        assert metric_ids == ["M-003", "M-001", "M-002"]
    
    def test_print_execution_plan(self):
        """Test de l'affichage du plan (ne doit pas crasher)."""
        from src.plugins.sequencer import build_execution_plan, print_execution_plan
        
        config = {
            "metrics": [
                {"id": "M-001", "type": "aggregation_by_column", "params": {}}
            ],
            "tests": [
                {"id": "T-001", "type": "range", "database": "virtual:M-001"}
            ]
        }
        
        plan = build_execution_plan(config)
        
        # Juste vérifier que ça ne crash pas
        import io
        import contextlib
        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            print_execution_plan(plan)
        
        output = f.getvalue()
        assert "EXECUTION PLAN" in output
        assert "M-001" in output
        assert "T-001" in output


class TestExecutor:
    """Tests de l'executor."""
    
    def test_executor_simple_metric(self):
        """Test d'exécution d'une métrique simple."""
        from src.plugins.sequencer import build_execution_plan
        from src.plugins.executor import Executor, ExecutionContext
        
        config = {
            "metrics": [
                {"id": "M-001", "type": "missing_rate", "params": {"dataset": "sales", "column": "amount"}}
            ],
            "tests": []
        }
        
        plan = build_execution_plan(config)
        context = MockContext()
        executor = Executor(ExecutionContext(context.load))
        
        result = executor.execute(plan)
        
        assert result.success
        assert len(result.step_results) == 1
        assert "M-001" in result.metrics
        assert result.metrics["M-001"] is not None
    
    def test_executor_with_aggregation(self):
        """Test d'exécution d'une métrique d'agrégation."""
        from src.plugins.sequencer import build_execution_plan
        from src.plugins.executor import Executor, ExecutionContext
        
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
        
        plan = build_execution_plan(config)
        context = MockContext()
        executor = Executor(ExecutionContext(context.load))
        
        result = executor.execute(plan)
        
        assert result.success
        assert "M-001" in result.dataframes
        df = result.dataframes["M-001"]
        assert df is not None
        assert len(df) > 0
    
    def test_executor_with_test(self):
        """Test d'exécution d'un test dépendant d'une métrique."""
        discover_all_plugins(verbose=False)
        from src.plugins.sequencer import build_execution_plan
        from src.plugins.executor import Executor, ExecutionContext
        
        config = {
            "metrics": [
                {"id": "M-001", "type": "missing_rate", "params": {"dataset": "sales", "column": "amount"}}
            ],
            "tests": [
                {
                    "id": "T-001",
                    "type": "range",
                    "params": {
                        "value_from_metric": "M-001",
                        "low": 0.0,
                        "high": 1.0,
                        "inclusive": True
                    }
                }
            ]
        }
        
        plan = build_execution_plan(config)
        context = MockContext()
        executor = Executor(ExecutionContext(context.load))
        
        result = executor.execute(plan)
        
        assert result.success
        assert "T-001" in result.tests
        assert result.tests["T-001"]["passed"] is not None
    
    def test_executor_with_virtual_dataset(self):
        """Test avec un test référençant un virtual dataset."""
        discover_all_plugins(verbose=False)
        from src.plugins.sequencer import build_execution_plan
        from src.plugins.executor import Executor, ExecutionContext
        
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
        
        plan = build_execution_plan(config)
        context = MockContext()
        exec_context = ExecutionContext(context.load)
        executor = Executor(exec_context)
        
        result = executor.execute(plan)
        
        # Vérifier que le virtual dataset est accessible
        assert result.success
        assert "M-001" in result.dataframes
        
        # Le virtual dataset devrait être chargeable
        virtual_df = exec_context.load("virtual:M-001")
        assert virtual_df is not None
    
    def test_executor_fail_fast(self):
        """Test du mode fail-fast."""
        from src.plugins.sequencer import build_execution_plan
        from src.plugins.executor import Executor, ExecutionContext, ExecutionStatus
        
        # Config avec une métrique qui va échouer
        config = {
            "metrics": [
                {"id": "M-001", "type": "nonexistent_plugin", "params": {}},  # Va échouer
                {"id": "M-002", "type": "missing_rate", "params": {"dataset": "sales", "column": "amount"}}
            ],
            "tests": []
        }
        
        plan = build_execution_plan(config)
        context = MockContext()
        executor = Executor(ExecutionContext(context.load), fail_fast=True)
        
        result = executor.execute(plan)
        
        assert not result.success
        # M-001 devrait avoir échoué
        m1_result = result.get_step_result("M-001")
        assert m1_result.status == ExecutionStatus.FAILED
        # M-002 ne devrait pas avoir été exécuté en fail-fast
        # (ou exécuté si même niveau, selon implémentation)
    
    def test_executor_dependency_skip(self):
        """Test que les steps dépendants sont skippés si leur dépendance échoue."""
        discover_all_plugins(verbose=False)
        from src.plugins.sequencer import build_execution_plan
        from src.plugins.executor import Executor, ExecutionContext, ExecutionStatus
        
        config = {
            "metrics": [
                {"id": "M-001", "type": "nonexistent_plugin", "params": {}}  # Va échouer
            ],
            "tests": [
                {
                    "id": "T-001",
                    "type": "range",
                    "params": {"value_from_metric": "M-001", "low": 0, "high": 1}
                }
            ]
        }
        
        plan = build_execution_plan(config)
        context = MockContext()
        executor = Executor(ExecutionContext(context.load), fail_fast=False)
        
        result = executor.execute(plan)
        
        # M-001 devrait avoir échoué
        m1_result = result.get_step_result("M-001")
        assert m1_result.status == ExecutionStatus.FAILED
        
        # T-001 devrait avoir été skippé (dépend de M-001)
        t1_result = result.get_step_result("T-001")
        assert t1_result.status == ExecutionStatus.SKIPPED
    
    def test_executor_schema_validation(self):
        """Test de validation du schéma de sortie."""
        from src.plugins.sequencer import build_execution_plan
        from src.plugins.executor import Executor, ExecutionContext
        
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
        
        plan = build_execution_plan(config)
        context = MockContext()
        executor = Executor(ExecutionContext(context.load))
        
        result = executor.execute(plan)
        
        # L'executor doit valider le schéma automatiquement
        assert result.success
        m1_result = result.get_step_result("M-001")
        assert m1_result.status == "success"


if __name__ == "__main__":
    # Permet de lancer les tests directement
    pytest.main([__file__, "-v", "-s"])
