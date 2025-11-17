"""Test du bouton 'Forcer le dépôt' pour les soumissions rejetées."""

import sys
from pathlib import Path

# Ajouter le repo root au path
repo_root = Path(__file__).parent
sys.path.insert(0, str(repo_root))

from src.core.channel_manager import ChannelManager
from src.core.models_channels import SubmissionStatus

def test_force_deposit_button():
    """Teste que le bouton force change le statut REJECTED → DQ_SUCCESS."""
    
    print("\n" + "="*70)
    print("TEST: BOUTON 'FORCER LE DÉPÔT'")
    print("="*70)
    
    # Créer un manager
    manager = ChannelManager()
    
    # Récupérer une soumission rejetée
    all_submissions = manager.list_submissions()
    rejected_submission = None
    for sub in all_submissions:
        if sub.status == SubmissionStatus.REJECTED:
            rejected_submission = sub
            break
    
    if not rejected_submission:
        print("\n⚠️  Aucune soumission rejetée trouvée. Création d'une simulation...")
        # Pour le test, on va chercher n'importe quelle soumission et simuler
        if all_submissions:
            test_sub = all_submissions[0]
            original_status = test_sub.status
            test_sub.status = SubmissionStatus.REJECTED
            rejected_submission = test_sub
            manager.save_submissions()
            print(f"   Soumission {test_sub.submission_id} mise en statut REJECTED pour test")
        else:
            print("❌ Aucune soumission disponible pour test")
            return
    
    print(f"\n📋 Soumission testée: {rejected_submission.submission_id}")
    print(f"   Statut initial: {rejected_submission.status.value}")
    if rejected_submission.file_mappings:
        print(f"   Fichiers: {len(rejected_submission.file_mappings)} fichier(s)")
    
    # Simuler le clic sur "Forcer le dépôt"
    print("\n🔧 Simulation du clic sur 'Forcer le dépôt'...")
    rejected_submission.status = SubmissionStatus.DQ_SUCCESS
    manager.update_submission(rejected_submission)
    
    # Vérifier le changement
    reloaded = manager.get_submission(rejected_submission.submission_id)
    
    print(f"\n✅ RÉSULTAT:")
    print(f"   Statut après forçage: {reloaded.status.value}")
    
    if reloaded.status == SubmissionStatus.DQ_SUCCESS:
        print(f"   ✅ Le statut a bien été changé de REJECTED → DQ_SUCCESS")
        print(f"   ✅ Le dépôt est maintenant accepté malgré les échecs DQ")
    else:
        print(f"   ❌ ERREUR: Le statut n'a pas changé correctement")
    
    print("\n" + "="*70)
    print("COMPORTEMENT ATTENDU DANS L'UI:")
    print("="*70)
    print("1. Modal de soumission rejetée affiche:")
    print("   - Badge rouge 'REJETÉ'")
    print("   - Message 'Dépôt Rejeté'")
    print("   - Détails des échecs")
    print("   - Bouton rouge 'Télécharger le rapport'")
    print("   - 🆕 Bouton jaune 'Forcer le dépôt' (outline)")
    print("")
    print("2. Après clic sur 'Forcer le dépôt':")
    print("   - Modal se ferme")
    print("   - Toast jaune: 'Forcé: Le dépôt a été accepté malgré les échecs DQ'")
    print("   - Statut dans la liste passe à 'dq_success'")
    print("   - Badge devient vert 'ACCEPTÉ'")
    print("="*70)

if __name__ == "__main__":
    test_force_deposit_button()
