from typing import Annotated
from pydantic import BaseModel, Field
from src.plugins.base import BasePlugin, Result, register
from src.plugins.base_models import CommonArgs
from src.core.ui_meta import UIMeta

class RangeSpecific(BaseModel):
    value_from_metric: Annotated[str, UIMeta(group="specific", widget="select", choices_source="metrics", help="ID de métrique calculée")] = Field(title="Metric ID")
    low: Annotated[float, UIMeta(group="specific", widget="number", help="Borne basse")] = Field(title="Low")
    high: Annotated[float, UIMeta(group="specific", widget="number", help="Borne haute")] = Field(title="High")
    inclusive: Annotated[bool, UIMeta(group="specific", widget="checkbox", help="Bornes inclusives")] = Field(default=True, title="Inclusif")

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
