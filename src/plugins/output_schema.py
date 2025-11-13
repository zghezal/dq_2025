"""
Système de schémas de sortie pour les métriques.

Ce module permet aux métriques de déclarer quelles colonnes elles vont produire
AVANT leur exécution. Cela permet au système de construire un catalogue de 
"datasets virtuels" que les tests peuvent référencer.

Exemple d'usage:
    class MyAggregationMetric(BasePlugin):
        @classmethod
        def output_schema(cls, params: dict) -> Optional[OutputSchema]:
            # Cette métrique produit un dataset avec 3 colonnes
            return OutputSchema(
                columns=[
                    OutputColumn(name="region", dtype="string"),
                    OutputColumn(name="total_sales", dtype="float"),
                    OutputColumn(name="avg_amount", dtype="float")
                ]
            )
"""

from typing import Literal, Optional, List
from pydantic import BaseModel, Field


class OutputColumn(BaseModel):
    """
    Description d'une colonne produite par une métrique.
    
    Attributes:
        name: Nom de la colonne (doit être un identifiant SQL valide)
        dtype: Type de données ("string", "int", "float", "bool", "date")
        nullable: Si True, la colonne peut contenir des valeurs NULL
        description: Description optionnelle pour l'UI
    """
    name: str = Field(description="Nom de la colonne")
    dtype: Literal["string", "int", "float", "bool", "date"] = Field(
        description="Type de données SQL"
    )
    nullable: bool = Field(default=True, description="La colonne accepte-t-elle NULL?")
    description: Optional[str] = Field(
        default=None,
        description="Description pour l'utilisateur"
    )


class OutputSchema(BaseModel):
    """
    Schéma complet de sortie d'une métrique.
    
    Une métrique peut produire:
    - Soit une valeur scalaire unique (output_schema renvoie None)
    - Soit un dataset avec plusieurs lignes et colonnes (output_schema renvoie OutputSchema)
    
    Attributes:
        columns: Liste des colonnes produites
        estimated_row_count: Estimation du nombre de lignes (optionnel, pour l'UI)
    """
    columns: List[OutputColumn] = Field(
        description="Colonnes produites par cette métrique"
    )
    estimated_row_count: Optional[int] = Field(
        default=None,
        description="Estimation du nombre de lignes (optionnel)"
    )
    
    def column_names(self) -> List[str]:
        """Retourne juste les noms des colonnes, pratique pour les dropdowns."""
        return [col.name for col in self.columns]
    
    def validate_actual_output(self, actual_columns: List[str]) -> List[str]:
        """
        Valide que les colonnes réellement produites correspondent au schéma.
        
        Args:
            actual_columns: Noms des colonnes effectivement produites lors du run
            
        Returns:
            Liste des erreurs de validation (vide si tout est OK)
        """
        errors = []
        expected = set(self.column_names())
        actual = set(actual_columns)
        
        # Colonnes manquantes
        missing = expected - actual
        if missing:
            errors.append(f"Colonnes manquantes: {sorted(missing)}")
        
        # Colonnes inattendues
        extra = actual - expected
        if extra:
            errors.append(f"Colonnes inattendues: {sorted(extra)}")
        
        return errors


class VirtualDataset(BaseModel):
    """
    Représente un dataset virtuel créé par une métrique.
    
    Ce dataset n'existe pas physiquement dans l'inventory, mais le système
    le traite comme un vrai dataset pour la configuration des tests.
    
    Attributes:
        alias: Alias du dataset virtuel (format: "virtual:M-001")
        source_metric_id: ID de la métrique qui produit ce dataset
        schema: Schéma des colonnes disponibles
    """
    alias: str = Field(description="Alias du dataset virtuel")
    source_metric_id: str = Field(description="ID de la métrique source")
    schema: OutputSchema = Field(description="Schéma de sortie")
    
    @classmethod
    def from_metric(cls, metric_id: str, schema: OutputSchema) -> "VirtualDataset":
        """
        Crée un VirtualDataset à partir d'un ID de métrique et son schéma.
        
        Args:
            metric_id: ID de la métrique (ex: "M-001")
            schema: Schéma de sortie de la métrique
            
        Returns:
            VirtualDataset avec l'alias "virtual:{metric_id}"
        """
        return cls(
            alias=f"virtual:{metric_id}",
            source_metric_id=metric_id,
            schema=schema
        )
