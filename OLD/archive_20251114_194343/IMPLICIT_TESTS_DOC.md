# Tests Implicites - Documentation

## Vue d'ensemble

Le séquenceur DQ génère automatiquement des **tests techniques implicites** pour garantir la validité de l'exécution avant de lancer les métriques et tests principaux.

## Validation préalable

Avant la génération des tests implicites, le séquenceur effectue une **validation de l'unicité des IDs**:

### Validation d'unicité des IDs 🔐

**Objectif**: Garantir qu'il n'y a pas de collision ou doublon dans les identifiants.

**Vérifications effectuées**:
1. ✅ Pas de doublons dans les IDs de métriques
2. ✅ Pas de doublons dans les IDs de tests
3. ✅ Pas de collision entre IDs de métriques et tests

**Exemple d'erreur détectée**:
```yaml
metrics:
  M_001: {...}
  
tests:
  M_001: {...}  # ❌ COLLISION - Même ID qu'une métrique
```

**Message d'erreur**:
```
❌ Collision d'IDs entre métriques et tests: ['M_001']
```

**Note**: Les dictionnaires Python empêchent naturellement les doublons de clés, mais cette validation est cruciale lors du parsing YAML/JSON où des erreurs de configuration peuvent survenir.

---

## Types de tests implicites

### 1. PARAMETERS_TYPE_VALIDATION 🔍

**Objectif**: Vérifier que les paramètres fournis peuvent être castés dans les types attendus par les signatures des plugins (métriques et tests).

**Génération**: Pour chaque métrique et test ayant des paramètres dans leur section `specific`.

**Exemple**:
```yaml
# Métrique avec paramètres
M_001_missing_date:
  type: missing_rate
  specific:
    dataset: "sales_2024"      # str attendu
    column: "date"             # str attendu
```

**Test implicite généré**:
- ID: `M_001_missing_date_implicit_param_validation`
- Type: `parameters_type_validation`
- Vérifie: `dataset` est castable en `str`, `column` est castable en `str`
- Description: "Vérifie que les paramètres de M_001_missing_date sont castables dans les types attendus par missing_rate"

**Ordre d'exécution**: S'exécute **avant** la métrique ou le test parent.

---

### 2. FILTER_COLUMNS_PRESENCE 📋

**Objectif**: Vérifier que toutes les colonnes utilisées dans un filtre WHERE existent dans le dataset cible.

**Génération**: Pour chaque test ayant une clause `where` dans ses paramètres.

**Exemple**:
```yaml
# Test avec filtre
T_007_check_amounts_north_region:
  type: interval_check
  specific:
    value_from_dataset: "sales_2024"
    where: "region = 'North' AND date > '2024-01-01'"
    bounds:
      lower: 50
      upper: 300
```

**Test implicite généré**:
- ID: `T_007_check_amounts_north_region_implicit_columns_presence`
- Type: `filter_columns_presence`
- Colonnes extraites: `['region', 'date']`
- Vérifie: Les colonnes `region` et `date` existent dans `sales_2024`
- Description: "Vérifie la présence des colonnes ['region', 'date'] dans sales_2024"

**Ordre d'exécution**: S'exécute **avant** le test parent.

---

### 3. FILTER_COLUMNS_TYPE_MATCH 🔤

**Objectif**: Vérifier que les colonnes utilisées dans un filtre ont des types compatibles avec les opérations SQL appliquées.

**Génération**: Pour chaque test ayant une clause `where` dans ses paramètres.

**Exemple**:
```yaml
# Test avec filtre complexe
T_008_check_high_value_products:
  type: interval_check
  specific:
    value_from_dataset: "sales_2024"
    where: "amount > 200 AND product_id LIKE 'P%' AND quantity >= 5"
    bounds:
      lower: 5
      upper: 50
```

**Test implicite généré**:
- ID: `T_008_check_high_value_products_implicit_columns_type`
- Type: `filter_columns_type_match`
- Colonnes extraites: `['amount', 'product_id', 'quantity']`
- Vérifie: 
  - `amount` est numérique (opérateur `>`)
  - `product_id` est string (opérateur `LIKE`)
  - `quantity` est numérique (opérateur `>=`)
- Description: "Vérifie la compatibilité des types des colonnes ['amount', 'product_id', 'quantity'] dans sales_2024"

**Ordre d'exécution**: S'exécute **avant** le test parent.

---

## Processus de construction de la séquence

```
1. 🔍 VALIDATION D'UNICITÉ DES IDs
   - Vérification des doublons de métriques
   - Vérification des doublons de tests
   - Vérification des collisions métrique-test
   ↓ (Erreur si collision détectée)

2. 📊 CRÉATION DES COMMANDES
   - Métriques
   - Tests
   ↓

3. 🔧 GÉNÉRATION DES TESTS IMPLICITES
   - Tests de validation de paramètres
   - Tests de présence de colonnes (pour filtres)
   - Tests de compatibilité de types (pour filtres)
   ↓

4. 🔗 RÉSOLUTION DES DÉPENDANCES
   - Graphe de dépendances
   ↓

5. 📋 ORDONNANCEMENT TOPOLOGIQUE
   - Tri de Kahn
   - Ordre d'exécution optimal
```

## Graphe de dépendances

```
┌─────────────────────────────────────────────────────────┐
│  VALIDATION D'UNICITÉ (phase 0)                         │
│  - Pas de doublons métriques                            │
│  - Pas de doublons tests                                │
│  - Pas de collision métrique-test                       │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  TESTS IMPLICITES (aucune dépendance)                  │
│  - *_implicit_param_validation                          │
│  - *_implicit_columns_presence                          │
│  - *_implicit_columns_type                              │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  MÉTRIQUES                                              │
│  Dépendent de: leur test de validation de paramètres   │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  TESTS                                                  │
│  Dépendent de:                                          │
│  1. Leur métrique associée (si applicable)              │
│  2. Leur test de validation de paramètres              │
│  3. Leurs tests de présence/type de colonnes (si filtre)│
└─────────────────────────────────────────────────────────┘
```

## Exemple complet

Pour un test avec filtre dépendant d'une métrique:

```yaml
M_001_missing_date:
  type: missing_rate
  specific:
    dataset: "sales_2024"
    column: "date"

T_007_check_amounts_north_region:
  type: interval_check
  specific:
    value_from_metric: "M_001_missing_date"
    value_from_dataset: "sales_2024"
    where: "region = 'North' AND date > '2024-01-01'"
    bounds: {lower: 50, upper: 300}
```

**Tests implicites générés** (6 au total):

1. ✅ `M_001_missing_date_implicit_param_validation` (valide dataset="sales_2024", column="date")
2. ✅ `T_007_..._implicit_param_validation` (valide tous les paramètres du test)
3. ✅ `T_007_..._implicit_columns_presence` (vérifie présence de region, date)
4. ✅ `T_007_..._implicit_columns_type` (vérifie types de region, date)

**Ordre d'exécution**:

1. `M_001_missing_date_implicit_param_validation`
2. `T_007_..._implicit_param_validation`
3. `T_007_..._implicit_columns_presence`
4. `T_007_..._implicit_columns_type`
5. `M_001_missing_date` ← après (1)
6. `T_007_check_amounts_north_region` ← après (2, 3, 4, 5)

## Statistiques

Dans l'exemple `demo_sequencer_filters.py`:

- **Configuration**: 5 métriques + 8 tests = 13 éléments
- **Tests implicites générés**: 17
  - 13 tests de validation de paramètres (1 par métrique/test)
  - 4 tests de filtre (2 tests × 2 types: présence + type)
- **Total commandes**: 30 (13 + 17)

## Avantages

✅ **Détection précoce des erreurs**: Les problèmes de paramètres ou de colonnes sont détectés avant l'exécution coûteuse des métriques/tests

✅ **Traçabilité**: Chaque test implicite est identifié et tracé dans les logs

✅ **Maintenabilité**: Génération automatique, pas besoin de définir manuellement ces validations

✅ **Robustesse**: Évite les crashes runtime en validant les contrats d'interface des plugins

✅ **Performance**: Ordre optimal d'exécution calculé automatiquement par tri topologique
