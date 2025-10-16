from typing import List, Optional, Literal, Union
from pydantic import BaseModel, Field

class LocalSource(BaseModel):
    kind: Literal["local"] = "local"
    path: str

class DataikuSource(BaseModel):
    kind: Literal["dataiku"] = "dataiku"
    project_key: str
    dataset: str

class SharePointSource(BaseModel):
    kind: Literal["sharepoint"] = "sharepoint"
    site: str
    drive: str
    path: str

Source = Union[LocalSource, DataikuSource, SharePointSource]

class Dataset(BaseModel):
    alias: str
    name: str
    source: Source

class Zone(BaseModel):
    id: str
    datasets: List[Dataset] = Field(default_factory=list)

class Project(BaseModel):
    id: str
    zones: List[Zone] = Field(default_factory=list)

class Stream(BaseModel):
    id: str
    label: Optional[str] = None
    projects: List[Project] = Field(default_factory=list)

class Inventory(BaseModel):
    streams: List[Stream] = Field(default_factory=list)
