# ✅ CHECKLIST DE TEST MANUEL - APPLICATION DQ

## 🎯 Objectif
Vérifier que toutes les fonctionnalités principales de l'application fonctionnent correctement après nettoyage.

---

## 🏠 PAGE D'ACCUEIL (/)

### Navigation
- [ ] **Bouton "Accès Client"** → Redirige vers `/check-drop-dashboard`
- [ ] **Bouton "DQ Editor"** → Redirige vers `/dq-editor-dashboard`

---

## 📥 PAGE ACCÈS CLIENT (/check-drop-dashboard)

### Sélection de canal
- [ ] Dropdown affiche les 9 canaux disponibles
- [ ] Sélection d'un canal affiche ses fichiers attendus

### Upload de fichiers
- [ ] **Bouton "📂 Parcourir..."** ouvre le sélecteur de fichiers
- [ ] Texte d'aide "💡 Fichiers de test disponibles dans: data/" visible
- [ ] Après sélection, le chemin complet s'affiche dans le champ

### Formulaire de soumission
- [ ] Champs "Nom" et "Email" fonctionnels
- [ ] Résumé de soumission se met à jour automatiquement
- [ ] Bouton "Soumettre" actif quand tous les champs requis sont remplis

### Test de soumission - Fichier VALIDE
**Canal:** Canal de Validation des Ventes  
**Fichier:** `data/sales_valid_upload.csv`

- [ ] Soumission réussie
- [ ] Modal de succès s'affiche
- [ ] Numéro de suivi affiché
- [ ] Statut: **DQ_SUCCESS**
- [ ] **Bouton "📥 Télécharger le rapport DQ"** visible
- [ ] Clic sur téléchargement → Fichier Excel téléchargé
- [ ] Rapport Excel contient onglets: Tests, Metrics, Scripts

**Résultats attendus dans le rapport:**
- ✅ 3 tests DQ passés (no_missing_amount, no_missing_customer, no_missing_date)
- ✅ 3 tests script passés (no_negative_amounts, amounts_in_range, no_duplicate_ids)
- **Total: 6/6 tests réussis**

### Test de soumission - Fichier INVALIDE
**Canal:** Canal de Validation des Ventes  
**Fichier:** `data/sales_invalid_upload.csv`

- [ ] Soumission réussie
- [ ] Modal de succès s'affiche
- [ ] Statut: **DQ_FAILED** (badge warning/danger)
- [ ] **Bouton "📥 Télécharger le rapport DQ"** visible
- [ ] Rapport Excel téléchargé

**Résultats attendus dans le rapport:**
- ❌ 1 test DQ échoué: `no_missing_customer` (1 valeur manquante)
- ✅ 2 tests DQ passés
- ❌ 3 tests script échoués:
  - `no_negative_amounts`: 1 montant négatif (-250.00)
  - `amounts_in_range`: 1 montant > 10000 (15000.00)
  - `no_duplicate_ids`: 1 ID dupliqué (TXN001)
- **Total: 2/6 tests réussis, 4/6 échecs**

---

## 🔧 PAGE DQ EDITOR (/dq-editor-dashboard)

### Sélection DQ
- [ ] Liste des DQ disponibles s'affiche
- [ ] Sélection d'une DQ affiche ses détails

### Exécution
- [ ] Bouton "Exécuter" lance l'analyse
- [ ] Résultats s'affichent (métriques + tests)
- [ ] Option "Investigation" génère des rapports détaillés

---

## 🧪 TESTS UNITAIRES

Exécuter dans le terminal:
```powershell
pytest tests/ -v
```

**Tests à vérifier:**
- [ ] `test_dq_runner.py` → ✅ Tous passent
- [ ] `test_metrics.py` → ✅ Tous passent
- [ ] `test_plugin_system.py` → ✅ Tous passent

---

## 📂 STRUCTURE DES FICHIERS

### Essentiels (doivent être présents)
- [ ] `run.py` - Point d'entrée
- [ ] `app.py` - Application Dash
- [ ] `requirements.txt` - Dépendances
- [ ] `config/inventory.yaml` - Configuration
- [ ] `dq/definitions/*.yaml` - 7 fichiers DQ
- [ ] `managed_folders/channels/channels.json` - 9 canaux
- [ ] `data/sales_valid_upload.csv` - Fichier test valide
- [ ] `data/sales_invalid_upload.csv` - Fichier test invalide
- [ ] `scripts/validation/business_checks.py` - Script de validation

### Archivés (dans OLD/)
- [ ] 59 fichiers/dossiers déplacés vers `OLD/archive_YYYYMMDD_HHMMSS/`
- [ ] Démos (demo_*.py)
- [ ] Tests rapides (quick_test*.py)
- [ ] Documentation temporaire (*.md)

---

## 🚀 DÉMARRAGE DE L'APP

```powershell
python run.py
```

**Vérifications:**
- [ ] Aucune erreur au démarrage
- [ ] Message: "Dash is running on http://0.0.0.0:5002/"
- [ ] Accès à http://127.0.0.1:5002 → Page d'accueil s'affiche
- [ ] Tous les assets (CSS, images) se chargent

---

## ✅ RÉSUMÉ FINAL

**Fonctionnalités critiques:**
1. ✅ Navigation entre pages
2. ✅ Upload de fichiers avec parcourir
3. ✅ Exécution DQ (vraie, pas mock)
4. ✅ Génération rapport Excel
5. ✅ Téléchargement du rapport
6. ✅ Détection des erreurs (fichier invalide)
7. ✅ Validation réussie (fichier valide)

**Si tous les tests passent:**
✅ L'application est prête pour la production/démo

**En cas de problème:**
1. Vérifier les logs du terminal Python
2. Vérifier la console navigateur (F12)
3. Vérifier que tous les fichiers essentiels sont présents
4. Restaurer depuis OLD/ si nécessaire
