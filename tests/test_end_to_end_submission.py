"""
Test final: Créer les soumissions via submission_processor
"""
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

from src.core.channel_manager import ChannelManager
from src.core.submission_processor import SubmissionProcessor

print("="*80)
print("TEST FINAL - SIMULATION SOUMISSIONS")
print("="*80)

manager = ChannelManager()
processor = SubmissionProcessor(channel_manager=manager)

# Trouver le canal de validation
channels = manager.list_channels()
validation_channel = next((c for c in channels if 'validation' in c.name.lower()), None)

if not validation_channel:
    print("✗ Canal de validation introuvable")
    sys.exit(1)

print(f"\n[1] Canal trouvé: {validation_channel.name}")
print(f"    ID: {validation_channel.channel_id}")
print(f"    DQ configs: {validation_channel.dq_configs}")

# === TEST 1: Données INVALIDES ===
print("\n" + "="*80)
print("TEST 1: SOUMISSION INVALIDE (doit échouer)")
print("="*80)

df_invalid = pd.read_csv('data/sales_invalid_upload.csv')
print(f"\nDonnées: {len(df_invalid)} lignes")
print(f"  - NaN customer_id: {df_invalid['customer_id'].isna().sum()}")
print(f"  - Amount négatif: {(df_invalid['amount'] < 0).sum()}")
print(f"  - Amount > 10000: {(df_invalid['amount'] > 10000).sum()}")
print(f"  - IDs dupliqués: {df_invalid['transaction_id'].duplicated().sum()}")

# Créer la soumission manuellement
from src.core.models_channels import ChannelSubmission, SubmissionStatus, FileMapping
from datetime import datetime
import uuid

submission1 = ChannelSubmission(
    submission_id=str(uuid.uuid4())[:8],
    channel_id=validation_channel.channel_id,
    submitted_by="test_user",
    submitted_at=datetime.now(),
    status=SubmissionStatus.PENDING,
    file_mappings=[
        FileMapping(
            file_spec_id='sales_data',
            provided_path='data/sales_invalid_upload.csv',
            provided_name='sales_invalid_upload.csv'
        )
    ]
)

# Enregistrer la soumission
manager.create_submission(submission1)

# Traiter
result1 = processor.process_submission(submission1)

print(f"\n📊 Résultat soumission invalide:")
print(f"   Status: {result1.status.value}")
print(f"   DQ Total: {result1.dq_total}")
print(f"   DQ Passed: {result1.dq_passed}")
print(f"   DQ Failed: {result1.dq_failed}")
print(f"   Rapport: {result1.dq_report_path}")

if result1.dq_failed > 0:
    print(f"   ✓ SUCCÈS: {result1.dq_failed} tests ont échoué (attendu)")
else:
    print(f"   ✗ ÉCHEC: Aucun test n'a échoué (attendu: 4 échecs)")

# === TEST 2: Données VALIDES ===
print("\n" + "="*80)
print("TEST 2: SOUMISSION VALIDE (doit réussir)")
print("="*80)

df_valid = pd.read_csv('data/sales_valid_upload.csv')
print(f"\nDonnées: {len(df_valid)} lignes")
print(f"  - NaN customer_id: {df_valid['customer_id'].isna().sum()}")
print(f"  - Amount négatif: {(df_valid['amount'] < 0).sum()}")
print(f"  - Amount > 10000: {(df_valid['amount'] > 10000).sum()}")
print(f"  - IDs dupliqués: {df_valid['transaction_id'].duplicated().sum()}")

submission2 = ChannelSubmission(
    submission_id=str(uuid.uuid4())[:8],
    channel_id=validation_channel.channel_id,
    submitted_by="test_user",
    submitted_at=datetime.now(),
    status=SubmissionStatus.PENDING,
    file_mappings=[
        FileMapping(
            file_spec_id='sales_data',
            provided_path='data/sales_valid_upload.csv',
            provided_name='sales_valid_upload.csv'
        )
    ]
)

# Enregistrer
manager.create_submission(submission2)

result2 = processor.process_submission(submission2)

print(f"\n📊 Résultat soumission valide:")
print(f"   Status: {result2.status.value}")
print(f"   DQ Total: {result2.dq_total}")
print(f"   DQ Passed: {result2.dq_passed}")
print(f"   DQ Failed: {result2.dq_failed}")
print(f"   Rapport: {result2.dq_report_path}")

if result2.dq_failed == 0:
    print(f"   ✓ SUCCÈS: Tous les tests ont réussi (attendu)")
else:
    print(f"   ✗ ÉCHEC: {result2.dq_failed} tests ont échoué (attendu: 0 échecs)")

# Résumé
print("\n" + "="*80)
print("RÉSUMÉ FINAL")
print("="*80)

success = (result1.dq_failed > 0) and (result2.dq_failed == 0)

if success:
    print("✅ TOUS LES TESTS PASSENT!")
    print(f"   1. Données invalides: {result1.dq_failed} échecs détectés")
    print(f"   2. Données valides: Tous les tests passent")
    print(f"\n📥 Rapports générés:")
    print(f"   - Invalide: {result1.dq_report_path}")
    print(f"   - Valide: {result2.dq_report_path}")
else:
    print("❌ ÉCHEC:")
    if result1.dq_failed == 0:
        print("   - Les données invalides ne sont PAS rejetées")
    if result2.dq_failed > 0:
        print("   - Les données valides sont REJETÉES par erreur")

print("="*80)
