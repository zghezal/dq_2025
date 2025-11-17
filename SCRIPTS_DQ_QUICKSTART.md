# 🎯 Quick Start - Scripts DQ Personnalisés

## En 3 étapes

### 1️⃣ Créer un script Python

```python
# scripts/mon_script.py
import json, sys

input_data = json.loads(sys.stdin.read())
output = {
    "metrics": {
        "MON_METRIC": {"value": 0.95, "passed": True, "message": "OK"}
    },
    "tests": {
        "MON_TEST": {"value": 1.0, "passed": True, "message": "Validé"}
    }
}
print(json.dumps(output))
```

### 2️⃣ Ajouter dans la définition DQ YAML

```yaml
scripts:
  - id: "MON_SCRIPT"
    path: "scripts/mon_script.py"
    enabled: true
    execute_on: "post_dq"
    params:
      seuil: 0.90
```

### 3️⃣ Exécuter

Les résultats du script sont **automatiquement agrégés** avec les métriques/tests natifs dans le même Excel !

## Test rapide

```bash
python test_script_integration.py
```

Génère `reports/test_script_integration.xlsx` avec:
- ✅ 1 métrique native + 2 métriques du script
- ✅ 1 test natif + 3 tests du script  
- ✅ Tout dans le même fichier Excel

## Documentation complète

Voir `SCRIPTS_DQ_DOC.md` pour tous les détails.
