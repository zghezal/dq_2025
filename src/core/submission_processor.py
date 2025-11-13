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
            if submission.dq_failed > 0 or submission.dq_skipped > 0:
                submission.status = SubmissionStatus.DQ_FAILED
            else:
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
                
                # Construire la séquence
                sequencer = DQSequencer(config)
                sequence = sequencer.build_sequence()
                
                # Simuler l'exécution (à remplacer par vraie exécution)
                executor = DQExecutor(sequence)
                
                def execute_mock(cmd):
                    """Mock d'exécution - à remplacer par vraie logique"""
                    import random
                    rand = random.random()
                    
                    if rand > 0.15:
                        return {
                            'status': ExecutionStatus.SUCCESS,
                            'value': round(random.uniform(0, 0.1), 4),
                            'error': ''
                        }
                    else:
                        return {
                            'status': ExecutionStatus.ERROR,
                            'error': 'Simulation erreur'
                        }
                
                results = executor.execute(execute_mock, skip_on_dependency_failure=True)
                
                # Compter les résultats
                summary = executor.get_summary()
                total_passed += summary.get(ExecutionStatus.SUCCESS, 0)
                total_failed += summary.get(ExecutionStatus.FAIL, 0) + summary.get(ExecutionStatus.ERROR, 0)
                total_skipped += summary.get(ExecutionStatus.SKIPPED, 0)
                
                all_results[dq_config_path] = {
                    'sequence': sequence,
                    'results': results,
                    'summary': summary
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
        
        # Utiliser DQExcelExporter pour générer le rapport complet
        # (prendre la première config DQ pour l'exemple)
        first_dq = list(dq_results.values())[0]
        sequence = first_dq['sequence']
        results = first_dq['results']
        
        exporter = DQExcelExporter(
            sequence=sequence,
            execution_results=results
        )
        
        # Remplacer le timestamp de l'exporter
        exporter.timestamp = submission.submitted_at
        
        exporter.generate_excel(
            output_path=str(report_path),
            quarter=f"Soumission {submission.submission_id}",
            project=channel.name,
            run_version="1.0",
            user=submission.submitted_by
        )
        
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
