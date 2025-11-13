"""
DQ Configuration Parser

Ce module parse les fichiers de configuration DQ (YAML/JSON) et les transforme
en une structure Python hiérarchique prête pour l'exécution.

Structure:
    DQConfig
    ├── context: DQContext
    ├── globals: DQGlobals
    ├── databases: List[Database]
    ├── metrics: Dict[str, Metric]
    └── tests: Dict[str, Test]
"""

import yaml
import json
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class DQContext:
    """Contexte d'exécution de la DQ"""
    stream: Optional[str] = None
    project: Optional[str] = None
    zone: Optional[str] = None
    dq_point: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DQContext':
        return cls(
            stream=data.get('stream'),
            project=data.get('project'),
            zone=data.get('zone'),
            dq_point=data.get('dq_point')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'stream': self.stream,
            'project': self.project,
            'zone': self.zone,
            'dq_point': self.dq_point
        }


@dataclass
class DQGlobals:
    """Paramètres globaux de la configuration DQ"""
    default_severity: str = "medium"
    sample_size: int = 1000
    fail_fast: bool = False
    timezone: str = "Europe/Paris"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DQGlobals':
        return cls(
            default_severity=data.get('default_severity', 'medium'),
            sample_size=data.get('sample_size', 1000),
            fail_fast=data.get('fail_fast', False),
            timezone=data.get('timezone', 'Europe/Paris')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'default_severity': self.default_severity,
            'sample_size': self.sample_size,
            'fail_fast': self.fail_fast,
            'timezone': self.timezone
        }


@dataclass
class Database:
    """Référence à une base de données / dataset"""
    alias: str
    dataset: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Database':
        return cls(
            alias=data.get('alias', ''),
            dataset=data.get('dataset')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        result = {'alias': self.alias}
        if self.dataset:
            result['dataset'] = self.dataset
        return result


@dataclass
class MetricIdentification:
    """Identification d'une métrique"""
    metric_id: str
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MetricIdentification':
        return cls(metric_id=data.get('metric_id', ''))
    
    def to_dict(self) -> Dict[str, Any]:
        return {'metric_id': self.metric_id}


@dataclass
class MetricNature:
    """Nature / description d'une métrique"""
    name: Optional[str] = None
    description: Optional[str] = None
    preliminary_comments: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MetricNature':
        return cls(
            name=data.get('name'),
            description=data.get('description'),
            preliminary_comments=data.get('preliminary_comments')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        result = {}
        if self.name:
            result['name'] = self.name
        if self.description:
            result['description'] = self.description
        if self.preliminary_comments:
            result['preliminary_comments'] = self.preliminary_comments
        return result


@dataclass
class MetricGeneral:
    """Paramètres généraux d'une métrique"""
    export: bool = False
    owner: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MetricGeneral':
        return cls(
            export=data.get('export', False),
            owner=data.get('owner')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        result = {'export': self.export}
        if self.owner:
            result['owner'] = self.owner
        return result


@dataclass
class Metric:
    """Métrique DQ complète"""
    metric_id: str  # Clé du dictionnaire
    type: str
    identification: Optional[MetricIdentification] = None
    nature: Optional[MetricNature] = None
    general: Optional[MetricGeneral] = None
    specific: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, metric_id: str, data: Dict[str, Any]) -> 'Metric':
        return cls(
            metric_id=metric_id,
            type=data.get('type', ''),
            identification=MetricIdentification.from_dict(data.get('identification', {})) if data.get('identification') else None,
            nature=MetricNature.from_dict(data.get('nature', {})) if data.get('nature') else None,
            general=MetricGeneral.from_dict(data.get('general', {})) if data.get('general') else None,
            specific=data.get('specific', {})
        )
    
    def to_dict(self) -> Dict[str, Any]:
        result = {'type': self.type}
        if self.identification:
            result['identification'] = self.identification.to_dict()
        if self.nature:
            result['nature'] = self.nature.to_dict()
        if self.general:
            result['general'] = self.general.to_dict()
        if self.specific:
            result['specific'] = self.specific
        return result


@dataclass
class TestIdentification:
    """Identification d'un test"""
    test_id: str
    control_name: Optional[str] = None
    control_id: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TestIdentification':
        return cls(
            test_id=data.get('test_id', ''),
            control_name=data.get('control_name'),
            control_id=data.get('control_id')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        result = {'test_id': self.test_id}
        if self.control_name:
            result['control_name'] = self.control_name
        if self.control_id:
            result['control_id'] = self.control_id
        return result


@dataclass
class TestNature:
    """Nature / description d'un test"""
    name: Optional[str] = None
    description: Optional[str] = None
    functional_category_1: Optional[str] = None
    functional_category_2: Optional[str] = None
    category: Optional[str] = None
    preliminary_comments: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TestNature':
        return cls(
            name=data.get('name'),
            description=data.get('description'),
            functional_category_1=data.get('functional_category_1'),
            functional_category_2=data.get('functional_category_2'),
            category=data.get('category'),
            preliminary_comments=data.get('preliminary_comments')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        result = {}
        if self.name:
            result['name'] = self.name
        if self.description:
            result['description'] = self.description
        if self.functional_category_1:
            result['functional_category_1'] = self.functional_category_1
        if self.functional_category_2:
            result['functional_category_2'] = self.functional_category_2
        if self.category:
            result['category'] = self.category
        if self.preliminary_comments:
            result['preliminary_comments'] = self.preliminary_comments
        return result


@dataclass
class TestGeneral:
    """Paramètres généraux d'un test"""
    severity: str = "medium"
    stop_on_failure: bool = False
    action_on_fail: Optional[str] = None
    associated_metric_id: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TestGeneral':
        return cls(
            severity=data.get('severity', 'medium'),
            stop_on_failure=data.get('stop_on_failure', False),
            action_on_fail=data.get('action_on_fail'),
            associated_metric_id=data.get('associated_metric_id')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            'severity': self.severity,
            'stop_on_failure': self.stop_on_failure
        }
        if self.action_on_fail:
            result['action_on_fail'] = self.action_on_fail
        if self.associated_metric_id:
            result['associated_metric_id'] = self.associated_metric_id
        return result


@dataclass
class Test:
    """Test DQ complet"""
    test_id: str  # Clé du dictionnaire
    type: str
    identification: Optional[TestIdentification] = None
    nature: Optional[TestNature] = None
    general: Optional[TestGeneral] = None
    specific: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, test_id: str, data: Dict[str, Any]) -> 'Test':
        return cls(
            test_id=test_id,
            type=data.get('type', ''),
            identification=TestIdentification.from_dict(data.get('identification', {})) if data.get('identification') else None,
            nature=TestNature.from_dict(data.get('nature', {})) if data.get('nature') else None,
            general=TestGeneral.from_dict(data.get('general', {})) if data.get('general') else None,
            specific=data.get('specific', {})
        )
    
    def to_dict(self) -> Dict[str, Any]:
        result = {'type': self.type}
        if self.identification:
            result['identification'] = self.identification.to_dict()
        if self.nature:
            result['nature'] = self.nature.to_dict()
        if self.general:
            result['general'] = self.general.to_dict()
        if self.specific:
            result['specific'] = self.specific
        return result


@dataclass
class DQConfig:
    """Configuration DQ complète"""
    id: str
    label: Optional[str] = None
    version: str = "1.0"
    context: Optional[DQContext] = None
    globals: Optional[DQGlobals] = None
    databases: List[Database] = field(default_factory=list)
    metrics: Dict[str, Metric] = field(default_factory=dict)
    tests: Dict[str, Test] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DQConfig':
        """Parse un dictionnaire en structure DQConfig"""
        # Parse context
        context = DQContext.from_dict(data.get('context', {})) if data.get('context') else None
        
        # Parse globals
        globals_data = DQGlobals.from_dict(data.get('globals', {})) if data.get('globals') else None
        
        # Parse databases
        databases = [Database.from_dict(db) for db in data.get('databases', [])]
        
        # Parse metrics (dictionnaire avec ID comme clé)
        metrics = {}
        for metric_id, metric_data in data.get('metrics', {}).items():
            metrics[metric_id] = Metric.from_dict(metric_id, metric_data)
        
        # Parse tests (dictionnaire avec ID comme clé)
        tests = {}
        for test_id, test_data in data.get('tests', {}).items():
            tests[test_id] = Test.from_dict(test_id, test_data)
        
        return cls(
            id=data.get('id', ''),
            label=data.get('label'),
            version=data.get('version', '1.0'),
            context=context,
            globals=globals_data,
            databases=databases,
            metrics=metrics,
            tests=tests
        )
    
    @classmethod
    def from_yaml(cls, file_path: Union[str, Path]) -> 'DQConfig':
        """Charge une config depuis un fichier YAML"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)
    
    @classmethod
    def from_json(cls, file_path: Union[str, Path]) -> 'DQConfig':
        """Charge une config depuis un fichier JSON"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit la structure en dictionnaire"""
        result = {
            'id': self.id,
            'version': self.version
        }
        
        if self.label:
            result['label'] = self.label
        
        if self.context:
            result['context'] = self.context.to_dict()
        
        if self.globals:
            result['globals'] = self.globals.to_dict()
        
        if self.databases:
            result['databases'] = [db.to_dict() for db in self.databases]
        
        if self.metrics:
            result['metrics'] = {mid: m.to_dict() for mid, m in self.metrics.items()}
        
        if self.tests:
            result['tests'] = {tid: t.to_dict() for tid, t in self.tests.items()}
        
        return result
    
    def to_yaml(self, file_path: Union[str, Path]) -> None:
        """Sauvegarde la config dans un fichier YAML"""
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(self.to_dict(), f, sort_keys=False, allow_unicode=True)
    
    def to_json(self, file_path: Union[str, Path]) -> None:
        """Sauvegarde la config dans un fichier JSON"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
    
    def get_metric(self, metric_id: str) -> Optional[Metric]:
        """Récupère une métrique par son ID"""
        return self.metrics.get(metric_id)
    
    def get_test(self, test_id: str) -> Optional[Test]:
        """Récupère un test par son ID"""
        return self.tests.get(test_id)
    
    def get_database(self, alias: str) -> Optional[Database]:
        """Récupère une database par son alias"""
        return next((db for db in self.databases if db.alias == alias), None)
    
    def list_metrics(self) -> List[str]:
        """Liste tous les IDs de métriques"""
        return list(self.metrics.keys())
    
    def list_tests(self) -> List[str]:
        """Liste tous les IDs de tests"""
        return list(self.tests.keys())
    
    def summary(self) -> str:
        """Retourne un résumé de la configuration"""
        lines = [
            f"DQ Config: {self.id}",
            f"Label: {self.label or 'N/A'}",
            f"Version: {self.version}",
            f"",
            f"Context:",
            f"  - Stream: {self.context.stream if self.context else 'N/A'}",
            f"  - Project: {self.context.project if self.context else 'N/A'}",
            f"  - Zone: {self.context.zone if self.context else 'N/A'}",
            f"  - DQ Point: {self.context.dq_point if self.context else 'N/A'}",
            f"",
            f"Databases: {len(self.databases)}",
            f"Metrics: {len(self.metrics)}",
            f"Tests: {len(self.tests)}",
            f"",
            f"Metrics IDs: {', '.join(self.list_metrics())}",
            f"",
            f"Tests IDs: {', '.join(self.list_tests())}"
        ]
        return '\n'.join(lines)


# Fonction helper pour charger facilement une config
def load_dq_config(file_path: Union[str, Path]) -> DQConfig:
    """
    Charge automatiquement une config DQ depuis YAML ou JSON
    
    Args:
        file_path: Chemin vers le fichier YAML ou JSON
        
    Returns:
        DQConfig parsé
        
    Example:
        >>> config = load_dq_config("dq/definitions/sales_complete_quality.yaml")
        >>> print(config.summary())
    """
    path = Path(file_path)
    
    if path.suffix.lower() in ['.yaml', '.yml']:
        return DQConfig.from_yaml(path)
    elif path.suffix.lower() == '.json':
        return DQConfig.from_json(path)
    else:
        raise ValueError(f"Unsupported file format: {path.suffix}. Use .yaml, .yml, or .json")


if __name__ == "__main__":
    # Test du parser
    print("=" * 60)
    print("DQ Configuration Parser - Test")
    print("=" * 60)
    
    # Charger la config
    config_path = "dq/definitions/sales_complete_quality.yaml"
    print(f"\n📂 Chargement: {config_path}")
    
    config = load_dq_config(config_path)
    
    # Afficher le résumé
    print("\n" + "=" * 60)
    print(config.summary())
    print("=" * 60)
    
    # Afficher quelques détails
    print("\n📊 Détails des métriques:")
    for metric_id, metric in list(config.metrics.items())[:3]:
        print(f"\n  {metric_id}:")
        print(f"    Type: {metric.type}")
        if metric.nature:
            print(f"    Nom: {metric.nature.name}")
        if metric.specific:
            print(f"    Dataset: {metric.specific.get('dataset')}")
            print(f"    Column: {metric.specific.get('column')}")
    
    print("\n✅ Tests:")
    for test_id, test in list(config.tests.items())[:3]:
        print(f"\n  {test_id}:")
        print(f"    Type: {test.type}")
        if test.nature:
            print(f"    Nom: {test.nature.name}")
        if test.general:
            print(f"    Sévérité: {test.general.severity}")
            print(f"    Stop on failure: {test.general.stop_on_failure}")
