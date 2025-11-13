"""
Export Excel pour les résultats d'exécution DQ

Ce module génère un fichier Excel avec 2 onglets :
- Métriques : Statut d'exécution et détails des métriques
- Tests : Résultats des tests avec tracking complet
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import pandas as pd
from pathlib import Path

from src.core.sequencer import ExecutionSequence, ExecutionCommand, CommandType, ImplicitTestType


class DQExcelExporter:
    """Générateur de rapport Excel pour l'exécution DQ"""
    
    def __init__(self, sequence: ExecutionSequence, execution_results: Dict[str, Any]):
        """
        Args:
            sequence: Séquence d'exécution DQ
            execution_results: Résultats d'exécution {command_id: result_dict}
        """
        self.sequence = sequence
        self.execution_results = execution_results
        self.timestamp = datetime.now()
    
    def generate_excel(
        self, 
        output_path: str,
        quarter: Optional[str] = None,
        project: Optional[str] = None,
        run_version: Optional[str] = None,
        user: Optional[str] = None
    ):
        """
        Génère le fichier Excel complet
        
        Args:
            output_path: Chemin du fichier Excel de sortie
            quarter: Trimestre (Q1 2025, Q2 2025, etc.)
            project: Nom du projet
            run_version: Version du run
            user: Utilisateur ayant lancé l'exécution
        """
        # Créer les DataFrames
        df_metrics = self._build_metrics_dataframe()
        df_tests = self._build_tests_dataframe(
            quarter=quarter,
            project=project,
            run_version=run_version,
            user=user
        )
        
        # Écrire dans Excel
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            df_metrics.to_excel(writer, sheet_name='Métriques', index=False)
            df_tests.to_excel(writer, sheet_name='Tests', index=False)
            
            # Formater les colonnes
            self._format_worksheet(writer, 'Métriques', df_metrics)
            self._format_worksheet(writer, 'Tests', df_tests)
            
            # Exporter les données des métriques si export=True
            exported_count = self._export_metrics_data(writer)
        
        print(f"✅ Rapport Excel généré: {output_path}")
        print(f"   - {len(df_metrics)} métriques")
        print(f"   - {len(df_tests)} tests")
        if exported_count > 0:
            print(f"   - {exported_count} onglets de données exportés")
    
    def _build_metrics_dataframe(self) -> pd.DataFrame:
        """Construit le DataFrame des métriques avec statut d'exécution"""
        
        rows = []
        
        for cmd in self.sequence.commands:
            if cmd.command_type != CommandType.METRIC:
                continue
            
            # Récupérer les métadonnées
            identification = cmd.metadata.get('identification', {})
            nature = cmd.metadata.get('nature', {})
            general = cmd.metadata.get('general', {})
            specific = cmd.parameters
            
            # Résultat d'exécution
            result = self.execution_results.get(cmd.command_id, {})
            execution_status = result.get('status', 'NOT_RUN')
            error_message = result.get('error', '')
            value = result.get('value', None)
            
            row = {
                # Colonnes de visualisation
                'ID': identification.get('metric_id', cmd.element_id),
                'Type': cmd.element_type,
                'Name': nature.get('name', ''),
                'Description': nature.get('description', ''),
                'Comments': nature.get('comments', ''),
                'Export': general.get('export', True),
                'Owner': general.get('owner', ''),
                
                # Paramètres spécifiques
                'Dataset': specific.get('dataset', ''),
                'Column': specific.get('column', ''),
                'Filter': specific.get('filter', ''),
                
                # Statut d'exécution
                'Execution_Status': execution_status,
                'Value': value,
                'Error': error_message,
                'Timestamp': result.get('timestamp', self.timestamp)
            }
            
            rows.append(row)
        
        df = pd.DataFrame(rows)
        
        # Ordre des colonnes
        columns_order = [
            'ID', 'Type', 'Name', 'Description', 'Comments', 
            'Export', 'Owner', 'Dataset', 'Column', 'Filter',
            'Execution_Status', 'Value', 'Error', 'Timestamp'
        ]
        
        # Garder seulement les colonnes qui existent
        columns_order = [c for c in columns_order if c in df.columns]
        
        return df[columns_order] if not df.empty else pd.DataFrame(columns=columns_order)
    
    def _build_tests_dataframe(
        self,
        quarter: Optional[str] = None,
        project: Optional[str] = None,
        run_version: Optional[str] = None,
        user: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Construit le DataFrame des tests avec tracking complet
        
        Inclut tous les tests : normaux + implicites (techniques)
        """
        
        rows = []
        
        for cmd in self.sequence.commands:
            # Inclure tests normaux ET tests implicites
            if cmd.command_type not in [CommandType.TEST, CommandType.IMPLICIT_TEST]:
                continue
            
            # Récupérer les métadonnées
            identification = cmd.metadata.get('identification', {})
            nature = cmd.metadata.get('nature', {})
            general = cmd.metadata.get('general', {})
            specific = cmd.parameters
            
            # Résultat d'exécution
            result = self.execution_results.get(cmd.command_id, {})
            
            # Statut d'exécution (SUCCESS, FAIL, ERROR, SKIPPED)
            execution_status = result.get('status', 'NOT_RUN')
            
            # Pour les tests: SUCCESS = PASS, FAIL = FAIL, ERROR = ERROR, SKIPPED = SKIPPED
            if execution_status == 'SUCCESS':
                test_result = 'PASS'
            elif execution_status == 'FAIL':
                test_result = 'FAIL'
            elif execution_status == 'ERROR':
                test_result = 'ERROR'
            elif execution_status == 'SKIPPED':
                test_result = 'SKIPPED'
            else:
                test_result = result.get('result', 'NOT_RUN')
            
            error_message = result.get('error', '')
            
            # Dataset(s) testé(s)
            dataset = specific.get('value_from_dataset') or specific.get('dataset', '')
            
            # Catégorie
            if cmd.command_type == CommandType.IMPLICIT_TEST:
                # Test technique
                category = 'Technical'
                test_name = cmd.command_id
                control_id = f"TECH_{cmd.element_id}"
                description = cmd.metadata.get('description', f"Test technique: {cmd.element_type}")
                comments = f"Test implicite généré automatiquement"
            else:
                # Test normal
                category = nature.get('category', nature.get('functional_category_1', 'Business'))
                test_name = nature.get('name', identification.get('control_name', ''))
                control_id = identification.get('control_id', identification.get('test_id', ''))
                description = nature.get('description', '')
                comments = nature.get('comments', '')
            
            # Blocking
            blocking = general.get('stop_on_failure', False)
            
            row = {
                'quarter': quarter or self._get_quarter(),
                'project': project or '',
                'run_version': run_version or self._get_run_version(),
                'control_id': control_id,
                'dataset': dataset,
                'category': category,
                'blocking': 'Yes' if blocking else 'No',
                'execution_status': execution_status,  # Nouveau: statut d'exécution
                'result': test_result,
                'description': description,
                'comments': comments,
                'error': error_message,  # Nouveau: détails des erreurs
                'user': user or '',
                'timestamp': result.get('timestamp', self.timestamp)
            }
            
            rows.append(row)
        
        df = pd.DataFrame(rows)
        
        # Ordre des colonnes (avec les nouvelles colonnes execution_status et error)
        columns_order = [
            'quarter', 'project', 'run_version', 'control_id', 'dataset',
            'category', 'blocking', 'execution_status', 'result', 'description', 
            'comments', 'error', 'user', 'timestamp'
        ]
        
        return df[columns_order] if not df.empty else pd.DataFrame(columns=columns_order)
    
    def _export_metrics_data(self, writer) -> int:
        """
        Exporte les données des métriques dans des onglets séparés si export=True
        
        Args:
            writer: ExcelWriter object
            
        Returns:
            Nombre d'onglets de données exportés
        """
        exported_count = 0
        
        for cmd in self.sequence.commands:
            if cmd.command_type != CommandType.METRIC:
                continue
            
            # Vérifier si export est activé
            general = cmd.metadata.get('general', {})
            should_export = general.get('export', True)
            
            if not should_export:
                continue
            
            # Récupérer le DataFrame résultat
            result = self.execution_results.get(cmd.command_id, {})
            df_data = result.get('dataframe', None)
            
            # Si pas de dataframe ou vide, passer
            if df_data is None or (isinstance(df_data, pd.DataFrame) and df_data.empty):
                continue
            
            # Créer un nom d'onglet valide (Excel limite à 31 caractères)
            identification = cmd.metadata.get('identification', {})
            sheet_name = identification.get('metric_id', cmd.element_id)
            
            # Nettoyer le nom d'onglet (Excel n'accepte pas certains caractères)
            sheet_name = self._sanitize_sheet_name(sheet_name)
            
            # Limiter à 31 caractères
            if len(sheet_name) > 31:
                sheet_name = sheet_name[:28] + "..."
            
            try:
                # Écrire le DataFrame dans un nouvel onglet
                df_data.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # Formater l'onglet
                self._format_worksheet(writer, sheet_name, df_data)
                
                exported_count += 1
                
            except Exception as e:
                # En cas d'erreur (nom dupliqué, etc.), on continue
                print(f"   ⚠️  Impossible d'exporter {sheet_name}: {e}")
        
        return exported_count
    
    @staticmethod
    def _sanitize_sheet_name(name: str) -> str:
        """
        Nettoie un nom pour qu'il soit valide comme nom d'onglet Excel
        
        Excel n'accepte pas : : \\ / ? * [ ]
        """
        invalid_chars = [':', '\\', '/', '?', '*', '[', ']']
        cleaned = name
        for char in invalid_chars:
            cleaned = cleaned.replace(char, '_')
        return cleaned
    
    def _get_quarter(self) -> str:
        """Calcule le trimestre à partir de la date"""
        month = self.timestamp.month
        year = self.timestamp.year
        quarter = (month - 1) // 3 + 1
        return f"Q{quarter} {year}"
    
    def _get_run_version(self) -> str:
        """Génère un numéro de version de run"""
        return self.timestamp.strftime("%Y%m%d_%H%M%S")
    
    def _format_worksheet(self, writer, sheet_name: str, df: pd.DataFrame):
        """Formate une feuille Excel (largeur colonnes, etc.)"""
        if df.empty:
            return
        
        worksheet = writer.sheets[sheet_name]
        
        # Ajuster la largeur des colonnes
        for idx, col in enumerate(df.columns, 1):
            max_length = max(
                df[col].astype(str).apply(len).max(),
                len(str(col))
            )
            # Limiter à 50 caractères
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[self._get_column_letter(idx)].width = adjusted_width
    
    @staticmethod
    def _get_column_letter(col_idx: int) -> str:
        """Convertit un index de colonne en lettre Excel (1 -> A, 2 -> B, etc.)"""
        letter = ''
        while col_idx > 0:
            col_idx, remainder = divmod(col_idx - 1, 26)
            letter = chr(65 + remainder) + letter
        return letter


def export_execution_results(
    sequence: ExecutionSequence,
    execution_results: Dict[str, Any],
    output_path: str,
    **metadata
) -> str:
    """
    Fonction helper pour exporter facilement les résultats
    
    Args:
        sequence: Séquence d'exécution
        execution_results: Résultats d'exécution
        output_path: Chemin de sortie
        **metadata: quarter, project, run_version, user, etc.
    
    Returns:
        Chemin du fichier généré
    """
    exporter = DQExcelExporter(sequence, execution_results)
    exporter.generate_excel(output_path, **metadata)
    return output_path
