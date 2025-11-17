from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, field_validator, model_validator
import time


class ScriptDefinition(BaseModel):
    id: str
    label: Optional[str] = None
    path: str
    enabled: bool = True
    execute_on: Literal["pre_dq", "post_dq", "independent"] = "post_dq"
    params: Dict[str, Any] = {}


class DQContext(BaseModel):
    stream: Optional[str] = None
    project: Optional[str] = None
    zone: Optional[str] = None
    dq_point: Optional[str] = None

class DQDefinition(BaseModel):
    id: Optional[str] = None  # Optionnel, sera généré si manquant
    label: Optional[str] = None
    context: Optional[DQContext] = None
    databases: List[Dict[str, str]] = []
    metrics: Dict[str, Dict[str, Any]] = {}  # ID comme clé au lieu de liste
    tests: Dict[str, Dict[str, Any]] = {}    # ID comme clé au lieu de liste
    scripts: List[ScriptDefinition] = []
    
    @model_validator(mode='before')
    @classmethod
    def generate_id_if_missing(cls, data):
        """Génère un ID automatiquement s'il est manquant"""
        if isinstance(data, dict) and not data.get('id'):
            data['id'] = f"dq_{int(time.time())}"
        return data
