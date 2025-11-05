import yaml
from pathlib import Path
from typing import List, Dict, Optional

INVENTORY_PATH = Path(__file__).resolve().parents[1] / "config" / "inventory.yaml"


def _load_inventory() -> Dict:
    if not INVENTORY_PATH.exists():
        return {}
    with open(INVENTORY_PATH, "r", encoding="utf-8") as f:
        text = f.read()
        if text.strip().startswith('```'):
            lines = [l for l in text.splitlines() if not l.strip().startswith('```')]
            text = "\n".join(lines)
        return yaml.safe_load(text) or {}


def get_datasets(stream_id: str, project_id: str, zone_id: str) -> List[Dict]:
    inv = _load_inventory()
    streams = inv.get("streams", [])
    for s in streams:
        if s.get("id") == stream_id:
            for p in s.get("projects", []):
                if p.get("id") == project_id:
                    for z in p.get("zones", []):
                        if z.get("id") == zone_id:
                            return z.get("datasets", []) or []
    return []


def get_zones(stream_id: Optional[str] = None, project_id: Optional[str] = None) -> List[Dict]:
    """Retourne les zones disponibles pour un stream/project donné.
    
    Returns:
        List de dicts avec {id, label, datasets_count}
    """
    inv = _load_inventory()
    zones_found = []
    
    for s in inv.get("streams", []):
        if stream_id and s.get("id") != stream_id:
            continue
        for p in s.get("projects", []):
            if project_id and p.get("id") != project_id:
                continue
            for z in p.get("zones", []):
                zone_id = z.get("id")
                datasets = z.get("datasets", [])
                zones_found.append({
                    "id": zone_id,
                    "label": zone_id.capitalize(),
                    "datasets_count": len(datasets)
                })
    
    return zones_found


def get_datasets_for_zone(zone_id: str, stream_id: Optional[str] = None, project_id: Optional[str] = None) -> List[Dict]:
    """Retourne les datasets pour une zone donnée."""
    inv = _load_inventory()
    results: List[Dict] = []

    for s in inv.get("streams", []):
        if stream_id and s.get("id") != stream_id:
            continue
        for p in s.get("projects", []):
            if project_id and p.get("id") != project_id:
                continue
            for z in p.get("zones", []):
                if z.get("id") == zone_id:
                    for d in z.get("datasets", []) or []:
                        item = dict(d)
                        item.update({"stream": s.get("id"), "project": p.get("id"), "zone": z.get("id")})
                        results.append(item)

    return results


def get_datasets_for_dq_point(dq_point: str, stream: Optional[str] = None, project: Optional[str] = None) -> List[Dict]:
    """DEPRECATED: Utilisez get_datasets_for_zone() à la place."""
    point_map = {
        "Extraction": ["raw"],
        "Transformation": ["trusted"],
        "Chargement": ["trusted"]
    }
    zones = point_map.get(dq_point, [])

    inv = _load_inventory()
    results: List[Dict] = []

    for s in inv.get("streams", []):
        if stream and s.get("id") != stream:
            continue
        for p in s.get("projects", []):
            if project and p.get("id") != project:
                continue
            for z in p.get("zones", []):
                if z.get("id") in zones:
                    for d in z.get("datasets", []) or []:
                        item = dict(d)
                        item.update({"stream": s.get("id"), "project": p.get("id"), "zone": z.get("id")})
                        results.append(item)

    return results


def get_stream_overview(stream_id: str) -> List[Dict]:
    """Retourne un tableau de tous les projets/zones/datasets pour un stream donné.
    
    Returns:
        List de dicts avec {project, zone, dataset, alias}
    """
    inv = _load_inventory()
    results = []
    
    for s in inv.get("streams", []):
        if s.get("id") == stream_id:
            for p in s.get("projects", []):
                project_id = p.get("id")
                for z in p.get("zones", []):
                    zone_id = z.get("id")
                    datasets = z.get("datasets", [])
                    if datasets:
                        for ds in datasets:
                            results.append({
                                "Projet": project_id,
                                "Zone": zone_id,
                                "Dataset": ds.get("name", ""),
                                "Alias": ds.get("alias", "")
                            })
                    else:
                        results.append({
                            "Projet": project_id,
                            "Zone": zone_id,
                            "Dataset": "-",
                            "Alias": "-"
                        })
    return results


def get_project_overview(stream_id: str, project_id: str) -> List[Dict]:
    """Retourne un tableau de toutes les zones/datasets pour un projet donné.
    
    Returns:
        List de dicts avec {zone, dataset, alias}
    """
    inv = _load_inventory()
    results = []
    
    for s in inv.get("streams", []):
        if s.get("id") == stream_id:
            for p in s.get("projects", []):
                if p.get("id") == project_id:
                    for z in p.get("zones", []):
                        zone_id = z.get("id")
                        datasets = z.get("datasets", [])
                        if datasets:
                            for ds in datasets:
                                results.append({
                                    "Zone": zone_id,
                                    "Dataset": ds.get("name", ""),
                                    "Alias": ds.get("alias", "")
                                })
                        else:
                            results.append({
                                "Zone": zone_id,
                                "Dataset": "-",
                                "Alias": "-"
                            })
    return results


def get_zone_overview(stream_id: str, project_id: str, zone_id: str) -> List[Dict]:
    """Retourne un tableau de tous les datasets pour une zone donnée.
    
    Returns:
        List de dicts avec {dataset, alias}
    """
    inv = _load_inventory()
    results = []
    
    for s in inv.get("streams", []):
        if s.get("id") == stream_id:
            for p in s.get("projects", []):
                if p.get("id") == project_id:
                    for z in p.get("zones", []):
                        if z.get("id") == zone_id:
                            datasets = z.get("datasets", [])
                            for ds in datasets:
                                results.append({
                                    "Dataset": ds.get("name", ""),
                                    "Alias": ds.get("alias", ""),
                                    "Source": ds.get("source", {}).get("path", "")
                                })
    return results


def get_project_tag(stream_id: str, project_id: str) -> str:
    """Retourne le tag configuré pour un projet (ex: ALMT_) ou None."""
    inv = _load_inventory()
    for s in inv.get("streams", []):
        if s.get("id") == stream_id:
            for p in s.get("projects", []):
                if p.get("id") == project_id:
                    tag = p.get("tag")
                    if tag:
                        return str(tag).upper().rstrip("_") + "_"
                    return str(project_id).upper().rstrip("_") + "_"
    return ""


def get_zone_tag(stream_id: str, project_id: str, zone_id: str) -> str:
    """Retourne le tag configuré pour une zone (ex: MACH_) ou None."""
    inv = _load_inventory()
    for s in inv.get("streams", []):
        if stream_id and s.get("id") != stream_id:
            continue
        for p in s.get("projects", []):
            if project_id and p.get("id") != project_id:
                continue
            for z in p.get("zones", []):
                if z.get("id") == zone_id:
                    tag = z.get("tag")
                    if tag:
                        return str(tag).upper().rstrip("_") + "_"
                    return str(zone_id).upper().rstrip("_") + "_"
    return ""
