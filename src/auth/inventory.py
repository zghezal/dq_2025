import yaml
from pathlib import Path
from typing import List, Dict, Optional

INVENTORY_PATH = Path(__file__).resolve().parents[1] / "config" / "inventory.yaml"


def _load_inventory() -> Dict:
    if not INVENTORY_PATH.exists():
        return {}
    with open(INVENTORY_PATH, "r", encoding="utf-8") as f:
        # inventory.yaml may have code fences in repository; be resilient
        text = f.read()
        # strip potential ```yaml fences
        if text.strip().startswith('```'):
            # remove leading/trailing fences
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


def get_datasets_for_dq_point(dq_point: str, stream: Optional[str] = None, project: Optional[str] = None) -> List[Dict]:
    """
    Map a DQ point (Extraction/Transformation/Chargement) to an inventory zone(s).
    By default:
      - Extraction -> raw
      - Transformation -> trusted
      - Chargement -> trusted

    If stream/project are provided, filter to that scope; otherwise return union across inventory.
    """
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
                        # enrich with stream/project/zone context
                        item = dict(d)
                        item.update({"stream": s.get("id"), "project": p.get("id"), "zone": z.get("id")})
                        results.append(item)

    return results
