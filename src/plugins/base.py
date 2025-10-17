from typing import Any, Dict
from pydantic import BaseModel

class Result(BaseModel):
    passed: bool | None = None
    value: Any | None = None
    message: str | None = None
    meta: Dict[str, Any] = {}

class BasePlugin:
    plugin_id: str
    label: str
    group: str = "General"
    ParamsModel: type[BaseModel]

    @classmethod
    def schema_for_ui(cls) -> Dict[str, Any]:
        return cls.ParamsModel.model_json_schema()

    def run(self, context, **params) -> Result:
        raise NotImplementedError

REGISTRY: Dict[str, type[BasePlugin]] = {}

def register(cls: type[BasePlugin]):
    REGISTRY[cls.plugin_id] = cls
    return cls
