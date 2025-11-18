# Guide des Scripts DQ Personnalisés

## Vue d'ensemble

Les scripts DQ permettent d'ajouter des **tests personnalisés** qui ne peuvent pas être implémentés avec les plugins standards. Les scripts produisent uniquement des **tests** (pas de métriques) qui sont intégrés dans l'onglet Tests de l'export Excel.

## Format de sortie attendu

Le script doit produire un JSON sur stdout avec cette structure :

```json
{
  "tests": [
    {
      "id": "TEST_001",
      "value": 0.95,
      "passed": true,
      "message": "Description du test",
      "meta": {
        "test_type": "custom",
        "criticality": "high"
      }
    }
  ]
}
```

### Champs obligatoires

- `id` : Identifiant unique du test
- `value` : Valeur numérique du test
- `passed` : Booléen indiquant si le test a réussi
- `message` : Description du résultat

### Champs optionnels (meta)

- `test_type` : Type de test (ex: "business_rule", "coherence", "threshold")
- `criticality` : Criticité ("low", "medium", "high", "critical")
- Tout autre champ métier pertinent

## Format d'entrée (stdin)

Le script reçoit un JSON sur stdin avec :

```json
{
  "params": {
    "threshold": 0.95,
    "custom_param": "value"
  },
  "datasets": {
    "sales_2024": "sales_2024",
    "customers": "customers"
  },
  "metrics": {
    "M-001": 0.05,
    "M-002": 0.98
  }
}
```

- `params` : Paramètres définis dans le YAML (section `scripts[].params`)
- `datasets` : Liste des datasets chargés
- `metrics` : Valeurs des métriques calculées avant le script

## Exemple de script

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
import sys

def main():
    # Lire les paramètres
    input_data = json.loads(sys.stdin.read())
    params = input_data.get("params", {})
    metrics = input_data.get("metrics", {})
    
    tests = []
    
    # Exemple 1: Test basé sur un seuil
    tests.append({
        "id": "CUSTOM_TEST_001",
        "value": 0.95,
        "passed": True,
        "message": "Score de qualité: 95%",
        "meta": {
            "test_type": "quality_score",
            "criticality": "high"
        }
    })
    
    # Exemple 2: Test utilisant une métrique existante
    if "M-001" in metrics:
        missing_rate = metrics["M-001"]
        tests.append({
            "id": "CUSTOM_TEST_002",
            "value": missing_rate,
            "passed": missing_rate <= 0.10,
            "message": f"Taux de valeurs manquantes: {missing_rate:.2%}",
            "meta": {
                "test_type": "threshold",
                "criticality": "medium",
                "associated_metric": "M-001"
            }
        })
    
    # Sortie
    print(json.dumps({"tests": tests}, indent=2))
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

## Configuration dans le YAML

```yaml
scripts:
  - id: "CUSTOM_SCRIPT_001"
    label: "Script DQ personnalisé"
    path: "scripts/my_custom_script.py"
    enabled: true
    execute_on: "post_dq"  # ou "pre_dq"
    params:
      threshold: 0.95
      check_coherence: true
```

### Paramètres de configuration

- `id` : Identifiant unique du script
- `label` : Libellé descriptif
- `path` : Chemin vers le script Python (relatif à la racine du projet)
- `enabled` : Activer/désactiver le script
- `execute_on` : 
  - `"pre_dq"` : Exécute AVANT les métriques/tests DQ
  - `"post_dq"` : Exécute APRÈS les métriques/tests DQ
- `params` : Dictionnaire de paramètres passés au script

## Ordre d'exécution

1. **pre_dq scripts** → Exécutés en premier
2. **load datasets** → Chargement des datasets
3. **metrics** → Calcul des métriques
4. **tests** → Exécution des tests DQ
5. **post_dq scripts** → Exécutés en dernier

## Export Excel

Les tests issus des scripts sont **automatiquement intégrés** dans l'onglet Tests de l'export Excel, avec les colonnes suivantes :

| Colonne | Description |
|---------|-------------|
| DQ_ID | ID de la définition DQ |
| Quarter | Trimestre |
| Project | Projet |
| Test_ID | ID du test (du script) |
| Test_Type | Type de test (depuis meta.test_type) |
| Criticality | Criticité (depuis meta.criticality) |
| Value | Valeur du test |
| Status | PASSED / FAILED |
| Message | Message descriptif |
| Run_ID | ID d'exécution |
| Investigation | Oui/Non |

## Bonnes pratiques

1. **IDs uniques** : Utilisez des préfixes pour éviter les collisions (ex: `CUSTOM_`, `BUSINESS_`, `SCRIPT_`)
2. **Gestion d'erreurs** : Le script doit gérer ses propres erreurs et retourner un JSON valide
3. **Performance** : Les scripts ont un timeout de 5 minutes
4. **Logging** : Utilisez stderr pour les logs (stdout est réservé au JSON)
5. **Tests paramétrables** : Utilisez `params` pour rendre les scripts réutilisables

## Cas d'usage

### Règles métier complexes

```python
# Vérifier que montant = quantité × prix unitaire
tests.append({
    "id": "BUSINESS_RULE_001",
    "value": coherence_score,
    "passed": coherence_score >= 0.99,
    "message": f"Cohérence montants: {coherence_score:.2%}",
    "meta": {
        "test_type": "business_rule",
        "criticality": "critical"
    }
})
```

### Cohérence inter-datasets

```python
# Vérifier que tous les clients existent dans le référentiel
tests.append({
    "id": "COHERENCE_001",
    "value": match_rate,
    "passed": match_rate >= 0.95,
    "message": f"Clients référencés: {match_rate:.2%}",
    "meta": {
        "test_type": "coherence",
        "criticality": "high"
    }
})
```

### Seuils dynamiques

```python
# Seuil variable selon le paramètre
threshold = params.get("threshold", 0.90)
tests.append({
    "id": "DYNAMIC_THRESHOLD_001",
    "value": actual_value,
    "passed": actual_value >= threshold,
    "message": f"Valeur: {actual_value:.2%} (seuil: {threshold:.2%})",
    "meta": {
        "test_type": "threshold",
        "criticality": "medium",
        "threshold": threshold
    }
})
```

## Dépannage

### Le script ne s'exécute pas

- Vérifiez que `enabled: true` dans le YAML
- Vérifiez que le chemin du script est correct
- Vérifiez les permissions d'exécution

### Erreur de parsing JSON

- Assurez-vous que le script produit un JSON valide sur stdout
- Utilisez stderr pour les logs, pas stdout

### Tests non visibles

- Vérifiez que le JSON contient une clé `"tests"` (tableau)
- Vérifiez que chaque test a un `id` unique

### Timeout

- Les scripts ont 5 minutes max d'exécution
- Optimisez les traitements lourds
- Utilisez des échantillons si nécessaire
