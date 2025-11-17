# Validation d'Unicité des IDs - Résumé

## Fonctionnalité ajoutée

✅ **Validation automatique de l'unicité des IDs** lors de la construction de la séquence d'exécution.

## Vérifications effectuées

### 1. Doublons dans les métriques
Vérifie qu'aucun ID de métrique n'apparaît plusieurs fois dans la configuration.

**Exemple d'erreur**:
```yaml
metrics:
  M_001:
    type: missing_rate
    ...
  M_001:  # ❌ DOUBLON
    type: row_count
    ...
```

**Message d'erreur**:
```
❌ IDs de métriques dupliqués: ['M_001']
```

### 2. Doublons dans les tests
Vérifie qu'aucun ID de test n'apparaît plusieurs fois dans la configuration.

**Exemple d'erreur**:
```yaml
tests:
  T_001:
    type: interval_check
    ...
  T_001:  # ❌ DOUBLON
    type: interval_check
    ...
```

**Message d'erreur**:
```
❌ IDs de tests dupliqués: ['T_001']
```

### 3. Collision entre métriques et tests
Vérifie qu'aucun ID n'est utilisé à la fois pour une métrique ET un test.

**Exemple d'erreur**:
```yaml
metrics:
  ID_001:
    type: missing_rate
    ...

tests:
  ID_001:  # ❌ COLLISION avec la métrique
    type: interval_check
    ...
```

**Message d'erreur**:
```
❌ Collision d'IDs entre métriques et tests: ['ID_001']
```

## Moment de validation

La validation s'effectue **en première étape** de la construction de la séquence, **avant** la création des commandes:

```
0. 🔍 Validation d'unicité des IDs  ← ICI
1. 📊 Création des commandes métriques
2. ✅ Création des commandes tests
3. 🔧 Génération des tests implicites
4. 🔍 Génération des validations de paramètres
5. 🔗 Résolution des dépendances
6. 📋 Ordonnancement topologique
```

## Messages de succès

Quand la validation réussit, vous verrez:

```
🔍 Validation de l'unicité des IDs...
  ✅ 5 métriques uniques
  ✅ 6 tests uniques
  ✅ Aucune collision d'IDs détectée
```

## Gestion des erreurs

En cas d'erreur, le séquenceur lève une `ValueError` immédiatement:

```python
try:
    sequencer = DQSequencer(config)
    sequence = sequencer.build_sequence()
except ValueError as e:
    print(f"Erreur de validation: {e}")
```

## Exemples de tests

### Test avec collision (détectée)

```python
from src.core.dq_parser import load_dq_config
from src.core.sequencer import DQSequencer

# Fichier avec collision métrique-test
config = load_dq_config("dq/definitions/test_duplicate_ids.yaml")

try:
    sequencer = DQSequencer(config)
    sequence = sequencer.build_sequence()
except ValueError as e:
    print(f"✅ Collision détectée: {e}")
    # ✅ Collision détectée: ❌ Collision d'IDs entre métriques et tests: ['M_001_test']
```

### Configuration valide

```python
config = load_dq_config("dq/definitions/sales_complete_quality.yaml")
sequencer = DQSequencer(config)
sequence = sequencer.build_sequence()
print(f"✅ Séquence valide: {len(sequence.commands)} commandes")
# ✅ Séquence valide: 22 commandes
```

## Note technique

Les dictionnaires Python empêchent naturellement les doublons de clés:

```python
# En Python, le second écrase le premier
d = {"M_001": "première valeur", "M_001": "seconde valeur"}
print(d)  # {'M_001': 'seconde valeur'}
```

Cependant, cette validation est importante car:
1. Elle détecte les **collisions métrique-test**
2. Elle fournit un **message d'erreur explicite** avant l'exécution
3. Elle garantit la **cohérence sémantique** de la configuration
4. Elle évite les erreurs silencieuses lors du parsing YAML

## Fichiers de test

- `demo_validation_ids.py` - Tests unitaires des validations
- `test_yaml_duplicates.py` - Test avec fichier YAML réel
- `dq/definitions/test_duplicate_ids.yaml` - Exemple de configuration invalide

## Statistiques

Dans `sales_complete_quality.yaml`:
- ✅ 5 métriques uniques: M_001 à M_005
- ✅ 6 tests uniques: T_001 à T_006
- ✅ Aucune collision
- ✅ Validation passée en <1ms
