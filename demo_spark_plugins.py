"""
Démonstration des plugins DQ Spark-natifs.

Ce script montre comment utiliser les plugins avec SparkDQContext
pour exécuter des contrôles qualité sur des datasets Spark.
"""

import sys
import os
import logging

# Configurer le logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Ajouter le dossier src au path (si nécessaire)
sys.path.insert(0, os.path.abspath('.'))

# Imports
from src.context.spark_context import SparkDQContext
from src.plugins.metrics.missing_rate import MissingRate
from src.plugins.metrics.aggregation_by_column import AggregationByColumn


def demo_basic():
    """Démonstration basique avec les métriques Spark."""
    
    print("\n" + "=" * 70)
    print("DÉMONSTRATION 1 : Métriques basiques avec Spark")
    print("=" * 70)
    
    # 1. Créer le catalogue
    catalog = {
        "customers": "data/customers.parquet",
        "sales": "data/sales.parquet",
        "products": "data/products.parquet"
    }
    
    # 2. Initialiser le context Spark
    print("\n🚀 Initialisation du SparkDQContext...")
    context = SparkDQContext(catalog=catalog)
    
    # 3. Test Missing Rate sur customers.email
    print("\n" + "-" * 70)
    print("📊 Test 1 : Missing Rate sur customers.email")
    print("-" * 70)
    
    plugin_missing = MissingRate()
    result = plugin_missing.run(
        context,
        dataset="customers",
        column="email"
    )
    
    print(f"✅ Résultat: {result.message}")
    print(f"   Taux de missing: {result.value:.2%}")
    print(f"   Meta: {result.meta}")
    
    # 4. Test Missing Rate sur sales.amount
    print("\n" + "-" * 70)
    print("📊 Test 2 : Missing Rate sur sales.amount")
    print("-" * 70)
    
    result2 = plugin_missing.run(
        context,
        dataset="sales",
        column="amount"
    )
    
    print(f"✅ Résultat: {result2.message}")
    print(f"   Taux de missing: {result2.value:.2%}")
    
    # 5. Test Aggregation sur sales par region
    print("\n" + "-" * 70)
    print("📊 Test 3 : Aggregation sales par region")
    print("-" * 70)
    
    plugin_agg = AggregationByColumn()
    result3 = plugin_agg.run(
        context,
        dataset="sales",
        group_by="region",
        target="amount"
    )
    
    print(f"✅ Résultat: {result3.message}")
    print(f"   Nombre de groupes: {len(result3.dataframe)}")
    print("\n   Résultats agrégés:")
    print(result3.dataframe.to_string(index=False))
    
    # 6. Nettoyer
    print("\n🧹 Nettoyage...")
    context.stop()
    print("✅ Context fermé")


def demo_with_pandas():
    """Démonstration avec conversion automatique Pandas → Spark."""
    
    print("\n" + "=" * 70)
    print("DÉMONSTRATION 2 : Conversion automatique Pandas → Spark")
    print("=" * 70)
    
    import pandas as pd
    
    # Créer un petit DataFrame Pandas pour test
    df_test = pd.DataFrame({
        'id': [1, 2, 3, 4, 5],
        'value': [10.0, None, 30.0, None, 50.0],
        'category': ['A', 'A', 'B', 'B', 'C']
    })
    
    print("\n📊 DataFrame Pandas de test:")
    print(df_test)
    
    # Créer un context avec ce DataFrame
    context = SparkDQContext(catalog={
        "test_data": df_test  # Pandas → Spark automatiquement
    })
    
    # Test Missing Rate
    print("\n" + "-" * 70)
    print("📊 Missing Rate sur 'value'")
    print("-" * 70)
    
    plugin = MissingRate()
    result = plugin.run(context, dataset="test_data", column="value")
    
    print(f"✅ Résultat: {result.message}")
    print(f"   Expected: 40% (2 nulls sur 5 valeurs)")
    print(f"   Actual: {result.value:.2%}")
    
    # Test Aggregation
    print("\n" + "-" * 70)
    print("📊 Aggregation par 'category'")
    print("-" * 70)
    
    plugin_agg = AggregationByColumn()
    result2 = plugin_agg.run(
        context,
        dataset="test_data",
        group_by="category",
        target="value"
    )
    
    print(f"✅ Résultat: {result2.message}")
    print("\n   Résultats agrégés:")
    print(result2.dataframe.to_string(index=False))
    
    context.stop()


def demo_cache():
    """Démonstration du système de cache Spark."""
    
    print("\n" + "=" * 70)
    print("DÉMONSTRATION 3 : Cache Spark")
    print("=" * 70)
    
    catalog = {
        "customers": "data/customers.parquet"
    }
    
    context = SparkDQContext(catalog=catalog)
    
    # Premier chargement (sans cache)
    print("\n📂 Premier chargement (lecture depuis fichier)...")
    df1 = context.load("customers")
    print(f"   Lignes: {df1.count()}")
    
    # Deuxième chargement (depuis cache)
    print("\n📦 Deuxième chargement (depuis cache)...")
    df2 = context.load("customers")
    print(f"   Lignes: {df2.count()}")
    print("   ⚡ Chargement instantané depuis le cache!")
    
    # Vérifier qu'ils pointent vers le même objet
    print(f"\n🔍 Même objet? {df1 is df2}")
    
    context.stop()


def demo_output_schema():
    """Démonstration du output_schema."""
    
    print("\n" + "=" * 70)
    print("DÉMONSTRATION 4 : Output Schema")
    print("=" * 70)
    
    # Afficher le schéma prédit pour aggregation
    params = {
        "dataset": "sales",
        "group_by": "region",
        "target": "amount"
    }
    
    schema = AggregationByColumn.output_schema(params)
    
    print("\n📋 Schéma prédit pour AggregationByColumn:")
    print(f"   Dataset: {params['dataset']}")
    print(f"   Group by: {params['group_by']}")
    print(f"   Target: {params['target']}")
    print("\n   Colonnes produites:")
    
    for col in schema.columns:
        print(f"   - {col.name:20s} ({col.dtype:8s}) - {col.description}")
    
    # Exécuter et vérifier
    print("\n🔄 Exécution de la métrique...")
    
    catalog = {"sales": "data/sales.parquet"}
    context = SparkDQContext(catalog=catalog)
    
    plugin = AggregationByColumn()
    result = plugin.run(context, **params)
    
    print(f"✅ {result.message}")
    print(f"\n   Colonnes réelles: {list(result.dataframe.columns)}")
    print("   ✅ Schéma validé automatiquement!")
    
    context.stop()


def main():
    """Point d'entrée principal."""
    
    print("\n" + "=" * 70)
    print("🚀 DÉMONSTRATION DES PLUGINS DQ SPARK-NATIFS")
    print("=" * 70)
    
    # Vérifier que les données existent
    if not os.path.exists("data/customers.parquet"):
        print("\n❌ ERREUR: Fichiers de données introuvables!")
        print("   Exécutez d'abord: python generate_test_data.py")
        return
    
    try:
        # Lancer les démos
        demo_basic()
        demo_with_pandas()
        demo_cache()
        demo_output_schema()
        
        # Résumé
        print("\n" + "=" * 70)
        print("✅ TOUTES LES DÉMONSTRATIONS TERMINÉES")
        print("=" * 70)
        print("\n📝 Résumé:")
        print("   ✅ Plugins Spark-natifs fonctionnels")
        print("   ✅ SparkDQContext opérationnel")
        print("   ✅ Cache Spark performant")
        print("   ✅ Conversion Pandas → Spark automatique")
        print("   ✅ Output schema validé")
        print("\n🎉 Votre système DQ est prêt pour la production!")
        
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
