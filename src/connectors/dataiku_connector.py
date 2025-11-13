"""
Connecteur pour les datasets Dataiku existants
"""

from typing import Any, Dict, Optional
import pandas as pd
from .base import DataConnector

try:
    import dataiku
    DATAIKU_AVAILABLE = True
except ImportError:
    DATAIKU_AVAILABLE = False
    # Utiliser le stub pour développement local
    try:
        import dataiku_stub as dataiku
    except ImportError:
        dataiku = None


class DataikuConnector(DataConnector):
    """
    Connecteur pour les datasets Dataiku existants
    Permet de récupérer des données depuis un dataset Dataiku
    
    Paramètres de connexion attendus:
    - project_key: str - Clé du projet Dataiku (ex: DKU_PROJECT)
    - dataset_name: str - Nom du dataset
    - sampling: str (optionnel) - Méthode d'échantillonnage ('head', 'random', 'full')
    - limit: int (optionnel) - Nombre de lignes max (si sampling != 'full')
    - columns: list[str] (optionnel) - Liste des colonnes à récupérer (toutes par défaut)
    """
    
    def validate_connection(self) -> tuple[bool, Optional[str]]:
        """Valide les paramètres de connexion Dataiku"""
        if not DATAIKU_AVAILABLE and dataiku is None:
            return False, "Module dataiku non disponible (ni SDK ni stub)"
        
        project_key = self.connection_params.get('project_key')
        dataset_name = self.connection_params.get('dataset_name')
        
        if not project_key:
            return False, "Le paramètre 'project_key' est requis"
        
        if not dataset_name:
            return False, "Le paramètre 'dataset_name' est requis"
        
        return True, None
    
    def test_connection(self) -> tuple[bool, Optional[str]]:
        """Teste l'accès au dataset Dataiku"""
        is_valid, error = self.validate_connection()
        if not is_valid:
            return False, error
        
        try:
            project_key = self.connection_params['project_key']
            dataset_name = self.connection_params['dataset_name']
            
            # Tenter de récupérer les métadonnées du dataset
            client = dataiku.api_client()
            project = client.get_project(project_key)
            dataset = project.get_dataset(dataset_name)
            
            # Vérifier que le dataset existe
            metadata = dataset.get_metadata()
            
            self.is_connected = True
            return True, f"Dataset trouvé: {project_key}.{dataset_name}"
        
        except AttributeError:
            # Mode stub - simuler le succès
            if not DATAIKU_AVAILABLE:
                return True, f"[STUB MODE] Dataset simulé: {project_key}.{dataset_name}"
            raise
        
        except Exception as e:
            error_msg = str(e)
            if "not found" in error_msg.lower():
                return False, f"Dataset introuvable: {project_key}.{dataset_name}"
            elif "permission" in error_msg.lower():
                return False, "Permissions insuffisantes pour accéder au dataset"
            else:
                return False, f"Erreur lors du test de connexion: {error_msg}"
    
    def fetch_data(self) -> pd.DataFrame:
        """Récupère les données depuis un dataset Dataiku"""
        is_valid, error = self.validate_connection()
        if not is_valid:
            raise ValueError(f"Connexion invalide: {error}")
        
        project_key = self.connection_params['project_key']
        dataset_name = self.connection_params['dataset_name']
        sampling = self.connection_params.get('sampling', 'head')
        limit = self.connection_params.get('limit', 10000)
        columns = self.connection_params.get('columns')
        
        try:
            # Mode stub pour développement local
            if not DATAIKU_AVAILABLE:
                print(f"[STUB MODE] Simulation de chargement: {project_key}.{dataset_name}")
                # Retourner un DataFrame vide avec les colonnes demandées
                if columns:
                    return pd.DataFrame(columns=columns)
                else:
                    return pd.DataFrame(columns=['col1', 'col2', 'col3'])
            
            # Mode production avec SDK Dataiku
            client = dataiku.api_client()
            project = client.get_project(project_key)
            dataset = project.get_dataset(dataset_name)
            
            # Configuration du chargement
            if sampling == 'full':
                # Charger tout le dataset
                df = dataset.get_dataframe(columns=columns)
            
            elif sampling == 'head':
                # Charger les N premières lignes
                df = dataset.get_dataframe(limit=limit, columns=columns)
            
            elif sampling == 'random':
                # Échantillonnage aléatoire
                df = dataset.get_dataframe(sampling='random', limit=limit, columns=columns)
            
            else:
                raise ValueError(f"Méthode de sampling invalide: {sampling}. Valeurs acceptées: 'head', 'random', 'full'")
            
            self.is_connected = True
            return df
        
        except Exception as e:
            raise Exception(f"Erreur lors du chargement du dataset Dataiku {project_key}.{dataset_name}: {str(e)}")
    
    def get_metadata(self) -> Dict[str, Any]:
        """Retourne les métadonnées du dataset Dataiku"""
        metadata = super().get_metadata()
        
        project_key = self.connection_params.get('project_key')
        dataset_name = self.connection_params.get('dataset_name')
        
        metadata.update({
            "project_key": project_key,
            "dataset_name": dataset_name,
            "full_name": f"{project_key}.{dataset_name}",
            "dataiku_available": DATAIKU_AVAILABLE
        })
        
        # Enrichir avec les métadonnées Dataiku si disponibles
        if DATAIKU_AVAILABLE:
            try:
                client = dataiku.api_client()
                project = client.get_project(project_key)
                dataset = project.get_dataset(dataset_name)
                dku_metadata = dataset.get_metadata()
                
                metadata.update({
                    "dataset_type": dku_metadata.get('type'),
                    "schema_columns": [col['name'] for col in dku_metadata.get('schema', {}).get('columns', [])],
                    "records_count": dku_metadata.get('metricsLastValues', {}).get('records_count')
                })
            except:
                pass
        
        return metadata
