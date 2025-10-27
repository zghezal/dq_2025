from typing import Annotated
from pydantic import BaseModel, Field
from src.plugins.base import BasePlugin, Result, register
from src.plugins.base_models import CommonArgs
from src.core.ui_meta import UIMeta

class RangeSpecific(BaseModel):
    # Use plain types here so ParamsModel accepts simple dicts in tests.
    # UI metadata (UIMeta) is intentionally omitted from the type annotation
    # to avoid strict pydantic interpretation during tests.
    value_from_metric: str = Field(title="Metric ID")
    low: float = Field(title="Low")
    high: float = Field(title="High")
    inclusive: bool = Field(default=True, title="Inclusif")

class Range2Params(CommonArgs):
    specific: RangeSpecific

@register
class RangeTest2(BasePlugin):
    plugin_id = "test.range2"
    label = "Value in Range (auto-UI)"
    group = "Validation"
    ParamsModel = Range2Params

    def run(self, context, **params) -> Result:
        p = self.ParamsModel(**params)
        v = context.metrics_values[p.specific.value_from_metric]
        if p.specific.inclusive:
            ok = (v >= p.specific.low) and (v <= p.specific.high)
            bounds = f"[{p.specific.low}, {p.specific.high}]"
        else:
            ok = (v > p.specific.low) and (v < p.specific.high)
            bounds = f"({p.specific.low}, {p.specific.high})"
        msg = "ok" if ok else f"value {v} out of range {bounds}"
        return Result(passed=bool(ok), value=v, message=msg)
