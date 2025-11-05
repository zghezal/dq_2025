"""Registry simple pour déclarer des métriques et leurs métadonnées.

Chaque métrique est déclarée avec :
- label : affichage
- params : liste de paramètres attendus (pour construction de formulaire UI)
- requires_column / requires_database : helpers bool
- description : brève description

Ce fichier vise à centraliser l'ajout d'une nouvelle métrique : il suffit d'ajouter
une entrée ici et l'UI pourra lister le type.
"""
from typing import List, Dict

from src.plugins.discovery import discover_all_plugins

# METRICS est maintenant construit dynamiquement à partir des plugins découverts.
# On remplit un dict utilisable par l'UI et les validateurs.
METRICS: Dict[str, Dict] = {}


def _populate_metrics_registry():
    """Remplit METRICS depuis les plugins découverts (metrics only)."""
    global METRICS
    try:
        discovered = discover_all_plugins(verbose=False, force_rescan=True)
    except Exception:
        discovered = {}

    metrics_map: Dict[str, Dict] = {}
    for pid, info in discovered.items():
        if info.category != "metrics":
            continue
        cls = info.plugin_class
        # Basic metadata
        meta = {
            "name": getattr(cls, "label", pid),
            "type": "metric",
            "description": (cls.__doc__ or "").strip().splitlines()[0] if cls.__doc__ else "",
            "requires_column": False,
            "requires_database": True,
            "params": []
        }

        # Try to infer if ParamsModel declares a 'column' field
        try:
            schema = cls.ParamsModel.model_fields if hasattr(cls.ParamsModel, 'model_fields') else None
            # Pydantic v1 compatibility: inspect model_json_schema
            if schema is None:
                js = cls.ParamsModel.model_json_schema()
                props = js.get("properties", {})
                if "column" in props:
                    meta["requires_column"] = True
                # Map params keys for lightweight UI
                for name, prop in props.items():
                    meta["params"].append({"name": name, "type": prop.get("type", "string"), "label": name})
            else:
                if "column" in schema:
                    meta["requires_column"] = True
                for name, fld in schema.items():
                    meta["params"].append({"name": name, "type": str(getattr(fld, 'annotation', 'string')), "label": name})
        except Exception:
            # best-effort: ignore failures
            pass

        metrics_map[pid] = meta

    METRICS = metrics_map


def get_metric_options() -> List[Dict[str, str]]:
    """Retourne la liste d'options pour la dropdown des métriques (discoverées)."""
    if not METRICS:
        _populate_metrics_registry()
    return [{"label": v.get("name", k), "value": k} for k, v in METRICS.items()]


def get_metric_meta(metric_type: str) -> Dict:
    if not METRICS:
        _populate_metrics_registry()
    return METRICS.get(metric_type, {})
