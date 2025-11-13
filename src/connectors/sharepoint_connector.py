"""
Connecteur pour SharePoint Online
"""

from typing import Any, Dict, Optional
import pandas as pd
from pathlib import Path
import requests
from io import BytesIO
from .base import DataConnector


class SharePointConnector(DataConnector):
    """
    Connecteur pour SharePoint Online
    Permet de récupérer des fichiers depuis des bibliothèques de documents SharePoint
    
    Paramètres de connexion attendus:
    - site_url: str - URL du site SharePoint (ex: https://tenant.sharepoint.com/sites/mysite)
    - folder_path: str - Chemin du dossier (ex: /Shared Documents/Data)
    - file_name: str - Nom du fichier à récupérer
    - client_id: str (optionnel) - Client ID pour OAuth2
    - client_secret: str (optionnel) - Client Secret pour OAuth2
    - access_token: str (optionnel) - Token d'accès direct
    - username: str (optionnel) - Nom d'utilisateur
    - password: str (optionnel) - Mot de passe
    - format: str - Format du fichier (csv, xlsx, parquet, json)
    """
    
    def __init__(self, connection_params: Dict[str, Any]):
        super().__init__(connection_params)
        self.access_token = None
    
    def validate_connection(self) -> tuple[bool, Optional[str]]:
        """Valide les paramètres de connexion SharePoint"""
        site_url = self.connection_params.get('site_url')
        folder_path = self.connection_params.get('folder_path')
        file_name = self.connection_params.get('file_name')
        
        if not site_url:
            return False, "Le paramètre 'site_url' est requis"
        
        if not folder_path:
            return False, "Le paramètre 'folder_path' est requis"
        
        if not file_name:
            return False, "Le paramètre 'file_name' est requis"
        
        # Vérifier les credentials
        access_token = self.connection_params.get('access_token')
        client_id = self.connection_params.get('client_id')
        client_secret = self.connection_params.get('client_secret')
        username = self.connection_params.get('username')
        password = self.connection_params.get('password')
        
        if not access_token and not (client_id and client_secret) and not (username and password):
            return False, "Authentification requise: fournir 'access_token', 'client_id'+'client_secret', ou 'username'+'password'"
        
        return True, None
    
    def _get_access_token(self) -> str:
        """Obtient un access token SharePoint"""
        if self.access_token:
            return self.access_token
        
        # Si token fourni directement
        if self.connection_params.get('access_token'):
            self.access_token = self.connection_params['access_token']
            return self.access_token
        
        # Sinon, obtenir via OAuth2
        site_url = self.connection_params['site_url']
        tenant = site_url.split('.sharepoint.com')[0].split('//')[1]
        
        # OAuth2 avec client credentials
        if self.connection_params.get('client_id') and self.connection_params.get('client_secret'):
            token_url = f"https://accounts.accesscontrol.windows.net/{tenant}/tokens/OAuth/2"
            
            data = {
                'grant_type': 'client_credentials',
                'client_id': f"{self.connection_params['client_id']}@{tenant}",
                'client_secret': self.connection_params['client_secret'],
                'resource': f"00000003-0000-0ff1-ce00-000000000000/{tenant}.sharepoint.com@{tenant}"
            }
            
            response = requests.post(token_url, data=data, timeout=10)
            response.raise_for_status()
            
            self.access_token = response.json()['access_token']
            return self.access_token
        
        # Authentification par username/password (legacy)
        else:
            raise NotImplementedError("Authentification par username/password non implémentée. Utiliser OAuth2 ou access_token.")
    
    def test_connection(self) -> tuple[bool, Optional[str]]:
        """Teste la connexion à SharePoint"""
        is_valid, error = self.validate_connection()
        if not is_valid:
            return False, error
        
        try:
            site_url = self.connection_params['site_url']
            folder_path = self.connection_params['folder_path']
            
            # Obtenir le token
            access_token = self._get_access_token()
            
            # Tester l'accès au dossier
            api_url = f"{site_url}/_api/web/GetFolderByServerRelativeUrl('{folder_path}')"
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Accept': 'application/json;odata=verbose'
            }
            
            response = requests.get(api_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            self.is_connected = True
            return True, "Connexion à SharePoint réussie"
        
        except requests.exceptions.Timeout:
            return False, "Timeout lors de la connexion à SharePoint"
        except requests.exceptions.ConnectionError:
            return False, f"Impossible de se connecter à {site_url}"
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                return False, "Erreur d'authentification (token invalide ou expiré)"
            elif e.response.status_code == 404:
                return False, f"Dossier introuvable: {folder_path}"
            else:
                return False, f"Erreur HTTP: {e.response.status_code} - {e.response.reason}"
        except Exception as e:
            return False, f"Erreur lors du test de connexion: {str(e)}"
    
    def fetch_data(self) -> pd.DataFrame:
        """Récupère les données depuis SharePoint"""
        is_valid, error = self.validate_connection()
        if not is_valid:
            raise ValueError(f"Connexion invalide: {error}")
        
        site_url = self.connection_params['site_url']
        folder_path = self.connection_params['folder_path']
        file_name = self.connection_params['file_name']
        file_format = self.connection_params.get('format', 'csv').lower()
        
        try:
            # Obtenir le token
            access_token = self._get_access_token()
            
            # Construire l'URL du fichier
            file_server_relative_url = f"{folder_path}/{file_name}"
            api_url = f"{site_url}/_api/web/GetFileByServerRelativeUrl('{file_server_relative_url}')/$value"
            
            headers = {
                'Authorization': f'Bearer {access_token}'
            }
            
            # Télécharger le fichier
            response = requests.get(api_url, headers=headers, timeout=60)
            response.raise_for_status()
            
            # Parser selon le format
            if file_format == 'csv':
                csv_options = self.connection_params.get('csv_options', {})
                df = pd.read_csv(BytesIO(response.content), **csv_options)
            
            elif file_format == 'xlsx':
                sheet_name = self.connection_params.get('sheet_name', 0)
                df = pd.read_excel(BytesIO(response.content), sheet_name=sheet_name)
            
            elif file_format == 'parquet':
                df = pd.read_parquet(BytesIO(response.content))
            
            elif file_format == 'json':
                df = pd.read_json(BytesIO(response.content))
            
            else:
                raise ValueError(f"Format non supporté: {file_format}")
            
            self.is_connected = True
            return df
        
        except requests.exceptions.Timeout:
            raise ConnectionError("Timeout lors de la récupération du fichier depuis SharePoint")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise FileNotFoundError(f"Fichier introuvable: {file_server_relative_url}")
            else:
                raise ConnectionError(f"Erreur HTTP SharePoint: {e.response.status_code} - {e.response.reason}")
        except Exception as e:
            raise Exception(f"Erreur lors du chargement depuis SharePoint: {str(e)}")
    
    def get_metadata(self) -> Dict[str, Any]:
        """Retourne les métadonnées du fichier SharePoint"""
        metadata = super().get_metadata()
        metadata.update({
            "site_url": self.connection_params.get('site_url'),
            "folder_path": self.connection_params.get('folder_path'),
            "file_name": self.connection_params.get('file_name')
        })
        return metadata
