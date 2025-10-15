# Fonctions utilitaires

import re
import urllib.parse as urlparse
from src.config import DATASET_MAPPING, project

try:
    import dataiku
except Exception:
    import dataiku_stub as dataiku


def list_project_datasets(stream=None, projet=None, dq_point=None):
    """Liste les datasets filtrés par contexte (stream, projet, dq_point)"""
    try:
        # Si contexte fourni, utiliser le mapping
        if stream and projet and dq_point:
            key = (stream, projet, dq_point)
            mapped_datasets = DATASET_MAPPING.get(key, [])
            if mapped_datasets:
                return mapped_datasets
        
        # Sinon, retourner tous les datasets disponibles
        return [d["name"] for d in project.list_datasets()]
    except Exception:
        return []


def get_columns_for_dataset(ds_name):
    """Récupère les colonnes d'un dataset (via Dataiku ou fichier CSV local)"""
    try:
        ds = dataiku.Dataset(ds_name)
        schema = ds.read_schema() or []
        return [c.get("name") for c in schema if c.get("name")]
    except Exception:
        import csv
        import os
        csv_path = f"./datasets/{ds_name}.csv"
        if os.path.exists(csv_path):
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                headers = next(reader, [])
                return headers
        return []


def safe_id(s):
    """Nettoie une chaîne pour en faire un identifiant valide"""
    return re.sub(r"[^a-zA-Z0-9_]+", "_", s).lower()


def cfg_template():
    """Template de configuration DQ"""
    return {
        "version": "1.0",
        "globals": {
            "default_severity": "medium",
            "sample_size": 10,
            "fail_fast": False,
            "timezone": "Europe/Paris"
        },
        "context": {},
        "databases": [],
        "metrics": [],
        "tests": [],
        "orchestration": {"order": [], "dependencies": []}
    }


def parse_query(search: str):
    """Parse les paramètres d'URL"""
    if not search:
        return {}
    q = urlparse.parse_qs(search.lstrip("?"))
    return {k: (v[0] if isinstance(v, list) and v else v) for k, v in q.items()}


def list_dq_files(folder_id="dq_params"):
    """Liste les fichiers DQ dans un folder Dataiku"""
    try:
        folder = dataiku.Folder(folder_id)
    except Exception:
        return []
    import os
    path = getattr(folder, "path", None)
    if not path or not os.path.isdir(path):
        return []
    return sorted([
        fn for fn in os.listdir(path) 
        if fn.startswith("dq_config_") and (fn.endswith(".json") or fn.endswith(".yaml"))
    ])


def first(val):
    """Helper pour extraire la première valeur d'une liste ou d'une chaîne (gestion pattern matching Dash)"""
    if val is None:
        return None
    if isinstance(val, list):
        return val[0] if val else None
    return val


def get_dq_folder_path(folder_id="dq_params"):
    """Retourne le chemin du folder DQ"""
    try:
        folder = dataiku.Folder(folder_id)
        path = getattr(folder, "path", None)
        return path if path else None
    except Exception:
        return None


def read_dq_file(filename, folder_id="dq_params"):
    """Lit le contenu d'un fichier DQ"""
    import os
    import json
    import yaml
    
    path = get_dq_folder_path(folder_id)
    if not path:
        return None
    
    filepath = os.path.join(path, filename)
    if not os.path.exists(filepath):
        return None
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            if filename.endswith('.json'):
                return json.load(f)
            elif filename.endswith('.yaml') or filename.endswith('.yml'):
                return yaml.safe_load(f)
    except Exception:
        return None
    return None


def write_dq_file(filename, content, folder_id="dq_params"):
    """Écrit un fichier DQ"""
    import os
    import json
    import yaml
    
    path = get_dq_folder_path(folder_id)
    if not path:
        return False
    
    filepath = os.path.join(path, filename)
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            if filename.endswith('.json'):
                json.dump(content, f, ensure_ascii=False, indent=2)
            elif filename.endswith('.yaml') or filename.endswith('.yml'):
                yaml.dump(content, f, allow_unicode=True, default_flow_style=False)
        return True
    except Exception:
        return False


def delete_dq_file(filename, folder_id="dq_params"):
    """Supprime un fichier DQ"""
    import os
    
    path = get_dq_folder_path(folder_id)
    if not path:
        return False
    
    filepath = os.path.join(path, filename)
    if not os.path.exists(filepath):
        return False
    
    try:
        os.remove(filepath)
        return True
    except Exception:
        return False


def rename_dq_file(old_filename, new_filename, folder_id="dq_params"):
    """Renomme un fichier DQ"""
    import os
    
    path = get_dq_folder_path(folder_id)
    if not path:
        return False
    
    old_path = os.path.join(path, old_filename)
    new_path = os.path.join(path, new_filename)
    
    if not os.path.exists(old_path):
        return False
    if os.path.exists(new_path):
        return False
    
    try:
        os.rename(old_path, new_path)
        return True
    except Exception:
        return False


def duplicate_dq_file(filename, new_filename, folder_id="dq_params"):
    """Duplique un fichier DQ"""
    content = read_dq_file(filename, folder_id)
    if content is None:
        return False
    return write_dq_file(new_filename, content, folder_id)
