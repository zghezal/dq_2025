from typing import Literal, Optional
from pydantic import BaseModel

class UIMeta(BaseModel):
    """Metadata that describes how to render a field in the Builder UI."""
    group: Literal["general", "data", "specific"] = "specific"
    widget: Literal["input", "select", "multi-select", "checkbox", "code", "number"] = "input"
    choices_source: Optional[Literal["aliases", "columns", "metrics", "databases_and_metrics", "columns_for_database", "enums", "none"]] = "none"
    enum_values: Optional[list[str]] = None
    depends_on: Optional[str] = None
    placeholder: Optional[str] = None
    help: Optional[str] = None
