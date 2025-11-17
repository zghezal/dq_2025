"""
Export simple des résultats DQ vers Excel
Basé sur RunResult de src/core/executor.py

Note: Les scripts produisent uniquement des tests qui sont intégrés
dans l'onglet Tests principal (pas d'onglet Scripts séparé)
"""

import pandas as pd
from pathlib import Path
from typing import Optional
from src.core.executor import RunResult


def export_run_result_to_excel(
    run_result: RunResult,
    output_path: str,
    dq_id: Optional[str] = None,
    quarter: Optional[str] = None,
    project: Optional[str] = None
):
    """
    Exporte les résultats d'une exécution DQ vers Excel
    
    Args:
        run_result: Résultat de l'exécution DQ
        output_path: Chemin du fichier Excel de sortie
        dq_id: ID de la définition DQ
        quarter: Trimestre (ex: 2025Q4)
        project: Nom du projet
    
    Note: Les tests issus des scripts sont déjà intégrés dans run_result.tests
    """
    
    # ===== ONGLET MÉTRIQUES =====
    metrics_rows = []
    for metric_id, result in run_result.metrics.items():
        metrics_rows.append({
            'DQ_ID': dq_id or 'N/A',
            'Quarter': quarter or 'N/A',
            'Project': project or 'N/A',
            'Metric_ID': metric_id,
            'Value': result.value,
            'Status': 'SUCCESS' if result.passed is not False else 'FAILED',
            'Message': result.message or '',
            'Run_ID': run_result.run_id
        })
    
    # ===== ONGLET TESTS =====
    # Inclut les tests DQ automatiques ET les tests issus des scripts
    tests_rows = []
    for test_id, result in run_result.tests.items():
        # Récupérer le type de test depuis meta (si disponible)
        test_type = result.meta.get('test_type', 'standard') if result.meta else 'standard'
        criticality = result.meta.get('criticality', 'medium') if result.meta else 'medium'
        
        tests_rows.append({
            'DQ_ID': dq_id or 'N/A',
            'Quarter': quarter or 'N/A',
            'Project': project or 'N/A',
            'Test_ID': test_id,
            'Test_Type': test_type,
            'Criticality': criticality,
            'Value': result.value,
            'Status': 'PASSED' if result.passed else 'FAILED',
            'Message': result.message or '',
            'Run_ID': run_result.run_id,
            'Investigation': 'Yes' if result.investigation else 'No'
        })
    
    # ===== ONGLET RÉSUMÉ =====
    summary_rows = [{
        'DQ_ID': dq_id or 'N/A',
        'Quarter': quarter or 'N/A',
        'Project': project or 'N/A',
        'Run_ID': run_result.run_id,
        'Total_Metrics': len(run_result.metrics),
        'Total_Tests': len(run_result.tests),
        'Scripts_Executed': len(run_result.scripts),
        'Tests_Passed': sum(1 for r in run_result.tests.values() if r.passed),
        'Tests_Failed': sum(1 for r in run_result.tests.values() if not r.passed),
        'Investigations': len(run_result.investigations),
        'Investigation_Report': run_result.investigation_report
    }]
    
    # Créer les DataFrames
    df_summary = pd.DataFrame(summary_rows)
    df_metrics = pd.DataFrame(metrics_rows) if metrics_rows else pd.DataFrame()
    df_tests = pd.DataFrame(tests_rows) if tests_rows else pd.DataFrame()
    
    # Écrire dans Excel
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        df_summary.to_excel(writer, sheet_name='Résumé', index=False)
        
        if not df_metrics.empty:
            df_metrics.to_excel(writer, sheet_name='Métriques', index=False)
        
        if not df_tests.empty:
            df_tests.to_excel(writer, sheet_name='Tests', index=False)
    
    print(f"✅ Export Excel créé: {output_path}")
    print(f"   - {len(run_result.metrics)} métriques")
    print(f"   - {len(run_result.tests)} tests (dont tests issus de scripts)")
    
    return output_path
