# 🎯 Guide Rapide - Système de Canaux

## ✅ Statut Actuel

Le système de canaux est **100% fonctionnel** avec **3 canaux actifs** :

1. 💰 **Finance Mensuel** — 2 fichiers attendus, 1 config DQ
2. 📊 **Marketing Hebdomadaire** — 1 fichier attendu
3. 👥 **RH Mensuel** — 2 fichiers attendus (nouveau!)

---

## 🚀 Démarrage Rapide

### Pour Lancer l'Application

```powershell
python run.py
```

L'application démarre sur **http://localhost:5002**

### URLs Principales

| Page | URL | Description |
|------|-----|-------------|
| 🏠 Accueil | http://localhost:5002/ | Page d'accueil |
| 🔧 Admin Canaux | http://localhost:5002/channel-admin | Créer/éditer des canaux |
| 📤 Dépôt | http://localhost:5002/channel-drop | Déposer des fichiers |
| 📋 Check & Drop | http://localhost:5002/check-drop | Dashboard de dépôt |

---

## 📝 Actions Courantes

### 1. Créer un Canal (Interface Admin)

1. Aller sur http://localhost:5002/channel-admin
2. Cliquer sur **"Nouveau Canal"**
3. Remplir le formulaire :
   - **ID** : Identifiant unique (ex: `finance_q1`)
   - **Nom** : Nom d'affichage (ex: "Dépôt Finance Q1")
   - **Équipe** : Nom de l'équipe (ex: "Finance")
   - **Description** : Texte descriptif
4. Ajouter les fichiers attendus avec **"Ajouter un fichier"**
5. Configurer les emails
6. **Enregistrer**

### 2. Créer un Canal (Script Python)

```python
from src.core.channel_manager import get_channel_manager
from src.core.models_channels import DropChannel, FileSpecification, EmailConfig, FileFormat

# Créer le canal
channel = DropChannel(
    channel_id="mon_canal",
    name="Mon Canal",
    team_name="Mon Équipe",
    file_specifications=[...],
    email_config=EmailConfig(...),
    active=True
)

# Sauvegarder
manager = get_channel_manager()
manager.create_channel(channel)
```

Voir `demo_create_channel.py` pour un exemple complet.

### 3. Déposer des Fichiers

1. Aller sur http://localhost:5002/channel-drop
2. **Sélectionner votre canal** dans le dropdown
3. **Fournir les fichiers** (chemins locaux ou URLs)
4. **Renseigner vos coordonnées** (nom + email)
5. **Soumettre**

→ Vous recevez un numéro de suivi et un email avec les résultats DQ

### 4. Lister les Canaux (Script)

```powershell
python test_channels_display.py
```

→ Affiche tous les canaux avec leurs détails et statistiques

---

## 🔍 Vérification Rapide

Pour vérifier que tout fonctionne :

```powershell
# Test 1: Lister les canaux
python test_channels_display.py

# Test 2: Créer un canal de démo
python demo_create_channel.py

# Test 3: Lancer l'app
python run.py
# Puis ouvrir http://localhost:5002/channel-admin
```

---

## 📂 Fichiers de Données

Les canaux et soumissions sont stockés en JSON :

```
managed_folders/
  channels/
    channels.json       ← Définitions des canaux
    submissions.json    ← Historique des soumissions
```

**Sauvegarde recommandée** : Faites une copie de ces fichiers régulièrement !

---

## 🛠️ Résolution de Problèmes

### Problème : "Le canal n'apparaît pas dans le dropdown"

**Solutions :**
1. Vérifier que le canal est **actif** (`active: true`)
2. Attendre 30 secondes (rafraîchissement automatique)
3. Cliquer sur **"Actualiser"** dans l'interface
4. Vérifier `managed_folders/channels/channels.json`

### Problème : "Le bouton Soumettre est grisé"

**Causes possibles :**
- ✋ Fichiers requis manquants
- ✋ Email non renseigné
- ✋ Aucun canal sélectionné

→ Vérifier le **récapitulatif** en bas de page pour voir ce qui manque.

### Problème : "Erreur lors de la création d'un canal"

**Vérifications :**
1. L'ID du canal est-il **unique** ?
2. Tous les champs **obligatoires** sont-ils remplis ?
3. Le fichier `channels.json` est-il **accessible en écriture** ?

---

## 🎨 Fonctionnalités Clés

✨ **Rafraîchissement auto** — Liste mise à jour toutes les 30s  
✨ **Toast notifications** — Confirmations visuelles instantanées  
✨ **Validation temps réel** — Vérification des fichiers pendant la saisie  
✨ **Bouton intelligent** — Activation uniquement si le formulaire est valide  
✨ **Modal responsive** — Interface fluide avec fermeture propre  
✨ **Statistiques** — Suivi des soumissions et taux de succès par canal  

---

## 📚 Documentation Complète

| Document | Description |
|----------|-------------|
| `CHANNELS_READY.md` | ✅ Guide complet du système de canaux |
| `CHANNEL_SYSTEM_DOC.md` | 📖 Documentation technique détaillée |
| `TEST_CHANNELS_UI.md` | 🧪 Guide de test de l'interface |
| `.github/copilot-instructions.md` | 🤖 Instructions pour agents AI |

---

## 🎓 Exemples de Code

### Récupérer un Canal

```python
from src.core.channel_manager import get_channel_manager

manager = get_channel_manager()
channel = manager.get_channel("finance_monthly")

if channel:
    print(f"Canal: {channel.name}")
    print(f"Fichiers: {len(channel.file_specifications)}")
```

### Lister les Canaux Actifs

```python
manager = get_channel_manager()
active_channels = manager.list_channels(active_only=True)

for channel in active_channels:
    print(f"- {channel.name} ({channel.team_name})")
```

### Obtenir les Statistiques

```python
manager = get_channel_manager()
stats = manager.get_channel_statistics("finance_monthly")

print(f"Soumissions: {stats['total_submissions']}")
print(f"Succès: {stats['dq_success']}")
print(f"Taux: {stats['success_rate']:.1f}%")
```

---

## ✅ Checklist de Validation

Avant de mettre en production, vérifiez :

- [ ] L'application démarre sans erreur (`python run.py`)
- [ ] Les canaux apparaissent dans `/channel-admin`
- [ ] Les canaux apparaissent dans `/channel-drop`
- [ ] La création de canal fonctionne
- [ ] L'édition de canal fonctionne
- [ ] La suppression de canal fonctionne
- [ ] La soumission de fichiers fonctionne
- [ ] Les emails sont bien configurés (destinataires)
- [ ] Les configs DQ sont associées (si applicable)
- [ ] Le fichier `channels.json` est sauvegardé

---

## 🚀 Prochaines Améliorations (Optionnel)

1. **SMTP réel** — Envoyer de vrais emails (actuellement simulé)
2. **Upload de fichiers** — Permettre l'upload direct plutôt que des liens
3. **Dashboard stats** — Graphiques et métriques avancées
4. **Permissions** — Restreindre l'accès admin
5. **API REST** — Endpoints pour intégration externe
6. **Webhook** — Notifications vers systèmes tiers
7. **Archivage** — Compression et archivage des anciennes soumissions

---

**💡 Conseil Final**

Le système est conçu pour être **simple et extensible**. Pour toute personnalisation :

1. Consultez les modèles dans `src/core/models_channels.py`
2. Étudiez les callbacks dans `src/callbacks/channels_*.py`
3. Référez-vous aux layouts dans `src/layouts/channel_*.py`

**Bon courage avec votre système de dépôt de données ! 🎉**
