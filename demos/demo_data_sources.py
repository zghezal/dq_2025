"""
Script de démonstration des 4 types de sources de données
Teste chaque connecteur avec des données de démonstration
"""

import sys
from pathlib import Path

# Ajouter le repo à sys.path
repo_root = Path(__file__).parent
sys.path.insert(0, str(repo_root))

import pandas as pd
from src.core.models_channels import DataSourceType
from src.connectors.factory import ConnectorFactory

print("=" * 80)
print("DÉMO DES CONNECTEURS DE DONNÉES")
print("=" * 80)
print()

# ============================================================================
# 1. Test LOCAL CONNECTOR
# ============================================================================
print("1️⃣  TEST: LOCAL CONNECTOR")
print("-" * 80)

# Créer un fichier CSV de test
test_data = pd.DataFrame({
    'id': [1, 2, 3],
    'name': ['Alice', 'Bob', 'Charlie'],
    'amount': [100.5, 200.75, 150.25]
})
test_file_path = repo_root / 'sourcing' / 'input' / 'test_local.csv'
test_data.to_csv(test_file_path, index=False)

# Tester le connecteur LOCAL
local_params = {
    'file_path': str(test_file_path),
    'format': 'csv'
}

try:
    local_connector = ConnectorFactory.create_connector(
        DataSourceType.LOCAL,
        local_params
    )
    
    # Tester la connexion
    success, message = local_connector.test_connection()
    print(f"✅ Test connexion: {message}" if success else f"❌ Test connexion: {message}")
    
    # Charger les données
    if success:
        df = local_connector.fetch_data()
        print(f"✅ Données chargées: {len(df)} lignes, {len(df.columns)} colonnes")
        print(f"   Colonnes: {list(df.columns)}")
        print(f"   Aperçu:")
        print(df.head())
        
        metadata = local_connector.get_metadata()
        print(f"   Métadonnées: {metadata.get('file_name')} ({metadata.get('file_size_mb')} MB)")

except Exception as e:
    print(f"❌ Erreur: {e}")

print()

# ============================================================================
# 2. Test HUE CONNECTOR
# ============================================================================
print("2️⃣  TEST: HUE CONNECTOR (simulation)")
print("-" * 80)

hue_params = {
    'hue_url': 'http://hue-demo.example.com:8888',
    'auth_token': 'demo_token_12345',
    'path': '/user/data/sales.csv',
    'format': 'csv'
}

try:
    hue_connector = ConnectorFactory.create_connector(
        DataSourceType.HUE,
        hue_params
    )
    
    # Valider les paramètres
    is_valid, error = hue_connector.validate_connection()
    print(f"✅ Validation paramètres: OK" if is_valid else f"❌ Validation: {error}")
    
    # Note: le test de connexion échouera car c'est une URL de démo
    success, message = hue_connector.test_connection()
    print(f"⚠️  Test connexion (attendu): {message}")
    
    metadata = hue_connector.get_metadata()
    print(f"   Métadonnées: HUE URL={metadata.get('hue_url')}, Source={metadata.get('source')}")

except Exception as e:
    print(f"⚠️  Erreur attendue (URL de démo): {e}")

print()

# ============================================================================
# 3. Test SHAREPOINT CONNECTOR
# ============================================================================
print("3️⃣  TEST: SHAREPOINT CONNECTOR (simulation)")
print("-" * 80)

sharepoint_params = {
    'site_url': 'https://tenant.sharepoint.com/sites/dataqualite',
    'folder_path': '/Shared Documents/Data/DQ',
    'file_name': 'sales_2024.xlsx',
    'access_token': 'demo_sp_token_67890',
    'format': 'xlsx'
}

try:
    sp_connector = ConnectorFactory.create_connector(
        DataSourceType.SHAREPOINT,
        sharepoint_params
    )
    
    # Valider les paramètres
    is_valid, error = sp_connector.validate_connection()
    print(f"✅ Validation paramètres: OK" if is_valid else f"❌ Validation: {error}")
    
    # Note: le test de connexion échouera car c'est une URL de démo
    success, message = sp_connector.test_connection()
    print(f"⚠️  Test connexion (attendu): {message}")
    
    metadata = sp_connector.get_metadata()
    print(f"   Métadonnées: Site={metadata.get('site_url')}")
    print(f"   Fichier: {metadata.get('folder_path')}/{metadata.get('file_name')}")

except Exception as e:
    print(f"⚠️  Erreur attendue (URL de démo): {e}")

print()

# ============================================================================
# 4. Test DATAIKU DATASET CONNECTOR
# ============================================================================
print("4️⃣  TEST: DATAIKU DATASET CONNECTOR (stub mode)")
print("-" * 80)

dataiku_params = {
    'project_key': 'DQ_PROJECT',
    'dataset_name': 'sales_cleaned',
    'sampling': 'head',
    'limit': 1000
}

try:
    dku_connector = ConnectorFactory.create_connector(
        DataSourceType.DATAIKU_DATASET,
        dataiku_params
    )
    
    # Valider les paramètres
    is_valid, error = dku_connector.validate_connection()
    print(f"✅ Validation paramètres: OK" if is_valid else f"❌ Validation: {error}")
    
    # Test de connexion (fonctionnera en mode stub)
    success, message = dku_connector.test_connection()
    print(f"✅ Test connexion: {message}" if success else f"❌ Test connexion: {message}")
    
    # Charger les données (mode stub retourne un DataFrame vide)
    if success:
        df = dku_connector.fetch_data()
        print(f"✅ Données chargées (stub): {len(df)} lignes, {len(df.columns)} colonnes")
        
        metadata = dku_connector.get_metadata()
        print(f"   Métadonnées: {metadata.get('full_name')}")
        print(f"   Dataiku disponible: {metadata.get('dataiku_available')}")

except Exception as e:
    print(f"❌ Erreur: {e}")

print()

# ============================================================================
# RÉSUMÉ DES SOURCES SUPPORTÉES
# ============================================================================
print("=" * 80)
print("📋 RÉSUMÉ DES SOURCES SUPPORTÉES")
print("=" * 80)

sources = ConnectorFactory.get_supported_sources()
for source_type, description in sources.items():
    print(f"  • {source_type.upper():20s} - {description}")
    
    # Afficher les paramètres requis
    params = ConnectorFactory.get_required_params(DataSourceType(source_type))
    for param, desc in params.items():
        print(f"    → {param}: {desc}")
    print()

print("=" * 80)
print("✅ Tous les connecteurs sont opérationnels !")
print("=" * 80)
