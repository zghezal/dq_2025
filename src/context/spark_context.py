"""
Spark DQ Context - Context pour exécuter des DQ avec PySpark.

Ce context charge les datasets en Spark DataFrames, permettant des calculs
distribués sur de gros volumes de données sans charger en mémoire.

Compatible avec l'architecture BasePlugin existante :
- Les plugins appellent context.load(alias)
- Le context retourne un pyspark.sql.DataFrame
- Les plugins utilisent l'API PySpark pour leurs calculs
"""

from pyspark.sql import SparkSession, DataFrame
from typing import Dict, Optional, Union
import pandas as pd
import logging


class SparkDQContext:
    """
    Context qui retourne TOUJOURS des Spark DataFrames.
    
    Accepte en entrée :
    - Fichiers Parquet/CSV
    - Tables Hive/Delta
    - Pandas DataFrames (convertis en Spark automatiquement)
    
    Compatible avec BasePlugin.run(context, **params) où les plugins
    attendent context.load() qui retourne un DataFrame.
    
    Exemples:
        # Avec fichiers Parquet
        context = SparkDQContext(catalog={
            "customers": "data/customers.parquet",
            "sales": "data/sales.parquet"
        })
        
        # Avec Pandas DataFrames (pour tests)
        df_test = pd.DataFrame({'col': [1, 2, None]})
        context = SparkDQContext(catalog={
            "test_data": df_test
        })
        
        # Utilisation dans un plugin
        df_spark = context.load("customers")  # pyspark.sql.DataFrame
        result = df_spark.filter(F.col("email").isNull()).count()
    """
    
    def __init__(self, 
                 spark: Optional[SparkSession] = None,
                 catalog: Optional[Dict[str, Union[str, pd.DataFrame]]] = None):
        """
        Initialise le context Spark.
        
        Args:
            spark: Session Spark existante (créée automatiquement si None)
            catalog: Mapping alias → source
                    - str: chemin fichier (.parquet, .csv) ou nom de table
                    - pd.DataFrame: DataFrame Pandas (converti auto en Spark)
        """
        # Initialiser le logger EN PREMIER (avant de l'utiliser)
        self.logger = logging.getLogger(__name__)
        
        # Puis initialiser les autres attributs
        self.catalog = catalog or {}
        self._cache: Dict[str, DataFrame] = {}
        
        # Créer la session Spark (peut maintenant utiliser self.logger)
        self.spark = spark or self._create_spark_session()
    
    def _create_spark_session(self) -> SparkSession:
        """
        Crée une session Spark locale pour développement/test.
        
        Configuration optimisée pour dev local :
        - local[*] : utilise tous les cores disponibles
        - shuffle.partitions : réduit à 4 (au lieu de 200 par défaut)
        - driver.memory : 2g pour éviter OOM sur petites machines
        """
        self.logger.info("🚀 Création d'une session Spark locale")
        return SparkSession.builder \
            .appName("DQ_Framework") \
            .master("local[*]") \
            .config("spark.sql.shuffle.partitions", "4") \
            .config("spark.driver.memory", "2g") \
            .getOrCreate()
    
    def load(self, alias: str, cache: bool = True) -> DataFrame:
        """
        Charge un dataset en Spark DataFrame.
        
        Signature compatible avec BasePlugin qui attend context.load(alias).
        
        Args:
            alias: Alias du dataset (ex: "customers")
            cache: Si True, cache le DataFrame Spark pour réutilisation
        
        Returns:
            pyspark.sql.DataFrame (distribué, pas chargé en mémoire)
        
        Raises:
            ValueError: Si l'alias n'existe pas dans le catalogue
        """
        # Vérifier le cache
        if cache and alias in self._cache:
            self.logger.info(f"📦 Dataset '{alias}' chargé depuis le cache Spark")
            return self._cache[alias]
        
        # Vérifier le catalogue
        if alias not in self.catalog:
            raise ValueError(
                f"Dataset '{alias}' introuvable dans le catalogue. "
                f"Disponibles: {list(self.catalog.keys())}"
            )
        
        source = self.catalog[alias]
        
        # Cas 1 : Pandas DataFrame → Convertir en Spark
        if isinstance(source, pd.DataFrame):
            self.logger.info(f"🔄 Conversion Pandas → Spark pour '{alias}'")
            df = self.spark.createDataFrame(source)
        
        # Cas 2 : Fichier Parquet
        elif isinstance(source, str) and source.endswith('.parquet'):
            self.logger.info(f"📂 Chargement Parquet: {source}")
            df = self.spark.read.parquet(source)
        
        # Cas 3 : Fichier CSV
        elif isinstance(source, str) and source.endswith('.csv'):
            self.logger.info(f"📂 Chargement CSV: {source}")
            df = self.spark.read.csv(source, header=True, inferSchema=True)
        
        # Cas 4 : Table Hive/Delta (format: "database.table")
        elif isinstance(source, str):
            self.logger.info(f"🗄️ Chargement table: {source}")
            df = self.spark.table(source)
        
        else:
            raise ValueError(
                f"Type de source non supporté pour '{alias}': {type(source)}"
            )
        
        self.logger.info(
            f"✅ Dataset '{alias}' chargé: {df.count()} lignes, "
            f"{len(df.columns)} colonnes"
        )
        
        # Cacher si demandé
        if cache:
            df.cache()
            self._cache[alias] = df
        
        return df
    
    def get_columns(self, alias: str) -> list:
        """
        Récupère la liste des colonnes d'un dataset (sans charger les données).
        
        Args:
            alias: Alias du dataset
        
        Returns:
            Liste des noms de colonnes
        """
        df = self.load(alias)
        return df.columns
    
    def clear_cache(self):
        """
        Libère le cache Spark pour tous les datasets chargés.
        
        Important pour libérer la mémoire après l'exécution des DQ.
        """
        if self._cache:
            self.logger.info(f"🧹 Libération du cache ({len(self._cache)} datasets)")
            for alias, df in self._cache.items():
                df.unpersist()
            self._cache.clear()
    
    def stop(self):
        """
        Arrête la session Spark et libère toutes les ressources.
        
        À appeler en fin d'exécution DQ.
        """
        self.clear_cache()
        self.spark.stop()
        self.logger.info("🛑 Session Spark arrêtée")
    
    def __enter__(self):
        """Support pour context manager (with statement)"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Nettoyage automatique avec context manager"""
        self.stop()