"""
Plugin Missing Rate - Métrique de profiling.

Calcule le taux de valeurs manquantes (NaN/NULL) pour une colonne ou un dataset entier.

Ce plugin produit une valeur scalaire simple (pas de colonnes), donc:
- output_schema() retourne None
- run() retourne un Result avec value (float entre 0.0 et 1.0)
"""

from typing import Optional
from pydantic import BaseModel, Field
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
    Métrique Missing Rate - calcule le taux de valeurs manquantes.
    
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
        Exécute le calcul de missing rate.
        
        Args:
            context: Context qui fournit accès aux datasets via context.load()
            **params: Paramètres validés par MissingRateParams
        
        Returns:
            Result avec value = taux de missing (0.0 à 1.0)
        """
        # Valider les paramètres
        p = self.ParamsModel(**params)
        
        # Charger le dataset
        df = context.load(p.dataset)
        
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
            
            total = len(df)
            if total == 0:
                rate = 0.0
            else:
                missing = df[p.column].isna().sum()
                rate = float(missing) / float(total)
        else:
            # Missing rate sur le dataset entier
            total_cells = df.size
            if total_cells == 0:
                rate = 0.0
            else:
                missing_cells = df.isna().sum().sum()
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
