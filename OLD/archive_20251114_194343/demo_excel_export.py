"""
Démonstration de l'export Excel des résultats DQ avec gestion des dépendances

Ce script simule une exécution de métriques et tests avec gestion automatique
des dépendances (SKIPPED), puis génère un rapport Excel.
"""

from datetime import datetime
import random
from src.core.dq_parser import load_dq_config
from src.core.sequencer import DQSequencer, CommandType
from src.core.dependency_executor import DQExecutor, ExecutionStatus
from src.core.excel_exporter import export_execution_results
import pandas as pd


def create_metric_dataframe(cmd):
    """
    Crée un DataFrame simulé pour une métrique
    """
    # Récupérer les paramètres
    specific = cmd.parameters
    columns = specific.get('column', [])
    
    # Si column n'est pas une liste, la convertir
    if isinstance(columns, str):
        columns = [columns]
    elif not columns:
        columns = ['value']
    
    # Créer des données simulées
    data = {}
    for col in columns:
        data[f'{col}_missing_rate'] = [round(random.uniform(0, 0.1), 4)]
        data[f'{col}_missing_number'] = [random.randint(0, 50)]
    
    return pd.DataFrame(data)


def simulate_execution_with_dependencies(sequence):
    """
    Simule l'exécution avec gestion automatique des dépendances
    """
    
    def execute_command(cmd):
        """Fonction d'exécution simulée"""
        rand = random.random()
        
        if cmd.command_type == CommandType.METRIC:
            # Métriques : 90% succès
            if rand > 0.1:
                df_result = create_metric_dataframe(cmd)
                return {
                    'status': ExecutionStatus.SUCCESS,
                    'value': round(random.uniform(0, 0.1), 4),
                    'dataframe': df_result,
                    'error': '',
                }
            else:
                return {
                    'status': ExecutionStatus.ERROR,
                    'value': None,
                    'dataframe': None,
                    'error': 'Dataset not found or connection error',
                }
        
        elif cmd.command_type == CommandType.TEST:
            # Tests : 85% succès
            if rand > 0.15:
                passed = rand > 0.3
                return {
                    'status': ExecutionStatus.SUCCESS if passed else ExecutionStatus.FAIL,
                    'result': 'PASS' if passed else 'FAIL',
                    'error': '' if passed else 'Value outside bounds',
                }
            else:
                return {
                    'status': ExecutionStatus.ERROR,
                    'result': 'ERROR',
                    'error': 'Test execution failed',
                }
        
        else:  # Tests implicites
            # Tests techniques : 95% succès
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
                    'error': 'Technical validation failed',
                }
    
    # Utiliser DQExecutor pour gérer les dépendances
    executor = DQExecutor(sequence)
    results = executor.execute(execute_command, skip_on_dependency_failure=True)
    
    return results, executor


def demo_excel_export():
    """Démonstration complète de l'export Excel"""
    
    print("=" * 80)
    print("DÉMONSTRATION DE L'EXPORT EXCEL DQ")
    print("=" * 80)
    
    # 1. Charger la configuration
    print("\n📝 Chargement de la configuration...")
    config = load_dq_config("dq/definitions/sales_complete_quality.yaml")
    print(f"   Config: {config.label}")
    print(f"   Métriques: {len(config.metrics)}")
    print(f"   Tests: {len(config.tests)}")
    
    # 2. Construire la séquence
    print("\n🔄 Construction de la séquence d'exécution...")
    sequencer = DQSequencer(config)
    sequence = sequencer.build_sequence()
    print(f"   Total commandes: {len(sequence.commands)}")
    
    # 3. Simuler l'exécution avec dépendances
    print("\n⚙️  Simulation de l'exécution...")
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
    print("\n📊 Génération du rapport Excel...")
    output_path = "reports/dq_execution_report.xlsx"
    
    export_execution_results(
        sequence=sequence,
        execution_results=execution_results,
        output_path=output_path,
        quarter="Q4 2025",
        project="Sales Data Quality",
        run_version="v1.0.0",
        user="admin"
    )
    
    print("\n" + "=" * 80)
    print("✨ Démonstration terminée!")
    print("=" * 80)
    print(f"\n📁 Fichier généré: {output_path}")
    print("\nOnglets créés:")
    print("  1. Métriques - Statut d'exécution (SUCCESS, ERROR, SKIPPED) et valeurs")
    print("  2. Tests - Résultats détaillés (PASS, FAIL, ERROR, SKIPPED) avec tracking")
    print(f"  3-N. Données des métriques (export=True)")
    
    # Afficher les SKIPPED s'il y en a
    if summary.get(ExecutionStatus.SKIPPED, 0) > 0:
        print(f"\n⚠️  {summary[ExecutionStatus.SKIPPED]} élément(s) SKIPPED (dépendances échouées)")
    
    print("\n💡 Ouvrez le fichier Excel pour voir le résultat !")


if __name__ == "__main__":
    # Créer le dossier reports si nécessaire
    from pathlib import Path
    Path("reports").mkdir(exist_ok=True)
    
    demo_excel_export()
