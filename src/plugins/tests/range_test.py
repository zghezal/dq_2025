from typing import Annotated
from pydantic import BaseModel, Field
from src.plugins.base import BasePlugin, Result, register
from src.core.ui_meta import UIMeta

class RangeParams(BaseModel):
    value_from_metric: Annotated[
        str, 
        UIMeta(
            group="specific", 
            widget="select", 
            choices_source="metrics",
            help="Métrique à tester"
        )
    ] = Field(title="Métrique source")
    
    low: Annotated[
        float, 
        UIMeta(
            group="specific", 
            widget="number",
            placeholder="Ex: 0",
            help="Borne minimale (min)"
        )
    ] = Field(title="Min")
    
    high: Annotated[
        float, 
        UIMeta(
            group="specific", 
            widget="number",
            placeholder="Ex: 100",
            help="Borne maximale (max)"
        )
    ] = Field(title="Max")
    
    inclusive: Annotated[
        bool, 
        UIMeta(
            group="specific", 
            widget="checkbox",
            help="Bornes inclusives [min, max] ou exclusives (min, max)"
        )
    ] = Field(default=True, title="Inclusif")

@register
class RangeTest(BasePlugin):
    plugin_id = "range"
    label = "Value in Range"
    group = "Validation"
    ParamsModel = RangeParams

    def run(self, context, **params) -> Result:
        p = self.ParamsModel(**params)
        v = context.metrics_values[p.value_from_metric]
        if p.inclusive:
            ok = (v >= p.low) and (v <= p.high)
            bounds = f"[{p.low}, {p.high}]"
        else:
            ok = (v > p.low) and (v < p.high)
            bounds = f"({p.low}, {p.high})"
        msg = "ok" if ok else f"value {v} out of range {bounds}"
        return Result(passed=bool(ok), value=v, message=msg)
