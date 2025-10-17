import pandas as pd
from typing import Dict, Any
from pydantic import BaseModel
from src.plugins.base import REGISTRY, Result

class Context:
    def __init__(self, alias_map, loader):
        self.alias_map = alias_map
        self.loader = loader
        self.datasets: Dict[str, pd.DataFrame] = {}
        self.metrics_values: Dict[str, Any] = {}

    def load(self, alias: str) -> pd.DataFrame:
        if alias not in self.datasets:
            self.datasets[alias] = self.loader(alias)
        return self.datasets[alias]

class RunResult(BaseModel):
    run_id: str
    metrics: Dict[str, Result]
    tests: Dict[str, Result]
    artifacts: Dict[str, Any] = {}

def _make_run_id():
    import time, uuid
    return f"{time.strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:8]}"

def execute(plan, loader) -> RunResult:
    ctx = Context(plan.alias_map, loader)
    metrics: Dict[str, Result] = {}
    tests: Dict[str, Result] = {}
    for step in plan.steps:
        if step.kind == "load":
            ctx.load(step.id)
        elif step.kind == "metric":
            plugin = REGISTRY[step.id]()
            res = plugin.run(ctx, **step.params)
            metrics[step.id] = res
            if res.value is not None:
                ctx.metrics_values[step.id] = res.value
        elif step.kind == "test":
            plugin = REGISTRY[step.id]()
            res = plugin.run(ctx, **step.params)
            tests[step.id] = res
        else:
            raise ValueError(f"Unknown step kind: {step.kind}")
    return RunResult(run_id=_make_run_id(), metrics=metrics, tests=tests)
