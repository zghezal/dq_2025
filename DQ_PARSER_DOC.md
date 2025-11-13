# DQ Parser - Documentation

## Vue d'ensemble

Le parser DQ transforme les fichiers de configuration YAML/JSON en structures Python hiérarchiques facilement manipulables.

## Architecture

### Structure hiérarchique complète

```
DQConfig
├── id: str
├── label: Optional[str]
├── version: str
├── context: DQContext
│   ├── stream: Optional[str]
│   ├── project: Optional[str]
│   ├── zone: Optional[str]
│   └── dq_point: Optional[str]
├── globals: DQGlobals
│   ├── default_severity: str
│   ├── sample_size: int
│   ├── fail_fast: bool
│   └── timezone: str
├── databases: List[Database]
│   ├── alias: str
│   └── dataset: Optional[str]
├── metrics: Dict[str, Metric]
│   └── Metric
│       ├── metric_id: str (clé)
│       ├── type: str
│       ├── identification: MetricIdentification
│       │   └── metric_id: str
│       ├── nature: MetricNature
│       │   ├── name: Optional[str]
│       │   ├── description: Optional[str]
│       │   └── preliminary_comments: Optional[str]
│       ├── general: MetricGeneral
│       │   ├── export: bool
│       │   └── owner: Optional[str]
│       └── specific: Dict[str, Any]
└── tests: Dict[str, Test]
    └── Test
        ├── test_id: str (clé)
        ├── type: str
        ├── identification: TestIdentification
        │   ├── test_id: str
        │   ├── control_name: Optional[str]
        │   └── control_id: Optional[str]
        ├── nature: TestNature
        │   ├── name: Optional[str]
        │   ├── description: Optional[str]
        │   ├── functional_category_1: Optional[str]
        │   ├── functional_category_2: Optional[str]
        │   ├── category: Optional[str]
        │   └── preliminary_comments: Optional[str]
        ├── general: TestGeneral
        │   ├── severity: str
        │   ├── stop_on_failure: bool
        │   ├── action_on_fail: Optional[str]
        │   └── associated_metric_id: Optional[str]
        └── specific: Dict[str, Any]
```

## Utilisation

### 1. Charger une configuration

```python
from src.core.dq_parser import load_dq_config

# Charger depuis YAML
config = load_dq_config("dq/definitions/sales_complete_quality.yaml")

# Ou depuis JSON
config = load_dq_config("dq/definitions/config.json")
```

### 2. Accéder aux données

```python
# Contexte
print(config.context.stream)      # "sales_stream"
print(config.context.zone)        # "bronze"

# Lister les métriques
for metric_id in config.list_metrics():
    print(metric_id)

# Récupérer une métrique spécifique
metric = config.get_metric("M_001_missing_date")
print(metric.type)                # "missing_rate"
print(metric.specific['dataset']) # "sales_2024"
print(metric.specific['column'])  # "date"

# Récupérer un test
test = config.get_test("T_001_check_date_completeness")
print(test.general.severity)      # "high"
print(test.specific['bounds'])    # {'lower': 0.0, 'upper': 0.05}

# Récupérer une database
db = config.get_database("sales_2024")
print(db.dataset)                 # "sales_2024"
```

### 3. Itérer sur les éléments

```python
# Itérer sur toutes les métriques
for metric_id, metric in config.metrics.items():
    print(f"{metric_id}: {metric.type}")
    if metric.nature:
        print(f"  Description: {metric.nature.description}")

# Itérer sur tous les tests
for test_id, test in config.tests.items():
    print(f"{test_id}: {test.type}")
    if test.general:
        print(f"  Sévérité: {test.general.severity}")
```

### 4. Exporter la configuration

```python
# Exporter en YAML
config.to_yaml("output/config.yaml")

# Exporter en JSON
config.to_json("output/config.json")

# Obtenir un dictionnaire
config_dict = config.to_dict()
```

### 5. Afficher un résumé

```python
print(config.summary())
```

## Exemple de fichier DQ

Voir: `dq/definitions/sales_complete_quality.yaml`

## Classes principales

### DQConfig
Configuration complète avec accès à tous les éléments.

**Méthodes principales:**
- `from_yaml(file_path)`: Charge depuis YAML
- `from_json(file_path)`: Charge depuis JSON
- `to_yaml(file_path)`: Exporte en YAML
- `to_json(file_path)`: Exporte en JSON
- `get_metric(metric_id)`: Récupère une métrique
- `get_test(test_id)`: Récupère un test
- `get_database(alias)`: Récupère une database
- `list_metrics()`: Liste tous les IDs de métriques
- `list_tests()`: Liste tous les IDs de tests
- `summary()`: Affiche un résumé

### Metric
Représente une métrique DQ.

**Attributs:**
- `metric_id`: Identifiant unique
- `type`: Type de métrique (missing_rate, row_count, etc.)
- `identification`: Informations d'identification
- `nature`: Description et catégorisation
- `general`: Paramètres généraux (export, owner)
- `specific`: Paramètres spécifiques au type

### Test
Représente un test DQ.

**Attributs:**
- `test_id`: Identifiant unique
- `type`: Type de test (interval_check, etc.)
- `identification`: Informations d'identification et contrôle
- `nature`: Description et catégorisation fonctionnelle
- `general`: Paramètres généraux (severity, stop_on_failure)
- `specific`: Paramètres spécifiques au type (bounds, target_mode, etc.)

## Avantages du parser

1. **Type-safe**: Structures Python typées avec dataclasses
2. **Validation**: Chargement validé depuis YAML/JSON
3. **Navigation facile**: Accès direct aux éléments par ID
4. **Hiérarchique**: Structure en arbre cohérente
5. **Bidirectionnel**: Import et export YAML/JSON
6. **Lisible**: Code clair et documenté

## Prochaines étapes

Le parser est maintenant prêt pour:
1. **Génération de séquence d'exécution**: Transformer les métriques et tests en commandes
2. **Ordonnancement**: Déterminer l'ordre d'exécution optimal
3. **Validation**: Vérifier la cohérence des dépendances
4. **Exécution**: Lancer les calculs des métriques et tests

## Scripts de démonstration

- `demo_dq_parser.py`: Démonstration complète des fonctionnalités
- `src/core/dq_parser.py`: Module principal avec test intégré
