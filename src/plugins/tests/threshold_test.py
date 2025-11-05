# src/plugins/tests/threshold_test.py
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from src.plugins.base import BasePlugin, Result, register
from src.plugins.base_models import CommonArgs

class ThresholdSpecific(BaseModel):
    metric_id: str = Field(title="Metric ID")
    min_value: Optional[float] = Field(default=None, title="Min (incl.)")
    max_value: Optional[float] = Field(default=None, title="Max (incl.)")

class ThresholdParams(CommonArgs):
    specific: ThresholdSpecific

@register
class ThresholdTest(BasePlugin):
    plugin_id = "test.threshold"
    label = "Threshold (min/max)"
    group = "Validation"
    ParamsModel = ThresholdParams

    def run(self, context, **params) -> Result:
        p = self.ParamsModel(**params)

        # Valeur de métrique (stockée par la métrique, ex: missing_rate)
        value = getattr(context, "metrics_values", {}).get(p.specific.metric_id)
        if value is None:
            return Result(
                passed=False,
                value=None,
                message=f"Metric '{p.specific.metric_id}' introuvable ou non calculée",
            )

        reasons, passed = [], True
        if p.specific.min_value is not None and value < p.specific.min_value:
            passed = False; reasons.append(f"{value} < min {p.specific.min_value}")
        if p.specific.max_value is not None and value > p.specific.max_value:
            passed = False; reasons.append(f"{value} > max {p.specific.max_value}")

        return Result(
            passed=passed,
            value=float(value),
            message="; ".join(reasons) if reasons else "OK",
        )
