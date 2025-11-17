# 📄 Guide : Téléchargement du Résumé DQ

## Vue d'ensemble

Le bouton **"📄 Télécharger le résumé"** permet de télécharger un résumé visuel et lisible de votre configuration Data Quality au format Markdown (`.md`), au lieu du JSON brut.

## Localisation

Le bouton se trouve dans l'onglet **"⚙️ Finaliser"** du DQ Builder, à côté des boutons "Publier" et "Run DQ".

## Fonctionnement

1. **Configuration du DQ** : Configurez vos datasets, métriques, tests et scripts dans le Builder
2. **Cliquez sur le bouton** : Cliquez sur "📄 Télécharger le résumé"
3. **Téléchargement automatique** : Un fichier `.md` est généré et téléchargé automatiquement

## Format du fichier généré

### Nom du fichier
```
dq_summary_{stream}_{project}_{zone}_{timestamp}.md
```

Exemple : `dq_summary_A_P1_raw_20251116_143022.md`

### Contenu du résumé

Le fichier Markdown contient les sections suivantes :

#### 1. 🎯 Contexte
- Stream
- Project
- Zone  
- Quarter (si applicable)

#### 2. 📁 Datasets
Pour chaque dataset :
- Alias
- Chemin du dataset
- Filtres appliqués (si applicable)

#### 3. 📈 Métriques
Pour chaque métrique :
- ID et type
- Colonne(s) ciblée(s)
- Dataset source
- Paramètres spécifiques

#### 4. ✅ Tests
Pour chaque test :
- ID et type
- Métrique associée
- Paramètres de validation (seuils, etc.)

#### 5. 🔧 Scripts
Pour chaque script :
- Label et ID
- Moment d'exécution (pre_dq / post_dq)
- Chemin du script
- Paramètres

#### 6. 📊 Statistiques
Résumé quantitatif :
- Nombre de datasets
- Nombre de métriques
- Nombre de tests
- Nombre de scripts

## Exemple de résumé généré

```markdown
# 📊 Résumé de la Configuration Data Quality

**Date de génération:** 2025-11-16 14:30:22

---

## 🎯 Contexte

- **Stream:** A
- **Project:** P1
- **Zone:** raw
- **Quarter:** N/A

## 📁 Datasets

### 1. sales_2024
- **Dataset:** `sourcing/input/sales_2024.csv`

## 📈 Métriques

### 1. missing_rate_quantity (missing_rate)
- **Type:** missing_rate
- **Colonne:** `quantity`
- **Dataset:** sales_2024

### 2. avg_amount (avg)
- **Type:** avg
- **Colonne:** `amount`
- **Dataset:** sales_2024

## ✅ Tests

### 1. check_missing_quantity (range)
- **Type:** range
- **Métrique:** missing_rate_quantity
- **Paramètres:** {"low": 0, "high": 0.05}

### 2. check_avg_amount (range)
- **Type:** range
- **Métrique:** avg_amount
- **Paramètres:** {"low": 50, "high": 500}

## 🔧 Scripts

### 1. Validation des ventes
- **ID:** sales_validation
- **Exécution:** post_dq
- **Path:** `scripts/A/P1/raw/sales_validation.py`

---

## 📊 Statistiques

- **Datasets:** 1
- **Métriques:** 2
- **Tests:** 2
- **Scripts:** 1
```

## Avantages par rapport au JSON

| Aspect | JSON | Résumé Markdown |
|--------|------|-----------------|
| **Lisibilité** | ❌ Format technique | ✅ Format visuel structuré |
| **Organisation** | ⚠️ Clés/valeurs plates | ✅ Sections hiérarchiques |
| **Documentation** | ❌ Difficile à partager | ✅ Facile à lire et partager |
| **Statistiques** | ❌ Calcul manuel | ✅ Résumé automatique |
| **Visualisation** | ❌ Nécessite un parser | ✅ Lisible dans n'importe quel viewer Markdown |

## Cas d'usage

1. **Documentation** : Partager la configuration DQ avec des non-techniques
2. **Revue** : Valider la configuration avant déploiement
3. **Archivage** : Conserver une trace lisible de la configuration
4. **Communication** : Présenter la stratégie DQ aux équipes métier
5. **Audit** : Tracer les configurations DQ au fil du temps

## Visualisation du fichier

Les fichiers `.md` peuvent être visualisés dans :
- **VS Code** : Aperçu intégré (Ctrl+Shift+V)
- **GitHub** : Rendu automatique
- **Obsidian / Notion** : Import direct
- **Navigateurs** : Avec extensions Markdown
- **Éditeurs** : Typora, Mark Text, etc.

## Notes techniques

- Le résumé est généré côté client (navigateur)
- Aucune donnée n'est envoyée au serveur pour la génération
- Le fichier est créé à la volée lors du clic
- Format compatible avec tous les standards Markdown (CommonMark, GitHub Flavored Markdown)
- Encodage UTF-8 avec support des emojis

## Intégration avec le workflow DQ

```
┌─────────────────┐
│  Configurer DQ  │
│   dans Builder  │
└────────┬────────┘
         │
         ├──────────────┐
         │              │
         v              v
  ┌──────────┐    ┌─────────────┐
  │ Publier  │    │ Télécharger │
  │   YAML   │    │   Résumé    │
  └────┬─────┘    └──────┬──────┘
       │                 │
       v                 v
  ┌──────────┐    ┌─────────────┐
  │ Exécuter │    │  Documenter │
  │    DQ    │    │  / Partager │
  └──────────┘    └─────────────┘
```

Le résumé Markdown complète le workflow en offrant une vue human-friendly de la configuration technique.
