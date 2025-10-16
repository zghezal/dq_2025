from pydantic import BaseModel, Field
from src.plugins.base import BasePlugin, Result, register

class MissingRateParams(BaseModel):
    dataset: str = Field(title="Dataset alias")
    column: str | None = Field(default=None, title="Column")

@register
class MissingRate(BasePlugin):
    plugin_id = "missing_rate"
    label = "Missing Rate"
    group = "Profiling"
    ParamsModel = MissingRateParams

    def run(self, context, **params) -> Result:
        p = self.ParamsModel(**params)
        df = context.load(p.dataset)
        if p.column:
            rate = float(df[p.column].isna().mean())
        else:
            total = df.size or 1
            rate = float(df.isna().sum().sum()) / float(total)
        return Result(passed=None, value=rate, message="ok", meta={"dataset": p.dataset, "column": p.column})
