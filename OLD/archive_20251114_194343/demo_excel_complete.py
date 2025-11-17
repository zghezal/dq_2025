"""
Export Excel complet - Avec tests implicites de filtres et gestion des dépendances

Démontre:
1. Export avec tous les types de tests implicites
2. Gestion des dépendances (SKIPPED si dépendance échoue)
3. Flags d'exécution pour métriques et tests
"""

from datetime import datetime
import random
from pathlib import Path

from src.core.dq_parser import DQConfig, DQContext, Metric, Test
from src.core.dq_parser import MetricIdentification, MetricNature, MetricGeneral
from src.core.dq_parser import TestIdentification, TestNature, TestGeneral
from src.core.sequencer import DQSequencer, CommandType
from src.core.dependency_executor import DQExecutor, ExecutionStatus
from src.core.excel_exporter import export_execution_results
import pandas as pd


def create_config_with_filters():
    """Crée une config avec des tests utilisant des filtres"""
    from src.core.dq_parser import load_dq_config
    
    # Charger config de base
    config = load_dq_config("dq/definitions/sales_complete_quality.yaml")
    
    # Ajouter un test avec filtre
    test_with_filter = Test(
        test_id="T_007_check_amounts_north_region",
        type="interval_check",
        identification=TestIdentification(
            test_id="T_007_check_amounts_north_region",
            control_name="Amount validation for North region",
            control_id="CTRL_007"
        ),
        nature=TestNature(
            name="Validation montants région North",
            description="Vérifie que les montants de la région North sont dans la plage valide",
            functional_category_1="Cohérence",
            functional_category_2="Données régionales",
            category="business_rule"
        ),
        general=TestGeneral(
            severity="medium",
            stop_on_failure=False,
            action_on_fail="alert"
        ),
        specific={
            'value_from_dataset': 'sales_2024',
            'target_mode': 'dataset',
            'where': "region = 'North' AND date > '2024-01-01'",
            'bounds': {'lower': 50, 'upper': 300},
            'column_rules': []
        }
    )
    
    config.tests[test_with_filter.test_id] = test_with_filter
    
    return config


def create_metric_dataframe(cmd):
    """
    Crée un DataFrame simulé pour une métrique
    
    Simule le résultat d'une métrique missing_rate avec les colonnes
    <column>_missing_rate et <column>_missing_number
    """
    import pandas as pd
    
    # Récupérer les paramètres
    specific = cmd.parameters
    columns = specific.get('column', [])
    
    # Si column n'est pas une liste, la convertir
    if isinstance(columns, str):
        columns = [columns]
    elif not columns:
        columns = ['value']  # Colonne par défaut
    
    # Créer des données simulées
    data = {}
    for col in columns:
        data[f'{col}_missing_rate'] = [round(random.uniform(0, 0.1), 4)]
        data[f'{col}_missing_number'] = [random.randint(0, 50)]
    
    return pd.DataFrame(data)


def simulate_execution_with_dependencies(sequence):
    """
    Simulation avec gestion réelle des dépendances.
    Utilise DQExecutor pour gérer automatiquement les SKIP.
    """
    
    def execute_command(cmd):
        """Fonction d'exécution simulée pour une commande"""
        rand = random.random()
        
        if cmd.command_type == CommandType.METRIC:
            # Métriques: forcer l'échec de M_002 pour tester les dépendances
            if cmd.element_id == 'M_002_missing_amount':
                return {
                    'status': ExecutionStatus.ERROR,
                    'value': None,
                    'dataframe': None,
                    'error': 'Connexion timeout to database',
                }
            
            # Autres métriques: 90% succès
            if rand > 0.1:
                df_result = create_metric_dataframe(cmd)
                return {
                    'status': ExecutionStatus.SUCCESS,
                    'value': round(random.uniform(0, 0.08), 4),
                    'dataframe': df_result,
                    'error': '',
                }
            else:
                return {
                    'status': ExecutionStatus.ERROR,
                    'value': None,
                    'dataframe': None,
                    'error': f'Dataset {cmd.parameters.get("dataset", "unknown")} not accessible',
                }
        
        elif cmd.command_type == CommandType.TEST:
            # Tests normaux: 80% succès
            if rand > 0.2:
                passed = rand > 0.3
                return {
                    'status': ExecutionStatus.SUCCESS if passed else ExecutionStatus.FAIL,
                    'result': 'PASS' if passed else 'FAIL',
                    'error': '' if passed else f'Value {round(random.uniform(0.1, 0.2), 4)} outside bounds',
                }
            else:
                return {
                    'status': ExecutionStatus.ERROR,
                    'result': 'ERROR',
                    'error': 'Runtime error during test execution',
                }
        
        else:  # Tests implicites
            # Tests techniques : très haute réussite
            if 'param_validation' in cmd.command_id:
                # Validation paramètres : 98% succès
                if rand > 0.02:
                    return {
                        'status': ExecutionStatus.SUCCESS,
                        'result': 'PASS',
                        'error': '',
                    }
                else:
                    return {
                        'status': ExecutionStatus.FAIL,
                        'result': 'FAIL',
                        'error': 'Parameter type mismatch: expected int, got string',
                    }
            
            elif 'presence' in cmd.command_id:
                # Présence colonnes : 95% succès
                if rand > 0.05:
                    return {
                        'status': ExecutionStatus.SUCCESS,
                        'result': 'PASS',
                        'error': '',
                    }
                else:
                    cols = cmd.parameters.get('required_columns', [])
                    missing_col = cols[0] if cols else 'unknown'
                    return {
                        'status': ExecutionStatus.FAIL,
                        'result': 'FAIL',
                        'error': f'Column "{missing_col}" not found in dataset',
                    }
            
            elif 'type' in cmd.command_id:
                # Type des colonnes : 95% succès
                if rand > 0.05:
                    return {
                        'status': ExecutionStatus.SUCCESS,
                        'result': 'PASS',
                        'error': '',
                    }
                else:
                    return {
                        'status': ExecutionStatus.FAIL,
                        'result': 'FAIL',
                        'error': 'Column type mismatch: expected numeric, got string',
                    }
    
    # Utiliser DQExecutor pour gérer automatiquement les dépendances
    executor = DQExecutor(sequence)
    results = executor.execute(execute_command, skip_on_dependency_failure=True)
    
    return results, executor


def demo_excel_export_complete():
    """Démonstration complète avec tous les types de tests"""
    
    print("=" * 80)
    print("EXPORT EXCEL COMPLET - AVEC FILTRES ET TESTS IMPLICITES")
    print("=" * 80)
    
    # 1. Créer configuration enrichie
    print("\n📝 Création de la configuration avec filtres...")
    config = create_config_with_filters()
    print(f"   Métriques: {len(config.metrics)}")
    print(f"   Tests: {len(config.tests)}")
    
    # 2. Construire la séquence
    print("\n🔄 Construction de la séquence d'exécution...")
    sequencer = DQSequencer(config)
    sequence = sequencer.build_sequence()
    
    # Compter les types de commandes
    metrics_count = sum(1 for c in sequence.commands if c.command_type == CommandType.METRIC)
    tests_count = sum(1 for c in sequence.commands if c.command_type == CommandType.TEST)
    implicit_count = sum(1 for c in sequence.commands if c.command_type == CommandType.IMPLICIT_TEST)
    
    print(f"   Total commandes: {len(sequence.commands)}")
    print(f"   - Métriques: {metrics_count}")
    print(f"   - Tests: {tests_count}")
    print(f"   - Tests implicites: {implicit_count}")
    
    # 3. Simuler l'exécution avec gestion des dépendances
    print("\n⚙️  Simulation de l'exécution avec dépendances...")
    execution_results, executor = simulate_execution_with_dependencies(sequence)
    
    # Statistiques avec gestion des SKIPPED
    summary = executor.get_summary()
    metrics_summary = executor.get_metrics_summary()
    tests_summary = executor.get_tests_summary()
    
    print(f"   Métriques: SUCCESS={metrics_summary.get(ExecutionStatus.SUCCESS, 0)}, "
          f"ERROR={metrics_summary.get(ExecutionStatus.ERROR, 0)}, "
          f"SKIPPED={metrics_summary.get(ExecutionStatus.SKIPPED, 0)}")
    
    print(f"   Tests: PASS={tests_summary.get(ExecutionStatus.SUCCESS, 0)}, "
          f"FAIL={tests_summary.get(ExecutionStatus.FAIL, 0)}, "
          f"ERROR={tests_summary.get(ExecutionStatus.ERROR, 0)}, "
          f"SKIPPED={tests_summary.get(ExecutionStatus.SKIPPED, 0)}")
    
    # 4. Générer le rapport Excel
    print("\n📊 Génération du rapport Excel complet...")
    output_path = "reports/dq_execution_report_complete.xlsx"
    
    export_execution_results(
        sequence=sequence,
        execution_results=execution_results,
        output_path=output_path,
        quarter="Q4 2025",
        project="Sales Data Quality - Complete",
        run_version="v1.0.1",
        user="data_quality_team"
    )
    
    print("\n" + "=" * 80)
    print("✨ Rapport complet généré!")
    print("=" * 80)
    print(f"\n📁 Fichier: {output_path}")
    print("\n📋 Contenu:")
    print(f"  • Onglet 'Métriques': {metrics_count} lignes")
    print(f"  • Onglet 'Tests': {tests_count + implicit_count} lignes")
    
    # Lister les onglets de données exportés
    print("\n📊 Onglets de données des métriques (export=True):")
    exported_metrics = []
    for cmd in sequence.commands:
        if cmd.command_type == CommandType.METRIC:
            general = cmd.metadata.get('general', {})
            result = execution_results.get(cmd.command_id, {})
            if general.get('export', True) and result.get('status') == 'SUCCESS':
                identification = cmd.metadata.get('identification', {})
                metric_id = identification.get('metric_id', cmd.element_id)
                exported_metrics.append(metric_id)
    
    if exported_metrics:
        for i, metric_id in enumerate(exported_metrics, 1):
            print(f"  {i}. Onglet '{metric_id}' - Données de la métrique")
    else:
        print("  (Aucune métrique exportée)")
    
    print("\n🔍 Types de tests inclus:")
    print("  ✅ Tests business (normaux)")
    print("  ✅ Tests techniques de validation de paramètres")
    print("  ✅ Tests techniques de présence de colonnes (filtres)")
    print("  ✅ Tests techniques de compatibilité de types (filtres)")
    
    print("\n⚠️  Gestion des dépendances:")
    print(f"  • Tests/métriques SKIPPED: {summary.get(ExecutionStatus.SKIPPED, 0)}")
    
    # Afficher quelques exemples de SKIPPED
    skipped_examples = [(k, v) for k, v in execution_results.items() 
                       if v.get('status') == ExecutionStatus.SKIPPED][:3]
    if skipped_examples:
        print("\n  Exemples d'éléments SKIPPED:")
        for cmd_id, result in skipped_examples:
            print(f"    - {cmd_id}: {result.get('error', 'N/A')}")


if __name__ == "__main__":
    # Créer le dossier reports
    Path("reports").mkdir(exist_ok=True)
    
    demo_excel_export_complete()
