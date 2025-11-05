# Configuration et constantes
from __future__ import annotations
import os
import yaml
from pathlib import Path
from typing import Dict, List
import os

try:
    import dataiku
except Exception:
    import dataiku_stub as dataiku

INVENTORY_PATH = Path(__file__).resolve().parents[1] / "config" / "inventory.yaml"


def _load_inventory() -> Dict:
    """Charge l'inventory depuis config/inventory.yaml"""
    if not INVENTORY_PATH.exists():
        return {}
    with open(INVENTORY_PATH, "r", encoding="utf-8") as f:
        text = f.read()
        if text.strip().startswith('```'):
            lines = [l for l in text.splitlines() if not l.strip().startswith('```')]
            text = "\n".join(lines)
        return yaml.safe_load(text) or {}


def get_streams() -> Dict[str, List[str]]:
    """Retourne les streams et leurs projets depuis l'inventory
    
    Format de retour: {stream_id: [project_ids]}
    Ex: {"A": ["P1", "P2"], "B": ["P1", "P3"]}
    """
    inv = _load_inventory()
    streams = {}
    for s in inv.get("streams", []):
        stream_id = s.get("id", "")
        project_ids = [p.get("id") for p in s.get("projects", [])]
        streams[stream_id] = project_ids
    return streams


def get_streams_with_labels() -> Dict[str, Dict]:
    """Retourne les streams avec leurs IDs et labels
    
    Format: {stream_id: {"label": "...", "projects": [...]}}
    """
    inv = _load_inventory()
    streams = {}
    for s in inv.get("streams", []):
        stream_id = s.get("id", "")
        stream_label = s.get("label", stream_id)
        project_ids = [p.get("id") for p in s.get("projects", [])]
        streams[stream_id] = {
            "label": stream_label,
            "projects": project_ids
        }
    return streams


def get_datasets_for_context(stream_id: str, project_id: str, dq_point: str) -> List[str]:
    """Retourne les datasets pour un contexte donné (stream_id, projet, dq_point)"""
    inv = _load_inventory()
    
    # Mapping DQ Point -> Zone
    point_to_zone = {
        "Extraction": "raw",
        "Transformation": "trusted",
        "Chargement": "trusted"
    }
    zone_id = point_to_zone.get(dq_point, "raw")
    
    # Trouver le stream par ID
    for s in inv.get("streams", []):
        if s.get("id") == stream_id:
            # Trouver le projet
            for p in s.get("projects", []):
                if p.get("id") == project_id:
                    # Trouver la zone
                    for z in p.get("zones", []):
                        if z.get("id") == zone_id:
                            return [d.get("alias") for d in z.get("datasets", [])]
    return []


# Données de configuration (chargées depuis l'inventory)
STREAMS = get_streams()

# Fonction pour obtenir le mapping dynamique
def get_dataset_mapping():
    """Génère le mapping des datasets par contexte depuis l'inventory"""
    mapping = {}
    inv = _load_inventory()
    
    point_to_zone = {
        "Extraction": "raw",
        "Transformation": "trusted",
        "Chargement": "trusted"
    }
    
    for s in inv.get("streams", []):
        stream_id = s.get("id", "")
        for p in s.get("projects", []):
            project_id = p.get("id")
            for dq_point, zone_id in point_to_zone.items():
                for z in p.get("zones", []):
                    if z.get("id") == zone_id:
                        datasets = [d.get("alias") for d in z.get("datasets", [])]
                        mapping[(stream_id, project_id, dq_point)] = datasets
    return mapping

DATASET_MAPPING = get_dataset_mapping()

# Client Dataiku
client = dataiku.api_client()
project = client.get_default_project()

# Mode debug UI (contrôlé par l'env var DQ_DEBUG_UI)
_dq_debug_env = os.getenv('DQ_DEBUG_UI', 'false').lower()
DEBUG_UI = _dq_debug_env in ('1', 'true', 'yes', 'on')



def get_default_stream() -> str:
    return os.getenv("DQ_DEFAULT_STREAM", "")

def get_default_project() -> str:
    return os.getenv("DQ_DEFAULT_PROJECT", "")

def get_default_zone() -> str:
    return os.getenv("DQ_DEFAULT_ZONE", "")
