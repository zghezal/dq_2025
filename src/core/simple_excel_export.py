"""
Export unifié des résultats DQ vers Excel
Utilisé partout dans l'application (Builder, Runner, Channels)

Format standardisé avec onglets:
- Résumé (contexte général)
- Métriques (toutes les métriques)
- Tests (tous les tests)
- Un onglet par métrique avec ses détails
- Un onglet par test avec ses détails
- Un onglet d'investigation par test KO (hors scripts)
"""

import pandas as pd
from pathlib import Path
from typing import Optional, Dict, Any
from src.core.executor import RunResult


def export_run_result_to_excel(
    run_result: RunResult,
    output_path: str,
    dq_id: Optional[str] = None,
    quarter: Optional[str] = None,
    project: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
):
    """
    Exporte les résultats d'une exécution DQ vers Excel (format unifié)
    
    Args:
        run_result: Résultat de l'exécution DQ
        output_path: Chemin du fichier Excel de sortie
        dq_id: ID de la définition DQ
        quarter: Trimestre (ex: 2025Q4)
        project: Nom du projet
        context: Contexte additionnel (canal, équipe, etc.)
    """
    
    context = context or {}
    
    # Compter les métriques calculées
    metrics_computed = sum(1 for r in run_result.metrics.values() if r.passed is not False)
    
    # ===== ONGLET RÉSUMÉ =====
    summary_data = {
        'DQ_ID': dq_id or context.get('canal', 'N/A'),
        'Quarter': quarter or context.get('submission_date', 'N/A'),
        'Project': project or context.get('equipe', 'N/A'),
        'Run_ID': run_result.run_id,
        'Total_Metrics': len(run_result.metrics),
        'Metrics_Computed': metrics_computed,
        'Total_Tests': len(run_result.tests),
        'Scripts_Executed': len(run_result.scripts),
        'Tests_Passed': sum(1 for r in run_result.tests.values() if r.passed),
        'Tests_Failed': sum(1 for r in run_result.tests.values() if not r.passed),
        'Status': 'SUCCESS' if sum(1 for r in run_result.tests.values() if not r.passed) == 0 else 'FAILED',
        'Investigations': len(run_result.investigations),
        'Investigation_Report': 'Yes' if run_result.investigation_report else 'No'
    }
    
    # Ajouter contexte canal si disponible
    if 'canal' in context:
        summary_data['Canal'] = context['canal']
    if 'equipe' in context:
        summary_data['Équipe'] = context['equipe']
    if 'submission_id' in context:
        summary_data['Submission_ID'] = context['submission_id']
    
    df_summary = pd.DataFrame([summary_data])
    
    # ===== ONGLET MÉTRIQUES =====
    metrics_rows = []
    for metric_id, result in run_result.metrics.items():
        # Construire description des paramètres depuis meta
        param_desc = ""
        if result.meta:
            params = []
            if result.meta.get('type'):
                params.append(f"type={result.meta['type']}")
            if result.meta.get('dataset'):
                params.append(f"dataset={result.meta['dataset']}")
            if result.meta.get('column'):
                params.append(f"column={result.meta['column']}")
            if result.meta.get('group_by'):
                params.append(f"group_by={result.meta['group_by']}")
            if result.meta.get('filter'):
                params.append(f"filter={result.meta['filter']}")
            param_desc = ", ".join(params)
        
        row = {
            'DQ_ID': dq_id or context.get('canal', 'N/A'),
            'Quarter': quarter or 'N/A',
            'Project': project or 'N/A',
            'Metric_ID': metric_id,
            'Status': 'COMPUTED' if result.passed is not False else 'NOT_COMPUTED',
            'Message': result.message or ('Computed successfully' if result.passed is not False else 'Computation failed'),
            'Run_ID': run_result.run_id,
            'Description_des_parametres': param_desc
        }
        
        metrics_rows.append(row)
    
    df_metrics = pd.DataFrame(metrics_rows) if metrics_rows else pd.DataFrame()
    
    # ===== ONGLET TESTS =====
    tests_rows = []
    for test_id, result in run_result.tests.items():
        # Récupérer métadonnées
        test_type = result.meta.get('test_type', 'standard') if result.meta else 'standard'
        criticality = result.meta.get('criticality', 'medium') if result.meta else 'medium'
        metric_ref = result.meta.get('metric', 'N/A') if result.meta else 'N/A'
        
        row = {
            'DQ_ID': dq_id or context.get('canal', 'N/A'),
            'Quarter': quarter or 'N/A',
            'Project': project or 'N/A',
            'Test_ID': test_id,
            'Test_Type': test_type,
            'Metric_Ref': metric_ref,
            'Criticality': criticality,
            'Value': result.value,
            'Status': 'PASSED' if result.passed else 'FAILED',
            'Message': result.message or '',
            'Run_ID': run_result.run_id,
            'Investigation': 'Yes' if result.investigation else 'No'
        }
        
        tests_rows.append(row)
    
    df_tests = pd.DataFrame(tests_rows) if tests_rows else pd.DataFrame()
    
    # ===== ONGLETS DÉTAILS MÉTRIQUES (un onglet par métrique) =====
    metric_detail_sheets = {}
    for metric_id, result in run_result.metrics.items():
        # Nettoyer le nom de l'onglet (max 31 caractères pour Excel)
        sheet_name = f"M_{metric_id}"
        if len(sheet_name) > 31:
            sheet_name = sheet_name[:31]
        
        # Créer un DataFrame avec les détails de la métrique
        detail_data = {
            'Metric_ID': [metric_id],
            'Value': [result.value],
            'Status': ['COMPUTED' if result.passed is not False else 'NOT_COMPUTED'],
            'Message': [result.message or ''],
            'Passed': [result.passed]
        }
        
        # Ajouter les métadonnées
        if result.meta:
            for key, val in result.meta.items():
                detail_data[f'Meta_{key}'] = [val]
        
        df_detail = pd.DataFrame(detail_data)
        metric_detail_sheets[sheet_name] = df_detail
    
    # ===== ONGLETS DÉTAILS TESTS (un onglet par test) =====
    test_detail_sheets = {}
    for test_id, result in run_result.tests.items():
        # Nettoyer le nom de l'onglet
        sheet_name = f"T_{test_id}"
        if len(sheet_name) > 31:
            sheet_name = sheet_name[:31]
        
        # Créer un DataFrame avec les détails du test
        detail_data = {
            'Test_ID': [test_id],
            'Value': [result.value],
            'Status': ['PASSED' if result.passed else 'FAILED'],
            'Message': [result.message or ''],
            'Passed': [result.passed],
            'Investigation': ['Yes' if result.investigation else 'No']
        }
        
        # Ajouter les métadonnées
        if result.meta:
            for key, val in result.meta.items():
                detail_data[f'Meta_{key}'] = [val]
        
        df_detail = pd.DataFrame(detail_data)
        test_detail_sheets[sheet_name] = df_detail
    
    # ===== ONGLETS INVESTIGATIONS (tests KO uniquement, hors scripts) =====
    investigation_sheets = {}
    if run_result.investigations:
        for inv_key, inv_data in run_result.investigations.items():
            # Vérifier que c'est un DataFrame et non vide
            if isinstance(inv_data, pd.DataFrame) and not inv_data.empty:
                # Vérifier si c'est un test script (on les exclut)
                is_script_test = 'script' in inv_key.lower()
                
                if not is_script_test:
                    # Limiter à 1000 lignes par investigation
                    df_inv = inv_data.head(1000).copy()
                    
                    # Nettoyer le nom de l'onglet
                    sheet_name = f"Inv_{inv_key}"
                    if len(sheet_name) > 31:
                        sheet_name = sheet_name[:31]
                    
                    investigation_sheets[sheet_name] = df_inv
    
    # ===== ÉCRITURE EXCEL =====
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # 1. Résumé
        df_summary.to_excel(writer, sheet_name='Résumé', index=False)
        
        # 2. Métriques
        if not df_metrics.empty:
            df_metrics.to_excel(writer, sheet_name='Métriques', index=False)
        
        # 3. Tests
        if not df_tests.empty:
            df_tests.to_excel(writer, sheet_name='Tests', index=False)
        
        # 4. Détails métriques (un onglet par métrique)
        for sheet_name, df_detail in metric_detail_sheets.items():
            df_detail.to_excel(writer, sheet_name=sheet_name, index=False)
        
        # 5. Détails tests (un onglet par test)
        for sheet_name, df_detail in test_detail_sheets.items():
            df_detail.to_excel(writer, sheet_name=sheet_name, index=False)
        
        # 6. Investigations (tests KO hors scripts)
        for sheet_name, df_inv in investigation_sheets.items():
            df_inv.to_excel(writer, sheet_name=sheet_name, index=False)
    
    print(f"✅ Export Excel créé: {output_path}")
    print(f"   - {len(run_result.metrics)} métriques")
    print(f"   - {len(run_result.tests)} tests")
    print(f"   - {len(metric_detail_sheets)} onglet(s) détail métrique")
    print(f"   - {len(test_detail_sheets)} onglet(s) détail test")
    print(f"   - {len(investigation_sheets)} investigation(s)")
    
    return output_path
