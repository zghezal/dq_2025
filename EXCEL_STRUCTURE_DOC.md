# Structure des Fichiers Excel d'Export

## Vue d'ensemble

Le fichier Excel généré contient plusieurs onglets:
1. **Métriques** - Suivi de l'exécution des métriques
2. **Tests** - Résultats détaillés de tous les tests (business + techniques)
3. **[Nom Métrique 1]** - Données exportées de la métrique (si export=true)
4. **[Nom Métrique 2]** - Données exportées de la métrique (si export=true)
...

## Onglet "Métriques"

### Colonnes (14 au total)

| Colonne | Type | Description | Exemples |
|---------|------|-------------|----------|
| ID | str | Identifiant unique de la métrique | M_001_missing_date |
| Type | str | Type technique de métrique | missing_rate, row_count |
| Name | str | Nom descriptif | Date Completeness Check |
| Description | str | Description détaillée | Vérifie le taux de valeurs manquantes... |
| Comments | str | Commentaires additionnels | Métrique critique pour le reporting |
| Export | str | Flag d'export de données | Yes, No |
| Owner | str | Propriétaire/responsable | data_quality_team |
| Dataset | str | Dataset source | sales_2024 |
| Column | str | Colonne(s) analysée(s) | date, amount |
| Filter | str | Filtre SQL appliqué | WHERE region = 'North' |
| **Execution_Status** | str | **Statut d'exécution** | **SUCCESS, ERROR, SKIPPED** |
| Value | float | Valeur calculée | 0.0523 |
| **Error** | str | **Message d'erreur détaillé** | **Connexion timeout / Dépendances non satisfaites: ...** |
| Timestamp | datetime | Horodatage d'exécution | 2025-11-06 14:23:45 |

### Exemples de Lignes

#### Métrique Réussie
```
ID: M_001_missing_date
Type: missing_rate
Name: Date Completeness
Execution_Status: SUCCESS
Value: 0.0234
Error: (vide)
```

#### Métrique Échouée
```
ID: M_002_missing_amount
Type: missing_rate
Name: Amount Completeness
Execution_Status: ERROR
Value: (vide)
Error: Connexion timeout to database after 30s
```

#### Métrique SKIPPED (dépendance échouée)
```
ID: M_003_derived_metric
Type: custom_metric
Name: Derived Analysis
Execution_Status: SKIPPED
Value: (vide)
Error: Dépendances non satisfaites: M_002_missing_amount (ERROR)
```

## Onglet "Tests"

### Colonnes (14 au total)

| Colonne | Type | Description | Exemples |
|---------|------|-------------|----------|
| quarter | str | Trimestre d'exécution | Q4 2025 |
| project | str | Nom du projet | Sales Data Quality |
| run_version | str | Version du run | v1.0.0 |
| control_id | str | Identifiant du contrôle | T_001_check_date |
| dataset | str | Dataset testé | sales_2024 |
| category | str | Catégorie du test | Business, Technical |
| blocking | str | Test bloquant ? | Yes, No |
| **execution_status** | str | **Statut d'exécution** | **SUCCESS, FAIL, ERROR, SKIPPED** |
| **result** | str | **Résultat du test** | **PASS, FAIL, ERROR, SKIPPED** |
| description | str | Description du test | Vérifie que le taux de valeurs manquantes... |
| comments | str | Commentaires | Test critique mensuel |
| **error** | str | **Détails de l'erreur** | **Value 0.15 outside bounds [0, 0.1] / Dépendances: ...** |
| user | str | Utilisateur | admin |
| timestamp | datetime | Horodatage | 2025-11-06 14:23:47 |

### Mapping execution_status ↔ result

| execution_status | result | Signification |
|------------------|--------|---------------|
| SUCCESS | PASS | Test exécuté avec succès, valeur dans les bornes |
| FAIL | FAIL | Test exécuté, valeur hors bornes |
| ERROR | ERROR | Erreur technique pendant l'exécution |
| SKIPPED | SKIPPED | Dépendance échouée, test non exécuté |

### Exemples de Lignes

#### Test Business Réussi (PASS)
```
control_id: T_001_check_date_completeness
category: Business
blocking: Yes
execution_status: SUCCESS
result: PASS
error: (vide)
description: Vérifie le taux de dates manquantes
```

#### Test Business Échoué (FAIL)
```
control_id: T_002_check_amount_completeness
category: Business
blocking: Yes
execution_status: FAIL
result: FAIL
error: Value 0.15 outside bounds [0, 0.1]
description: Vérifie le taux d'amounts manquants
```

#### Test Technique Réussi (Validation Paramètres)
```
control_id: TECH_M_001_missing_date
category: Technical
blocking: No
execution_status: SUCCESS
result: PASS
error: (vide)
description: Test technique: missing_rate
comments: Test implicite généré automatiquement
```

#### Test Technique Échoué (Colonne Manquante)
```
control_id: TECH_T_007_check_amounts_north_region
category: Technical
blocking: No
execution_status: FAIL
result: FAIL
error: Column "region" not found in dataset
description: Test technique: interval_check
comments: Test implicite généré automatiquement
```

#### Test SKIPPED (Dépendance Échouée)
```
control_id: T_002_check_amount_completeness
category: Business
blocking: Yes
execution_status: SKIPPED
result: SKIPPED
error: Dépendances non satisfaites: M_002_missing_amount (ERROR)
description: Vérifie le taux d'amounts manquants
```

## Onglets de Données des Métriques

### Conditions d'Export

Un onglet de données est créé si:
1. ✅ La métrique a `export: true` dans sa configuration
2. ✅ L'exécution a réussi (`status == SUCCESS`)
3. ✅ Un DataFrame est présent dans `result['dataframe']`

### Nom de l'Onglet

- Basé sur `metric_id`
- Caractères interdits remplacés par `_`: `: \ / ? * [ ]`
- Limité à 31 caractères (limite Excel)
- Exemples:
  - `M_001_missing_date` → `M_001_missing_date`
  - `M_002_missing_amount_by_region` → `M_002_missing_amount_by_re...`

### Structure du DataFrame

#### Exemple pour missing_rate

| date_missing_rate | date_missing_number | amount_missing_rate | amount_missing_number |
|-------------------|---------------------|---------------------|----------------------|
| 0.0234 | 47 | 0.0156 | 31 |

#### Exemple pour row_count avec groupby

| region | product | row_count |
|--------|---------|-----------|
| North | A | 1234 |
| North | B | 2345 |
| South | A | 3456 |
| South | B | 4567 |

## Résumé des Statuts

### Pour les Métriques (Execution_Status)

| Statut | Nombre | Signification |
|--------|--------|---------------|
| SUCCESS | 4 | Métriques calculées avec succès |
| ERROR | 1 | Erreur technique (timeout, connexion) |
| SKIPPED | 0 | Validation de paramètres échouée |

### Pour les Tests (execution_status)

| Statut | Nombre | Signification |
|--------|--------|---------------|
| SUCCESS (PASS) | 14 | Tests réussis |
| FAIL | 1 | Tests échoués (valeur hors bornes) |
| ERROR | 1 | Erreur technique |
| SKIPPED | 1 | Dépendance échouée |

## Format de Timestamp

```
2025-11-06 14:23:45.123456
```

- Format: `YYYY-MM-DD HH:MM:SS.ffffff`
- Timezone: Local
- Type Excel: Datetime

## Largeur des Colonnes

Les colonnes sont automatiquement ajustées:
- Largeur minimale: 10 caractères
- Largeur maximale: 50 caractères
- Calcul: `max(len(header), max(len(str(val)) for val in column)) + 2`

## Exemple Complet de Fichier

```
reports/dq_execution_report_complete.xlsx
│
├─ Métriques (5 lignes)
│  ├─ M_001_missing_date: SUCCESS, value=0.0234
│  ├─ M_002_missing_amount: ERROR, error="Connexion timeout"
│  ├─ M_003_missing_product: SUCCESS, value=0.0156
│  ├─ M_004_row_count: SUCCESS, value=12345
│  └─ M_005_missing_refund_reason: SUCCESS, value=0.0089
│
├─ Tests (21 lignes)
│  ├─ Business Tests (7)
│  │  ├─ T_001: SUCCESS/PASS
│  │  ├─ T_002: SKIPPED (dépend de M_002 qui a ERROR)
│  │  ├─ T_003: SUCCESS/PASS
│  │  ├─ T_004: SUCCESS/PASS
│  │  ├─ T_005: FAIL (valeur hors bornes)
│  │  ├─ T_006: SUCCESS/PASS
│  │  └─ T_007: SUCCESS/PASS
│  │
│  └─ Technical Tests (14)
│     ├─ Param Validation (12) - tous SUCCESS/PASS
│     ├─ Column Presence (1) - SUCCESS/PASS
│     └─ Column Type (1) - SUCCESS/PASS
│
├─ M_001_missing_date (DataFrame)
│  └─ date_missing_rate, date_missing_number
│
├─ M_003_missing_product (DataFrame)
│  └─ product_missing_rate, product_missing_number
│
├─ M_004_row_count (DataFrame)
│  └─ row_count
│
└─ M_005_missing_refund_reason (DataFrame)
   └─ refund_reason_missing_rate, refund_reason_missing_number
```

**Note**: M_002 n'a pas d'onglet de données car status=ERROR

## Utilisation dans Power BI / Tableau

Les fichiers Excel générés peuvent être importés directement dans:
- **Power BI**: Import Excel → Sélectionner les onglets
- **Tableau**: Connect to Excel → Sélectionner les sheets
- **Python/Pandas**: `pd.read_excel(path, sheet_name='Métriques')`
- **R**: `readxl::read_excel(path, sheet = "Tests")`

## Filtres Recommandés

### Dans Excel

- Filtrer sur `Execution_Status` pour voir uniquement les erreurs
- Filtrer sur `blocking = Yes` pour voir les tests critiques
- Filtrer sur `category = Technical` pour masquer les tests techniques

### Dans Power BI

```DAX
ErrorMetrics = CALCULATE(
    COUNT([ID]),
    'Métriques'[Execution_Status] = "ERROR"
)

SkippedTests = CALCULATE(
    COUNT([control_id]),
    'Tests'[execution_status] = "SKIPPED"
)
```
