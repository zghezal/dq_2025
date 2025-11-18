"""
Modèles de données pour le système de canaux de dépôt (Drop Channels)

Ce module définit les structures pour:
- Canaux de dépôt configurés par les admins
- Spécifications de fichiers attendus
- Soumissions par les équipes externes
- Résultats DQ et notifications
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum


class SubmissionStatus(Enum):
    """Statuts possibles d'une soumission"""
    PENDING = "pending"  # En attente de traitement
    PROCESSING = "processing"  # Traitement en cours
    DQ_SUCCESS = "dq_success"  # DQ réussie
    DQ_FAILED = "dq_failed"  # DQ échouée
    REJECTED = "rejected"  # Dépôt rejeté (échec critique)
    ERROR = "error"  # Erreur technique


class FileFormat(Enum):
    """Formats de fichiers acceptés"""
    CSV = "csv"
    EXCEL = "xlsx"
    PARQUET = "parquet"
    JSON = "json"
    TSV = "tsv"


class DataSourceType(Enum):
    """Types de sources de données supportés"""
    LOCAL = "local"  # Fichier local uploadé
    HUE = "hue"  # HUE (HDFS/Hive via HUE)
    SHAREPOINT = "sharepoint"  # SharePoint Online
    DATAIKU_DATASET = "dataiku_dataset"  # Dataset Dataiku existant


@dataclass
class FileSpecification:
    """
    Spécification d'un fichier attendu dans un canal
    """
    file_id: str  # Identifiant unique du fichier dans le canal
    name: str  # Nom descriptif
    description: str = ""
    format: FileFormat = FileFormat.CSV
    required: bool = True  # Fichier obligatoire ou optionnel
    pattern: Optional[str] = None  # Pattern regex pour le nom de fichier
    expected_columns: List[str] = field(default_factory=list)  # Colonnes attendues
    schema_validation: bool = False  # Valider le schéma strictement
    
    # Source de données
    source_type: DataSourceType = DataSourceType.LOCAL  # Type de source par défaut
    connection_params: Dict[str, Any] = field(default_factory=dict)  # Paramètres spécifiques à la source
    # Examples de connection_params par type:
    # LOCAL: {} (vide, upload direct)
    # HUE: {"hue_url": "http://hue.example.com", "path": "/user/data/file.csv", "auth_token": "..."}
    # SHAREPOINT: {"site_url": "https://tenant.sharepoint.com/sites/mysite", "folder_path": "/Shared Documents/Data", "file_name": "data.xlsx"}
    # DATAIKU_DATASET: {"project_key": "DKU_PROJECT", "dataset_name": "my_dataset"}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_id": self.file_id,
            "name": self.name,
            "description": self.description,
            "format": self.format.value,
            "required": self.required,
            "pattern": self.pattern,
            "expected_columns": self.expected_columns,
            "schema_validation": self.schema_validation,
            "source_type": self.source_type.value,
            "connection_params": self.connection_params
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FileSpecification':
        data_copy = data.copy()
        if 'format' in data_copy:
            data_copy['format'] = FileFormat(data_copy['format'])
        if 'source_type' in data_copy:
            data_copy['source_type'] = DataSourceType(data_copy['source_type'])
        return cls(**data_copy)


@dataclass
class EmailConfig:
    """Configuration des emails pour un canal"""
    recipient_team_emails: List[str] = field(default_factory=list)  # Emails équipe externe
    admin_emails: List[str] = field(default_factory=list)  # Emails admins (notification succès)
    cc_emails: List[str] = field(default_factory=list)  # En copie
    
    # Templates
    success_subject: str = "✅ Dépôt de données validé - {channel_name}"
    success_body_template: str = """
Bonjour,

Votre dépôt de données sur le canal "{channel_name}" a été traité avec succès.

Résumé:
- Date de dépôt: {submission_date}
- Fichiers traités: {file_count}
- Contrôles qualité: {dq_passed}/{dq_total} réussis

Vous trouverez le rapport détaillé en pièce jointe.

Cordialement,
L'équipe Data Quality
"""
    
    failure_subject: str = "⚠️ Dépôt de données - Anomalies détectées - {channel_name}"
    failure_body_template: str = """
Bonjour,

Votre dépôt de données sur le canal "{channel_name}" a été traité mais des anomalies ont été détectées.

Résumé:
- Date de dépôt: {submission_date}
- Fichiers traités: {file_count}
- Contrôles qualité: {dq_passed}/{dq_total} réussis
- Anomalies: {dq_failed} contrôle(s) en échec

Merci de consulter le rapport détaillé en pièce jointe et de corriger les données.

Cordialement,
L'équipe Data Quality
"""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "recipient_team_emails": self.recipient_team_emails,
            "admin_emails": self.admin_emails,
            "cc_emails": self.cc_emails,
            "success_subject": self.success_subject,
            "success_body_template": self.success_body_template,
            "failure_subject": self.failure_subject,
            "failure_body_template": self.failure_body_template
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EmailConfig':
        return cls(**data)


@dataclass
class DropChannel:
    """
    Canal de dépôt configuré par les administrateurs
    
    Un canal représente un point de livraison pour une équipe externe.
    Il définit les fichiers attendus, les contrôles DQ à effectuer et la configuration email.
    """
    channel_id: str  # Identifiant unique du canal
    name: str  # Nom du canal
    description: str = ""
    team_name: str = ""  # Nom de l'équipe externe
    direction: str = "incoming"  # "incoming" (vers STDA) ou "outgoing" (depuis STDA)
    
    # Fichiers attendus
    file_specifications: List[FileSpecification] = field(default_factory=list)
    
    # DQ à exécuter
    dq_configs: List[str] = field(default_factory=list)  # Liste des paths de configs DQ
    
    # Configuration email
    email_config: EmailConfig = field(default_factory=EmailConfig)
    
    # Permissions d'accès
    is_public: bool = True  # Si False, seuls les utilisateurs autorisés peuvent voir le canal
    allowed_users: List[str] = field(default_factory=list)  # Liste des emails autorisés
    allowed_groups: List[str] = field(default_factory=list)  # Liste des groupes autorisés (ex: "Finance", "Marketing")
    
    # Métadonnées
    active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = "admin"
    updated_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "channel_id": self.channel_id,
            "name": self.name,
            "description": self.description,
            "team_name": self.team_name,
            "direction": self.direction,
            "file_specifications": [fs.to_dict() for fs in self.file_specifications],
            "dq_configs": self.dq_configs,
            "email_config": self.email_config.to_dict(),
            "is_public": self.is_public,
            "allowed_users": self.allowed_users,
            "allowed_groups": self.allowed_groups,
            "active": self.active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def has_access(self, user_email: Optional[str] = None, user_groups: Optional[List[str]] = None) -> bool:
        """
        Vérifie si un utilisateur a accès au canal
        
        Args:
            user_email: Email de l'utilisateur
            user_groups: Liste des groupes de l'utilisateur
            
        Returns:
            True si l'utilisateur a accès, False sinon
        """
        # Si le canal est public, tout le monde a accès
        if self.is_public:
            return True
        
        # Vérifier si l'utilisateur est dans la liste des utilisateurs autorisés
        if user_email and user_email in self.allowed_users:
            return True
        
        # Vérifier si l'utilisateur appartient à un groupe autorisé
        if user_groups:
            for group in user_groups:
                if group in self.allowed_groups:
                    return True
        
        # Sinon, pas d'accès
        return False
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DropChannel':
        data_copy = data.copy()
        if 'file_specifications' in data_copy:
            data_copy['file_specifications'] = [
                FileSpecification.from_dict(fs) for fs in data_copy['file_specifications']
            ]
        if 'email_config' in data_copy:
            data_copy['email_config'] = EmailConfig.from_dict(data_copy['email_config'])
        if 'created_at' in data_copy and isinstance(data_copy['created_at'], str):
            data_copy['created_at'] = datetime.fromisoformat(data_copy['created_at'])
        if 'updated_at' in data_copy and isinstance(data_copy['updated_at'], str):
            data_copy['updated_at'] = datetime.fromisoformat(data_copy['updated_at'])
        return cls(**data_copy)


@dataclass
class FileMapping:
    """Mapping entre un fichier attendu et le fichier fourni"""
    file_spec_id: str  # ID de la spécification
    provided_path: str  # Chemin/URL du fichier fourni
    provided_name: str  # Nom du fichier fourni
    validated: bool = False
    validation_errors: List[str] = field(default_factory=list)


@dataclass
class ChannelSubmission:
    """
    Soumission d'une équipe externe sur un canal
    """
    submission_id: str  # Identifiant unique de la soumission
    channel_id: str  # Canal utilisé
    
    # Fichiers soumis
    file_mappings: List[FileMapping] = field(default_factory=list)
    
    # Statut
    status: SubmissionStatus = SubmissionStatus.PENDING
    submitted_at: datetime = field(default_factory=datetime.now)
    submitted_by: str = ""  # Email/nom de la personne
    
    # Résultats de traitement
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    
    # Résultats DQ
    dq_execution_results: Dict[str, Any] = field(default_factory=dict)
    dq_report_path: Optional[str] = None  # Chemin vers le rapport Excel
    
    dq_total: int = 0
    dq_passed: int = 0
    dq_failed: int = 0
    dq_skipped: int = 0
    
    # Erreurs
    errors: List[str] = field(default_factory=list)
    
    # Notifications
    email_sent: bool = False
    email_sent_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "submission_id": self.submission_id,
            "channel_id": self.channel_id,
            "file_mappings": [
                {
                    "file_spec_id": fm.file_spec_id,
                    "provided_path": fm.provided_path,
                    "provided_name": fm.provided_name,
                    "validated": fm.validated,
                    "validation_errors": fm.validation_errors
                } for fm in self.file_mappings
            ],
            "status": self.status.value,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "submitted_by": self.submitted_by,
            "processing_started_at": self.processing_started_at.isoformat() if self.processing_started_at else None,
            "processing_completed_at": self.processing_completed_at.isoformat() if self.processing_completed_at else None,
            "dq_execution_results": self.dq_execution_results,
            "dq_report_path": self.dq_report_path,
            "dq_total": self.dq_total,
            "dq_passed": self.dq_passed,
            "dq_failed": self.dq_failed,
            "dq_skipped": self.dq_skipped,
            "errors": self.errors,
            "email_sent": self.email_sent,
            "email_sent_at": self.email_sent_at.isoformat() if self.email_sent_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChannelSubmission':
        data_copy = data.copy()
        if 'status' in data_copy:
            data_copy['status'] = SubmissionStatus(data_copy['status'])
        if 'file_mappings' in data_copy:
            data_copy['file_mappings'] = [
                FileMapping(**fm) for fm in data_copy['file_mappings']
            ]
        for date_field in ['submitted_at', 'processing_started_at', 'processing_completed_at', 'email_sent_at']:
            if date_field in data_copy and data_copy[date_field] and isinstance(data_copy[date_field], str):
                data_copy[date_field] = datetime.fromisoformat(data_copy[date_field])
        return cls(**data_copy)
