from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from src.core.models_inventory import Inventory, LocalSource, Source
from src.core.models_dq import DQDefinition
from src.plugins.base import REGISTRY
from src.plugins.discovery import ensure_plugins_discovered

class Step(BaseModel):
    kind: str  # "load" | "metric" | "test"
    id: str
    params: Dict[str, Any] = {}

class ExecutionPlan(BaseModel):
    steps: List[Step]
    alias_map: Dict[str, Source]

def resolve_alias_map(inv: Inventory, dbs: List[Dict[str, str]], overrides: Dict[str, Any]) -> Dict[str, Source]:
    alias_map: Dict[str, Source] = {}
    needed_aliases = [d["alias"] for d in dbs]
    for stream in inv.streams:
        for proj in stream.projects:
            for zone in proj.zones:
                for ds in zone.datasets:
                    if ds.alias in needed_aliases and ds.alias not in alias_map:
                        alias_map[ds.alias] = ds.source
    for alias, src in overrides.items():
        if isinstance(src, str):
            alias_map[alias] = LocalSource(kind="local", path=src)
    return alias_map

def build_execution_plan(inv: Inventory, dq: DQDefinition, overrides: Optional[Dict[str, Any]] = None) -> ExecutionPlan:
    # S'assurer que les plugins sont découverts AVANT de vérifier REGISTRY
    ensure_plugins_discovered()
    
    alias_map = resolve_alias_map(inv, dq.databases, overrides or {})
    steps: List[Step] = []
    for db in dq.databases:
        steps.append(Step(kind="load", id=db["alias"]))
    
    # Gérer metrics comme dict (clé = id)
    if isinstance(dq.metrics, dict):
        metrics_items = list(dq.metrics.items())
    else:
        metrics_items = [(m.get('id', f'metric_{i}'), m) for i, m in enumerate(dq.metrics)]
    
    for metric_id, m in metrics_items:
        m_dict = m if isinstance(m, dict) else m.model_dump()
        # S'assurer que l'id est présent dans les paramètres
        if 'id' not in m_dict:
            m_dict['id'] = metric_id
        m_type = m_dict.get('type', m_dict.get('id'))
        assert m_type in REGISTRY, f"Unknown metric plugin: {m_type}"
        steps.append(Step(kind="metric", id=m_type, params=m_dict))
    
    # Gérer tests comme dict (clé = id)
    if isinstance(dq.tests, dict):
        tests_items = list(dq.tests.items())
    else:
        tests_items = [(t.get('id', f'test_{i}'), t) for i, t in enumerate(dq.tests)]
    
    for test_id, t in tests_items:
        t_dict = t if isinstance(t, dict) else t.model_dump()
        # S'assurer que l'id est présent dans les paramètres
        if 'id' not in t_dict:
            t_dict['id'] = test_id
        t_type = t_dict.get('type', t_dict.get('id'))
        assert t_type in REGISTRY, f"Unknown test plugin: {t_type}"
        steps.append(Step(kind="test", id=t_type, params=t_dict))
    
    return ExecutionPlan(steps=steps, alias_map=alias_map)
