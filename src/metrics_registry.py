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

METRICS: Dict[str, Dict] = {
    "range": {
        "name": "Range",
        "type": "metric",
        "description": "Métrique de plage de valeurs",
        "requires_column": True,
        "params": [
            {
                "name": "dataset_filter",
                "type": "dataset",
                "label": "Dataset",
                "required": True,
                "description": "Filtre pour choisir le dataset sur lequel calculer la métrique"
            },
            {
                "name": "columns",
                "type": "columns",
                "label": "Colonnes",
                "required": True,
                "multi": True,
                "description": "Colonnes sur lesquelles calculer la plage"
            }
        ],
    }
}


def get_metric_options() -> List[Dict[str, str]]:
    # Retourne la liste d'options pour la dropdown en utilisant le champ "name"
    return [{"label": v.get("name", k), "value": k} for k, v in METRICS.items()]


def get_metric_meta(metric_type: str) -> Dict:
    return METRICS.get(metric_type, {})
