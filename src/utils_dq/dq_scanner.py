"""
Scanner pour détecter et analyser les définitions DQ disponibles
"""

import yaml
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime


class DQDefinition:
    """Représente une définition DQ scannée"""
    
    def __init__(self, file_path: Path, data: Dict[str, Any]):
        self.file_path = file_path
        self.file_name = file_path.name
        self.data = data
        
        # Extraction des infos principales
        self.id = data.get('id', file_path.stem)
        self.label = data.get('label', data.get('description', self.id))
        self.version = data.get('version', 'N/A')
        
        # Contexte
        context = data.get('context', {})
        self.stream = context.get('stream', 'N/A')
        self.project = context.get('project', 'N/A')
        self.zone = context.get('zone', 'N/A')
        self.dq_point = context.get('dq_point', 'N/A')
        self.quarter = context.get('quarter', 'N/A')  # Format: 2025Q3
        
        # Statistiques
        self.datasets = self._extract_datasets(data)
        self.metrics_count = len(data.get('metrics', {}))
        self.tests_count = len(data.get('tests', {}))
        
        # Métadonnées du fichier
        self.file_size = file_path.stat().st_size if file_path.exists() else 0
        self.modified_date = datetime.fromtimestamp(file_path.stat().st_mtime) if file_path.exists() else None
        
    def _extract_datasets(self, data: Dict[str, Any]) -> List[str]:
        """Extrait la liste des datasets utilisés"""
        datasets = []
        
        # Format 1: databases avec alias
        if 'databases' in data:
            databases = data['databases']
            if isinstance(databases, list):
                for db in databases:
                    if isinstance(db, dict):
                        alias = db.get('alias', db.get('dataset'))
                        if alias:
                            datasets.append(alias)
                    elif isinstance(db, str):
                        datasets.append(db)
        
        # Format 2: datasets avec alias
        if 'datasets' in data:
            dataset_defs = data['datasets']
            if isinstance(dataset_defs, dict):
                for key, value in dataset_defs.items():
                    if isinstance(value, dict):
                        alias = value.get('alias', key)
                        datasets.append(alias)
                    else:
                        datasets.append(key)
        
        return list(set(datasets))  # Dédupliquer
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire pour affichage"""
        return {
            'id': self.id,
            'label': self.label,
            'version': self.version,
            'file_name': self.file_name,
            'file_path': str(self.file_path),
            'context': {
                'stream': self.stream,
                'project': self.project,
                'zone': self.zone,
                'dq_point': self.dq_point,
                'quarter': self.quarter
            },
            'datasets': self.datasets,
            'metrics_count': self.metrics_count,
            'tests_count': self.tests_count,
            'file_size': self.file_size,
            'modified_date': self.modified_date.isoformat() if self.modified_date else None
        }


class DQScanner:
    """Scanne et indexe toutes les définitions DQ disponibles"""
    
    def __init__(self, definitions_dir: str = "dq/definitions"):
        self.definitions_dir = Path(definitions_dir)
        
    def scan_all(self) -> List[DQDefinition]:
        """Scanne toutes les définitions DQ dans le répertoire"""
        definitions = []
        
        if not self.definitions_dir.exists():
            print(f"Répertoire {self.definitions_dir} introuvable")
            return definitions
        
        # Scanner tous les fichiers YAML et JSON
        for pattern in ['*.yaml', '*.yml', '*.json']:
            for file_path in self.definitions_dir.glob(pattern):
                try:
                    definition = self._load_definition(file_path)
                    if definition:
                        definitions.append(definition)
                except Exception as e:
                    print(f"Erreur lors du chargement de {file_path}: {e}")
        
        # Trier par nom
        definitions.sort(key=lambda d: d.id)
        
        return definitions
    
    def _load_definition(self, file_path: Path) -> Optional[DQDefinition]:
        """Charge une définition depuis un fichier"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_path.suffix.lower() == '.json':
                    data = json.load(f)
                else:
                    data = yaml.safe_load(f)
            
            if not data:
                return None
            
            return DQDefinition(file_path, data)
        
        except Exception as e:
            print(f"Erreur parsing {file_path}: {e}")
            return None
    
    def get_summary_stats(self, definitions: List[DQDefinition]) -> Dict[str, Any]:
        """Calcule des statistiques globales"""
        if not definitions:
            return {
                'total_definitions': 0,
                'total_metrics': 0,
                'total_tests': 0,
                'total_datasets': 0,
                'streams': [],
                'projects': [],
                'zones': [],
                'quarters': []
            }
        
        all_datasets = set()
        streams = set()
        projects = set()
        zones = set()
        quarters = set()
        
        for dq in definitions:
            all_datasets.update(dq.datasets)
            if dq.stream != 'N/A':
                streams.add(dq.stream)
            if dq.project != 'N/A':
                projects.add(dq.project)
            if dq.zone != 'N/A':
                zones.add(dq.zone)
            if dq.quarter != 'N/A':
                quarters.add(dq.quarter)
        
        return {
            'total_definitions': len(definitions),
            'total_metrics': sum(d.metrics_count for d in definitions),
            'total_tests': sum(d.tests_count for d in definitions),
            'total_datasets': len(all_datasets),
            'datasets': sorted(list(all_datasets)),
            'streams': sorted(list(streams)),
            'projects': sorted(list(projects)),
            'zones': sorted(list(zones)),
            'quarters': sorted(list(quarters), reverse=True)  # Plus récent en premier
        }


# Instance globale
_scanner = None

def get_dq_scanner() -> DQScanner:
    """Obtient l'instance du scanner"""
    global _scanner
    if _scanner is None:
        _scanner = DQScanner()
    return _scanner
