"""
Plugin Aggregation By Column - Métrique d'agrégation.

Agrège un dataset par une colonne de grouping et calcule des statistiques
sur une colonne cible. Utilise PySpark pour des calculs distribués.

Cette métrique PRODUIT un dataset avec des colonnes, donc:
- output_schema() retourne OutputSchema avec les colonnes résultantes
- run() retourne un Result avec dataframe
"""

from typing import Dict, Any
import pandas as pd
from pydantic import BaseModel, Field
from pyspark.sql import functions as F

from src.plugins.base import BasePlugin, Result, register
from src.plugins.output_schema import OutputSchema, OutputColumn


class AggregationByColumnParams(BaseModel):
    """
    Paramètres pour l'agrégation par colonne.
    
    Attributes:
        dataset: Alias du dataset source
        group_by: Colonne de grouping
        target: Colonne sur laquelle calculer les stats
    """
    dataset: str = Field(description="Dataset source")
    group_by: str = Field(description="Colonne de grouping")
    target: str = Field(description="Colonne cible pour les calculs")


@register
class AggregationByColumn(BasePlugin):
    """
    Métrique d'agrégation qui groupe par une colonne et calcule des stats avec Spark.
    
    Utilise l'API PySpark pour des agrégations distribuées sans charger toutes 
    les données en mémoire. Seul le résultat agrégé (généralement petit) est collecté.
    
    Produit un dataset avec colonnes:
    - {group_by}: valeur du groupe
    - count: nombre de lignes
    - sum_{target}: somme
    - avg_{target}: moyenne
    - min_{target}: minimum
    - max_{target}: maximum
    
    Exemple:
        # Agrégation des ventes par région
        params = {
            "dataset": "sales_2024",
            "group_by": "region",
            "target": "amount"
        }
        
        # Produit un dataset virtuel avec colonnes:
        # region, count, sum_amount, avg_amount, min_amount, max_amount
    """
    
    plugin_id = "aggregation_by_column"
    label = "Aggregation By Column"
    group = "Aggregation"
    ParamsModel = AggregationByColumnParams
    
    @classmethod
    def output_schema(cls, params: Dict[str, Any]) -> OutputSchema:
        """
        Déclare les colonnes qui seront produites.
        
        Le schéma dépend des paramètres: la colonne de grouping et la cible.
        """
        p = cls.ParamsModel(**params)
        
        # Colonnes produites:
        # 1. La colonne de grouping (type string par défaut)
        # 2. count (nombre de lignes)
        # 3-6. Stats sur la colonne cible (sum, avg, min, max)
        
        return OutputSchema(
            columns=[
                OutputColumn(
                    name=p.group_by,
                    dtype="string",
                    nullable=False,
                    description=f"Valeur de grouping ({p.group_by})"
                ),
                OutputColumn(
                    name="count",
                    dtype="int",
                    nullable=False,
                    description="Nombre de lignes dans le groupe"
                ),
                OutputColumn(
                    name=f"sum_{p.target}",
                    dtype="float",
                    nullable=True,
                    description=f"Somme de {p.target}"
                ),
                OutputColumn(
                    name=f"avg_{p.target}",
                    dtype="float",
                    nullable=True,
                    description=f"Moyenne de {p.target}"
                ),
                OutputColumn(
                    name=f"min_{p.target}",
                    dtype="float",
                    nullable=True,
                    description=f"Minimum de {p.target}"
                ),
                OutputColumn(
                    name=f"max_{p.target}",
                    dtype="float",
                    nullable=True,
                    description=f"Maximum de {p.target}"
                ),
            ]
        )
    
    def run(self, context, **params) -> Result:
        """
        Exécute l'agrégation avec Spark.
        
        Args:
            context: Context qui fournit accès aux datasets via context.load()
                    Doit retourner un pyspark.sql.DataFrame
            **params: Paramètres validés par AggregationByColumnParams
        
        Returns:
            Result avec dataframe contenant les résultats agrégés (Pandas)
        """
        p = self.ParamsModel(**params)
        
        # Charger le dataset (Spark DataFrame attendu mais on accepte pandas)
        df = context.load(p.dataset)

        # Pandas path
        if isinstance(df, pd.DataFrame):
            if p.group_by not in df.columns:
                return Result(passed=None, message=f"Colonne de grouping '{p.group_by}' introuvable", meta={"error": "group_by_not_found"})
            if p.target not in df.columns:
                return Result(passed=None, message=f"Colonne cible '{p.target}' introuvable", meta={"error": "target_not_found"})

            agg_pd = df.groupby(p.group_by).agg(
                count=(p.target, 'count'),
                **{
                    f"sum_{p.target}": (p.target, 'sum'),
                    f"avg_{p.target}": (p.target, 'mean'),
                    f"min_{p.target}": (p.target, 'min'),
                    f"max_{p.target}": (p.target, 'max')
                }
            ).reset_index()

            # Ensure column names match expected
            agg_pandas = agg_pd.rename(columns={p.group_by: p.group_by})

            # Validate schema
            expected_schema = self.output_schema(params)
            actual_columns = list(agg_pandas.columns)
            validation_errors = expected_schema.validate_actual_output(actual_columns)

            if validation_errors:
                return Result(passed=None, message=f"Schema mismatch: {validation_errors}", meta={"error": "schema_validation_failed"})

            return Result(passed=None, dataframe=agg_pandas, message=f"Aggregation complete: {len(agg_pandas)} groups", meta={"dataset": p.dataset, "group_by": p.group_by, "target": p.target, "num_groups": len(agg_pandas)})

        # Spark path
        # Vérifier que les colonnes existent
        if p.group_by not in df.columns:
            return Result(
                passed=None,
                message=f"Colonne de grouping '{p.group_by}' introuvable",
                meta={"error": "group_by_not_found"}
            )

        if p.target not in df.columns:
            return Result(
                passed=None,
                message=f"Colonne cible '{p.target}' introuvable",
                meta={"error": "target_not_found"}
            )

        # Effectuer l'agrégation avec Spark (distribué)
        agg_spark = df.groupBy(p.group_by).agg(
            F.count("*").alias("count"),
            F.sum(p.target).alias(f"sum_{p.target}"),
            F.avg(p.target).alias(f"avg_{p.target}"),
            F.min(p.target).alias(f"min_{p.target}"),
            F.max(p.target).alias(f"max_{p.target}")
        )

        # Collecter SEULEMENT le résultat agrégé (généralement petit DataFrame)
        # Conversion en Pandas pour compatibilité avec le reste du système
        agg_pandas = agg_spark.toPandas()
        
        # Valider que le dataframe correspond au schéma prédit
        expected_schema = self.output_schema(params)
        actual_columns = list(agg_pandas.columns)
        validation_errors = expected_schema.validate_actual_output(actual_columns)
        
        if validation_errors:
            return Result(
                passed=None,
                message=f"Schema mismatch: {validation_errors}",
                meta={"error": "schema_validation_failed"}
            )
        
        return Result(
            passed=None,
            dataframe=agg_pandas,
            message=f"Aggregation complete: {len(agg_pandas)} groups",
            meta={
                "dataset": p.dataset,
                "group_by": p.group_by,
                "target": p.target,
                "num_groups": len(agg_pandas)
            }
        )
