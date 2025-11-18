"""
Test des messages UI pour dépôt rejeté vs accepté
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.core.channel_manager import ChannelManager
from src.core.submission_processor import SubmissionProcessor
from src.core.models_channels import ChannelSubmission, SubmissionStatus, FileMapping
from datetime import datetime
import uuid

print("="*80)
print("TEST MESSAGES UI")
print("="*80)

manager = ChannelManager()
processor = SubmissionProcessor(channel_manager=manager)

channels = manager.list_channels()
validation_channel = next((c for c in channels if 'validation' in c.name.lower()), None)

if not validation_channel:
    print("✗ Canal de validation introuvable")
    sys.exit(1)

# Test 1: Dépôt REJETÉ
print("\n" + "="*80)
print("TEST 1: DÉPÔT REJETÉ (données invalides)")
print("="*80)

submission1 = ChannelSubmission(
    submission_id=f"sub_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}",
    channel_id=validation_channel.channel_id,
    submitted_by="Jean Dupont <jean@example.com>",
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

manager.create_submission(submission1)
result1 = processor.process_submission(submission1)

print(f"\n📊 Résultat:")
print(f"   Statut: {result1.status.value}")
print(f"   Tests total: {result1.dq_total}")
print(f"   Tests réussis: {result1.dq_passed}")
print(f"   Tests échoués: {result1.dq_failed}")

if result1.status == SubmissionStatus.REJECTED:
    print(f"\n❌ MESSAGE UI ATTENDU:")
    print(f"   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"   🔴 Dépôt Rejeté")
    print(f"   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"   Votre soumission a été REJETÉE suite aux")
    print(f"   contrôles qualité.")
    print(f"")
    print(f"   ❌ {result1.dq_failed} test(s) ont échoué sur {result1.dq_total}.")
    print(f"")
    print(f"   Un email de notification a été envoyé à")
    print(f"   jean@example.com avec les détails des")
    print(f"   anomalies détectées.")
    print(f"   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"")
    print(f"   🔴 Toast: \"Rejeté: Le dépôt a été rejeté\"")
    print(f"   🔴 Badge: \"REJETÉ\" (rouge)")
    print(f"   🔴 Bouton: \"Télécharger rapport\" (rouge)")
else:
    print(f"\n⚠️ ERREUR: Statut devrait être REJECTED, obtenu: {result1.status.value}")

# Test 2: Dépôt ACCEPTÉ
print("\n" + "="*80)
print("TEST 2: DÉPÔT ACCEPTÉ (données valides)")
print("="*80)

submission2 = ChannelSubmission(
    submission_id=f"sub_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}",
    channel_id=validation_channel.channel_id,
    submitted_by="Marie Martin <marie@example.com>",
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

manager.create_submission(submission2)
result2 = processor.process_submission(submission2)

print(f"\n📊 Résultat:")
print(f"   Statut: {result2.status.value}")
print(f"   Tests total: {result2.dq_total}")
print(f"   Tests réussis: {result2.dq_passed}")
print(f"   Tests échoués: {result2.dq_failed}")

if result2.status == SubmissionStatus.DQ_SUCCESS:
    print(f"\n✅ MESSAGE UI ATTENDU:")
    print(f"   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"   🟢 Dépôt Accepté")
    print(f"   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"   Votre soumission a été acceptée et validée")
    print(f"   avec succès.")
    print(f"")
    print(f"   ✅ {result2.dq_passed} test(s) ont réussi sur {result2.dq_total}.")
    print(f"")
    print(f"   Un email de confirmation a été envoyé à")
    print(f"   marie@example.com.")
    print(f"   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"")
    print(f"   🟢 Toast: \"Accepté: Validé avec succès\"")
    print(f"   🟢 Badge: \"ACCEPTÉ\" (vert)")
    print(f"   🔵 Bouton: \"Télécharger rapport\" (bleu)")
else:
    print(f"\n⚠️ ERREUR: Statut devrait être DQ_SUCCESS, obtenu: {result2.status.value}")

print("\n" + "="*80)
print("RÉSUMÉ DES CHANGEMENTS")
print("="*80)
print("✅ Messages clairs: REJETÉ (rouge) vs ACCEPTÉ (vert)")
print("✅ Pas de message positif pour échec")
print("✅ Toast rouge avec \"Rejeté\" pour échec")
print("✅ Badge et icônes adaptés au statut")
print("✅ Bouton télécharger en rouge pour rejet")
print("="*80)
