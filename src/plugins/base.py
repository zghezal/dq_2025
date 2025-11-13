"""
Système de plugins pour métriques et tests DQ.

Ce module définit le contrat de base que tous les plugins doivent respecter.
Chaque métrique ou test est une classe Python qui hérite de BasePlugin.

Architecture:
- BasePlugin: classe de base abstraite
- Result: résultat d'exécution d'un plugin
- REGISTRY: dictionnaire auto-peuplé par le décorateur @register
- register(): décorateur pour enregistrer automatiquement les plugins
"""

from typing import Any, Dict, Optional, Union
from pydantic import BaseModel, Field
import pandas as pd

# Import du système de schémas de sortie
from src.plugins.output_schema import OutputSchema, VirtualDataset


class Result(BaseModel):
    """
    Résultat de l'exécution d'un plugin (métrique ou test).
    
    Un Result peut contenir soit:
    - Une valeur scalaire simple (int, float, bool, str) dans le champ 'value'
    - Un DataFrame pandas dans le champ 'dataframe' (pour les métriques qui agrègent)
    
    Attributes:
        passed: Pour un test, indique s'il a réussi (True/False). None pour une métrique.
        value: Valeur scalaire produite (ex: taux de valeurs manquantes = 0.05)
        dataframe: DataFrame produit par la métrique (optionnel)
        message: Message descriptif du résultat
        meta: Métadonnées additionnelles (params utilisés, timestamps, etc.)
        investigation: Échantillon de données problématiques (si test échoué et investigate=True)
    """
    passed: Optional[bool] = Field(
        default=None,
        description="True si test réussi, False si échec, None pour métrique"
    )
    value: Optional[Any] = Field(
        default=None,
        description="Valeur scalaire simple produite"
    )
    dataframe: Optional[Any] = Field(  # On ne peut pas typer pd.DataFrame directement avec Pydantic
        default=None,
        description="DataFrame produit (pour métriques d'agrégation)"
    )
    message: Optional[str] = Field(
        default=None,
        description="Message descriptif"
    )
    meta: Dict[str, Any] = Field(
        default_factory=dict,
        description="Métadonnées additionnelles"
    )
    investigation: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Échantillon de données problématiques si le test échoue"
    )
    
    class Config:
        arbitrary_types_allowed = True  # Permet d'avoir des pd.DataFrame
    
    def get_dataframe(self) -> Optional[pd.DataFrame]:
        """Helper pour récupérer le DataFrame avec le bon type."""
        if self.dataframe is not None and isinstance(self.dataframe, pd.DataFrame):
            return self.dataframe
        return None


class BasePlugin:
    """
    Classe de base pour tous les plugins (métriques et tests).
    
    Chaque plugin doit définir:
    - plugin_id: identifiant unique (ex: "missing_rate", "aggregation_by_region")
    - label: nom affiché dans l'UI (ex: "Missing Rate", "Aggregation by Region")
    - group: catégorie du plugin (ex: "Profiling", "Aggregation", "Validation")
    - ParamsModel: modèle Pydantic des paramètres acceptés
    - run(): méthode d'exécution
    
    Les métriques qui produisent des datasets doivent aussi définir:
    - output_schema(): déclare les colonnes produites
    """
    
    plugin_id: str
    label: str
    group: str = "General"
    ParamsModel: type[BaseModel]
    
    @classmethod
    def schema_for_ui(cls) -> Dict[str, Any]:
        """
        Retourne le schéma JSON du ParamsModel pour générer l'UI.
        
        L'UI utilise ce schéma pour construire automatiquement le formulaire
        de configuration du plugin.
        
        Returns:
            Dict compatible avec JSON Schema
        """
        return cls.ParamsModel.model_json_schema()
    
    @classmethod
    def output_schema(cls, params: Dict[str, Any]) -> Optional[OutputSchema]:
        """
        Déclare le schéma de sortie de cette métrique AVANT exécution.
        
        Cette méthode est appelée par le catalogue virtuel pour savoir quelles
        colonnes seront disponibles. Elle doit être déterministe et ne dépendre
        que des paramètres fournis (pas de I/O, pas de run).
        
        Args:
            params: Paramètres de configuration du plugin (validés par ParamsModel)
        
        Returns:
            OutputSchema si la métrique produit un dataset
            None si la métrique produit juste une valeur scalaire
        
        Note:
            Par défaut retourne None (métrique scalaire).
            Les métriques qui produisent des datasets doivent override cette méthode.
        
        Exemple:
            @classmethod
            def output_schema(cls, params: Dict[str, Any]) -> OutputSchema:
                # Cette métrique agrège par région
                return OutputSchema(
                    columns=[
                        OutputColumn(name="region", dtype="string"),
                        OutputColumn(name="total_sales", dtype="float"),
                        OutputColumn(name="avg_amount", dtype="float")
                    ]
                )
        """
        return None  # Par défaut: métrique scalaire
    
    def run(self, context, **params) -> Result:
        """
        Exécute le plugin avec les paramètres donnés.
        
        Args:
            context: Objet Context qui donne accès aux datasets et métriques précédentes
            **params: Paramètres validés par ParamsModel
        
        Returns:
            Result contenant soit value (scalaire) soit dataframe (dataset)
        
        Raises:
            NotImplementedError: Si non implémenté (classe abstraite)
        """
        raise NotImplementedError(f"{self.__class__.__name__}.run() doit être implémenté")
    
    def investigate(
        self, 
        context, 
        df: pd.DataFrame, 
        params: Dict[str, Any],
        max_samples: int = 100
    ) -> Optional[Dict[str, Any]]:
        """
        Génère un échantillon de données problématiques pour investigation.
        
        Cette méthode est appelée automatiquement par l'executor quand un test échoue
        (passed=False) et que investigate=True. Elle permet d'identifier les lignes
        responsables de l'échec du test.
        
        Args:
            context: Objet Context qui donne accès aux datasets et métriques
            df: DataFrame source sur lequel le test a été exécuté
            params: Paramètres du plugin (dict brut, pas encore validé par ParamsModel)
            max_samples: Nombre maximum de lignes à échantillonner (défaut: 100)
        
        Returns:
            Dict contenant:
            - sample_df: pd.DataFrame avec l'échantillon de lignes problématiques
            - description: str décrivant le problème détecté
            - total_problematic_rows: int nombre total de lignes problématiques
            - sample_size: int nombre de lignes dans l'échantillon
            - sample_file: str chemin du fichier CSV sauvegardé
            - ... autres métadonnées spécifiques au plugin
            
            Retourne None si:
            - Le plugin ne supporte pas l'investigation
            - Aucune ligne problématique n'est trouvée
            - Une erreur empêche l'investigation
        
        Note:
            Par défaut retourne None (pas d'investigation).
            Les plugins peuvent override cette méthode pour implémenter leur logique
            d'investigation spécifique.
        
        Exemple:
            def investigate(self, context, df, params, max_samples=100):
                # Filtrer les lignes problématiques
                problematic = df[df['value'] < 0]
                if len(problematic) == 0:
                    return None
                
                sample = problematic.head(max_samples)
                file_path = save_sample(sample, "negative_values")
                
                return {
                    "sample_df": sample,
                    "description": "Lignes avec valeurs négatives",
                    "total_problematic_rows": len(problematic),
                    "sample_size": len(sample),
                    "sample_file": str(file_path)
                }
        """
        return None  # Par défaut: pas d'investigation
    
    @classmethod
    def create_virtual_dataset(cls, metric_id: str, params: Dict[str, Any]) -> Optional[VirtualDataset]:
        """
        Crée un VirtualDataset pour cette métrique si elle produit des colonnes.
        
        Cette méthode est appelée par le catalogue virtuel pendant la phase de
        préparation (avant exécution).
        
        Args:
            metric_id: ID de la métrique (ex: "M-001")
            params: Paramètres de configuration
        
        Returns:
            VirtualDataset si la métrique produit des colonnes, sinon None
        """
        schema = cls.output_schema(params)
        if schema is None:
            return None
        return VirtualDataset.from_metric(metric_id, schema)


# Registry global qui contient tous les plugins découverts
REGISTRY: Dict[str, type[BasePlugin]] = {}


def register(cls: type[BasePlugin]):
    """
    Décorateur pour enregistrer automatiquement un plugin dans le registry.
    
    Usage:
        @register
        class MissingRate(BasePlugin):
            plugin_id = "missing_rate"
            ...
    
    Le plugin sera automatiquement ajouté à REGISTRY["missing_rate"] = MissingRate
    
    Args:
        cls: Classe du plugin à enregistrer
    
    Returns:
        La classe inchangée (permet de chaîner les décorateurs)
    """
    REGISTRY[cls.plugin_id] = cls
    return cls

# Backwards compatibility alias used by older tests/code
registry = REGISTRY


# On import, essayer de découvrir et enregistrer automatiquement les plugins
try:
    # Import local to avoid circular import at module load time in some environments
    from src.plugins.discovery import ensure_plugins_discovered
    ensure_plugins_discovered()
except Exception:
    # best-effort: tests or environments that don't support dynamic import will still work
    pass
