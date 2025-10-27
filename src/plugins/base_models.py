from typing import Annotated, Optional, List
from pydantic import BaseModel, Field
from src.core.ui_meta import UIMeta

class CommonArgs(BaseModel):
    # Use plain types so tests can construct Params easily. UI metadata is
    # intentionally omitted from the type annotations to avoid strict
    # pydantic interpretation during test instantiation.
    id: str = Field(title="ID")
    label: Optional[str] = Field(default=None, title="Label")
    description: Optional[str] = Field(default=None, title="Description")

class DataArgs(BaseModel):
    alias: str = Field(title="Alias")
    columns: Optional[List[str]] = Field(default=None, title="Colonnes")
    where: Optional[str] = Field(default=None, title="Filtre (where)")
