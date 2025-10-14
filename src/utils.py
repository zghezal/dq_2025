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
