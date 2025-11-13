"""
Connecteurs pour sources de données multiples

Ce module fournit des connecteurs pour différents types de sources:
- LOCAL: Fichiers locaux uploadés
- HUE: HDFS/Hive via HUE
- SHAREPOINT: SharePoint Online
- DATAIKU_DATASET: Datasets Dataiku existants
"""

from .base import DataConnector
from .local_connector import LocalConnector
from .hue_connector import HueConnector
from .sharepoint_connector import SharePointConnector
from .dataiku_connector import DataikuConnector
from .factory import ConnectorFactory

__all__ = [
    'DataConnector',
    'LocalConnector',
    'HueConnector',
    'SharePointConnector',
    'DataikuConnector',
    'ConnectorFactory'
]
