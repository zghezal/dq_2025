"""
Plugin Aggregation By Column - Métrique d'agrégation.

Agrège un dataset par une colonne de grouping et calcule des statistiques
sur une colonne cible.

Cette métrique PRODUIT un dataset avec des colonnes, donc:
- output_schema() retourne OutputSchema avec les colonnes résultantes
- run() retourne un Result avec dataframe
"""

from typing import Dict, Any
from pydantic import BaseModel, Field
import pandas as pd

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
    Métrique d'agrégation qui groupe par une colonne et calcule des stats.
    
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
        Exécute l'agrégation.
        
        Returns:
            Result avec dataframe contenant les résultats agrégés
        """
        p = self.ParamsModel(**params)
        
        # Charger le dataset
        df = context.load(p.dataset)
        
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
        
        # Effectuer l'agrégation
        agg_df = df.groupby(p.group_by).agg(
            count=(p.target, 'count'),
            sum_target=(p.target, 'sum'),
            avg_target=(p.target, 'mean'),
            min_target=(p.target, 'min'),
            max_target=(p.target, 'max')
        ).reset_index()
        
        # Renommer les colonnes pour correspondre au schéma
        agg_df.columns = [
            p.group_by,
            'count',
            f'sum_{p.target}',
            f'avg_{p.target}',
            f'min_{p.target}',
            f'max_{p.target}'
        ]
        
        # Valider que le dataframe correspond au schéma prédit
        expected_schema = self.output_schema(params)
        actual_columns = list(agg_df.columns)
        validation_errors = expected_schema.validate_actual_output(actual_columns)
        
        if validation_errors:
            return Result(
                passed=None,
                message=f"Schema mismatch: {validation_errors}",
                meta={"error": "schema_validation_failed"}
            )
        
        return Result(
            passed=None,
            dataframe=agg_df,
            message=f"Aggregation complete: {len(agg_df)} groups",
            meta={
                "dataset": p.dataset,
                "group_by": p.group_by,
                "target": p.target,
                "num_groups": len(agg_df)
            }
        )
