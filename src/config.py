# Configuration et constantes

import yaml
from pathlib import Path
from typing import Dict, List

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
    """Retourne les streams et leurs projets depuis l'inventory"""
    inv = _load_inventory()
    streams = {}
    for s in inv.get("streams", []):
        stream_label = s.get("label", s.get("id", ""))
        project_ids = [p.get("id") for p in s.get("projects", [])]
        streams[stream_label] = project_ids
    return streams


def get_datasets_for_context(stream_label: str, project_id: str, dq_point: str) -> List[str]:
    """Retourne les datasets pour un contexte donné (stream, projet, dq_point)"""
    inv = _load_inventory()
    
    # Mapping DQ Point -> Zone
    point_to_zone = {
        "Extraction": "raw",
        "Transformation": "trusted",
        "Chargement": "trusted"
    }
    zone_id = point_to_zone.get(dq_point, "raw")
    
    # Trouver le stream par label
    for s in inv.get("streams", []):
        if s.get("label") == stream_label or s.get("id") == stream_label:
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
        stream_label = s.get("label", s.get("id", ""))
        for p in s.get("projects", []):
            project_id = p.get("id")
            for dq_point, zone_id in point_to_zone.items():
                for z in p.get("zones", []):
                    if z.get("id") == zone_id:
                        datasets = [d.get("alias") for d in z.get("datasets", [])]
                        mapping[(stream_label, project_id, dq_point)] = datasets
    return mapping

DATASET_MAPPING = get_dataset_mapping()

# Client Dataiku
client = dataiku.api_client()
project = client.get_default_project()
