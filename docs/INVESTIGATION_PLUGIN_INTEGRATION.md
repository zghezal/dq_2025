# Plan d'intégration de l'investigation dans le système de plugins

## Architecture proposée

### 1. Extension du `Result` (dans `src/plugins/base.py`)

```python
class Result(BaseModel):
    passed: Optional[bool] = None
    value: Optional[Any] = None
    dataframe: Optional[Any] = None
    message: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)
    
    # NOUVEAU : Investigation
    investigation: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Échantillon de données problématiques si le test échoue"
    )
```

### 2. Nouvelle méthode abstraite dans `BasePlugin`

```python
class BasePlugin:
    # ... existing code ...
    
    def investigate(
        self, 
        context, 
        df: pd.DataFrame, 
        params: Dict[str, Any],
        max_samples: int = 100
    ) -> Optional[Dict[str, Any]]:
        """
        Génère un échantillon de données problématiques.
        
        Cette méthode est appelée automatiquement par l'executor 
        quand un test échoue (passed=False).
        
        Args:
            context: Context d'exécution
            df: DataFrame source
            params: Paramètres du plugin
            max_samples: Nombre max de lignes à échantillonner
            
        Returns:
            Dict avec:
            - sample_df: pd.DataFrame échantillon
            - description: str description
            - total_problematic_rows: int nombre total de lignes problématiques
            - sample_file: Optional[str] chemin du fichier CSV sauvegardé
            
        Note:
            Par défaut retourne None (pas d'investigation).
            Les plugins peuvent override pour implémenter leur logique.
        """
        return None
```

### 3. Modification de `executor.py`

```python
def execute(plan, loader, investigate: bool = False, investigation_dir: str = "reports/investigations") -> RunResult:
    ctx = Context(plan.alias_map, loader)
    metrics: Dict[str, Result] = {}
    tests: Dict[str, Result] = {}
    investigations: List[Dict[str, Any]] = []
    
    for step in plan.steps:
        if step.kind == "load":
            ctx.load(step.id)
        elif step.kind == "metric":
            plugin = REGISTRY[step.id]()
            res = plugin.run(ctx, **step.params)
            metrics[step.id] = res
            if res.value is not None:
                ctx.metrics_values[step.id] = res.value
        elif step.kind == "test":
            plugin = REGISTRY[step.id]()
            res = plugin.run(ctx, **step.params)
            tests[step.id] = res
            
            # NOUVEAU : Investigation automatique si le test échoue
            if investigate and not res.passed and hasattr(plugin, 'investigate'):
                # Récupérer le DataFrame source
                dataset = step.params.get('specific', {}).get('database')
                if dataset and dataset in ctx.datasets:
                    df = ctx.datasets[dataset]
                    inv_result = plugin.investigate(ctx, df, step.params)
                    if inv_result:
                        inv_result['test_id'] = step.id
                        inv_result['test_type'] = plugin.plugin_id
                        investigations.append(inv_result)
                        # Ajouter à res.investigation
                        res.investigation = inv_result
    
    # Ajouter investigations au RunResult
    result = RunResult(
        run_id=_make_run_id(), 
        metrics=metrics, 
        tests=tests,
        artifacts={'investigations': investigations} if investigations else {}
    )
    
    return result
```

### 4. Implémentation dans les plugins de test

#### Exemple : `IntervalCheck.investigate()`

```python
@register
class IntervalCheck(BasePlugin):
    plugin_id = "interval_check"
    label = "Interval Check"
    group = "Validation"
    ParamsModel = IntervalCheckParams

    def run(self, context, **params) -> Result:
        # ... existing code ...
        pass
    
    def investigate(
        self, 
        context, 
        df: pd.DataFrame, 
        params: Dict[str, Any],
        max_samples: int = 100
    ) -> Optional[Dict[str, Any]]:
        """
        Échantillonne les valeurs hors limites pour interval_check.
        
        Deux modes:
        1. metric_value: Trace back to source dataset of the metric
        2. dataset_columns: Direct investigation on columns
        """
        p = self.ParamsModel(**params)
        
        # Mode 1: metric_value - trace to dataset source
        if p.specific.metric_value:
            return self._investigate_metric_value(context, params, max_samples)
        
        # Mode 2: dataset_columns - direct column investigation
        elif p.specific.dataset_columns:
            return self._investigate_dataset_columns(df, params, max_samples)
        
        return None
    
    def _investigate_metric_value(self, context, params, max_samples):
        """Parse metric_id to find dataset source and filter problematic rows."""
        # Implementation details in src/plugins/tests/interval_check.py
        pass
    
    def _investigate_dataset_columns(self, df, params, max_samples):
        """Filter rows with values outside bounds."""
        # Implementation details in src/plugins/tests/interval_check.py
        pass
```

#### Exemple : `MissingRate` (métrique avec auto-investigation)

```python
@register
class MissingRate(BasePlugin):
    plugin_id = "missing_rate"
    # ... existing code ...
    
    def investigate(
        self, 
        context, 
        df: pd.DataFrame, 
        params: Dict[str, Any],
        max_samples: int = 100
    ) -> Optional[Dict[str, Any]]:
        """
        Échantillonne les lignes avec valeurs manquantes.
        """
        p = self.ParamsModel(**params)
        
        # Récupérer la colonne cible
        col_config = p.specific.column
        if not col_config:
            return None
        
        column = col_config if isinstance(col_config, str) else col_config[0]
        
        if column not in df.columns:
            return None
        
        # Filtrer les lignes avec valeurs manquantes
        missing_mask = df[column].isna()
        problematic_df = df[missing_mask]
        total_problematic = len(problematic_df)
        
        if total_problematic == 0:
            return None
        
        sample_df = problematic_df.head(max_samples)
        
        # Sauvegarder
        from pathlib import Path
        from datetime import datetime
        inv_dir = Path("reports/investigations")
        inv_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{params.get('id', 'metric')}_missing_values_{timestamp}.csv"
        file_path = inv_dir / filename
        sample_df.to_csv(file_path, index=False)
        
        return {
            "sample_df": sample_df,
            "description": f"Lignes avec valeurs manquantes dans '{column}'",
            "total_problematic_rows": total_problematic,
            "sample_size": len(sample_df),
            "sample_file": str(file_path),
            "column": column
        }
```

### 5. UI Dash : Affichage des investigations

Dans les callbacks de l'UI, afficher le lien vers le fichier CSV quand `res.investigation` existe :

```python
# Dans src/callbacks/dq.py ou équivalent
def render_test_result(test_id: str, result: Result):
    if not result.passed and result.investigation:
        inv = result.investigation
        return html.Div([
            html.H5(f"❌ {test_id} - FAILED"),
            html.P(result.message),
            html.Div([
                html.H6("🔍 Investigation :"),
                html.P(inv['description']),
                html.P(f"Lignes problématiques : {inv['total_problematic_rows']}"),
                html.P(f"Échantillon sauvegardé : {inv['sample_size']} lignes"),
                html.A(
                    "📥 Télécharger CSV", 
                    href=f"/download/{inv['sample_file']}", 
                    className="btn btn-primary"
                )
            ], className="investigation-box")
        ])
```

## Avantages de cette architecture

1. ✅ **Séparation des responsabilités** : Chaque plugin sait comment investiguer ses propres échecs
2. ✅ **Extensibilité** : Nouveaux plugins peuvent override `investigate()` avec leur logique spécifique
3. ✅ **Backward compatible** : `investigate()` retourne `None` par défaut, pas d'impact sur les plugins existants
4. ✅ **Standardisation** : Format uniforme via `Result.investigation`
5. ✅ **UI-ready** : Investigation disponible immédiatement dans l'interface Dash
6. ✅ **Opt-in** : `investigate=True` au niveau de `execute()`, pas de surcharge si non utilisé

## Migration progressive

1. **Phase 1** : Étendre `Result` et `BasePlugin.investigate()` (base) ✅
2. **Phase 2** : Modifier `executor.py` pour détecter les échecs et appeler `investigate()` ✅
3. **Phase 3** : Implémenter `investigate()` dans interval_check (plugin de test autorisé) ✅
4. **Phase 4** : Étendre l'UI pour afficher les investigations
5. **Phase 5** : Implémenter `investigate()` dans missing_rate (métrique autorisée)

## Fichiers à modifier

1. `src/plugins/base.py` : Ajouter `investigation` à `Result`, ajouter méthode `investigate()` ✅
2. `src/core/executor.py` : Ajouter logique d'investigation après tests échoués ✅
3. `src/plugins/tests/interval_check.py` : Implémenter `investigate()` ✅
4. `src/plugins/metrics/missing_rate.py` : Implémenter `investigate()` (optionnel)
5. `tools/run_dq.py` : Ajouter `--investigate` flag
6. `src/callbacks/dq.py` : Afficher investigations dans l'UI

## Code réutilisable

Le module `src/investigation.py` existant peut être refactorisé en helpers :

```python
# src/investigation_helpers.py
from pathlib import Path
from datetime import datetime
import pandas as pd

def save_investigation_sample(
    df: pd.DataFrame, 
    test_id: str, 
    suffix: str,
    output_dir: str = "reports/investigations"
) -> Path:
    """Helper pour sauvegarder un échantillon d'investigation."""
    inv_dir = Path(output_dir)
    inv_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{test_id}_{suffix}_{timestamp}.csv"
    file_path = inv_dir / filename
    df.to_csv(file_path, index=False)
    
    return file_path
```

Puis chaque plugin utilise ces helpers dans son `investigate()`.


---

## IMPORTANT: Plugins autoris�s

**Ce projet utilise uniquement 2 plugins :**

1. **missing_rate** (m�trique) - Calcule le taux de valeurs manquantes
2. **interval_check** (test) - Valide que m�triques/colonnes sont dans des bornes

Tous les autres plugins mentionn�s dans ce document � titre d'exemple (range_test, threshold_test, etc.) ont �t� supprim�s du projet.

Le module `src/investigation.py` a �t� simplifi� pour ne supporter que missing_rate et count_where.
Le module `src/plugins/investigation_helpers.py` fournit des helpers r�utilisables pour l'impl�mentation de `investigate()` dans les plugins autoris�s.

