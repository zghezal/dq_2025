from pydantic import BaseModel, Field
from src.plugins.base import BasePlugin, Result, register

class RangeParams(BaseModel):
    value_from_metric: str = Field(title="Metric id")
    low: float = Field(title="Low bound")
    high: float = Field(title="High bound")
    inclusive: bool = Field(default=True)

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
