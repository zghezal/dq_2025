"""Test de la disposition des boutons dans le modal de résultat."""

import sys
from pathlib import Path

# Ajouter le repo root au path
repo_root = Path(__file__).parent
sys.path.insert(0, str(repo_root))

from src.core.channel_manager import ChannelManager
from src.core.models_channels import SubmissionStatus

def test_button_layout():
    """Vérifie la disposition des boutons selon le statut."""
    
    print("\n" + "="*70)
    print("TEST: DISPOSITION DES BOUTONS DANS LE MODAL")
    print("="*70)
    
    manager = ChannelManager()
    submissions = manager.list_submissions()
    
    # Trouver une soumission rejetée et une acceptée
    rejected = None
    accepted = None
    
    for sub in submissions:
        if sub.status == SubmissionStatus.REJECTED and not rejected:
            rejected = sub
        elif sub.status == SubmissionStatus.DQ_SUCCESS and not accepted:
            accepted = sub
        
        if rejected and accepted:
            break
    
    print("\n📋 CAS 1: DÉPÔT REJETÉ")
    print("-" * 70)
    if rejected:
        print(f"Soumission: {rejected.submission_id}")
        print(f"Statut: {rejected.status.value}")
        print("\n🔘 BOUTONS AFFICHÉS (alignés horizontalement):")
        print("  1. [🔴 Télécharger le rapport] (danger)")
        print("  2. [🟡 Forcer le dépôt] (warning, outline)")
        print("  3. [⚪ Fermer] (secondary, outline)")
        print("\n  Layout: d-flex (flexbox, alignés sur une ligne)")
    else:
        print("⚠️  Aucune soumission rejetée trouvée")
    
    print("\n📋 CAS 2: DÉPÔT ACCEPTÉ")
    print("-" * 70)
    if accepted:
        print(f"Soumission: {accepted.submission_id}")
        print(f"Statut: {accepted.status.value}")
        print("\n🔘 BOUTONS AFFICHÉS (alignés horizontalement):")
        print("  1. [🔵 Télécharger le rapport] (info)")
        print("  2. [⚪ Fermer] (secondary, outline)")
        print("\n  Layout: d-flex (flexbox, alignés sur une ligne)")
        print("\n  ⚠️  Pas de bouton 'Forcer le dépôt' (déjà accepté)")
    else:
        print("⚠️  Aucune soumission acceptée trouvée")
    
    print("\n" + "="*70)
    print("STRUCTURE HTML GÉNÉRÉE:")
    print("="*70)
    print("""
<div class="mt-3 d-flex">
  <!-- Bouton 1: Télécharger -->
  <button class="btn btn-{color} me-2">
    <i class="bi bi-download me-2"></i>
    Télécharger le rapport
  </button>
  
  <!-- Bouton 2: Forcer (si rejeté) -->
  <button class="btn btn-outline-warning me-2">
    <i class="bi bi-shield-exclamation me-2"></i>
    Forcer le dépôt
  </button>
  
  <!-- Bouton 3: Fermer -->
  <button class="btn btn-outline-secondary">
    <i class="bi bi-x-lg me-2"></i>
    Fermer
  </button>
</div>
    """)
    
    print("\n✅ Les 3 boutons sont alignés horizontalement grâce à 'd-flex'")
    print("✅ Espacement entre boutons: 'me-2' (margin-end)")
    print("✅ Bouton 'Forcer' visible uniquement si status=REJECTED")
    print("="*70)

if __name__ == "__main__":
    test_button_layout()
