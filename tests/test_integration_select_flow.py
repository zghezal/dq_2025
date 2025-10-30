import sys
import json

sys.path.append('/workspaces/dq_2025')

from src.config import get_streams_with_labels, STREAMS
from src.inventory import get_datasets_for_zone


def test_select_flow_populates_inventory_store():
    """Simule le flux UI: select-stream -> select-project -> select-dq-point

    Le test vérifie que pour le contexte (stream=A, project=P1, zone=raw)
    la fonction d'inventaire retourne bien des datasets — équivalent à
    l'`inventory-datasets-store` rempli par les callbacks Dash.
    """
    streams = get_streams_with_labels()
    assert 'A' in streams, "Stream 'A' doit exister dans l'inventory"

    projects = streams['A'].get('projects', [])
    assert 'P1' in projects, "Project 'P1' doit exister sous le stream 'A'"

    # Contexte simulé — identique à ce que les callbacks construisent depuis l'URL
    stream_id = 'A'
    project_id = 'P1'
    zone_id = 'raw'

    datasets = get_datasets_for_zone(zone_id, stream_id=stream_id, project_id=project_id)
    assert isinstance(datasets, list), "get_datasets_for_zone doit renvoyer une liste"
    assert len(datasets) > 0, "La zone 'raw' pour A/P1 doit contenir au moins un dataset"

    # Vérifier que les items contiennent le contexte enrichi (stream/project/zone)
    first = datasets[0]
    assert first.get('stream') == stream_id
    assert first.get('project') == project_id
    assert first.get('zone') == zone_id
    assert 'alias' in first, "Chaque dataset doit avoir un alias"

    # Simuler le payload que les callbacks mettent dans le store
    store_payload = {"zone": zone_id, "datasets": datasets}
    # Le store doit contenir au moins un dataset avec alias non vide
    assert store_payload['datasets'][0]['alias']
