"""Guide de debug pour les boutons du modal."""

print("\n" + "="*70)
print("🔍 GUIDE DE DEBUG - BOUTONS MODAL")
print("="*70)

print("""
ÉTAPES POUR DÉBOGUER:
=====================

1. Relancez l'application:
   python run.py

2. Soumettez un fichier qui sera rejeté (ex: sales_invalid_upload.csv)

3. DANS LE TERMINAL PYTHON, vous devriez voir:
   
   [DEBUG Boutons] Création des boutons pour submission: sub_xxx
   [DEBUG Boutons] is_rejected = True
   [DEBUG Boutons] dq_report_path = reports/...
   [DEBUG Boutons] Bouton télécharger créé avec ID: {'type': 'download-report-btn', 'submission_id': 'sub_xxx'}
   [DEBUG Boutons] Bouton forcer créé avec ID: {'type': 'force-deposit-btn', 'submission_id': 'sub_xxx'}
   [DEBUG Boutons] Nombre total de boutons: 2

4. Quand vous CLIQUEZ sur "Télécharger le rapport", vous devriez voir:
   
   ============================================================
   [DEBUG Download] Callback déclenché!
   [DEBUG Download] n_clicks_list = [1]
   [DEBUG Download] ctx.triggered = [{'prop_id': '...', 'value': 1}]
   [DEBUG Download] ctx.triggered_id = {'type': 'download-report-btn', 'submission_id': 'sub_xxx'}
   [Download] Demande de téléchargement pour: sub_xxx
   [Download] Téléchargement rapport: reports/...

5. Quand vous CLIQUEZ sur "Forcer le dépôt", vous devriez voir:
   
   ============================================================
   [DEBUG Force] Callback déclenché!
   [DEBUG Force] n_clicks_list = [1]
   [DEBUG Force] ctx.triggered = [{'prop_id': '...', 'value': 1}]
   [DEBUG Force] ctx.triggered_id = {'type': 'force-deposit-btn', 'submission_id': 'sub_xxx'}
   [Force] Demande de forçage pour: sub_xxx
   [Force] Dépôt sub_xxx forcé à l'acceptation

SI AUCUN LOG N'APPARAÎT QUAND VOUS CLIQUEZ:
============================================
→ Le callback n'est PAS déclenché
→ Vérifiez dans la console du navigateur (F12) s'il y a des erreurs
→ Vérifiez que les boutons sont bien rendus dans le HTML (Inspecter l'élément)

SI VOUS VOYEZ "[DEBUG Download] Pas de triggered_id":
======================================================
→ Le callback est déclenché mais ctx.triggered_id est None
→ Problème avec le pattern matching des IDs

SI VOUS VOYEZ DES ERREURS DANS LA CONSOLE DU NAVIGATEUR:
==========================================================
→ Copiez l'erreur complète et partagez-la
""")

print("="*70)
print("✅ Logs de debug ajoutés dans les callbacks")
print("="*70)
