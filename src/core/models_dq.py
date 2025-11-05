from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class DQContext(BaseModel):
    stream: Optional[str] = None
    project: Optional[str] = None
    zone: Optional[str] = None
    dq_point: Optional[str] = None

class DQDefinition(BaseModel):
    id: str
    label: Optional[str] = None
    context: Optional[DQContext] = None
    databases: List[Dict[str, str]] = []
    metrics: Dict[str, Dict[str, Any]] = {}  # ID comme clé au lieu de liste
    tests: Dict[str, Dict[str, Any]] = {}    # ID comme clé au lieu de liste
