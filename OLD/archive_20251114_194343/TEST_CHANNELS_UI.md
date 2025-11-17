# Guide de Test - Système de Canaux

## Application lancée ✅

L'application Dash tourne sur **http://127.0.0.1:8050/**

## Tests à effectuer

### 1. Page d'Administration des Canaux (`/channel-admin`)

**URL:** http://127.0.0.1:8050/channel-admin

**Tests:**
- [ ] Vérifier que la page se charge sans erreur
- [ ] Cliquer sur "Nouveau Canal" - le modal doit s'ouvrir
- [ ] Remplir les informations du canal:
  - Channel ID: `test_finance`
  - Nom: `Test Finance Channel`
  - Équipe: `Finance Team`
  - Description: `Canal de test pour les données financières`
  - Actif: ✓ coché
- [ ] Ajouter une file specification:
  - File ID: `sales_data`
  - Nom: `Données de Ventes`
  - Format: CSV
  - Requis: ✓ coché
- [ ] Sélectionner une ou plusieurs configs DQ (dropdown)
- [ ] Remplir emails:
  - Équipe: `finance@example.com`
  - Admins: `admin@example.com`
- [ ] Sauvegarder le canal
- [ ] Vérifier que le canal apparaît dans la liste
- [ ] Éditer le canal créé
- [ ] Supprimer le canal (si nécessaire)

### 2. Page de Dépôt (`/channel-drop`)

**URL:** http://127.0.0.1:8050/channel-drop

**Tests:**
- [ ] Vérifier que la page se charge
- [ ] Le dropdown "Canal de dépôt" doit contenir les canaux actifs créés via `/channel-admin`
- [ ] Sélectionner un canal - les fichiers attendus doivent s'afficher
- [ ] Pour chaque fichier attendu:
  - [ ] Entrer un chemin (ex: `sourcing/input/sales_2024.csv`)
  - [ ] La validation doit indiquer si le fichier existe
- [ ] Remplir informations de contact:
  - Nom: `Jean Dupont`
  - Email: `jean.dupont@finance.example.com`
- [ ] Vérifier le résumé
- [ ] Cliquer sur "Soumettre le Dépôt"
- [ ] Une modal de succès doit s'afficher avec le numéro de suivi

### 3. Dashboard DQ Management (`/dq-editor-dashboard`)

**URL:** http://127.0.0.1:8050/dq-editor-dashboard

**Tests:**
- [ ] Vérifier que la page se charge
- [ ] Le bouton "Admin Canaux" doit être visible
- [ ] Cliquer dessus doit rediriger vers `/channel-admin`

### 4. Dashboard Check & Drop (`/check-drop-dashboard`)

**URL:** http://127.0.0.1:8050/check-drop-dashboard

**Tests:**
- [ ] Vérifier que la page se charge
- [ ] Le bouton "Déposer mes Données" doit être visible
- [ ] Cliquer dessus doit rediriger vers `/channel-drop`

### 5. Backend - Workflow Complet

Si un canal existe avec un fichier mappé à un vrai fichier:

**Vérifications:**
- [ ] Après soumission, vérifier `managed_folders/channels/submissions.json`
  - La soumission doit être enregistrée
  - Le statut doit passer de `pending` → `processing` → `dq_success` ou `dq_failed`
- [ ] Vérifier la génération du rapport Excel:
  - Dossier: `reports/channel_submissions/`
  - Fichier: `{channel_id}_{submission_id}_{timestamp}.xlsx`
- [ ] Ouvrir le rapport Excel:
  - [ ] Onglet "Métriques" avec colonnes execution_status, value, error
  - [ ] Onglet "Tests" avec colonnes execution_status, result, error
- [ ] Vérifier les logs de l'email (console):
  - [ ] Template approprié (succès/échec)
  - [ ] Variables remplacées ({channel_name}, {dq_passed}, etc.)
  - [ ] Destinataires corrects

## Problèmes connus

### Avertissements (non bloquants)
- **Java warning**: Le contexte Spark émet un avertissement car Java n'est pas installé. Cela n'affecte pas le système de canaux.
- **Pydantic warning**: Un champ `schema` masque un attribut parent. Cela n'affecte pas le fonctionnement.

### Limitations actuelles
- **Emails simulés**: Les emails sont imprimés dans la console, pas envoyés réellement (SMTP non configuré)
- **Pattern matching callbacks**: Certains callbacks utilisent `dash.dependencies.ALL` - vérifier qu'ils fonctionnent correctement
- **Upload de fichiers**: L'interface utilise des inputs texte au lieu d'un upload component

## Workflows de test suggérés

### Workflow 1: Canal Simple
1. Créer canal `test_simple` avec 1 fichier CSV requis
2. Associer `sales_complete_quality.yaml` comme DQ
3. Sauvegarder
4. Aller sur `/channel-drop`
5. Sélectionner `test_simple`
6. Fournir `sourcing/input/sales_2024.csv`
7. Soumettre
8. Vérifier que le rapport est généré

### Workflow 2: Canal Multi-fichiers
1. Créer canal `test_multi` avec 2 fichiers requis
2. sales_data (CSV) et refunds_data (CSV)
3. Associer plusieurs configs DQ
4. Tester soumission avec tous les fichiers
5. Vérifier que tous les DQ sont exécutés

### Workflow 3: Validation des Erreurs
1. Créer un canal
2. Tenter de soumettre sans fournir un fichier requis
3. Vérifier que l'erreur est affichée
4. Fournir un chemin invalide
5. Vérifier le message d'avertissement

## Commandes utiles

```bash
# Voir les canaux créés
python -c "from src.core.channel_manager import get_channel_manager; m = get_channel_manager(); print([c.name for c in m.list_channels()])"

# Voir les soumissions
python -c "from src.core.channel_manager import get_channel_manager; m = get_channel_manager(); subs = m.list_submissions(); print(f'{len(subs)} soumissions')"

# Nettoyer les données de test
Remove-Item managed_folders\channels\*.json

# Relancer la démo backend
python demo_channels.py
```

## Prochaines étapes

Une fois les tests UI validés:
1. **SMTP réel**: Configurer un serveur SMTP pour envoyer de vrais emails
2. **File upload**: Remplacer les inputs texte par `dcc.Upload` pour uploader des fichiers
3. **Authentification**: Ajouter OAuth/JWT pour sécuriser l'accès
4. **Monitoring**: Créer une page de monitoring des soumissions
5. **Webhooks**: Notifier des systèmes externes (Slack, Teams, etc.)
