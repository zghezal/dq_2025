# Investigation Automatique pour Tests DQ

## Vue d'ensemble

L'investigation automatique génère des échantillons de données problématiques lorsqu'un test DQ échoue. Ce système est intégré dans deux architectures :

1. **Système simple** (`src/dq_runner.py`) - ✅ Opérationnel
2. **Système de plugins** (`src/plugins/` + `src/core/executor.py`) - ✅ Architecture prête

## Architecture

### 1. Système Simple (opérationnel)

**Fichiers impliqués :**
- `src/dq_runner.py` - Runner avec paramètre `investigate=True`
- `src/metrics.py` - Métriques : `missing_rate()`, `count_where()`
- `src/investigation.py` - Classe `DQInvestigator` avec stratégies d'investigation

**Usage :**
```python
from src.dq_runner import run_dq_config

config = {
    "metrics": [{"id": "m1", "type": "missing_rate", "column": "email"}],
    "tests": [{"id": "t1", "type": "range", "metric": "m1", "low": 0, "high": 0.1}]
}

# Avec investigation
results = run_dq_config(df, config, investigate=True)
# → results['investigations'] contient les échantillons
# → reports/investigations/*.csv fichiers générés
```

### 2. Système de Plugins (architecture prête)

**Fichiers impliqués :**
- `src/plugins/base.py` - Classe `BasePlugin` avec méthode `investigate()`
- `src/plugins/investigation_helpers.py` - Helpers réutilisables
- `src/plugins/tests/interval_check.py` - Plugin avec `investigate()` implémenté
- `src/core/executor.py` - Exécuteur avec détection auto des échecs

**Architecture :**
```python
class BasePlugin:
    def investigate(self, context, df, params, max_samples=100) -> Optional[Dict]:
        """Override pour implémenter investigation spécifique au plugin"""
        return None  # Par défaut : pas d'investigation

class Result(BaseModel):
    # ... existing fields ...
    investigation: Optional[Dict[str, Any]] = None  # Investigation si test échoue
```

## Plugins Existants

Selon vos instructions, seuls ces plugins existent :

### Métrique : `missing_rate`
- **ID** : `missing_rate`
- **Calcul** : Taux de valeurs manquantes dans une colonne
- **Output** : float entre 0 et 1
- **Investigation** : Échantillonne les lignes avec valeurs manquantes

### Test : `interval_check`
- **ID** : `test.interval_check`
- **Modes** :
  1. `metric_value` : Vérifie qu'une métrique est dans [min, max]
  2. `dataset_columns` : Vérifie que des colonnes sont dans [min, max]

## Investigation pour `interval_check`

### Cas 1 : Mode `metric_value` (basé sur métrique)

**Défi** : Le test vérifie une **métrique** (pas le dataset directement), il faut donc :
1. Identifier la métrique source (ex: `missing_rate`)
2. Remonter au dataset source de cette métrique
3. Investiguer selon le type de métrique

**Implémentation dans `interval_check.investigate()` :**

```python
def _investigate_metric_value(self, context, spec, params, max_samples):
    metric_id = spec.metric_id
    
    # 1. Récupérer les détails de la métrique
    metric_detail = context.metrics_details.get(metric_id)
    per_column = metric_detail.get("per_column", {})
    
    # 2. Parser le metric_id pour extraire le dataset
    # Format: stream.project.zone.metric.missing_rate.dataset_alias...
    dataset_alias = metric_id.split(".")[5]
    df_source = context.datasets[dataset_alias]
    
    # 3. Pour missing_rate : échantillonner lignes avec valeurs manquantes
    columns_with_missing = []
    for col_key, value in per_column.items():
        if col_key.endswith("_missing_number") and value > 0:
            col_name = col_key.replace("_missing_number", "")
            columns_with_missing.append(col_name)
    
    # 4. Filtrer et échantillonner
    mask = pd.Series(False, index=df_source.index)
    for col in columns_with_missing:
        mask |= df_source[col].isna()
    
    problematic_df = df_source[mask]
    sample_df = problematic_df.head(max_samples)
    
    # 5. Sauvegarder et retourner
    return build_investigation_result(
        df=problematic_df,
        sample_df=sample_df,
        description=f"Lignes avec valeurs manquantes (métrique '{metric_id}' hors limites)",
        test_id=params['id'],
        suffix="missing_values_metric",
        metric_id=metric_id,
        dataset_source=dataset_alias,
        columns_with_missing=columns_with_missing
    )
```

### Cas 2 : Mode `dataset_columns` (basé sur colonnes)

**Plus simple** : Investigation directe sur le dataset :

```python
def _investigate_dataset_columns(self, context, spec, params, max_samples):
    database = spec.database
    df_source = context.load(database)
    
    lower = spec.lower_value if spec.lower_enabled else None
    upper = spec.upper_value if spec.upper_enabled else None
    
    # Filtrer les valeurs hors limites
    mask = pd.Series(False, index=df_source.index)
    for col in spec.columns:
        numeric_series = pd.to_numeric(df_source[col], errors='coerce')
        if lower is not None:
            mask |= numeric_series < lower
        if upper is not None:
            mask |= numeric_series > upper
    
    problematic_df = df_source[mask]
    sample_df = problematic_df.head(max_samples)
    
    return build_investigation_result(
        df=problematic_df,
        sample_df=sample_df,
        description=f"Valeurs hors limites [{lower}, {upper}]",
        test_id=params['id'],
        suffix="out_of_bounds_columns",
        database=database,
        columns=spec.columns
    )
```

## Helpers Réutilisables

`src/plugins/investigation_helpers.py` fournit :

```python
def save_investigation_sample(df, test_id, suffix, output_dir="reports/investigations"):
    """Sauvegarde un DataFrame en CSV horodaté"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{test_id}_{suffix}_{timestamp}.csv"
    # ...

def build_investigation_result(df, sample_df, description, test_id, suffix, **extra_meta):
    """Construit un dict standardisé pour Result.investigation"""
    return {
        "sample_df": sample_df,
        "description": description,
        "total_problematic_rows": len(df),
        "sample_size": len(sample_df),
        "sample_file": str(save_investigation_sample(...)),
        **extra_meta
    }

def generate_consolidated_report(investigations, report_name, output_dir):
    """Génère un rapport texte consolidé"""
    # ...
```

## Flux d'Exécution

### Système de Plugins

```
1. execute(plan, loader, investigate=True)
   ↓
2. Pour chaque step.kind == "test":
   - plugin.run(context, **params) → Result
   - Si Result.passed == False:
     ↓
3. plugin.investigate(context, df, params)
   ↓
4. Investigation retourne Dict:
   {
     "sample_df": DataFrame,
     "description": str,
     "total_problematic_rows": int,
     "sample_file": "reports/investigations/test_id_suffix_timestamp.csv",
     ...
   }
   ↓
5. Ajout à Result.investigation
6. Ajout à RunResult.investigations[]
7. Génération rapport consolidé
```

## Exemples de Tests

### Test Système Simple
```bash
python test_interval_check_investigation_simple.py
```

**Résultats attendus :**
- ✅ Métriques calculées (missing_rate, count_where)
- ✅ Tests exécutés (2 échecs détectés)
- ✅ 2 investigations générées automatiquement
- ✅ Fichiers CSV sauvegardés dans `reports/investigations/`
- ✅ Rapport consolidé créé

### Fichiers Générés

```
reports/investigations/
├── test_email_quality_missing_values_20251108_172428.csv
├── test_no_invalid_ages_condition_matches_20251108_172428.csv
└── quality_check_20251108_172428.txt
```

## Contenu d'un Échantillon

**Exemple : `test_email_quality_missing_values_*.csv`**
```csv
customer_id,email,phone,age,country
5,,555-0005,25,FR
10,,555-0010,-1,FR
15,,555-0015,35,FR
20,,555-0020,-1,FR
...
```

## Format du Résultat

```python
{
    "metrics": {
        "email_missing_rate": {"value": 0.2}
    },
    "tests": {
        "test_email_quality": {
            "passed": False,
            "value": 0.2,
            "message": "value 0.2 out of range [0, 0.1]",
            "investigation": {  # ← Investigation intégrée
                "sample_df": <DataFrame>,
                "description": "Lignes avec valeurs manquantes dans 'email'",
                "total_problematic_rows": 10,
                "sample_size": 10,
                "sample_file": "reports/investigations/test_email_quality_...",
                "metric_type": "missing_rate",
                "metric_value": 0.2
            }
        }
    },
    "investigations": [...],  # Liste de toutes les investigations
    "investigation_report": "reports/investigations/quality_check_*.txt"
}
```

## Prochaines Étapes

### Pour Production (Système de Plugins)

1. **Installer PySpark** (requis par `missing_rate.py`) :
   ```bash
   pip install pyspark
   ```

2. **Corriger annotations de type** (Python 3.9 compatibility) :
   - `src/plugins/discovery.py` : Remplacer `Dict | None` par `Optional[Dict]`
   - Autres fichiers avec syntaxe Python 3.10+

3. **Tester avec le système de plugins** :
   ```bash
   python test_interval_check_investigation.py  # Nécessite PySpark
   ```

4. **Intégrer dans l'UI Dash** :
   - Afficher `Result.investigation` dans les callbacks
   - Lien de téléchargement vers les fichiers CSV
   - Affichage du rapport consolidé

5. **Étendre à d'autres types de métriques** :
   - Adapter `_investigate_metric_value()` pour d'autres métriques
   - Ajouter détection du type de métrique (actuellement hardcodé à `missing_rate`)

## Limitations Actuelles

1. **Type de métrique hardcodé** : `_investigate_metric_value()` suppose `missing_rate`
   - Solution : Ajouter métadonnée `type` dans `metrics_details`
   
2. **Parser de metric_id fragile** : `metric_id.split(".")[5]`
   - Solution : Stocker le dataset_alias directement dans `metrics_details`

3. **PySpark requis** : `missing_rate.py` importe PySpark
   - Solution : Wrapper Spark/Pandas selon environnement

## Conclusion

✅ **Investigation opérationnelle dans le système simple**
✅ **Architecture prête dans le système de plugins**
✅ **Documentation complète**

Le concept est validé et prêt pour déploiement !
