from typing import Annotated
from pydantic import BaseModel, Field
from src.plugins.base import BasePlugin, Result, register
from src.plugins.base_models import CommonArgs
from src.core.ui_meta import UIMeta

class RangeSpecific(BaseModel):
    """
    Paramètres spécifiques au test Range.
    
    Le test Range vérifie que les valeurs d'une colonne (database ou virtual dataset)
    se situent dans un intervalle [min, max].
    """
    database: Annotated[
        str, 
        UIMeta(
            group="specific",
            widget="select",
            choices_source="databases_and_metrics",
            help="Database ou métrique (virtual dataset)"
        )
    ] = Field(title="Source de données")
    
    column: Annotated[
        str, 
        UIMeta(
            group="specific",
            widget="select",
            choices_source="columns_for_database",
            help="Colonne à tester"
        )
    ] = Field(title="Colonne")
    
    low: Annotated[
        float, 
        UIMeta(
            group="specific", 
            widget="number",
            placeholder="Ex: 0",
            help="Borne minimale (min)"
        )
    ] = Field(title="Min")
    
    high: Annotated[
        float, 
        UIMeta(
            group="specific", 
            widget="number",
            placeholder="Ex: 100",
            help="Borne maximale (max)"
        )
    ] = Field(title="Max")
    
    inclusive: Annotated[
        bool, 
        UIMeta(
            group="specific", 
            widget="checkbox",
            help="Bornes inclusives [min, max] ou exclusives (min, max)"
        )
    ] = Field(default=True, title="Inclusif")

class RangeParams(CommonArgs):
    """Modèle complet pour le test Range (CommonArgs + RangeSpecific)."""
    specific: RangeSpecific

@register
class RangeTest(BasePlugin):
    plugin_id = "range"
    label = "Value in Range"
    group = "Validation"
    ParamsModel = RangeParams

    def run(self, context, **params) -> Result:
        """
        Exécute le test Range sur une colonne (database ou virtual dataset).
        
        Vérifie que toutes les valeurs de la colonne sont dans l'intervalle [low, high].
        """
        p = self.ParamsModel(**params)
        
        # Charger le dataset (normal ou virtual)
        df = context.load(p.specific.database)
        
        # Extraire la colonne
        if p.specific.column not in df.columns:
            return Result(
                passed=False,
                value=None,
                message=f"Colonne '{p.specific.column}' introuvable dans {p.specific.database}"
            )
        
        values = df[p.specific.column].dropna()
        
        if len(values) == 0:
            return Result(passed=False, value=None, message="Aucune valeur à tester (colonne vide)")
        
        # Vérifier les bornes
        if p.specific.inclusive:
            out_of_range = values[(values < p.specific.low) | (values > p.specific.high)]
            bounds = f"[{p.specific.low}, {p.specific.high}]"
        else:
            out_of_range = values[(values <= p.specific.low) | (values >= p.specific.high)]
            bounds = f"({p.specific.low}, {p.specific.high})"
        
        passed = len(out_of_range) == 0
        
        if passed:
            msg = f"✅ Toutes les valeurs ({len(values)}) sont dans {bounds}"
        else:
            msg = f"❌ {len(out_of_range)}/{len(values)} valeurs hors de {bounds}"
        
        return Result(
            passed=passed, 
            value=len(out_of_range), 
            message=msg
        )
