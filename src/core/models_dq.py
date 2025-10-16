from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class DQItem(BaseModel):
    id: str
    params: Dict[str, Any]

class DQDefinition(BaseModel):
    id: str
    label: Optional[str] = None
    databases: List[Dict[str, str]] = []
    metrics: List[DQItem] = []
    tests: List[DQItem] = []
