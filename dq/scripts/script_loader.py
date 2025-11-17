"""
Script Loader - Découverte et gestion des scripts DQ disponibles

Structure des dossiers:
- scripts/definition/ : Scripts génériques (disponibles partout)
- scripts/{stream}/{project}/{zone}/ : Scripts spécifiques à un contexte
- scripts/{stream}/{project}/ : Scripts pour un projet
- scripts/{stream}/ : Scripts pour un stream

Chaque script doit avoir un fichier .json de métadonnées associé.
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


DEFAULT_ROOT = "scripts"


@dataclass
class ScriptMetadata:
    """Métadonnées d'un script DQ"""
    id: str
    label: str
    description: str
    path: str  # Chemin relatif depuis la racine du projet
    params: Dict[str, Any]  # Paramètres par défaut
    execute_on: str  # "pre_dq" ou "post_dq"
    criticality: str  # "low", "medium", "high", "critical"
    tags: List[str]  # Tags pour filtrer/rechercher
    author: Optional[str] = None
    version: Optional[str] = None


def load_script_metadata(script_path: str) -> Optional[ScriptMetadata]:
    """
    Charge les métadonnées d'un script depuis son fichier .json
    
    Args:
        script_path: Chemin vers le fichier .py du script
        
    Returns:
        ScriptMetadata ou None si pas de métadonnées
    """
    # Chercher le fichier .json correspondant
    metadata_path = script_path.replace('.py', '.json')
    
    if not os.path.exists(metadata_path):
        return None
    
    try:
        with open(metadata_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return ScriptMetadata(
            id=data.get('id', Path(script_path).stem),
            label=data.get('label', ''),
            description=data.get('description', ''),
            path=script_path,
            params=data.get('params', {}),
            execute_on=data.get('execute_on', 'post_dq'),
            criticality=data.get('criticality', 'medium'),
            tags=data.get('tags', []),
            author=data.get('author'),
            version=data.get('version')
        )
    except Exception as e:
        print(f"[WARNING] Impossible de charger les métadonnées de {metadata_path}: {e}")
        return None


def list_scripts(
    stream: Optional[str] = None,
    project: Optional[str] = None,
    zone: Optional[str] = None,
    root: str = DEFAULT_ROOT
) -> List[ScriptMetadata]:
    """
    Liste les scripts disponibles pour un contexte donné
    
    Ordre de recherche (du plus spécifique au plus générique):
    1. scripts/{stream}/{project}/{zone}/
    2. scripts/{stream}/{project}/
    3. scripts/{stream}/
    4. scripts/definition/ (scripts génériques)
    
    Args:
        stream: ID du stream
        project: ID du projet
        zone: ID de la zone
        root: Racine du dossier scripts
        
    Returns:
        Liste des ScriptMetadata disponibles
    """
    scripts = []
    seen_ids = set()
    
    # Chemins à scanner (du plus spécifique au plus générique)
    search_paths = []
    
    if stream and project and zone:
        search_paths.append(os.path.join(root, stream, project, zone))
    if stream and project:
        search_paths.append(os.path.join(root, stream, project))
    if stream:
        search_paths.append(os.path.join(root, stream))
    
    # Toujours inclure les scripts génériques
    search_paths.append(os.path.join(root, "definition"))
    
    for path in search_paths:
        if not os.path.exists(path):
            continue
        
        # Lister tous les fichiers .py
        for file in os.listdir(path):
            if not file.endswith('.py'):
                continue
            
            script_path = os.path.join(path, file)
            metadata = load_script_metadata(script_path)
            
            if metadata and metadata.id not in seen_ids:
                scripts.append(metadata)
                seen_ids.add(metadata.id)
    
    return scripts


def get_script_by_id(
    script_id: str,
    stream: Optional[str] = None,
    project: Optional[str] = None,
    zone: Optional[str] = None,
    root: str = DEFAULT_ROOT
) -> Optional[ScriptMetadata]:
    """
    Récupère un script par son ID
    
    Args:
        script_id: ID du script
        stream, project, zone: Contexte de recherche
        root: Racine du dossier scripts
        
    Returns:
        ScriptMetadata ou None si non trouvé
    """
    scripts = list_scripts(stream, project, zone, root)
    
    for script in scripts:
        if script.id == script_id:
            return script
    
    return None


def get_script_options(
    stream: Optional[str] = None,
    project: Optional[str] = None,
    zone: Optional[str] = None,
    execute_on: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Retourne les options de scripts pour un dropdown Dash
    
    Args:
        stream, project, zone: Contexte
        execute_on: Filtrer par "pre_dq" ou "post_dq" (optionnel)
        
    Returns:
        Liste de dicts {"label": "...", "value": "script_id"}
    """
    scripts = list_scripts(stream, project, zone)
    
    # Filtrer par execute_on si spécifié
    if execute_on:
        scripts = [s for s in scripts if s.execute_on == execute_on]
    
    options = []
    for script in scripts:
        label = f"{script.label} ({script.execute_on})"
        if script.tags:
            label += f" [{', '.join(script.tags)}]"
        
        options.append({
            "label": label,
            "value": script.id
        })
    
    return options
