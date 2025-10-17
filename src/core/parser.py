from typing import Dict, List, Any
from pydantic import BaseModel
from src.core.models_inventory import Inventory, LocalSource, Source
from src.core.models_dq import DQDefinition
from src.plugins.base import REGISTRY

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

def build_execution_plan(inv: Inventory, dq: DQDefinition, overrides: Dict[str, Any] | None = None) -> ExecutionPlan:
    alias_map = resolve_alias_map(inv, dq.databases, overrides or {})
    steps: List[Step] = []
    for db in dq.databases:
        steps.append(Step(kind="load", id=db["alias"]))
    for m in dq.metrics:
        assert m.id in REGISTRY, f"Unknown metric plugin: {m.id}"
        steps.append(Step(kind="metric", id=m.id, params=m.params))
    for t in dq.tests:
        assert t.id in REGISTRY, f"Unknown test plugin: {t.id}"
        steps.append(Step(kind="test", id=t.id, params=t.params))
    return ExecutionPlan(steps=steps, alias_map=alias_map)
