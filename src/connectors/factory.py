"""
Factory pour créer des connecteurs de données
"""

from typing import Any, Dict
from src.core.models_channels import DataSourceType
from .base import DataConnector
from .local_connector import LocalConnector
from .hue_connector import HueConnector
from .sharepoint_connector import SharePointConnector
from .dataiku_connector import DataikuConnector


class ConnectorFactory:
    """Factory pour instancier le bon connecteur selon le type de source"""
    
    @staticmethod
    def create_connector(source_type: DataSourceType, connection_params: Dict[str, Any]) -> DataConnector:
        """
        Crée une instance du connecteur approprié
        
        Args:
            source_type: Type de source de données
            connection_params: Paramètres de connexion spécifiques
            
        Returns:
            Instance de DataConnector
            
        Raises:
            ValueError: Si le type de source n'est pas supporté
        """
        connector_map = {
            DataSourceType.LOCAL: LocalConnector,
            DataSourceType.HUE: HueConnector,
            DataSourceType.SHAREPOINT: SharePointConnector,
            DataSourceType.DATAIKU_DATASET: DataikuConnector
        }
        
        connector_class = connector_map.get(source_type)
        
        if not connector_class:
            raise ValueError(f"Type de source non supporté: {source_type}")
        
        return connector_class(connection_params)
    
    @staticmethod
    def get_supported_sources() -> Dict[str, str]:
        """
        Retourne la liste des sources supportées avec leur description
        
        Returns:
            Dict[source_type, description]
        """
        return {
            DataSourceType.LOCAL.value: "Fichier local uploadé",
            DataSourceType.HUE.value: "HUE (HDFS/Hive)",
            DataSourceType.SHAREPOINT.value: "SharePoint Online",
            DataSourceType.DATAIKU_DATASET.value: "Dataset Dataiku existant"
        }
    
    @staticmethod
    def get_required_params(source_type: DataSourceType) -> Dict[str, str]:
        """
        Retourne les paramètres requis pour un type de source
        
        Args:
            source_type: Type de source
            
        Returns:
            Dict[param_name, description]
        """
        params_map = {
            DataSourceType.LOCAL: {
                "file_path": "Chemin absolu du fichier",
                "format": "Format du fichier (csv, xlsx, parquet, json, tsv)"
            },
            DataSourceType.HUE: {
                "hue_url": "URL de HUE (ex: http://hue.example.com:8888)",
                "auth_token ou username+password": "Authentification",
                "path ou query": "Chemin HDFS ou requête Hive"
            },
            DataSourceType.SHAREPOINT: {
                "site_url": "URL du site SharePoint",
                "folder_path": "Chemin du dossier (ex: /Shared Documents/Data)",
                "file_name": "Nom du fichier",
                "access_token ou client_id+client_secret": "Authentification"
            },
            DataSourceType.DATAIKU_DATASET: {
                "project_key": "Clé du projet Dataiku",
                "dataset_name": "Nom du dataset"
            }
        }
        
        return params_map.get(source_type, {})
