"""
Adaptateur pour charger les datasets de l'inventory dans le SparkDQContext.

Ce module traduit les définitions de datasets de inventory.yaml en entrées 
du catalog Spark, permettant un chargement à la volée des données.
"""

from typing import Dict, List, Optional
from src.context.spark_context import SparkDQContext
import logging

logger = logging.getLogger(__name__)


def build_spark_catalog_from_inventory(datasets: List[dict]) -> Dict[str, str]:
    """
    Construit un dictionnaire catalog compatible SparkDQContext depuis des datasets inventory.
    
    Args:
        datasets: Liste de datasets de l'inventory (format: get_datasets_for_zone())
                  Chaque dataset contient {alias, name, source: {kind, path}}
    
    Returns:
        Dictionnaire {alias: source_path} pour SparkDQContext.catalog
        
    Exemples:
        >>> datasets = [
        ...     {"alias": "sales", "name": "sales.csv", 
        ...      "source": {"kind": "local", "path": "sourcing/input/sales.csv"}},
        ...     {"alias": "customers", "name": "customers.parquet",
        ...      "source": {"kind": "local", "path": "sourcing/input/customers.parquet"}}
        ... ]
        >>> catalog = build_spark_catalog_from_inventory(datasets)
        >>> catalog
        {'sales': 'sourcing/input/sales.csv', 'customers': 'sourcing/input/customers.parquet'}
    """
    catalog = {}
    
    for dataset in datasets:
        alias = dataset.get("alias")
        source = dataset.get("source", {})
        kind = source.get("kind")
        path = source.get("path")
        
        if not alias:
            logger.warning(f"Dataset sans alias trouvé: {dataset}")
            continue
            
        if kind == "local" and path:
            # Pour sources locales (fichiers parquet/csv)
            catalog[alias] = path
            logger.debug(f"Dataset '{alias}' → '{path}'")
        
        elif kind == "hive" and source.get("table"):
            # Pour tables Hive/Delta (format: "database.table")
            table_name = source.get("table")
            catalog[alias] = table_name
            logger.debug(f"Dataset '{alias}' → table '{table_name}'")
        
        else:
            logger.warning(f"Source non supportée pour '{alias}': {source}")
    
    logger.info(f"✅ Catalog Spark construit avec {len(catalog)} datasets: {list(catalog.keys())}")
    return catalog


def register_inventory_datasets_in_spark(
    spark_ctx: SparkDQContext, 
    datasets: List[dict]
) -> None:
    """
    Enregistre les datasets de l'inventory dans le catalog Spark existant.
    
    Cette fonction met à jour le catalog du SparkDQContext avec les nouveaux datasets
    de la zone sélectionnée, permettant aux callbacks Builder d'accéder aux schémas Spark.
    
    IMPORTANT: Invalide le cache Spark pour les alias modifiés afin d'éviter de servir
    des données périmées si une zone réutilise un alias avec une source différente.
    
    Args:
        spark_ctx: Instance de SparkDQContext (récupérée depuis app.server.spark_context)
        datasets: Liste de datasets depuis get_datasets_for_zone()
    
    Exemples:
        >>> from flask import current_app
        >>> spark_ctx = current_app.spark_context
        >>> datasets = get_datasets_for_zone("raw", "A", "P1")
        >>> register_inventory_datasets_in_spark(spark_ctx, datasets)
        # Les datasets sont maintenant accessibles via spark_ctx.load(alias)
    """
    if not spark_ctx:
        logger.error("⚠️ Aucun SparkDQContext disponible, impossible d'enregistrer les datasets")
        return
    
    catalog_entries = build_spark_catalog_from_inventory(datasets)
    
    # Invalider le cache pour les alias qui vont être mis à jour
    # (évite de servir des données périmées si un alias change de source)
    for alias in catalog_entries.keys():
        if alias in spark_ctx._cache:
            logger.info(f"🧹 Invalidation du cache pour '{alias}' (source mise à jour)")
            spark_ctx._cache[alias].unpersist()
            del spark_ctx._cache[alias]
    
    # Mettre à jour le catalog existant (écrase les anciennes entrées)
    spark_ctx.catalog.update(catalog_entries)
    
    logger.info(
        f"🔄 Catalog Spark mis à jour : {len(catalog_entries)} datasets enregistrés. "
        f"Total dans le catalog: {len(spark_ctx.catalog)}"
    )


def get_columns_from_spark(
    spark_ctx: Optional[SparkDQContext],
    alias: str
) -> List[str]:
    """
    Récupère les colonnes d'un dataset depuis Spark (pas depuis fichier statique).
    
    Args:
        spark_ctx: Instance de SparkDQContext
        alias: Alias du dataset (ex: "sales_2024")
    
    Returns:
        Liste des noms de colonnes
        
    Raises:
        ValueError: Si le dataset n'est pas dans le catalog Spark
    """
    if not spark_ctx:
        raise ValueError("SparkDQContext non disponible")
    
    try:
        columns = spark_ctx.get_columns(alias)
        logger.info(f"📊 Colonnes récupérées pour '{alias}': {columns}")
        return columns
    except ValueError as e:
        logger.error(f"❌ Erreur lors de la récupération des colonnes pour '{alias}': {e}")
        raise
