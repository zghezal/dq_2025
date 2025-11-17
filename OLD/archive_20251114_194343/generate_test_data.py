"""
Génération de données de test avec Spark.

Crée des fichiers Parquet pour tester les plugins DQ Spark-natifs.
"""

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, FloatType
import random
import os


def generate_test_data():
    """Génère des fichiers Parquet de test avec Spark."""
    
    print("🚀 Démarrage de Spark...")
    spark = SparkSession.builder \
        .appName("Generate_Test_Data") \
        .master("local[*]") \
        .getOrCreate()
    
    # Créer le dossier data s'il n'existe pas
    os.makedirs("data", exist_ok=True)
    
    # =========================================================================
    # Dataset 1 : Customers (10 000 lignes)
    # =========================================================================
    print("\n📊 Génération du dataset Customers...")
    
    customers_data = []
    countries = ["FR", "US", "UK", "DE", "ES"]
    
    for i in range(10000):
        # 2% de valeurs nulles dans email
        email = f"user{i}@example.com" if random.random() > 0.02 else None
        # 1% de valeurs nulles dans name
        name = f"User {i}" if random.random() > 0.01 else None
        
        customers_data.append((
            i,
            email,
            name,
            random.choice(countries)
        ))
    
    schema_customers = StructType([
        StructField("id", IntegerType(), False),
        StructField("email", StringType(), True),
        StructField("name", StringType(), True),
        StructField("country", StringType(), True)
    ])
    
    df_customers = spark.createDataFrame(customers_data, schema=schema_customers)
    
    # Écrire en Parquet
    df_customers.write.parquet("data/customers.parquet", mode="overwrite")
    print(f"✅ customers.parquet créé: {df_customers.count()} lignes")
    
    # Afficher quelques stats
    print(f"   - Colonnes: {df_customers.columns}")
    print(f"   - Nulls dans 'email': {df_customers.filter(F.col('email').isNull()).count()}")
    
    # =========================================================================
    # Dataset 2 : Sales (100 000 lignes)
    # =========================================================================
    print("\n📊 Génération du dataset Sales...")
    
    sales_data = []
    months = ["2024-01", "2024-02", "2024-03", "2024-04"]
    regions = ["North", "South", "East", "West", "Central"]
    
    for i in range(100000):
        # 0.5% de valeurs nulles dans amount
        amount = round(random.uniform(10, 1000), 2) if random.random() > 0.005 else None
        
        sales_data.append((
            i,
            random.randint(1, 10000),  # customer_id
            amount,
            random.choice(months),
            random.choice(regions)
        ))
    
    schema_sales = StructType([
        StructField("id", IntegerType(), False),
        StructField("customer_id", IntegerType(), True),
        StructField("amount", FloatType(), True),
        StructField("month", StringType(), True),
        StructField("region", StringType(), True)
    ])
    
    df_sales = spark.createDataFrame(sales_data, schema=schema_sales)
    
    # Écrire en Parquet
    df_sales.write.parquet("data/sales.parquet", mode="overwrite")
    print(f"✅ sales.parquet créé: {df_sales.count()} lignes")
    
    # Afficher quelques stats
    print(f"   - Colonnes: {df_sales.columns}")
    print(f"   - Nulls dans 'amount': {df_sales.filter(F.col('amount').isNull()).count()}")
    
    # Stats par région
    print("\n   📈 Statistiques par région:")
    df_sales.groupBy("region").agg(
        F.count("*").alias("count"),
        F.avg("amount").alias("avg_amount")
    ).show()
    
    # =========================================================================
    # Dataset 3 : Products (1 000 lignes)
    # =========================================================================
    print("\n📊 Génération du dataset Products...")
    
    categories = ["Electronics", "Clothing", "Food", "Books", "Toys"]
    
    products_data = []
    for i in range(1000):
        # 3% de valeurs nulles dans price
        price = round(random.uniform(5, 500), 2) if random.random() > 0.03 else None
        
        products_data.append((
            i,
            f"Product {i}",
            random.choice(categories),
            price,
            random.randint(0, 1000)  # stock
        ))
    
    schema_products = StructType([
        StructField("id", IntegerType(), False),
        StructField("name", StringType(), True),
        StructField("category", StringType(), True),
        StructField("price", FloatType(), True),
        StructField("stock", IntegerType(), True)
    ])
    
    df_products = spark.createDataFrame(products_data, schema=schema_products)
    
    # Écrire en Parquet
    df_products.write.parquet("data/products.parquet", mode="overwrite")
    print(f"✅ products.parquet créé: {df_products.count()} lignes")
    
    # Stats par catégorie
    print("\n   📈 Statistiques par catégorie:")
    df_products.groupBy("category").agg(
        F.count("*").alias("count"),
        F.avg("price").alias("avg_price")
    ).show()
    
    # =========================================================================
    # Résumé
    # =========================================================================
    print("\n" + "=" * 70)
    print("✅ GÉNÉRATION TERMINÉE")
    print("=" * 70)
    print("\nFichiers créés dans le dossier 'data/' :")
    print("  📁 customers.parquet  (10 000 lignes)")
    print("  📁 sales.parquet      (100 000 lignes)")
    print("  📁 products.parquet   (1 000 lignes)")
    print("\nVous pouvez maintenant tester vos plugins DQ avec ces données!")
    
    # Arrêter Spark
    spark.stop()
    print("\n🛑 Session Spark arrêtée")


if __name__ == "__main__":
    generate_test_data()
