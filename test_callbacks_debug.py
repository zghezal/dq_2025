"""Debug des callbacks pour les boutons du modal."""

import sys
from pathlib import Path

# Ajouter le repo root au path
repo_root = Path(__file__).parent
sys.path.insert(0, str(repo_root))

# Simuler ce qui se passe dans le callback
import json

# Exemple de triggered_id qui viendrait du callback
triggered_id_examples = [
    '{"index":0,"type":"download-report-btn","submission_id":"sub_20251114_215050_4ad1da4c"}.n_clicks',
    '{"type":"download-report-btn","submission_id":"sub_20251114_215050_4ad1da4c"}.n_clicks',
]

print("\n" + "="*70)
print("TEST: PARSING DES IDs DE BOUTONS")
print("="*70)

for triggered_id in triggered_id_examples:
    print(f"\n📋 Triggered ID: {triggered_id}")
    
    # Extraire la partie avant le point
    id_part = triggered_id.split('.')[0]
    print(f"   Partie ID: {id_part}")
    
    try:
        button_id = json.loads(id_part)
        print(f"   ✅ Parsé avec succès: {button_id}")
        print(f"   submission_id = {button_id['submission_id']}")
    except Exception as e:
        print(f"   ❌ Erreur de parsing: {e}")

print("\n" + "="*70)
print("VÉRIFICATION: Les boutons sont-ils générés avec les bons IDs ?")
print("="*70)

from src.core.channel_manager import ChannelManager
from src.core.models_channels import SubmissionStatus

manager = ChannelManager()
submissions = manager.list_submissions()

rejected = None
for sub in submissions:
    if sub.status == SubmissionStatus.REJECTED:
        rejected = sub
        break

if rejected:
    print(f"\n📋 Soumission rejetée trouvée: {rejected.submission_id}")
    print(f"\nID du bouton Télécharger devrait être:")
    print(f"   {{'type': 'download-report-btn', 'submission_id': '{rejected.submission_id}'}}")
    print(f"\nID du bouton Forcer devrait être:")
    print(f"   {{'type': 'force-deposit-btn', 'submission_id': '{rejected.submission_id}'}}")
    
    print(f"\n🔍 Vérification du rapport:")
    if rejected.dq_report_path:
        report_path = Path(rejected.dq_report_path)
        if report_path.exists():
            print(f"   ✅ Rapport existe: {report_path}")
        else:
            print(f"   ❌ Rapport introuvable: {report_path}")
    else:
        print(f"   ❌ Pas de chemin de rapport défini")
else:
    print("\n⚠️  Aucune soumission rejetée")

print("\n" + "="*70)
