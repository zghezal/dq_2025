"""
Catalogue des datasets virtuels produits par les métriques.

Ce module construit et maintient le catalogue de tous les datasets virtuels
qui seront disponibles pour les tests. Il le fait en analysant les métriques
configurées AVANT leur exécution.

Le catalogue permet aux tests de référencer "virtual:M-001" exactement comme
ils référenceraient un dataset normal de l'inventory.

Usage:
    # Dans le Builder, après configuration des métriques
    catalog = VirtualCatalog()
    catalog.register_from_config(config)
    
    # Maintenant les tests peuvent voir les colonnes disponibles
    columns = catalog.get_columns("virtual:M-001")
"""

from typing import Dict, List, Optional
from src.plugins.base import REGISTRY
from src.plugins.output_schema import VirtualDataset, OutputSchema
from src.plugins.discovery import ensure_plugins_discovered


class VirtualCatalog:
    """
    Catalogue des datasets virtuels disponibles.
    
    Le catalogue se construit en deux phases:
    1. Enregistrement (register_from_config): analyse la config pour savoir 
       quelles métriques seront exécutées et quels datasets elles produiront
    2. Consultation (get_columns, list_virtual_datasets): utilisé par l'UI
       pour peupler les dropdowns et valider les configurations de tests
    
    Attributes:
        virtuals: Dict mapping alias -> VirtualDataset
    """
    
    def __init__(self):
        """Initialise un catalogue vide."""
        self.virtuals: Dict[str, VirtualDataset] = {}
        ensure_plugins_discovered()  # S'assurer que REGISTRY est peuplé
    
    def register_metric(self, metric_id: str, metric_type: str, params: Dict) -> bool:
        """
        Enregistre une métrique dans le catalogue.
        
        Si la métrique produit des colonnes (output_schema != None), crée un
        VirtualDataset correspondant.
        
        Args:
            metric_id: ID de la métrique (ex: "M-001")
            metric_type: Type de plugin (ex: "missing_rate", "aggregation")
            params: Paramètres de configuration de la métrique
        
        Returns:
            True si un dataset virtuel a été créé, False sinon
        
        Raises:
            KeyError: Si metric_type n'existe pas dans REGISTRY
        """
        if metric_type not in REGISTRY:
            raise KeyError(f"Plugin '{metric_type}' introuvable dans REGISTRY. "
                          f"Plugins disponibles: {list(REGISTRY.keys())}")
        
        plugin_class = REGISTRY[metric_type]
        virtual_ds = plugin_class.create_virtual_dataset(metric_id, params)
        
        if virtual_ds is not None:
            self.virtuals[virtual_ds.alias] = virtual_ds
            return True
        
        return False
    
    def register_from_config(self, config: Dict) -> int:
        """
        Enregistre toutes les métriques d'une configuration DQ.
        
        Parcourt la liste des métriques dans config["metrics"] et enregistre
        celles qui produisent des colonnes.
        
        Args:
            config: Configuration DQ complète (format JSON du builder)
        
        Returns:
            Nombre de datasets virtuels créés
        
        Example:
            >>> config = {
            ...     "metrics": [
            ...         {"id": "M-001", "type": "aggregation_by_region", "params": {...}},
            ...         {"id": "M-002", "type": "missing_rate", "params": {...}}
            ...     ]
            ... }
            >>> catalog = VirtualCatalog()
            >>> count = catalog.register_from_config(config)
            >>> print(f"{count} virtual datasets created")
        """
        metrics = config.get("metrics", [])
        count = 0
        
        for metric in metrics:
            metric_id = metric.get("id")
            metric_type = metric.get("type")
            params = metric.get("params", {})
            
            if not metric_id or not metric_type:
                print(f"[WARN] Metric sans id ou type: {metric}")
                continue
            
            try:
                created = self.register_metric(metric_id, metric_type, params)
                if created:
                    count += 1
                    print(f"[OK] Virtual dataset created: virtual:{metric_id}")
            except Exception as e:
                print(f"[ERROR] Failed to register metric {metric_id}: {e}")
        
        return count
    
    def get_columns(self, virtual_alias: str) -> List[str]:
        """
        Retourne les noms des colonnes d'un dataset virtuel.
        
        Args:
            virtual_alias: Alias du dataset virtuel (ex: "virtual:M-001")
        
        Returns:
            Liste des noms de colonnes
        
        Raises:
            KeyError: Si l'alias n'existe pas dans le catalogue
        """
        if virtual_alias not in self.virtuals:
            raise KeyError(f"Virtual dataset '{virtual_alias}' introuvable. "
                          f"Disponibles: {list(self.virtuals.keys())}")
        
        return self.virtuals[virtual_alias].schema.column_names()
    
    def get_schema(self, virtual_alias: str) -> OutputSchema:
        """
        Retourne le schéma complet d'un dataset virtuel.
        
        Args:
            virtual_alias: Alias du dataset virtuel
        
        Returns:
            OutputSchema avec toutes les métadonnées de colonnes
        """
        if virtual_alias not in self.virtuals:
            raise KeyError(f"Virtual dataset '{virtual_alias}' introuvable")
        
        return self.virtuals[virtual_alias].schema
    
    def list_virtual_datasets(self) -> List[str]:
        """
        Liste tous les alias de datasets virtuels disponibles.
        
        Returns:
            Liste des alias (ex: ["virtual:M-001", "virtual:M-003"])
        """
        return list(self.virtuals.keys())
    
    def exists(self, alias: str) -> bool:
        """
        Vérifie si un dataset virtuel existe.
        
        Args:
            alias: Alias à vérifier
        
        Returns:
            True si le dataset existe dans le catalogue
        """
        return alias in self.virtuals
    
    def validate_test_references(self, test_config: Dict) -> List[str]:
        """
        Valide qu'un test référence correctement un dataset virtuel.
        
        Vérifie que:
        - Si le test référence un dataset "virtual:XXX", il existe dans le catalogue
        - Si le test référence une colonne, elle existe dans le schéma du dataset
        
        Args:
            test_config: Configuration d'un test
        
        Returns:
            Liste des erreurs de validation (vide si OK)
        
        Example:
            >>> test = {
            ...     "id": "T-001",
            ...     "type": "range",
            ...     "database": "virtual:M-001",
            ...     "column": "total_sales"
            ... }
            >>> errors = catalog.validate_test_references(test)
            >>> if errors:
            ...     print("Validation failed:", errors)
        """
        errors = []
        
        database = test_config.get("database")
        if database and database.startswith("virtual:"):
            # Le test référence un dataset virtuel
            if not self.exists(database):
                errors.append(f"Dataset virtuel '{database}' introuvable")
                return errors  # Pas la peine de valider la colonne si le dataset n'existe pas
            
            # Vérifier la colonne
            column = test_config.get("column")
            if column:
                try:
                    available_columns = self.get_columns(database)
                    if column not in available_columns:
                        errors.append(
                            f"Colonne '{column}' introuvable dans {database}. "
                            f"Colonnes disponibles: {available_columns}"
                        )
                except Exception as e:
                    errors.append(f"Erreur validation colonne: {e}")
        
        return errors
    
    def to_dict(self) -> Dict:
        """
        Exporte le catalogue en format dict (pour JSON/YAML).
        
        Returns:
            Dict avec la structure complète du catalogue
        """
        return {
            "virtual_datasets": [
                {
                    "alias": vd.alias,
                    "source_metric_id": vd.source_metric_id,
                    "columns": [
                        {
                            "name": col.name,
                            "dtype": col.dtype,
                            "nullable": col.nullable,
                            "description": col.description
                        }
                        for col in vd.schema.columns
                    ]
                }
                for vd in self.virtuals.values()
            ]
        }
    
    def clear(self):
        """Vide le catalogue (utile pour les tests)."""
        self.virtuals.clear()
