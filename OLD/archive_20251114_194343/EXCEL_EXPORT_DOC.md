# Export Excel DQ - Documentation

## Vue d'ensemble

Le module `excel_exporter.py` génère des rapports Excel avec 2 onglets :
- **Métriques** : Statut d'exécution et détails
- **Tests** : Résultats avec tracking complet (incluant tests implicites)

## Structure du rapport Excel

### 📊 Onglet "Métriques"

Colonnes incluses :

| Colonne | Description | Source |
|---------|-------------|--------|
| **ID** | Identifiant unique de la métrique | `identification.metric_id` |
| **Type** | Type de métrique (missing_rate, row_count, etc.) | `element_type` |
| **Name** | Nom descriptif | `nature.name` |
| **Description** | Description détaillée | `nature.description` |
| **Comments** | Commentaires additionnels | `nature.comments` |
| **Export** | Flag d'export | `general.export` |
| **Owner** | Propriétaire/équipe | `general.owner` |
| **Dataset** | Dataset source | `specific.dataset` |
| **Column** | Colonne(s) analysée(s) | `specific.column` |
| **Filter** | Filtre appliqué | `specific.filter` |
| **Execution_Status** | Statut : SUCCESS / ERROR / NOT_RUN | Résultat exécution |
| **Value** | Valeur calculée de la métrique | Résultat exécution |
| **Error** | Message d'erreur si échec | Résultat exécution |
| **Timestamp** | Date/heure d'exécution | Résultat exécution |

### ✅ Onglet "Tests"

Colonnes incluses (dans l'ordre spécifié) :

| Colonne | Description | Exemple |
|---------|-------------|---------|
| **quarter** | Trimestre (Q1 2025, Q2 2025...) | Q4 2025 |
| **project** | Nom du projet | Sales Data Quality |
| **run_version** | Version du run | v1.0.0 ou 20251106_143022 |
| **control_id** | Identifiant du contrôle | CTRL_001 ou TECH_M_001_... |
| **dataset** | Dataset testé | sales_2024 |
| **category** | Catégorie (Business, Technical, etc.) | Business / Technical |
| **blocking** | Test bloquant ? | Yes / No |
| **result** | Résultat : PASS / FAIL / ERROR / NOT_RUN | PASS |
| **description** | Description du test | Vérifie que... |
| **comments** | Commentaires | Test implicite généré... |
| **user** | Utilisateur ayant lancé l'exécution | admin |
| **timestamp** | Date/heure d'exécution | 2025-11-06 14:30:22 |

## Types de tests inclus

### 1. Tests Business (normaux)
- Tests définis dans la configuration YAML
- Category : valeur du champ `nature.category`
- control_id : depuis `identification.control_id`

### 2. Tests Techniques Implicites

#### A. Validation de paramètres
- **control_id** : `TECH_<element_id>_implicit_param_validation`
- **category** : `Technical`
- **description** : Vérifie que les paramètres sont castables dans les types attendus
- **comments** : Test implicite généré automatiquement

#### B. Présence de colonnes (pour filtres)
- **control_id** : `TECH_<test_id>_implicit_columns_presence`
- **category** : `Technical`
- **description** : Vérifie la présence des colonnes ['col1', 'col2'] dans dataset
- **comments** : Test implicite généré automatiquement

#### C. Compatibilité de types (pour filtres)
- **control_id** : `TECH_<test_id>_implicit_columns_type`
- **category** : `Technical`
- **description** : Vérifie la compatibilité des types des colonnes ['col1', 'col2']
- **comments** : Test implicite généré automatiquement

## Utilisation

### Depuis Python

```python
from src.core.dq_parser import load_dq_config
from src.core.sequencer import DQSequencer
from src.core.excel_exporter import export_execution_results

# 1. Charger config
config = load_dq_config("dq/definitions/sales_complete_quality.yaml")

# 2. Construire séquence
sequencer = DQSequencer(config)
sequence = sequencer.build_sequence()

# 3. Exécuter (vous devez implémenter l'exécution réelle)
execution_results = execute_sequence(sequence)  # À implémenter

# 4. Générer Excel
export_execution_results(
    sequence=sequence,
    execution_results=execution_results,
    output_path="reports/mon_rapport.xlsx",
    quarter="Q4 2025",
    project="Mon Projet DQ",
    run_version="v1.0.0",
    user="mon_user"
)
```

### Format des résultats d'exécution

```python
execution_results = {
    "M_001_missing_date": {
        "status": "SUCCESS",      # Pour métriques
        "value": 0.0523,         # Valeur calculée
        "error": "",             # Message d'erreur si échec
        "timestamp": datetime.now()
    },
    "T_001_check_date_completeness": {
        "result": "PASS",        # Pour tests : PASS / FAIL / ERROR
        "error": "",             # Message d'erreur
        "timestamp": datetime.now()
    },
    # ... pour chaque commande
}
```

## Scripts de démonstration

### 1. `demo_excel_export.py`
Démonstration simple avec la configuration de base (sans filtres)
- 5 métriques
- 6 tests normaux
- 11 tests implicites (validation paramètres)
- **Total : 22 lignes**

```bash
python demo_excel_export.py
```

Génère : `reports/dq_execution_report.xlsx`

### 2. `demo_excel_complete.py`
Démonstration complète avec tests utilisant des filtres
- 5 métriques
- 7 tests normaux (6 + 1 avec filtre)
- 14 tests implicites :
  - 12 validations de paramètres
  - 2 tests de filtres (présence + type)
- **Total : 26 lignes**

```bash
python demo_excel_complete.py
```

Génère : `reports/dq_execution_report_complete.xlsx`

## Métadonnées optionnelles

### Quarter
Calculé automatiquement si non fourni :
```python
quarter = f"Q{(month - 1) // 3 + 1} {year}"
# Exemple : Q4 2025
```

### Run Version
Généré automatiquement si non fourni :
```python
run_version = datetime.now().strftime("%Y%m%d_%H%M%S")
# Exemple : 20251106_143022
```

### User
Peut rester vide si non fourni (sera rempli lors de l'intégration avec l'authentification)

## Formatage Excel

- **Largeur automatique** : Les colonnes s'ajustent au contenu (max 50 caractères)
- **En-têtes** : Première ligne avec noms de colonnes
- **Onglets** : Nommés "Métriques" et "Tests"

## Extension future

Pour étendre le rapport avec d'autres onglets :

```python
class DQExcelExporter:
    def generate_excel(self, ...):
        df_metrics = self._build_metrics_dataframe()
        df_tests = self._build_tests_dataframe(...)
        df_summary = self._build_summary_dataframe()  # NOUVEAU
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            df_metrics.to_excel(writer, sheet_name='Métriques', index=False)
            df_tests.to_excel(writer, sheet_name='Tests', index=False)
            df_summary.to_excel(writer, sheet_name='Résumé', index=False)  # NOUVEAU
```

## Dépendances

```bash
pip install pandas openpyxl
```

- **pandas** : Manipulation de DataFrames
- **openpyxl** : Engine pour écrire des fichiers Excel (.xlsx)
