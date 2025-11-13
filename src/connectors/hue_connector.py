"""
Connecteur pour HUE (HDFS/Hive)
"""

from typing import Any, Dict, Optional
import pandas as pd
import requests
from io import StringIO, BytesIO
from .base import DataConnector


class HueConnector(DataConnector):
    """
    Connecteur pour HUE (Hadoop User Experience)
    Permet de récupérer des fichiers depuis HDFS ou des résultats de requêtes Hive
    
    Paramètres de connexion attendus:
    - hue_url: str - URL de HUE (ex: http://hue.example.com:8888)
    - auth_token: str (optionnel) - Token d'authentification
    - username: str (optionnel) - Nom d'utilisateur
    - password: str (optionnel) - Mot de passe
    - path: str (optionnel) - Chemin HDFS du fichier
    - query: str (optionnel) - Requête Hive/Impala à exécuter
    - database: str (optionnel) - Base de données Hive (défaut: default)
    - format: str - Format attendu (csv, parquet)
    """
    
    def __init__(self, connection_params: Dict[str, Any]):
        super().__init__(connection_params)
        self.session = None
    
    def validate_connection(self) -> tuple[bool, Optional[str]]:
        """Valide les paramètres de connexion HUE"""
        hue_url = self.connection_params.get('hue_url')
        
        if not hue_url:
            return False, "Le paramètre 'hue_url' est requis"
        
        # Vérifier qu'on a soit un path soit une query
        path = self.connection_params.get('path')
        query = self.connection_params.get('query')
        
        if not path and not query:
            return False, "Au moins un des paramètres 'path' ou 'query' est requis"
        
        # Vérifier les credentials
        auth_token = self.connection_params.get('auth_token')
        username = self.connection_params.get('username')
        password = self.connection_params.get('password')
        
        if not auth_token and not (username and password):
            return False, "Authentification requise: fournir 'auth_token' ou 'username'+'password'"
        
        return True, None
    
    def _get_session(self) -> requests.Session:
        """Crée une session avec authentification"""
        if self.session:
            return self.session
        
        self.session = requests.Session()
        
        # Authentification par token
        auth_token = self.connection_params.get('auth_token')
        if auth_token:
            self.session.headers.update({'Authorization': f'Bearer {auth_token}'})
        
        # Ou authentification par user/password
        else:
            username = self.connection_params.get('username')
            password = self.connection_params.get('password')
            self.session.auth = (username, password)
        
        return self.session
    
    def test_connection(self) -> tuple[bool, Optional[str]]:
        """Teste la connexion à HUE"""
        is_valid, error = self.validate_connection()
        if not is_valid:
            return False, error
        
        try:
            hue_url = self.connection_params['hue_url']
            session = self._get_session()
            
            # Tester l'accès à l'API HUE
            response = session.get(f"{hue_url}/api/v1/status", timeout=10)
            response.raise_for_status()
            
            self.is_connected = True
            return True, "Connexion à HUE réussie"
        
        except requests.exceptions.Timeout:
            return False, "Timeout lors de la connexion à HUE"
        except requests.exceptions.ConnectionError:
            return False, f"Impossible de se connecter à {hue_url}"
        except requests.exceptions.HTTPError as e:
            return False, f"Erreur HTTP: {e.response.status_code} - {e.response.reason}"
        except Exception as e:
            return False, f"Erreur lors du test de connexion: {str(e)}"
    
    def fetch_data(self) -> pd.DataFrame:
        """Récupère les données depuis HUE"""
        is_valid, error = self.validate_connection()
        if not is_valid:
            raise ValueError(f"Connexion invalide: {error}")
        
        hue_url = self.connection_params['hue_url']
        session = self._get_session()
        
        try:
            # Cas 1: Charger un fichier HDFS
            if self.connection_params.get('path'):
                path = self.connection_params['path']
                file_format = self.connection_params.get('format', 'csv').lower()
                
                # Utiliser l'API HUE pour lire le fichier
                response = session.get(
                    f"{hue_url}/filebrowser/view={path}",
                    params={'format': 'json'},
                    timeout=30
                )
                response.raise_for_status()
                
                # Parser selon le format
                if file_format == 'csv':
                    df = pd.read_csv(StringIO(response.text))
                elif file_format == 'parquet':
                    # Pour parquet, il faut télécharger le binaire
                    response = session.get(f"{hue_url}/filebrowser/download={path}", timeout=60)
                    response.raise_for_status()
                    df = pd.read_parquet(BytesIO(response.content))
                else:
                    raise ValueError(f"Format non supporté via HUE: {file_format}")
            
            # Cas 2: Exécuter une requête Hive/Impala
            elif self.connection_params.get('query'):
                query = self.connection_params['query']
                database = self.connection_params.get('database', 'default')
                
                # Soumettre la requête via l'API HUE
                response = session.post(
                    f"{hue_url}/notebook/api/execute/hive",
                    json={
                        'snippet': query,
                        'database': database
                    },
                    timeout=120
                )
                response.raise_for_status()
                
                result = response.json()
                
                # Parser les résultats
                if 'data' in result:
                    df = pd.DataFrame(result['data'], columns=result.get('columns', []))
                else:
                    raise Exception("Pas de données retournées par la requête")
            
            else:
                raise ValueError("Ni 'path' ni 'query' spécifié")
            
            self.is_connected = True
            return df
        
        except requests.exceptions.Timeout:
            raise ConnectionError("Timeout lors de la récupération des données depuis HUE")
        except requests.exceptions.HTTPError as e:
            raise ConnectionError(f"Erreur HTTP HUE: {e.response.status_code} - {e.response.reason}")
        except Exception as e:
            raise Exception(f"Erreur lors du chargement depuis HUE: {str(e)}")
    
    def get_metadata(self) -> Dict[str, Any]:
        """Retourne les métadonnées de la source HUE"""
        metadata = super().get_metadata()
        metadata.update({
            "hue_url": self.connection_params.get('hue_url'),
            "source": "hdfs_path" if self.connection_params.get('path') else "hive_query",
            "path_or_query": self.connection_params.get('path') or self.connection_params.get('query')
        })
        return metadata
