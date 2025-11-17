"""Guide de test avec logs détaillés."""

print("\n" + "="*70)
print("🔍 TESTS AVEC LOGS DÉTAILLÉS")
print("="*70)

print("""
MAINTENANT AVEC LES NOUVEAUX LOGS:
===================================

1. Relancez l'app: python run.py

2. Soumettez sales_invalid_upload.csv

3. Modal s'ouvre, cliquez sur "Télécharger le rapport"

DANS LE TERMINAL, VOUS DEVRIEZ VOIR:
-------------------------------------
[Download] Demande de téléchargement pour: sub_xxx
[Download] Téléchargement rapport: reports\\...
[Download] Taille du fichier: XXXX octets
[Download] Envoi via dcc.send_file...
[Download] ✅ dcc.send_file retourné: <class 'dict'>
[Download] Contenu: {'base64': True, 'content': '...', 'filename': '...'}

SI VOUS VOYEZ UNE ERREUR:
--------------------------
[Download] ❌ ERREUR dans dcc.send_file: ...
→ Partagez l'erreur complète

4. Cliquez sur "Forcer le dépôt"

DANS LE TERMINAL:
------------------
[Force] Demande de forçage pour: sub_xxx
[Force] Dépôt sub_xxx forcé à l'acceptation
[Force] Nouveau statut: dq_success
[DEBUG Force] Retour: modal=False (fermé), toast créé
[DEBUG Force] Type toast: <class 'dash.html.Div.Div'>
[DEBUG Force] ✅ Retournant: (False, <Div>)

SI VOUS VOYEZ UNE ERREUR:
--------------------------
[DEBUG Force] ❌ ERREUR lors du retour: ...
→ Partagez l'erreur complète

5. Rechargez la page, rouvrez le modal, cliquez sur "Fermer"

DANS LE TERMINAL:
------------------
[DEBUG Fermer] Callback déclenché! n_clicks=1
[DEBUG Fermer] Fermeture du modal, retour False
[DEBUG Fermer] ✅ Retournant: False

APRÈS CES TESTS:
================
→ Partagez-moi TOUTES les lignes [DEBUG...] du terminal
→ Dites-moi ce qui se passe visuellement:
  - Le fichier se télécharge-t-il ?
  - Le modal se ferme-t-il ?
  - Le toast apparaît-il ?

→ Vérifiez votre dossier Téléchargements:
  - Y a-t-il un fichier .xlsx téléchargé ?
  - Quelle est sa taille ?
""")

print("="*70)
print("📋 Les logs détaillés nous diront exactement où ça bloque")
print("="*70)
