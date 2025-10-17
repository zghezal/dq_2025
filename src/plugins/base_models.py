from typing import Annotated, Optional, List
from pydantic import BaseModel, Field
from src.core.ui_meta import UIMeta

class CommonArgs(BaseModel):
    id: Annotated[str, UIMeta(group="general", widget="input", help="Identifiant unique")] = Field(title="ID")
    label: Annotated[Optional[str], UIMeta(group="general", widget="input", help="Nom affiché")] = Field(default=None, title="Label")
    description: Annotated[Optional[str], UIMeta(group="general", widget="input", help="Description")] = Field(default=None, title="Description")

class DataArgs(BaseModel):
    alias: Annotated[str, UIMeta(group="data", widget="select", choices_source="aliases", help="Alias de l'inventaire")] = Field(title="Alias")
    columns: Annotated[Optional[List[str]], UIMeta(group="data", widget="multi-select", choices_source="columns", depends_on="alias", help="Colonnes")] = Field(default=None, title="Colonnes")
    where: Annotated[Optional[str], UIMeta(group="data", widget="code", placeholder="ex: amount > 0 and status == 'OK'", help="Filtre conditionnel")] = Field(default=None, title="Filtre (where)")
