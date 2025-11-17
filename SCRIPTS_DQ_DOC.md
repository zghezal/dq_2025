# Système de Scripts DQ

## Vue d'ensemble

Le système DQ supporte maintenant l'exécution de **scripts personnalisés** qui produisent des métriques et tests supplémentaires. Les résultats sont automatiquement agrégés avec les métriques et tests natifs dans un **seul fichier Excel**.

## Architecture

### 1. Modèle de données

**`ScriptDefinition`** (dans `src/core/models_dq.py`):
```python
class ScriptDefinition(BaseModel):
    id: str                          # ID unique du script
    label: Optional[str] = None      # Label descriptif
    path: str                        # Chemin vers le script Python
    enabled: bool = True             # Activer/désactiver
    execute_on: Literal["pre_dq", "post_dq", "independent"] = "post_dq"
    params: Dict[str, Any] = {}      # Paramètres personnalisés
```

**Moments d'exécution**:
- `pre_dq`: Avant les métriques et tests
- `post_dq`: Après les métriques et tests (par défaut)
- `independent`: Non implémenté (pour usage futur)

### 2. Format d'entrée/sortie des scripts

#### Entrée (stdin - JSON):
```json
{
  "params": {
    "threshold": 0.95,
    "check_coherence": true
  },
  "datasets": {
    "sales_2024": "sales_2024"
  },
  "metrics": {
    "M-001": 0.05
  }
}
```

#### Sortie attendue (stdout - JSON):
```json
{
  "metrics": {
    "CUSTOM_METRIC_001": {
      "value": 0.95,
      "passed": true,
      "message": "Score de complétude: 95%"
    }
  },
  "tests": {
    "CUSTOM_TEST_001": {
      "value": 0.05,
      "passed": true,
      "message": "Taux de valeurs manquantes acceptable"
    }
  }
}
```

### 3. Intégration dans le sequencer

Le parser (`src/core/parser.py`) intègre automatiquement les scripts dans le plan d'exécution:

1. **Chargement des scripts `pre_dq`**
2. Chargement des datasets
3. Exécution des métriques
4. Exécution des tests
5. **Chargement des scripts `post_dq`**

### 4. Exécution des scripts

L'executor (`src/core/executor.py`) gère l'exécution:

```python
def _execute_script(script_path: str, params: Dict, ctx: Context):
    # 1. Préparer les paramètres en JSON
    # 2. Exécuter le script avec subprocess
    # 3. Parser la sortie JSON
    # 4. Retourner les résultats
```

**Caractéristiques**:
- Timeout de 5 minutes
- Capture stdout/stderr
- Gestion d'erreurs complète
- Les métriques/tests des scripts sont automatiquement ajoutés au contexte

### 5. Export Excel unifié

Le module `src/core/simple_excel_export.py` génère un fichier Excel avec:

**Onglet "Résumé"**:
- Statistiques globales
- Compte total (métriques + tests + scripts)
- Tests passed/failed
- Investigations

**Onglet "Métriques"**:
- Métriques natives du DQ
- **+ Métriques produites par les scripts**
- Tout dans le même onglet !

**Onglet "Tests"**:
- Tests natifs du DQ
- **+ Tests produits par les scripts**
- Tout dans le même onglet !

**Onglet "Scripts"**:
- Détails d'exécution de chaque script
- Status (SUCCESS/FAILED)
- Nombre de métriques/tests générés
- Messages d'erreur si échec

## Exemple complet

### 1. Définition DQ YAML

Fichier: `dq/definitions/sales_with_script.yaml`

```yaml
id: "sales_dq_with_script"
label: "Sales DQ avec script personnalisé"

context:
  stream: "A"
  project: "P1"
  zone: "raw"
  quarter: "2025Q4"

databases:
  - alias: sales_2024
    dataset: sales_2024

metrics:
  M-001:
    type: missing_rate
    specific:
      dataset: sales_2024
      column: quantity

tests:
  T-001:
    type: interval_check
    specific:
      metric_id: "M-001"
      upper: 0.1

scripts:
  - id: "CUSTOM_SCRIPT_001"
    label: "Script DQ personnalisé"
    path: "scripts/example_custom_dq.py"
    enabled: true
    execute_on: "post_dq"
    params:
      threshold: 0.95
      check_coherence: true
```

### 2. Script Python personnalisé

Fichier: `scripts/example_custom_dq.py`

```python
#!/usr/bin/env python
import json
import sys

def main():
    # Lire les paramètres
    input_data = json.loads(sys.stdin.read())
    params = input_data.get("params", {})
    existing_metrics = input_data.get("metrics", {})
    
    # Produire des métriques
    metrics = {
        "CUSTOM_COMPLETENESS": {
            "value": 0.95,
            "passed": True,
            "message": "Score de complétude: 95.00%"
        }
    }
    
    # Produire des tests
    tests = {
        "CUSTOM_TEST_001": {
            "value": existing_metrics.get("M-001", 0),
            "passed": existing_metrics.get("M-001", 0) <= 0.10,
            "message": "Taux de valeurs manquantes acceptable"
        }
    }
    
    # Sortie JSON
    output = {"metrics": metrics, "tests": tests}
    print(json.dumps(output, indent=2))
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

### 3. Exécution

```python
from src.core.models_inventory import Inventory
from src.core.models_dq import DQDefinition
from src.core.parser import build_execution_plan
from src.core.executor import execute
from src.core.connectors import LocalReader
from src.core.simple_excel_export import export_run_result_to_excel

# Charger inventaire et DQ
inv = Inventory(**yaml.safe_load(open("config/inventory.yaml")))
dq = DQDefinition(**yaml.safe_load(open("dq/definitions/sales_with_script.yaml")))

# Construire et exécuter
plan = build_execution_plan(inv, dq)
run_result = execute(plan, loader=LocalReader(plan.alias_map))

# Exporter vers Excel
export_run_result_to_excel(
    run_result=run_result,
    output_path="reports/dq_results.xlsx",
    dq_id=dq.id,
    quarter=dq.context.dq_point,
    project=dq.context.project
)
```

### 4. Résultats

**Sortie console**:
```
📊 MÉTRIQUES:
   ✅ M-001: 0.0 - OK
   ✅ CUSTOM_COMPLETENESS: 0.95 - Score de complétude: 95.00%

🧪 TESTS:
   ✅ T-001: Missing rate within bounds
   ✅ CUSTOM_TEST_001: Taux de valeurs manquantes acceptable

📜 SCRIPTS:
   ✅ CUSTOM_SCRIPT_001:
      - Métriques ajoutées: 1
      - Tests ajoutés: 1
```

**Fichier Excel** (`reports/dq_results.xlsx`):
- Onglet "Résumé": 2 métriques, 2 tests, 1 script
- Onglet "Métriques": M-001 + CUSTOM_COMPLETENESS
- Onglet "Tests": T-001 + CUSTOM_TEST_001
- Onglet "Scripts": CUSTOM_SCRIPT_001 (SUCCESS)

## Script de test

Un script de test complet est disponible: `test_script_integration.py`

```bash
python test_script_integration.py
```

## Bonnes pratiques

### Structure d'un script DQ

```python
#!/usr/bin/env python
import json
import sys

def main():
    # 1. Lire l'entrée
    input_data = json.loads(sys.stdin.read())
    
    # 2. Traiter
    metrics = {}
    tests = {}
    
    # ... votre logique ...
    
    # 3. Produire la sortie
    output = {"metrics": metrics, "tests": tests}
    print(json.dumps(output))
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

### Gestion d'erreurs

Le script **doit**:
- Retourner un code de sortie 0 en cas de succès
- Produire un JSON valide sur stdout
- Loguer les erreurs sur stderr (optionnel)

En cas d'erreur, l'executor capture automatiquement:
- Le code de sortie
- stdout et stderr
- Le script est marqué comme FAILED

### IDs uniques

Les IDs des métriques/tests produits par les scripts **doivent être uniques**:
- Préfixer avec `CUSTOM_` ou `SCRIPT_`
- Utiliser le même format que les IDs natifs
- Exemple: `CUSTOM_METRIC_001`, `SCRIPT_COHERENCE_TEST`

## Extension future

Le système est conçu pour supporter:
- Scripts dans d'autres langages (R, Shell, etc.)
- Accès direct aux datasets via chemins de fichiers
- Métriques multi-valeurs (arrays, objects)
- Investigation automatique pour les tests de scripts
- Scripts "independent" exécutés en parallèle

## Fichiers modifiés

1. `src/core/models_dq.py` - Déjà existant (ScriptDefinition)
2. `src/core/parser.py` - Support des scripts dans le plan
3. `src/core/executor.py` - Exécution des scripts + agrégation
4. `src/core/simple_excel_export.py` - Export unifié (NOUVEAU)
5. `scripts/example_custom_dq.py` - Script exemple (NOUVEAU)
6. `dq/definitions/sales_with_script.yaml` - DQ exemple (NOUVEAU)
7. `test_script_integration.py` - Test complet (NOUVEAU)
