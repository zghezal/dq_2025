"""Test pour vérifier que les boutons ont des effets visibles."""

print("\n" + "="*70)
print("🔍 CHECKLIST DE VÉRIFICATION")
print("="*70)

print("""
APRÈS AVOIR SOUMIS UN FICHIER ET OUVERT LE MODAL:
==================================================

1. BOUTON "TÉLÉCHARGER LE RAPPORT":
   ✅ Dans le terminal: Voir "[Download] Téléchargement rapport: ..."
   ✅ Dans le navigateur: Un fichier Excel doit se télécharger
   ✅ Vérifier dans votre dossier Téléchargements
   ❌ Si rien ne se télécharge: Vérifier la console navigateur (F12)

2. BOUTON "FORCER LE DÉPÔT":
   ✅ Dans le terminal: Voir "[Force] Dépôt forcé à l'acceptation"
   ✅ Dans le terminal: Voir "[DEBUG Force] Retour: modal=False (fermé)"
   ✅ Le modal DOIT se fermer automatiquement
   ✅ Un toast jaune doit apparaître en haut à droite
   ❌ Si le modal ne se ferme pas: PROBLÈME !

3. BOUTON "FERMER":
   ✅ Dans le terminal: Voir "[DEBUG Fermer] Callback déclenché!"
   ✅ Dans le terminal: Voir "[DEBUG Fermer] Fermeture du modal"
   ✅ Le modal DOIT se fermer
   ❌ Si le modal ne se ferme pas: PROBLÈME !

TESTS À FAIRE:
==============
1. Soumettez sales_invalid_upload.csv
2. Regardez le modal qui s'ouvre
3. Cliquez sur "Télécharger le rapport"
   → Regardez votre dossier Téléchargements
   → Un fichier .xlsx doit apparaître
4. Cliquez sur "Forcer le dépôt"
   → Le modal doit se fermer immédiatement
   → Un toast jaune doit apparaître
5. Rouvrez le modal (rechargez la page si besoin)
6. Cliquez sur "Fermer"
   → Le modal doit se fermer

SI LE MODAL NE SE FERME PAS:
=============================
→ Vérifiez la console du navigateur (F12) pour des erreurs
→ Partagez les erreurs que vous voyez
→ Partagez ce que vous voyez dans le terminal Python
""")

print("="*70)
