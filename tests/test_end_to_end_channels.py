"""
Script de test end-to-end pour le système de canaux DQ

Ce script crée :
1. Des données de test (fichiers CSV, Excel)
2. Des canaux avec différentes configurations
3. Des définitions DQ pour ces canaux
4. Des soumissions de test
5. Exécute le traitement complet

Usage:
    python test_end_to_end_channels.py
"""

import sys
from pathlib import Path
import pandas as pd
import json
import yaml
from datetime import datetime
import uuid

# Ajouter le repo au path
repo_root = Path(__file__).parent
sys.path.insert(0, str(repo_root))

from src.core.models_channels import (
    DropChannel, FileSpecification, EmailConfig,
    FileFormat, DataSourceType, ChannelSubmission, 
    FileMapping, SubmissionStatus
)
from src.core.channel_manager import ChannelManager
from src.core.submission_processor import SubmissionProcessor

print("=" * 80)
print("TEST END-TO-END - SYSTÈME DE CANAUX DQ")
print("=" * 80)
print()

# ============================================================================
# ÉTAPE 1 : CRÉER DES DONNÉES DE TEST
# ============================================================================
print("📂 ÉTAPE 1 : Création des données de test")
print("-" * 80)

# Créer les dossiers nécessaires
test_data_dir = repo_root / 'test_data' / 'channels'
test_data_dir.mkdir(parents=True, exist_ok=True)

# Dataset 1 : Ventes mensuelles
print("  Création de 'sales_monthly.csv'...")
sales_data = pd.DataFrame({
    'date': pd.date_range('2024-01-01', periods=100, freq='D'),
    'product_id': ['PROD_' + str(i % 10) for i in range(100)],
    'amount': [round(100 + i * 1.5 + (i % 7) * 10, 2) for i in range(100)],
    'quantity': [1 + (i % 5) for i in range(100)],
    'store_id': ['STORE_' + str(i % 3) for i in range(100)],
    'customer_id': ['CUST_' + str(1000 + i) for i in range(100)]
})
sales_file = test_data_dir / 'sales_monthly.csv'
sales_data.to_csv(sales_file, index=False)
print(f"    ✅ {len(sales_data)} lignes créées")

# Dataset 2 : Produits (référentiel)
print("  Création de 'products_reference.xlsx'...")
products_data = pd.DataFrame({
    'product_id': ['PROD_' + str(i) for i in range(10)],
    'product_name': [f'Produit {i}' for i in range(10)],
    'category': ['Catégorie A', 'Catégorie B', 'Catégorie A', 'Catégorie C', 'Catégorie A', 
                 'Catégorie B', 'Catégorie C', 'Catégorie A', 'Catégorie B', 'Catégorie C'],
    'price': [50 + i * 10 for i in range(10)],
    'active': [True] * 8 + [False] * 2
})
products_file = test_data_dir / 'products_reference.xlsx'
products_data.to_excel(products_file, index=False)
print(f"    ✅ {len(products_data)} lignes créées")

# Dataset 3 : Clients (avec quelques problèmes de qualité intentionnels)
print("  Création de 'customers.csv' (avec problèmes de qualité)...")
customers_data = pd.DataFrame({
    'customer_id': ['CUST_' + str(1000 + i) for i in range(120)],
    'email': [f'client{i}@example.com' if i % 10 != 0 else None for i in range(120)],  # 10% manquants
    'age': [18 + i % 60 if i % 15 != 0 else -1 for i in range(120)],  # Quelques valeurs invalides
    'country': ['FR'] * 100 + ['US'] * 15 + ['UK'] * 5,
    'registration_date': pd.date_range('2023-01-01', periods=120, freq='3D')
})
customers_file = test_data_dir / 'customers.csv'
customers_data.to_csv(customers_file, index=False)
print(f"    ✅ {len(customers_data)} lignes créées (avec ~10% d'erreurs intentionnelles)")

print()

# ============================================================================
# ÉTAPE 2 : CRÉER DES DÉFINITIONS DQ
# ============================================================================
print("📋 ÉTAPE 2 : Création des définitions DQ")
print("-" * 80)

dq_dir = repo_root / 'dq' / 'definitions'
dq_dir.mkdir(parents=True, exist_ok=True)

# DQ 1 : Contrôles sur les ventes
print("  Création de 'dq_sales_channel.yaml'...")
dq_sales = {
    'id': 'dq_sales_channel',
    'description': 'Contrôles qualité pour le canal des ventes',
    'datasets': {
        'sales': {
            'alias': 'sales_file',
            'description': 'Fichier des ventes mensuelles'
        }
    },
    'metrics': [
        {
            'id': 'sales_count',
            'type': 'count',
            'dataset': 'sales',
            'description': 'Nombre total de ventes'
        },
        {
            'id': 'amount_missing_rate',
            'type': 'missing_rate',
            'dataset': 'sales',
            'column': 'amount',
            'description': 'Taux de valeurs manquantes dans amount'
        },
        {
            'id': 'amount_avg',
            'type': 'avg',
            'dataset': 'sales',
            'column': 'amount',
            'description': 'Montant moyen des ventes'
        },
        {
            'id': 'amount_min',
            'type': 'min',
            'dataset': 'sales',
            'column': 'amount',
            'description': 'Montant minimum'
        },
        {
            'id': 'negative_amounts',
            'type': 'count_where',
            'dataset': 'sales',
            'filter': 'amount < 0',
            'description': 'Nombre de montants négatifs'
        }
    ],
    'tests': [
        {
            'id': 'test_no_missing_amount',
            'type': 'threshold',
            'metric': 'amount_missing_rate',
            'operator': '==',
            'value': 0,
            'severity': 'error',
            'description': 'Aucune valeur manquante autorisée dans amount'
        },
        {
            'id': 'test_min_records',
            'type': 'threshold',
            'metric': 'sales_count',
            'operator': '>=',
            'value': 50,
            'severity': 'error',
            'description': 'Au moins 50 ventes attendues'
        },
        {
            'id': 'test_no_negative',
            'type': 'threshold',
            'metric': 'negative_amounts',
            'operator': '==',
            'value': 0,
            'severity': 'error',
            'description': 'Aucun montant négatif autorisé'
        },
        {
            'id': 'test_avg_range',
            'type': 'range',
            'metric': 'amount_avg',
            'min': 100,
            'max': 300,
            'severity': 'warning',
            'description': 'Montant moyen doit être entre 100 et 300'
        }
    ]
}

dq_sales_file = dq_dir / 'dq_sales_channel.yaml'
with open(dq_sales_file, 'w', encoding='utf-8') as f:
    yaml.dump(dq_sales, f, allow_unicode=True, sort_keys=False)
print(f"    ✅ 5 métriques, 4 tests")

# DQ 2 : Contrôles sur les clients
print("  Création de 'dq_customers_channel.yaml'...")
dq_customers = {
    'id': 'dq_customers_channel',
    'description': 'Contrôles qualité pour le canal clients',
    'datasets': {
        'customers': {
            'alias': 'customers_file',
            'description': 'Fichier des clients'
        }
    },
    'metrics': [
        {
            'id': 'customers_count',
            'type': 'count',
            'dataset': 'customers',
            'description': 'Nombre de clients'
        },
        {
            'id': 'email_missing_rate',
            'type': 'missing_rate',
            'dataset': 'customers',
            'column': 'email',
            'description': 'Taux d\'emails manquants'
        },
        {
            'id': 'age_missing_rate',
            'type': 'missing_rate',
            'dataset': 'customers',
            'column': 'age',
            'description': 'Taux d\'âges manquants'
        },
        {
            'id': 'invalid_ages',
            'type': 'count_where',
            'dataset': 'customers',
            'filter': 'age < 0 OR age > 120',
            'description': 'Nombre d\'âges invalides'
        },
        {
            'id': 'unique_emails',
            'type': 'nunique',
            'dataset': 'customers',
            'column': 'email',
            'description': 'Nombre d\'emails uniques'
        }
    ],
    'tests': [
        {
            'id': 'test_email_quality',
            'type': 'threshold',
            'metric': 'email_missing_rate',
            'operator': '<=',
            'value': 0.15,
            'severity': 'warning',
            'description': 'Max 15% d\'emails manquants'
        },
        {
            'id': 'test_no_invalid_age',
            'type': 'threshold',
            'metric': 'invalid_ages',
            'operator': '<=',
            'value': 5,
            'severity': 'warning',
            'description': 'Max 5 âges invalides tolérés'
        },
        {
            'id': 'test_min_customers',
            'type': 'threshold',
            'metric': 'customers_count',
            'operator': '>=',
            'value': 100,
            'severity': 'error',
            'description': 'Au moins 100 clients attendus'
        }
    ]
}

dq_customers_file = dq_dir / 'dq_customers_channel.yaml'
with open(dq_customers_file, 'w', encoding='utf-8') as f:
    yaml.dump(dq_customers, f, allow_unicode=True, sort_keys=False)
print(f"    ✅ 5 métriques, 3 tests")

print()

# ============================================================================
# ÉTAPE 3 : CRÉER DES CANAUX
# ============================================================================
print("🔀 ÉTAPE 3 : Création des canaux")
print("-" * 80)

manager = ChannelManager()

# Canal 1 : Ventes mensuelles (simple fichier)
print("  Canal 1 : 'canal_ventes_mensuelles'...")
canal_ventes = DropChannel(
    channel_id='canal_ventes_mensuelles',
    name='Canal Ventes Mensuelles',
    description='Canal pour le dépôt mensuel des données de ventes',
    team_name='Équipe Commerciale',
    file_specifications=[
        FileSpecification(
            file_id='sales_file',
            name='Fichier des ventes',
            description='Export mensuel des ventes',
            format=FileFormat.CSV,
            required=True,
            source_type=DataSourceType.LOCAL,
            expected_columns=['date', 'product_id', 'amount', 'quantity', 'store_id'],
            schema_validation=True
        )
    ],
    dq_configs=[str(dq_sales_file)],
    email_config=EmailConfig(
        recipient_team_emails=['commercial@example.com'],
        admin_emails=['dq_admin@example.com']
    ),
    is_public=True,
    active=True,
    created_by='admin_test'
)

manager.create_channel(canal_ventes)
print("    ✅ Canal créé avec 1 fichier et 1 DQ")

# Canal 2 : Clients (avec problèmes de qualité)
print("  Canal 2 : 'canal_clients'...")
canal_clients = DropChannel(
    channel_id='canal_clients',
    name='Canal Clients',
    description='Canal pour la mise à jour des données clients',
    team_name='Équipe CRM',
    file_specifications=[
        FileSpecification(
            file_id='customers_file',
            name='Fichier clients',
            description='Base clients à jour',
            format=FileFormat.CSV,
            required=True,
            source_type=DataSourceType.LOCAL,
            expected_columns=['customer_id', 'email', 'age', 'country'],
            schema_validation=True
        )
    ],
    dq_configs=[str(dq_customers_file)],
    email_config=EmailConfig(
        recipient_team_emails=['crm@example.com'],
        admin_emails=['dq_admin@example.com']
    ),
    is_public=False,
    allowed_groups=['CRM', 'Direction'],
    active=True,
    created_by='admin_test'
)

manager.create_channel(canal_clients)
print("    ✅ Canal créé avec 1 fichier et 1 DQ (privé)")

# Canal 3 : Multi-fichiers (ventes + produits)
print("  Canal 3 : 'canal_ventes_complet'...")
canal_ventes_complet = DropChannel(
    channel_id='canal_ventes_complet',
    name='Canal Ventes Complet',
    description='Canal pour ventes avec référentiel produits',
    team_name='Équipe Commerciale',
    file_specifications=[
        FileSpecification(
            file_id='sales_file',
            name='Fichier des ventes',
            description='Export des ventes',
            format=FileFormat.CSV,
            required=True,
            source_type=DataSourceType.LOCAL,
            expected_columns=['date', 'product_id', 'amount', 'quantity']
        ),
        FileSpecification(
            file_id='products_file',
            name='Référentiel produits',
            description='Liste des produits',
            format=FileFormat.EXCEL,
            required=True,
            source_type=DataSourceType.LOCAL,
            expected_columns=['product_id', 'product_name', 'category', 'price']
        )
    ],
    dq_configs=[str(dq_sales_file)],  # On pourrait ajouter des DQ de jointure
    email_config=EmailConfig(
        recipient_team_emails=['commercial@example.com'],
        admin_emails=['dq_admin@example.com']
    ),
    is_public=True,
    active=True,
    created_by='admin_test'
)

manager.create_channel(canal_ventes_complet)
print("    ✅ Canal créé avec 2 fichiers et 1 DQ")

print()

# Vérifier les canaux créés
all_channels = manager.list_channels()
print(f"  📊 Total canaux créés : {len(all_channels)}")
for ch in all_channels:
    print(f"     - {ch.name} ({len(ch.file_specifications)} fichier(s), {len(ch.dq_configs)} DQ)")

print()

# ============================================================================
# ÉTAPE 4 : CRÉER DES SOUMISSIONS
# ============================================================================
print("📤 ÉTAPE 4 : Création de soumissions de test")
print("-" * 80)

# Soumission 1 : Ventes mensuelles (devrait passer)
print("  Soumission 1 : Ventes mensuelles...")
submission1 = ChannelSubmission(
    submission_id=str(uuid.uuid4()),
    channel_id='canal_ventes_mensuelles',
    file_mappings=[
        FileMapping(
            file_spec_id='sales_file',
            provided_path=str(sales_file),
            provided_name='sales_monthly.csv'
        )
    ],
    status=SubmissionStatus.PENDING,
    submitted_by='commercial@example.com',
    submitted_at=datetime.now()
)

manager.create_submission(submission1)
print(f"    ✅ Soumission créée : {submission1.submission_id[:8]}...")

# Soumission 2 : Clients (devrait avoir des warnings)
print("  Soumission 2 : Clients...")
submission2 = ChannelSubmission(
    submission_id=str(uuid.uuid4()),
    channel_id='canal_clients',
    file_mappings=[
        FileMapping(
            file_spec_id='customers_file',
            provided_path=str(customers_file),
            provided_name='customers.csv'
        )
    ],
    status=SubmissionStatus.PENDING,
    submitted_by='crm@example.com',
    submitted_at=datetime.now()
)

manager.create_submission(submission2)
print(f"    ✅ Soumission créée : {submission2.submission_id[:8]}...")

# Soumission 3 : Multi-fichiers
print("  Soumission 3 : Ventes complètes (2 fichiers)...")
submission3 = ChannelSubmission(
    submission_id=str(uuid.uuid4()),
    channel_id='canal_ventes_complet',
    file_mappings=[
        FileMapping(
            file_spec_id='sales_file',
            provided_path=str(sales_file),
            provided_name='sales_monthly.csv'
        ),
        FileMapping(
            file_spec_id='products_file',
            provided_path=str(products_file),
            provided_name='products_reference.xlsx'
        )
    ],
    status=SubmissionStatus.PENDING,
    submitted_by='commercial@example.com',
    submitted_at=datetime.now()
)

manager.create_submission(submission3)
print(f"    ✅ Soumission créée : {submission3.submission_id[:8]}...")

print()

# ============================================================================
# ÉTAPE 5 : TRAITER LES SOUMISSIONS
# ============================================================================
print("⚙️  ÉTAPE 5 : Traitement des soumissions")
print("-" * 80)

processor = SubmissionProcessor(manager)

# Traiter chaque soumission
submissions = [submission1, submission2, submission3]

for i, submission in enumerate(submissions, 1):
    print(f"\n  🔄 Traitement soumission {i}/{len(submissions)}")
    print(f"     ID: {submission.submission_id[:8]}...")
    print(f"     Canal: {submission.channel_id}")
    print(f"     Fichiers: {len(submission.file_mappings)}")
    print()
    
    try:
        result = processor.process_submission(submission)
        
        print(f"\n  📊 Résultat :")
        print(f"     Statut: {result.status.value}")
        print(f"     DQ Total: {result.dq_total}")
        print(f"     DQ Passed: {result.dq_passed} ✅")
        print(f"     DQ Failed: {result.dq_failed} ❌")
        
        if result.errors:
            print(f"     Erreurs: {len(result.errors)}")
            for error in result.errors[:3]:
                print(f"       - {error}")
        
        if result.dq_report_path:
            print(f"     Rapport: {result.dq_report_path}")
        
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
    
    print()

print()

# ============================================================================
# ÉTAPE 6 : RÉSUMÉ
# ============================================================================
print("=" * 80)
print("📊 RÉSUMÉ DU TEST")
print("=" * 80)

# Statistiques sur les données
print("\n📂 Données créées :")
print(f"  - sales_monthly.csv : {len(sales_data)} lignes")
print(f"  - products_reference.xlsx : {len(products_data)} lignes")
print(f"  - customers.csv : {len(customers_data)} lignes (avec erreurs)")

# Statistiques sur les DQ
print("\n📋 Définitions DQ :")
print(f"  - dq_sales_channel.yaml : 5 métriques, 4 tests")
print(f"  - dq_customers_channel.yaml : 5 métriques, 3 tests")

# Statistiques sur les canaux
print("\n🔀 Canaux créés :")
all_channels = manager.list_channels()
for ch in all_channels:
    access = "Public" if ch.is_public else "Privé"
    print(f"  - {ch.name}")
    print(f"    • {len(ch.file_specifications)} fichier(s)")
    print(f"    • {len(ch.dq_configs)} DQ")
    print(f"    • {access}")

# Statistiques sur les soumissions
print("\n📤 Soumissions traitées :")
all_submissions = manager.list_submissions()
for sub in all_submissions:
    status_icon = {
        SubmissionStatus.DQ_SUCCESS: "✅",
        SubmissionStatus.DQ_FAILED: "⚠️",
        SubmissionStatus.ERROR: "❌",
        SubmissionStatus.PENDING: "⏳",
        SubmissionStatus.PROCESSING: "🔄"
    }.get(sub.status, "❓")
    
    print(f"  {status_icon} {sub.submission_id[:8]}... - {sub.status.value}")
    if sub.dq_total > 0:
        print(f"     DQ: {sub.dq_passed}/{sub.dq_total} passés")

print()
print("=" * 80)
print("✅ TEST END-TO-END TERMINÉ")
print("=" * 80)
print()
print("📁 Fichiers créés dans :")
print(f"  - Données: {test_data_dir}")
print(f"  - DQ: {dq_dir}")
print(f"  - Canaux: managed_folders/channels/")
print()
print("🎯 Prochaines étapes :")
print("  1. Vérifier les rapports générés dans reports/channel_submissions/")
print("  2. Tester l'interface web (python run.py)")
print("  3. Consulter les canaux dans /channel-admin")
print("  4. Voir les soumissions dans /channel-drop")
print()
