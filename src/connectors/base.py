"""
Classe de base pour tous les connecteurs de données
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import pandas as pd
from pathlib import Path


class DataConnector(ABC):
    """
    Interface de base pour tous les connecteurs de données
    
    Chaque connecteur doit implémenter:
    - validate_connection(): Valider les paramètres de connexion
    - fetch_data(): Récupérer les données et retourner un DataFrame pandas
    - test_connection(): Tester la connexion sans charger les données
    """
    
    def __init__(self, connection_params: Dict[str, Any]):
        """
        Args:
            connection_params: Paramètres spécifiques au connecteur
        """
        self.connection_params = connection_params
        self.is_connected = False
    
    @abstractmethod
    def validate_connection(self) -> tuple[bool, Optional[str]]:
        """
        Valide les paramètres de connexion
        
        Returns:
            (success: bool, error_message: Optional[str])
        """
        pass
    
    @abstractmethod
    def fetch_data(self) -> pd.DataFrame:
        """
        Récupère les données depuis la source
        
        Returns:
            DataFrame pandas avec les données
            
        Raises:
            ConnectionError: Si la connexion échoue
            ValueError: Si les paramètres sont invalides
            Exception: Pour toute autre erreur
        """
        pass
    
    @abstractmethod
    def test_connection(self) -> tuple[bool, Optional[str]]:
        """
        Teste la connexion sans charger les données
        
        Returns:
            (success: bool, message: Optional[str])
        """
        pass
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Retourne les métadonnées de la source (optionnel)
        
        Returns:
            Dictionnaire avec des métadonnées (taille, date de modif, etc.)
        """
        return {
            "connector_type": self.__class__.__name__,
            "connection_params": {k: v for k, v in self.connection_params.items() if k not in ['password', 'token', 'auth_token']}
        }
