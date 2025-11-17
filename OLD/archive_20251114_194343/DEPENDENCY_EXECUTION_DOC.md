# Gestion des Dépendances dans l'Exécution DQ

## Vue d'ensemble

Le système d'exécution DQ gère maintenant automatiquement les dépendances entre métriques et tests. Si une dépendance échoue, les éléments dépendants sont **automatiquement SKIPPED** avec indication claire des dépendances manquantes.

## Architecture

### DQExecutor

Classe principale qui gère l'exécution avec respect des dépendances:

```python
from src.core.dependency_executor import DQExecutor, ExecutionStatus

executor = DQExecutor(sequence)
results = executor.execute(execute_function, skip_on_dependency_failure=True)
```

### Statuts d'Exécution

| Statut | Description | Usage |
|--------|-------------|-------|
| `SUCCESS` | Exécution réussie | Métriques calculées, tests passés |
| `FAIL` | Test échoué (valeur hors bornes) | Tests uniquement |
| `ERROR` | Erreur technique | Timeout, connexion, exception |
| `SKIPPED` | Dépendance échouée | Automatique si dépendance != SUCCESS |

## Fonctionnement

### 1. Vérification des Dépendances

Avant chaque exécution, le système vérifie:
- ✅ Toutes les dépendances ont été exécutées
- ✅ Toutes les dépendances ont le statut SUCCESS

Si une dépendance a échoué:
```python
{
    'status': 'SKIPPED',
    'error': 'Dépendances non satisfaites: M_002_missing_amount (ERROR)',
    'timestamp': datetime.now(),
    'failed_dependencies': ['M_002_missing_amount (ERROR)']
}
```

### 2. Ordre d'Exécution

L'exécution respecte l'ordre topologique:
```
1. Tests implicites de validation (paramètres)
2. Métriques (si validation OK)
3. Tests implicites de filtres (si définis)
4. Tests business (si métriques + validations OK)
```

### 3. Propagation des Échecs

```
M_002_missing_amount [ERROR]
    ↓
T_002_check_amount_completeness [SKIPPED]
    ↓
(Tous les éléments dépendant de T_002) [SKIPPED]
```

## Export Excel

### Onglet Métriques

Nouvelles colonnes:
- `Execution_Status`: SUCCESS, ERROR, SKIPPED
- `Error`: Détails de l'erreur ou dépendances manquantes

### Onglet Tests

Nouvelles colonnes:
- `execution_status`: SUCCESS (PASS), FAIL, ERROR, SKIPPED
- `result`: PASS, FAIL, ERROR, SKIPPED
- `error`: Message d'erreur détaillé

Pour les tests SKIPPED:
```
execution_status: SKIPPED
result: SKIPPED
error: Dépendances non satisfaites: M_002_missing_amount (ERROR)
```

## Exemple d'Utilisation

### Simulation avec Dépendances

```python
from src.core.dependency_executor import DQExecutor, ExecutionStatus

def execute_command(cmd):
    """Fonction d'exécution personnalisée"""
    if cmd.command_type == CommandType.METRIC:
        # Simuler un échec pour tester
        if cmd.element_id == 'M_002_missing_amount':
            return {
                'status': ExecutionStatus.ERROR,
                'value': None,
                'error': 'Connexion timeout',
            }
        # Succès normal
        return {
            'status': ExecutionStatus.SUCCESS,
            'value': 0.05,
            'error': '',
        }

# Exécuter avec gestion des dépendances
executor = DQExecutor(sequence)
results = executor.execute(execute_command, skip_on_dependency_failure=True)

# Obtenir les résumés
summary = executor.get_summary()
print(f"SKIPPED: {summary[ExecutionStatus.SKIPPED]}")
```

### Statistiques

```python
# Résumé global
summary = executor.get_summary()
# {'SUCCESS': 18, 'FAIL': 1, 'ERROR': 2, 'SKIPPED': 1, 'PENDING': 0}

# Résumé métriques uniquement
metrics_summary = executor.get_metrics_summary()
# {'SUCCESS': 4, 'ERROR': 1, 'SKIPPED': 0}

# Résumé tests uniquement
tests_summary = executor.get_tests_summary()
# {'SUCCESS': 14, 'FAIL': 1, 'ERROR': 1, 'SKIPPED': 1}
```

## Cas d'Usage

### 1. Test dépend d'une Métrique

```yaml
metrics:
  - metric_id: M_001_missing_date
    type: missing_rate

tests:
  - test_id: T_001_check_date
    type: interval_check
    specific:
      value_from_metric: M_001_missing_date
```

Si `M_001_missing_date` échoue → `T_001_check_date` est SKIPPED.

### 2. Métrique dépend de la Validation de Paramètres

```python
# Test implicite généré automatiquement
M_001_missing_date_implicit_param_validation → M_001_missing_date
```

Si la validation échoue → métrique SKIPPED.

### 3. Test dépend d'un Test Implicite de Filtre

```yaml
tests:
  - test_id: T_007_check_region
    type: interval_check
    specific:
      filter: "WHERE region = 'North'"
```

Tests implicites générés:
- `T_007_implicit_columns_presence` (vérifie que 'region' existe)
- `T_007_implicit_columns_type` (vérifie le type de 'region')

Si un test implicite échoue → test business SKIPPED.

## Avantages

✅ **Sécurité**: Évite d'exécuter des tests sur des métriques invalides
✅ **Traçabilité**: Colonne `error` indique exactement quelles dépendances ont échoué
✅ **Clarté**: Distinction entre FAIL (valeur hors bornes) et SKIPPED (dépendance manquante)
✅ **Automatique**: Pas besoin de gérer manuellement les dépendances
✅ **Performance**: Évite les calculs inutiles

## Configuration

### Activer/Désactiver

```python
# AVEC gestion des dépendances (recommandé)
results = executor.execute(
    execute_command, 
    skip_on_dependency_failure=True  # Défaut
)

# SANS gestion des dépendances (mode legacy)
results = executor.execute(
    execute_command,
    skip_on_dependency_failure=False  # Force l'exécution
)
```

### Gestion des Erreurs

Le système distingue:
- **ERROR**: Erreur technique (timeout, connexion, exception)
- **FAIL**: Résultat valide mais hors limites (tests)
- **SKIPPED**: Dépendance non satisfaite

Seul **SUCCESS** permet aux dépendants de s'exécuter.

## Fichiers Impliqués

- `src/core/dependency_executor.py`: DQExecutor et ExecutionStatus
- `src/core/excel_exporter.py`: Export avec colonnes execution_status et error
- `demo_excel_complete.py`: Démo avec simulation d'échecs de dépendances
- `demo_excel_export.py`: Démo simple avec gestion des dépendances

## Exemples de Sortie

### Console

```
⚙️  Simulation de l'exécution avec dépendances...
   Métriques: SUCCESS=4, ERROR=1, SKIPPED=0
   Tests: PASS=14, FAIL=1, ERROR=1, SKIPPED=1

⚠️  Gestion des dépendances:
  • Tests/métriques SKIPPED: 1

  Exemples d'éléments SKIPPED:
    - T_002_check_amount_completeness: Dépendances non satisfaites: M_002_missing_amount (ERROR)
```

### Excel

**Onglet Tests:**

| control_id | execution_status | result | error | ... |
|------------|------------------|--------|-------|-----|
| T_001 | SUCCESS | PASS | | ... |
| T_002 | SKIPPED | SKIPPED | Dépendances non satisfaites: M_002_missing_amount (ERROR) | ... |
| T_003 | FAIL | FAIL | Value 0.15 outside bounds [0, 0.1] | ... |
| T_004 | ERROR | ERROR | Runtime exception | ... |

**Onglet Métriques:**

| metric_id | Execution_Status | Value | Error | ... |
|-----------|------------------|-------|-------|-----|
| M_001 | SUCCESS | 0.05 | | ... |
| M_002 | ERROR | | Connexion timeout | ... |
| M_003 | SUCCESS | 0.03 | | ... |

## Migration depuis l'Ancien Système

### Ancien Code
```python
execution_results = simulate_execution(sequence)
```

### Nouveau Code
```python
executor = DQExecutor(sequence)
execution_results, executor = executor.execute(execute_command)

# Obtenir les statistiques
summary = executor.get_summary()
```

### Compatibilité

Le format de `execution_results` reste le même:
```python
{
    'command_id': {
        'status': 'SUCCESS' | 'FAIL' | 'ERROR' | 'SKIPPED',
        'error': str,
        'timestamp': datetime,
        ...
    }
}
```

Les clés `status` et `error` sont maintenant standardisées et utilisées par l'export Excel.
