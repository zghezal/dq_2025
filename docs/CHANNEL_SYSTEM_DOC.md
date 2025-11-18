# Système de Canaux de Dépôt (Drop Channels)

## Vue d'ensemble

Le système de canaux de dépôt permet aux **équipes externes** de livrer des données via des **canaux configurés** par les **administrateurs**. Le système effectue automatiquement les contrôles qualité et envoie des rapports par email.

## Architecture

```
┌─────────────────┐
│  Administrateur │
│                 │
│  Crée canaux    │
│  Configure DQ   │
│  Définit emails │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│           Canal de Dépôt                │
│  • Fichiers attendus                    │
│  • Configurations DQ associées          │
│  • Templates d'emails                   │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│  Équipe Externe │
│                 │
│  Sélectionne    │
│  canal          │
│  Fournit liens  │
│  fichiers       │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│      Traitement Automatique             │
│  1. Validation fichiers                 │
│  2. Chargement données                  │
│  3. Exécution DQ                        │
│  4. Génération rapport Excel            │
│  5. Envoi email (succès/échec)          │
└─────────────────────────────────────────┘
         │
         ├──► Email équipe externe (toujours)
         │
         └──► Email admins (si succès)
```

## Composants

### 1. Modèles de Données (`src/core/models_channels.py`)

#### DropChannel
Canal configuré par les administrateurs:
- **channel_id**: Identifiant unique
- **name**: Nom descriptif
- **team_name**: Équipe responsable
- **file_specifications**: Liste des fichiers attendus
- **dq_configs**: Liste des configs DQ à exécuter
- **email_config**: Configuration des notifications

#### FileSpecification
Définition d'un fichier attendu:
- **file_id**: Identifiant unique du fichier
- **name**: Nom descriptif
- **format**: CSV, Excel, Parquet, JSON
- **required**: Obligatoire ou optionnel
- **expected_columns**: Colonnes attendues (validation)

#### ChannelSubmission
Soumission par une équipe externe:
- **submission_id**: Identifiant unique
- **channel_id**: Canal utilisé
- **file_mappings**: Liens vers fichiers fournis
- **status**: pending, processing, dq_success, dq_failed, error
- **dq_execution_results**: Résultats des contrôles
- **dq_report_path**: Chemin vers le rapport Excel

#### EmailConfig
Configuration des notifications:
- **recipient_team_emails**: Emails de l'équipe externe
- **admin_emails**: Emails des admins (notification succès)
- **success_subject/body_template**: Template email succès
- **failure_subject/body_template**: Template email échec

### 2. Gestionnaire de Canaux (`src/core/channel_manager.py`)

#### ChannelManager
CRUD complet pour les canaux et soumissions:

```python
from src.core.channel_manager import get_channel_manager

manager = get_channel_manager()

# Canaux
channel = manager.create_channel(channel)
channel = manager.update_channel(channel)
channel = manager.get_channel(channel_id)
channels = manager.list_channels(active_only=True)

# Soumissions
submission = manager.create_submission(submission)
submission = manager.update_submission(submission)
submissions = manager.list_submissions(channel_id=channel_id)

# Statistiques
stats = manager.get_channel_statistics(channel_id)
```

### 3. Processeur de Soumissions (`src/core/submission_processor.py`)

#### SubmissionProcessor
Traite automatiquement les soumissions:

```python
from src.core.submission_processor import SubmissionProcessor

processor = SubmissionProcessor(channel_manager)
processed_submission = processor.process_submission(submission)
```

**Étapes du traitement:**
1. **Validation** : Vérifier que tous fichiers requis sont fournis
2. **Chargement** : Charger les DataFrames depuis les fichiers
3. **Exécution DQ** : Exécuter tous les contrôles configurés
4. **Rapport** : Générer un rapport Excel avec DQExcelExporter
5. **Notification** : Envoyer emails selon le résultat

### 4. Interfaces Utilisateur

#### Interface Admin (`src/layouts/channel_admin.py`)
Page `/channel-admin` pour les administrateurs:
- Créer/éditer/supprimer des canaux
- Définir les fichiers attendus (format, colonnes, obligatoire/optionnel)
- Associer les configurations DQ
- Configurer les emails (destinataires, templates)
- Voir les statistiques par canal

#### Interface Dépôt (`src/layouts/channel_drop.py`)
Page `/channel-drop` pour les équipes externes:
- Sélectionner le canal approprié
- Voir les fichiers attendus
- Fournir les liens vers les fichiers
- Valider et soumettre
- Recevoir confirmation avec numéro de suivi

## Workflow Complet

### Côté Administrateur

```python
from src.core.models_channels import *
from src.core.channel_manager import get_channel_manager

manager = get_channel_manager()

# 1. Créer un canal
channel = DropChannel(
    channel_id="finance_monthly",
    name="Dépôt Finance Mensuel",
    team_name="Finance",
    file_specifications=[
        FileSpecification(
            file_id="sales_data",
            name="Données de Ventes",
            format=FileFormat.CSV,
            required=True,
            expected_columns=["date", "amount", "product_id"]
        )
    ],
    dq_configs=[
        "dq/definitions/sales_complete_quality.yaml"
    ],
    email_config=EmailConfig(
        recipient_team_emails=["finance@example.com"],
        admin_emails=["dq-admin@example.com"]
    )
)

manager.create_channel(channel)
```

### Côté Équipe Externe

```python
# 1. Créer une soumission
submission = ChannelSubmission(
    submission_id="sub_20251107_001",
    channel_id="finance_monthly",
    submitted_by="jean.dupont@finance.example.com",
    file_mappings=[
        FileMapping(
            file_spec_id="sales_data",
            provided_path="/path/to/sales_data.csv",
            provided_name="sales_data.csv"
        )
    ]
)

manager.create_submission(submission)

# 2. Traiter automatiquement
processor = SubmissionProcessor(manager)
result = processor.process_submission(submission)

# Résultat:
# - Statut: dq_success ou dq_failed
# - Rapport Excel généré
# - Emails envoyés
```

## Configuration des Emails

### Variables Disponibles

Templates email supportent ces variables:

- `{channel_name}` : Nom du canal
- `{submission_date}` : Date de soumission
- `{file_count}` : Nombre de fichiers
- `{dq_total}` : Total contrôles
- `{dq_passed}` : Contrôles réussis
- `{dq_failed}` : Contrôles échoués

### Exemple Email Succès

```
Sujet: ✅ Dépôt de données validé - {channel_name}

Bonjour,

Votre dépôt de données sur le canal "{channel_name}" a été traité avec succès.

Résumé:
- Date de dépôt: {submission_date}
- Fichiers traités: {file_count}
- Contrôles qualité: {dq_passed}/{dq_total} réussis

Vous trouverez le rapport détaillé en pièce jointe.

Cordialement,
L'équipe Data Quality
```

### Exemple Email Échec

```
Sujet: ⚠️ Dépôt de données - Anomalies détectées - {channel_name}

Bonjour,

Votre dépôt de données sur le canal "{channel_name}" a été traité mais des anomalies ont été détectées.

Résumé:
- Date de dépôt: {submission_date}
- Fichiers traités: {file_count}
- Contrôles qualité: {dq_passed}/{dq_total} réussis
- Anomalies: {dq_failed} contrôle(s) en échec

Merci de consulter le rapport détaillé en pièce jointe et de corriger les données.

Cordialement,
L'équipe Data Quality
```

## Rapports Générés

Les rapports Excel sont générés automatiquement et contiennent:

### Onglet "Métriques"
- ID, Type, Name, Description
- **Execution_Status** : SUCCESS, ERROR, SKIPPED
- Value, Error, Timestamp

### Onglet "Tests"
- control_id, dataset, category
- **execution_status** : SUCCESS, FAIL, ERROR, SKIPPED
- result, description, error
- Quarter, Project, User, Timestamp

### Onglets de Données (optionnel)
Si une métrique a `export=true`, un onglet avec les données détaillées est créé.

## Stockage

### Fichiers de Configuration

```
managed_folders/channels/
├── channels.json        # Définitions des canaux
└── submissions.json     # Historique des soumissions
```

### Rapports

```
reports/channel_submissions/
└── {channel_id}_{submission_id}_{timestamp}.xlsx
```

## Statuts de Soumission

| Statut | Description | Email envoyé | Destinataires |
|--------|-------------|--------------|---------------|
| **pending** | En attente de traitement | Non | - |
| **processing** | Traitement en cours | Non | - |
| **dq_success** | Tous contrôles OK | Oui (succès) | Équipe + Admins |
| **dq_failed** | Contrôles échoués | Oui (échec) | Équipe uniquement |
| **error** | Erreur technique | Oui (échec) | Équipe uniquement |

## API REST (À implémenter)

### Endpoints Proposés

```
POST /api/channels                    # Créer canal (admin)
GET  /api/channels                    # Lister canaux
GET  /api/channels/{id}              # Détails canal
PUT  /api/channels/{id}              # Modifier canal (admin)
DELETE /api/channels/{id}            # Supprimer canal (admin)

POST /api/channels/{id}/submit       # Soumettre fichiers
GET  /api/submissions                # Lister soumissions
GET  /api/submissions/{id}           # Détails soumission
GET  /api/submissions/{id}/report    # Télécharger rapport

GET  /api/channels/{id}/statistics   # Statistiques canal
```

## Sécurité

### À Implémenter

- **Authentification** : OAuth2 ou JWT pour identifier les utilisateurs
- **Autorisation** : Rôles (admin, team_member)
- **Validation** : Vérifier format des fichiers, taille max
- **Scan antivirus** : Scanner les fichiers uploadés
- **Chiffrement** : HTTPS pour les transferts, chiffrement au repos

## Démo

Exécutez `demo_channels.py` pour voir le workflow complet:

```bash
python demo_channels.py
```

Cette démo:
1. Crée 2 canaux (Finance, Marketing)
2. Soumet des données sur le canal Finance
3. Traite automatiquement (validation, DQ, rapport, email)
4. Affiche l'historique et les statistiques

## Intégration avec l'UI Dash

### Ajouter aux routes

```python
# app.py
from src.layouts.channel_admin import channel_admin_page
from src.layouts.channel_drop import channel_drop_page

# Dans le router
if clean_path == "/channel-admin":
    return channel_admin_page()
if clean_path == "/channel-drop":
    return channel_drop_page()
```

### Callbacks à Implémenter

- Charger liste canaux
- Créer/éditer canal (modal)
- Ajouter fichier attendu
- Soumettre dépôt
- Afficher résultats

## Évolutions Futures

### Phase 1 (Actuel)
- ✅ Modèles de données
- ✅ CRUD canaux
- ✅ Traitement automatique
- ✅ Génération rapports
- ✅ Simulation emails

### Phase 2
- [ ] Vrai envoi d'emails (SMTP)
- [ ] Upload de fichiers via UI
- [ ] Validation schéma stricte
- [ ] Support S3/Azure Blob
- [ ] Webhooks pour notifications

### Phase 3
- [ ] API REST complète
- [ ] Authentification/Autorisation
- [ ] Dashboard temps réel
- [ ] Alertes Slack/Teams
- [ ] Archivage automatique

## Maintenance

### Nettoyage des Soumissions

```python
from datetime import datetime, timedelta
from src.core.channel_manager import get_channel_manager

manager = get_channel_manager()

# Supprimer soumissions > 90 jours
cutoff_date = datetime.now() - timedelta(days=90)
old_submissions = [
    s for s in manager.list_submissions() 
    if s.submitted_at < cutoff_date
]

# (À implémenter: méthode delete_submission)
```

### Monitoring

```python
# Vérifier canaux sans soumission récente
for channel in manager.list_channels(active_only=True):
    stats = manager.get_channel_statistics(channel.channel_id)
    if stats['total_submissions'] == 0:
        print(f"⚠️  Canal inactif: {channel.name}")
    
    if stats['success_rate'] < 50:
        print(f"⚠️  Taux échec élevé: {channel.name} ({stats['success_rate']}%)")
```
