from __future__ import annotations

import json
import os
from typing import Dict, Tuple, Any, List, Optional

FilterDict = Dict[Tuple[Optional[str], str, Any], bool]
DEFAULT_ROOT = os.path.dirname(__file__)

def _json_to_filter_dict(data: dict) -> FilterDict:
    """
    Convertit le JSON
      { "conditions": [{column, type, value, result}], "default": bool }
    en dict Python: { (col, "D=CODE", value): bool, (None, "else", None): bool }
    """
    filt: FilterDict = {}
    for cond in data.get("conditions", []):
        col = cond.get("column")
        typ = cond.get("type")  # "S","I","N","F","B","T"/"D"
        val = cond.get("value")
        res = bool(cond.get("result", False))
        if col is None or not isinstance(typ, str):
            continue
        filt[(col, f"D={typ.upper()}", val)] = res
    # 'else' par défaut
    filt[(None, "else", None)] = bool(data.get("default", False))
    return filt

def load_filter_from_json(file_path: str) -> FilterDict:
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return _json_to_filter_dict(data)

def load_filter_by_name(
    name: str,
    *,
    root_dir: Optional[str] = None,
    stream: Optional[str] = None,
    project: Optional[str] = None,
    zone: Optional[str] = None,
) -> FilterDict:
    """
    Ordre de recherche (hybride) :
      1) <DEFAULT_ROOT>/<stream>/<project>/<zone>/<name>.json
      2) <DEFAULT_ROOT>/definition/<name>.json
      3) <DEFAULT_ROOT>/<name>.json
      + si root_dir différent est fourni, on ajoute la même séquence à la fin
    """
    root = DEFAULT_ROOT
    candidates: List[str] = []
    if stream and project and zone:
        candidates.append(os.path.join(root, stream, project, zone, f"{name}.json"))
    candidates.append(os.path.join(root, "definition", f"{name}.json"))
    candidates.append(os.path.join(root, f"{name}.json"))

    if root_dir and os.path.abspath(root_dir) != os.path.abspath(root):
        if stream and project and zone:
            candidates.append(os.path.join(root_dir, stream, project, zone, f"{name}.json"))
        candidates.append(os.path.join(root_dir, "definition", f"{name}.json"))
        candidates.append(os.path.join(root_dir, f"{name}.json"))

    for p in candidates:
        if os.path.exists(p):
            return load_filter_from_json(p)
    raise FileNotFoundError(f"Filter '{name}' not found in: " + " | ".join(candidates))

def list_filters(
    base_dir: Optional[str] = None,
    *,
    stream: Optional[str] = None,
    project: Optional[str] = None,
    zone: Optional[str] = None,
) -> List[str]:
    """
    Retourne l’union des noms de filtres présents dans :
      - overrides   : <DEFAULT_ROOT>/<stream>/<project>/<zone>/
      - banque glob : <DEFAULT_ROOT>/definition/
      - legacy      : <DEFAULT_ROOT>/
      - et (optionnel) base_dir + base_dir/definition
    """
    names = set()

    def _collect(dirpath: str):
        if os.path.isdir(dirpath):
            for f in os.listdir(dirpath):
                if f.lower().endswith(".json"):
                    names.add(os.path.splitext(f)[0])

    if stream and project and zone:
        _collect(os.path.join(DEFAULT_ROOT, stream, project, zone))
    _collect(os.path.join(DEFAULT_ROOT, "definition"))
    _collect(DEFAULT_ROOT)

    if base_dir:
        _collect(base_dir)
        _collect(os.path.join(base_dir, "definition"))

    return sorted(names)
