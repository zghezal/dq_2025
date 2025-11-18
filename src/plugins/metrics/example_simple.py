"""
Guide Minimal: Créer une Métrique DQ
=====================================

NÉCESSAIRE ET SUFFISANT pour créer une métrique:

1. Importer: BasePlugin, Result, register
2. Décorer avec @register(plugin_id="...", category="metrics")
3. Définir: plugin_id, label, group
4. Implémenter execute() qui retourne Result

C'est tout! Rien d'autre n'est obligatoire.
"""

from src.plugins.base import BasePlugin, Result, register
import pandas as pd


# ==================== EXEMPLE 1: MÉTRIQUE SIMPLE ====================
# Compte le nombre de lignes dans un dataset

@register(
    plugin_id="row_count",           # ID unique
    category="metrics"               # "metrics" ou "tests"
)
class RowCount(BasePlugin):
    """Compte simplement le nombre de lignes"""
    
    plugin_id = "row_count"          # Même ID que dans @register
    label = "Nombre de Lignes"      # Nom dans l'UI
    group = "Profiling"             # Catégorie
    
    @staticmethod
    def execute(df: pd.DataFrame, **params) -> Result:
        """
        Args:
            df: Le DataFrame à analyser
            **params: Paramètres additionnels (ignorés ici)
        
        Returns:
            Result avec le nombre de lignes
        """
        count = len(df)
        
        return Result(
            value=count,                              # La valeur calculée
            message=f"{count} lignes trouvées",      # Message descriptif
            meta={"row_count": count}                 # Métadonnées (optionnel)
        )


# ==================== EXEMPLE 2: MÉTRIQUE AVEC PARAMÈTRE ====================
# Compte les valeurs uniques dans une colonne

@register(
    plugin_id="unique_count",
    category="metrics"
)
class UniqueCount(BasePlugin):
    """Compte les valeurs uniques dans une colonne"""
    
    plugin_id = "unique_count"
    label = "Valeurs Uniques"
    group = "Profiling"
    
    @staticmethod
    def execute(df: pd.DataFrame, column: str, **params) -> Result:
        """
        Args:
            df: Le DataFrame à analyser
            column: Nom de la colonne à analyser
        
        Returns:
            Result avec le nombre de valeurs uniques
        """
        # Vérifier que la colonne existe
        if column not in df.columns:
            return Result(
                value=None,
                message=f"Colonne '{column}' introuvable",
                meta={"error": "column_not_found"}
            )
        
        # Compter les valeurs uniques
        unique_count = df[column].nunique()
        total_count = len(df)
        
        return Result(
            value=unique_count,
            message=f"{unique_count} valeurs uniques sur {total_count} lignes",
            meta={
                "column": column,
                "unique_count": unique_count,
                "total_count": total_count,
                "uniqueness_rate": unique_count / total_count if total_count > 0 else 0
            }
        )


# ==================== EXEMPLE 3: MÉTRIQUE AVEC CALCUL ====================
# Calcule la somme d'une colonne numérique

@register(
    plugin_id="column_sum",
    category="metrics"
)
class ColumnSum(BasePlugin):
    """Calcule la somme d'une colonne numérique"""
    
    plugin_id = "column_sum"
    label = "Somme de Colonne"
    group = "Aggregation"
    
    @staticmethod
    def execute(df: pd.DataFrame, column: str, **params) -> Result:
        """
        Args:
            df: Le DataFrame à analyser
            column: Colonne numérique à sommer
        
        Returns:
            Result avec la somme
        """
        try:
            # Calculer la somme (en ignorant les NaN)
            total = df[column].sum()
            count = df[column].notna().sum()  # Nombre de valeurs non-nulles
            
            return Result(
                value=float(total),
                message=f"Somme = {total:,.2f} ({count} valeurs)",
                meta={
                    "column": column,
                    "sum": float(total),
                    "non_null_count": int(count),
                    "null_count": int(df[column].isna().sum())
                }
            )
        
        except Exception as e:
            return Result(
                value=None,
                message=f"Erreur: {str(e)}",
                meta={"error": str(e)}
            )


"""
==================== UTILISATION DANS UNE DQ ====================

Dans un fichier YAML (dq/definitions/ma_dq.yaml):

```yaml
metrics:
  nombre_lignes:
    type: row_count
    dataset: sales
  
  regions_uniques:
    type: unique_count
    dataset: sales
    column: region
  
  total_ventes:
    type: column_sum
    dataset: sales
    column: amount
```

==================== C'EST TOUT! ====================

Pour activer ces métriques:
1. Redémarre l'application: python run.py
2. Elles apparaîtront automatiquement dans les dropdowns du Builder
3. Utilise-les dans tes DQ YAML ou via l'UI

RAPPEL DES ÉLÉMENTS OBLIGATOIRES:
- @register avec plugin_id et category
- Attributs: plugin_id, label, group
- Méthode: execute() qui retourne Result

Tout le reste est OPTIONNEL (ParamsModel, output_schema, etc.)
"""
