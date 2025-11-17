"""
Processeur de soumissions de canaux

Gère le traitement automatique:
1. Validation des fichiers
2. Chargement des données
3. Exécution des DQ
4. Génération des rapports
5. Envoi des emails
"""

import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import pandas as pd

from src.core.models_channels import (
    ChannelSubmission, SubmissionStatus, DropChannel, FileMapping, DataSourceType
)
from src.core.channel_manager import ChannelManager
from src.core.dq_parser import load_dq_config
from src.core.sequencer import DQSequencer
from src.core.dependency_executor import DQExecutor, ExecutionStatus
from src.core.excel_exporter import DQExcelExporter
from src.connectors.factory import ConnectorFactory
from src.core.script_executor import execute_scripts


class SubmissionProcessor:
    """Processeur de soumissions"""
    
    def __init__(self, channel_manager: ChannelManager):
        self.channel_manager = channel_manager
        self.reports_dir = Path("reports/channel_submissions")
        self.reports_dir.mkdir(parents=True, exist_ok=True)
    
    def process_submission(self, submission: ChannelSubmission) -> ChannelSubmission:
        """
        Traite une soumission complète
        
        Étapes:
        1. Valider les fichiers
        2. Charger les données
        3. Exécuter les DQ
        4. Générer le rapport
        5. Envoyer les emails
        """
        try:
            # Mise à jour du statut
            submission.status = SubmissionStatus.PROCESSING
            submission.processing_started_at = datetime.now()
            self.channel_manager.update_submission(submission)
            
            # Récupérer le canal
            channel = self.channel_manager.get_channel(submission.channel_id)
            if not channel:
                raise ValueError(f"Canal {submission.channel_id} introuvable")
            
            # 1. Validation des fichiers
            print(f"[{submission.submission_id}] Validation des fichiers...")
            validation_ok, validation_errors = self._validate_files(submission, channel)
            
            if not validation_ok:
                submission.status = SubmissionStatus.ERROR
                submission.errors.extend(validation_errors)
                submission.processing_completed_at = datetime.now()
                self.channel_manager.update_submission(submission)
                return submission
            
            # 2. Chargement des données
            print(f"[{submission.submission_id}] Chargement des données...")
            datasets = self._load_datasets(submission, channel)
            
            # 3. Exécution des DQ
            print(f"[{submission.submission_id}] Exécution des contrôles qualité...")
            dq_results = self._execute_dq_checks(submission, channel, datasets)
            
            # 4. Génération du rapport
            print(f"[{submission.submission_id}] Génération du rapport Excel...")
            report_path = self._generate_report(submission, channel, dq_results)
            submission.dq_report_path = str(report_path)
            
            # 5. Déterminer le statut final
            if submission.dq_failed > 0:
                # Si des tests DQ échouent, le dépôt est REJETÉ
                submission.status = SubmissionStatus.REJECTED
            elif submission.dq_skipped > 0:
                # Si des tests sont skipped, DQ failed mais pas rejeté
                submission.status = SubmissionStatus.DQ_FAILED
            else:
                # Tous les tests passent
                submission.status = SubmissionStatus.DQ_SUCCESS
            
            submission.processing_completed_at = datetime.now()
            self.channel_manager.update_submission(submission)
            
            # 6. Envoyer les emails
            print(f"[{submission.submission_id}] Envoi des notifications...")
            self._send_notifications(submission, channel)
            
            return submission
            
        except Exception as e:
            print(f"[{submission.submission_id}] Erreur: {e}")
            submission.status = SubmissionStatus.ERROR
            submission.errors.append(str(e))
            submission.processing_completed_at = datetime.now()
            self.channel_manager.update_submission(submission)
            return submission
    
    def _validate_files(self, submission: ChannelSubmission, 
                       channel: DropChannel) -> tuple[bool, list]:
        """Valide que tous les fichiers requis sont fournis"""
        errors = []
        
        # Vérifier que tous les fichiers requis sont mappés
        required_specs = {fs.file_id: fs for fs in channel.file_specifications if fs.required}
        provided_ids = {fm.file_spec_id for fm in submission.file_mappings}
        
        missing = set(required_specs.keys()) - provided_ids
        if missing:
            for file_id in missing:
                spec = required_specs[file_id]
                errors.append(f"Fichier requis manquant: {spec.name} ({file_id})")
        
        # TODO: Validation du format, des colonnes, etc.
        
        return len(errors) == 0, errors
    
    def _load_datasets(self, submission: ChannelSubmission, 
                      channel: DropChannel) -> Dict[str, pd.DataFrame]:
        """Charge les datasets depuis les fichiers fournis via les connecteurs appropriés"""
        datasets = {}
        
        for file_mapping in submission.file_mappings:
            # Trouver la spécification
            spec = next((fs for fs in channel.file_specifications 
                        if fs.file_id == file_mapping.file_spec_id), None)
            
            if not spec:
                continue
            
            try:
                # Utiliser le connecteur approprié selon le type de source
                source_type = spec.source_type
                
                # Préparer les paramètres de connexion
                connection_params = spec.connection_params.copy()
                
                # Pour LOCAL, on utilise le chemin fourni lors du dépôt
                if source_type == DataSourceType.LOCAL:
                    connection_params['file_path'] = file_mapping.provided_path
                    connection_params['format'] = spec.format.value
                
                # Créer le connecteur
                connector = ConnectorFactory.create_connector(source_type, connection_params)
                
                # Valider et charger les données
                is_valid, error_msg = connector.validate_connection()
                if not is_valid:
                    raise ValueError(f"Connexion invalide: {error_msg}")
                
                # Charger les données
                df = connector.fetch_data()
                
                # Optionnel: Valider les colonnes attendues
                if spec.schema_validation and spec.expected_columns:
                    missing_cols = set(spec.expected_columns) - set(df.columns)
                    if missing_cols:
                        raise ValueError(f"Colonnes manquantes: {missing_cols}")
                
                datasets[spec.file_id] = df
                file_mapping.validated = True
                
                print(f"  ✅ {spec.name}: {len(df)} lignes chargées via {source_type.value}")
                
            except Exception as e:
                file_mapping.validation_errors.append(str(e))
                submission.errors.append(
                    f"Erreur chargement {spec.name} ({spec.source_type.value}): {e}"
                )
                print(f"  ❌ Erreur {spec.name}: {e}")
        
        return datasets
        
        return datasets
    
    def _execute_dq_checks(self, submission: ChannelSubmission,
                          channel: DropChannel,
                          datasets: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Exécute les contrôles DQ configurés pour le canal"""
        
        if not channel.dq_configs:
            print(f"  Aucune configuration DQ définie pour ce canal")
            return {}
        
        all_results = {}
        total_passed = 0
        total_failed = 0
        total_skipped = 0
        
        for dq_config_path in channel.dq_configs:
            try:
                print(f"  Exécution DQ: {dq_config_path}")
                
                # Charger la config DQ
                config = load_dq_config(dq_config_path)
                
                # Convertir DQConfig en DQDefinition pour le parser
                from src.core.models_dq import DQDefinition
                
                dq_def_data = {
                    'id': config.id,
                    'label': config.label,
                    'databases': [{'alias': alias} for alias in datasets.keys()],
                    'metrics': {},
                    'tests': {},
                    'scripts': [s.model_dump() for s in config.scripts]
                }
                
                # Convertir metrics (DQConfig uses dataclass Metric objects)
                for metric_id, metric_obj in config.metrics.items():
                    dq_def_data['metrics'][metric_id] = {
                        'id': metric_id,
                        'type': metric_obj.type,
                        'specific': metric_obj.specific
                    }
                
                # Convertir tests (DQConfig uses dataclass Test objects)
                for test_id, test_obj in config.tests.items():
                    dq_def_data['tests'][test_id] = {
                        'id': test_id,
                        'type': test_obj.type,
                        'specific': test_obj.specific
                    }
                
                dq_definition = DQDefinition(**dq_def_data)
                
                # Préparer le loader de datasets
                def loader(alias: str):
                    if alias in datasets:
                        return datasets[alias]
                    raise ValueError(f"Dataset {alias} non trouvé")
                
                # Construire le plan d'exécution
                from src.core.parser import build_execution_plan
                from src.core.models_inventory import Inventory
                
                # Créer un inventaire minimal pour le parser
                inv_data = {
                    'streams': [],
                    'datasets': [{'alias': alias, 'path': f'memory://{alias}'} for alias in datasets.keys()]
                }
                inv = Inventory(**inv_data)
                
                # Construire le plan avec les overrides
                overrides = {alias: f'memory://{alias}' for alias in datasets.keys()}
                plan = build_execution_plan(inv, dq_definition, overrides=overrides)
                
                # Exécuter le plan
                from src.core.executor import execute
                run_result = execute(plan, loader, investigate=False)
                
                # Exécuter les scripts si présents
                script_results = []
                if config.scripts:
                    print(f"  Exécution de {len(config.scripts)} script(s)")
                    
                    # Créer un contexte pour les scripts (simple loader)
                    class ScriptContext:
                        def __init__(self, loader_func):
                            self.loader_func = loader_func
                        
                        def load(self, alias):
                            return self.loader_func(alias)
                    
                    script_ctx = ScriptContext(loader)
                    script_results = execute_scripts(config.scripts, script_ctx, execute_phase="post_dq")
                
                # Compter les résultats des tests DQ
                total_passed += sum(1 for t in run_result.tests.values() if t.passed)
                total_failed += sum(1 for t in run_result.tests.values() if not t.passed)
                
                # Compter les résultats des scripts
                for script_result in script_results:
                    if script_result.status == "success" or script_result.status == "failed":
                        for test_id, test_data in script_result.tests.items():
                            if test_data.get('status') == 'passed':
                                total_passed += 1
                            else:
                                total_failed += 1
                
                all_results[dq_config_path] = {
                    'metrics': {k: v.model_dump() for k, v in run_result.metrics.items()},
                    'tests': {k: v.model_dump() for k, v in run_result.tests.items()},
                    'scripts': [s.to_dict() for s in script_results],
                    'passed': sum(1 for t in run_result.tests.values() if t.passed) + sum(1 for s in script_results for t in s.tests.values() if t.get('status') == 'passed'),
                    'failed': sum(1 for t in run_result.tests.values() if not t.passed) + sum(1 for s in script_results for t in s.tests.values() if t.get('status') != 'passed')
                }
                
            except Exception as e:
                print(f"  Erreur DQ {dq_config_path}: {e}")
                submission.errors.append(f"Erreur DQ {dq_config_path}: {e}")
        
        # Mettre à jour les statistiques
        submission.dq_total = total_passed + total_failed + total_skipped
        submission.dq_passed = total_passed
        submission.dq_failed = total_failed
        submission.dq_skipped = total_skipped
        submission.dq_execution_results = {
            'total': submission.dq_total,
            'passed': submission.dq_passed,
            'failed': submission.dq_failed,
            'skipped': submission.dq_skipped
        }
        
        return all_results
    
    def _generate_report(self, submission: ChannelSubmission,
                        channel: DropChannel,
                        dq_results: Dict[str, Any]) -> Path:
        """Génère le rapport Excel"""
        
        # Nom du fichier
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_name = f"{channel.channel_id}_{submission.submission_id}_{timestamp}.xlsx"
        report_path = self.reports_dir / report_name
        
        # Si pas de DQ exécutée, créer un rapport simple
        if not dq_results:
            # Créer un rapport de base avec pandas
            summary_data = {
                'Canal': [channel.name],
                'Équipe': [channel.team_name],
                'Date soumission': [submission.submitted_at.strftime("%Y-%m-%d %H:%M:%S")],
                'Fichiers soumis': [len(submission.file_mappings)],
                'Statut': [submission.status.value]
            }
            df = pd.DataFrame(summary_data)
            df.to_excel(report_path, sheet_name='Résumé', index=False)
            return report_path
        
        # Générer un rapport Excel avec les résultats DQ et scripts
        with pd.ExcelWriter(report_path, engine='openpyxl') as writer:
            # Onglet Résumé
            summary_data = {
                'Canal': [channel.name],
                'Équipe': [channel.team_name],
                'Date soumission': [submission.submitted_at.strftime("%Y-%m-%d %H:%M:%S")],
                'Fichiers soumis': [len(submission.file_mappings)],
                'Statut': [submission.status.value],
                'Tests totaux': [submission.dq_total],
                'Tests réussis': [submission.dq_passed],
                'Tests échoués': [submission.dq_failed]
            }
            df_summary = pd.DataFrame(summary_data)
            df_summary.to_excel(writer, sheet_name='Résumé', index=False)
            
            # Onglet Tests (DQ et scripts)
            test_rows = []
            for dq_path, dq_data in dq_results.items():
                dq_name = Path(dq_path).stem
                
                # Tests DQ
                for test_id, test_data in dq_data.get('tests', {}).items():
                    test_rows.append({
                        'DQ': dq_name,
                        'Type': 'DQ Test',
                        'Test ID': test_id,
                        'Status': 'PASS' if test_data.get('passed') else 'FAIL',
                        'Message': test_data.get('message', ''),
                        'Details': str(test_data.get('context', ''))
                    })
                
                # Tests scripts
                for script_data in dq_data.get('scripts', []):
                    script_id = script_data.get('script_id', 'unknown')
                    for test_id, test_info in script_data.get('tests', {}).items():
                        test_rows.append({
                            'DQ': dq_name,
                            'Type': f'Script ({script_id})',
                            'Test ID': test_id,
                            'Status': test_info.get('status', 'unknown').upper(),
                            'Message': test_info.get('message', ''),
                            'Details': f"Value: {test_info.get('value', 'N/A')}, Threshold: {test_info.get('threshold', 'N/A')}"
                        })
            
            if test_rows:
                df_tests = pd.DataFrame(test_rows)
                df_tests.to_excel(writer, sheet_name='Tests', index=False)
            
            # Onglet Métriques
            metric_rows = []
            for dq_path, dq_data in dq_results.items():
                dq_name = Path(dq_path).stem
                
                # Métriques DQ
                for metric_id, metric_data in dq_data.get('metrics', {}).items():
                    metric_rows.append({
                        'DQ': dq_name,
                        'Type': 'DQ Metric',
                        'Metric ID': metric_id,
                        'Value': metric_data.get('value', 'N/A'),
                        'Status': metric_data.get('status', 'N/A'),
                        'Details': str(metric_data.get('context', ''))
                    })
                
                # Métriques scripts
                for script_data in dq_data.get('scripts', []):
                    script_id = script_data.get('script_id', 'unknown')
                    for metric_name, metric_value in script_data.get('metrics', {}).items():
                        metric_rows.append({
                            'DQ': dq_name,
                            'Type': f'Script ({script_id})',
                            'Metric ID': metric_name,
                            'Value': metric_value,
                            'Status': 'Calculated',
                            'Details': ''
                        })
            
            if metric_rows:
                df_metrics = pd.DataFrame(metric_rows)
                df_metrics.to_excel(writer, sheet_name='Métriques', index=False)
            
            # Onglet Scripts
            script_rows = []
            for dq_path, dq_data in dq_results.items():
                dq_name = Path(dq_path).stem
                for script_data in dq_data.get('scripts', []):
                    script_rows.append({
                        'DQ': dq_name,
                        'Script ID': script_data.get('script_id', 'unknown'),
                        'Status': script_data.get('status', 'unknown').upper(),
                        'Duration (s)': script_data.get('duration', 0),
                        'Error': script_data.get('error', ''),
                        'Metrics Count': len(script_data.get('metrics', {})),
                        'Tests Count': len(script_data.get('tests', {})),
                        'Timestamp': script_data.get('timestamp', '')
                    })
            
            if script_rows:
                df_scripts = pd.DataFrame(script_rows)
                df_scripts.to_excel(writer, sheet_name='Scripts', index=False)
        
        return report_path
    
    def _send_notifications(self, submission: ChannelSubmission,
                           channel: DropChannel):
        """Envoie les notifications par email"""
        
        # Pour l'instant, on simule l'envoi
        # TODO: Implémenter vraie logique d'envoi email
        
        email_config = channel.email_config
        
        # Préparer les variables pour les templates
        template_vars = {
            'channel_name': channel.name,
            'submission_date': submission.submitted_at.strftime("%Y-%m-%d %H:%M:%S"),
            'file_count': len(submission.file_mappings),
            'dq_total': submission.dq_total,
            'dq_passed': submission.dq_passed,
            'dq_failed': submission.dq_failed
        }
        
        if submission.status == SubmissionStatus.DQ_SUCCESS:
            subject = email_config.success_subject.format(**template_vars)
            body = email_config.success_body_template.format(**template_vars)
            recipients = email_config.recipient_team_emails + email_config.admin_emails
        else:
            subject = email_config.failure_subject.format(**template_vars)
            body = email_config.failure_body_template.format(**template_vars)
            recipients = email_config.recipient_team_emails
        
        print(f"  📧 Email envoyé:")
        print(f"     À: {', '.join(recipients)}")
        print(f"     Sujet: {subject}")
        print(f"     Pièce jointe: {submission.dq_report_path}")
        
        submission.email_sent = True
        submission.email_sent_at = datetime.now()
