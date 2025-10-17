from typing import Annotated, Literal
from pydantic import BaseModel, Field
from src.plugins.base import BasePlugin, Result, register
from src.plugins.base_models import CommonArgs, DataArgs
from src.core.ui_meta import UIMeta

class AggSpecific(BaseModel):
    target: Annotated[str, UIMeta(group="specific", widget="select", choices_source="columns", depends_on="data.alias", help="Colonne cible")] = Field(title="Colonne cible")
    agg: Annotated[Literal["count","sum","avg","min","max"], UIMeta(group="specific", widget="select", choices_source="enums", enum_values=["count","sum","avg","min","max"], help="Fonction d'agrégation")] = Field(default="count", title="Agrégation")

class AggMetricParams(CommonArgs):
    data: DataArgs
    specific: AggSpecific

@register
class AggMetric(BasePlugin):
    plugin_id = "metric.agg"
    label = "Aggregation"
    group = "Metric"
    ParamsModel = AggMetricParams

    def run(self, context, **params) -> Result:
        p = self.ParamsModel(**params)
        # This assumes 'context.read(alias, columns, where)' exists in your runner
        df = context.read(p.data.alias, columns=p.data.columns, where=p.data.where)
        if p.specific.agg == "count":
            value = len(df)
        elif p.specific.agg == "sum":
            value = float(df[p.specific.target].sum())
        elif p.specific.agg == "avg":
            value = float(df[p.specific.target].mean())
        elif p.specific.agg == "min":
            value = float(df[p.specific.target].min())
        elif p.specific.agg == "max":
            value = float(df[p.specific.target].max())
        else:
            value = None
        return Result(passed=True, value=value, message="ok")
