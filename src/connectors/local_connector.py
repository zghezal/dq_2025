"""
Connecteur pour fichiers locaux uploadés
"""

from typing import Any, Dict, Optional
import pandas as pd
from pathlib import Path
from .base import DataConnector


class LocalConnector(DataConnector):
    """
    Connecteur pour fichiers locaux
    
    Paramètres de connexion attendus:
    - file_path: str - Chemin absolu vers le fichier
    - format: str - Format du fichier (csv, xlsx, parquet, json)
    - csv_options: dict (optionnel) - Options pour pandas.read_csv (sep, encoding, etc.)
    """
    
    def validate_connection(self) -> tuple[bool, Optional[str]]:
        """Valide que le fichier existe et est accessible"""
        file_path = self.connection_params.get('file_path')
        
        if not file_path:
            return False, "Le paramètre 'file_path' est requis"
        
        file_path = Path(file_path)
        
        if not file_path.exists():
            return False, f"Le fichier n'existe pas: {file_path}"
        
        if not file_path.is_file():
            return False, f"Le chemin ne pointe pas vers un fichier: {file_path}"
        
        # Vérifier que le format est supporté
        file_format = self.connection_params.get('format', '').lower()
        supported_formats = ['csv', 'xlsx', 'parquet', 'json', 'tsv']
        
        if file_format not in supported_formats:
            return False, f"Format non supporté: {file_format}. Formats supportés: {supported_formats}"
        
        return True, None
    
    def test_connection(self) -> tuple[bool, Optional[str]]:
        """Teste l'accès au fichier"""
        is_valid, error = self.validate_connection()
        if not is_valid:
            return False, error
        
        try:
            file_path = Path(self.connection_params['file_path'])
            # Essayer de lire juste les premières lignes
            file_format = self.connection_params.get('format', '').lower()
            
            if file_format == 'csv' or file_format == 'tsv':
                sep = '\t' if file_format == 'tsv' else self.connection_params.get('csv_options', {}).get('sep', ',')
                pd.read_csv(file_path, nrows=1, sep=sep)
            elif file_format == 'xlsx':
                pd.read_excel(file_path, nrows=1)
            elif file_format == 'parquet':
                pd.read_parquet(file_path)
            elif file_format == 'json':
                pd.read_json(file_path, nrows=1)
            
            self.is_connected = True
            return True, f"Fichier accessible: {file_path.name}"
        
        except Exception as e:
            return False, f"Erreur lors de la lecture du fichier: {str(e)}"
    
    def fetch_data(self) -> pd.DataFrame:
        """Charge les données depuis le fichier local"""
        is_valid, error = self.validate_connection()
        if not is_valid:
            raise ValueError(f"Connexion invalide: {error}")
        
        file_path = Path(self.connection_params['file_path'])
        file_format = self.connection_params.get('format', '').lower()
        
        try:
            if file_format == 'csv':
                csv_options = self.connection_params.get('csv_options', {})
                df = pd.read_csv(file_path, **csv_options)
            
            elif file_format == 'tsv':
                csv_options = self.connection_params.get('csv_options', {})
                csv_options['sep'] = '\t'
                df = pd.read_csv(file_path, **csv_options)
            
            elif file_format == 'xlsx':
                sheet_name = self.connection_params.get('sheet_name', 0)
                df = pd.read_excel(file_path, sheet_name=sheet_name)
            
            elif file_format == 'parquet':
                df = pd.read_parquet(file_path)
            
            elif file_format == 'json':
                df = pd.read_json(file_path)
            
            else:
                raise ValueError(f"Format non supporté: {file_format}")
            
            self.is_connected = True
            return df
        
        except Exception as e:
            raise Exception(f"Erreur lors du chargement du fichier {file_path.name}: {str(e)}")
    
    def get_metadata(self) -> Dict[str, Any]:
        """Retourne les métadonnées du fichier"""
        metadata = super().get_metadata()
        
        file_path = Path(self.connection_params.get('file_path', ''))
        if file_path.exists():
            stat = file_path.stat()
            metadata.update({
                "file_name": file_path.name,
                "file_size_bytes": stat.st_size,
                "file_size_mb": round(stat.st_size / (1024 * 1024), 2),
                "last_modified": stat.st_mtime
            })
        
        return metadata
