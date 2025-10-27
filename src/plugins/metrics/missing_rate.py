"""
Plugin Missing Rate - Métrique de profiling.

Calcule le taux de valeurs manquantes (NaN/NULL) pour une colonne ou un dataset entier.
Utilise PySpark pour des calculs distribués.

Ce plugin produit une valeur scalaire simple (pas de colonnes), donc:
- output_schema() retourne None
- run() retourne un Result avec value (float entre 0.0 et 1.0)
"""

from typing import Optional
import pandas as pd
from pydantic import BaseModel, Field
from pyspark.sql import functions as F
from src.plugins.base import BasePlugin, Result, register


class MissingRateParams(BaseModel):
    """
    Paramètres pour la métrique Missing Rate.
    
    Attributes:
        dataset: Alias du dataset à analyser
        column: Nom de la colonne (optionnel, si None analyse tout le dataset)
    """
    dataset: str = Field(
        description="Alias du dataset à analyser (depuis l'inventory)"
    )
    column: Optional[str] = Field(
        default=None,
        description="Colonne spécifique à analyser (optionnel, si None = tout le dataset)"
    )


@register
class MissingRate(BasePlugin):
    """
    Métrique Missing Rate - calcule le taux de valeurs manquantes avec Spark.
    
    Utilise l'API PySpark pour des calculs distribués sans charger les données en mémoire.
    
    Exemples d'usage:
        # Taux de missing sur une colonne spécifique
        params = {"dataset": "sales_2024", "column": "amount"}
        result = MissingRate().run(context, **params)
        print(f"Missing rate: {result.value:.2%}")
        
        # Taux de missing sur le dataset entier
        params = {"dataset": "sales_2024", "column": None}
        result = MissingRate().run(context, **params)
    """
    
    plugin_id = "missing_rate"
    label = "Missing Rate"
    group = "Profiling"
    ParamsModel = MissingRateParams
    
    # Cette métrique produit une valeur scalaire, pas de colonnes
    # Donc output_schema() n'est pas override (reste à None par défaut)
    
    def run(self, context, **params) -> Result:
        """
        Exécute le calcul de missing rate avec Spark.
        
        Args:
            context: Context qui fournit accès aux datasets via context.load()
                    Doit retourner un pyspark.sql.DataFrame
            **params: Paramètres validés par MissingRateParams
        
        Returns:
            Result avec value = taux de missing (0.0 à 1.0)
        """
        # Valider les paramètres
        p = self.ParamsModel(**params)
        
        # Charger le dataset (Spark DataFrame attendu, mais on accepte aussi pandas)
        df = context.load(p.dataset)

        # Support pandas DataFrame for tests/mocks
        if isinstance(df, pd.DataFrame):
            # pandas path
            if p.column:
                if p.column not in df.columns:
                    return Result(passed=None, value=None, message=f"Colonne '{p.column}' introuvable dans {p.dataset}", meta={"error": "column_not_found"})
                total = len(df)
                missing = int(df[p.column].isnull().sum())
                rate = 0.0 if total == 0 else float(missing) / float(total)
            else:
                total_rows = len(df)
                if total_rows == 0:
                    rate = 0.0
                else:
                    missing_cells = int(df.isnull().sum().sum())
                    total_cells = total_rows * len(df.columns)
                    rate = float(missing_cells) / float(total_cells)

            return Result(passed=None, value=rate, message=f"Missing rate: {rate:.2%}", meta={"dataset": p.dataset, "column": p.column, "rate": rate})

        # Spark path
        # Calculer le taux de missing
        if p.column:
            # Missing rate sur une colonne spécifique
            if p.column not in df.columns:
                return Result(
                    passed=None,
                    value=None,
                    message=f"Colonne '{p.column}' introuvable dans {p.dataset}",
                    meta={"error": "column_not_found"}
                )

            # Compter total et nulls avec Spark en UNE SEULE passe
            stats = df.agg(
                F.count("*").alias("total"),
                F.sum(
                    F.when(F.col(p.column).isNull(), 1).otherwise(0)
                ).alias("missing")
            ).collect()[0]

            total = stats["total"]
            missing = stats["missing"]

            if total == 0:
                rate = 0.0
            else:
                rate = float(missing) / float(total)

        else:
            # Missing rate sur le dataset entier (Spark)
            total_rows = df.count()

            if total_rows == 0:
                rate = 0.0
            else:
                # Pour chaque colonne, compter les nulls
                null_counts = []
                for col_name in df.columns:
                    null_count = df.filter(F.col(col_name).isNull()).count()
                    null_counts.append(null_count)

                total_cells = total_rows * len(df.columns)
                missing_cells = sum(null_counts)
                rate = float(missing_cells) / float(total_cells)
        
        return Result(
            passed=None,  # C'est une métrique, pas un test
            value=rate,
            message=f"Missing rate: {rate:.2%}",
            meta={
                "dataset": p.dataset,
                "column": p.column,
                "rate": rate
            }
        )
