# Audit des Références aux Plugins à Supprimer

## Résumé

Le projet doit conserver uniquement :
- ✅ **Métrique** : `missing_rate`
- ✅ **Test** : `interval_check`

Tous les autres plugins doivent être supprimés.

---

## 📁 Fichiers de Plugins à SUPPRIMER

### Tests (src/plugins/tests/)
- ❌ `range_test.py` - Plugin "range" 
- ❌ `range2_test.py` - Plugin "test.range2"
- ❌ `threshold_test.py` - Plugin "test.threshold"

### Métriques (src/plugins/metrics/)
- ✅ `missing_rate.py` - **À CONSERVER**

---

## 📄 Fichiers avec Références à NETTOYER

### 1. Documentation Markdown

#### `INVESTIGATION_PLUGIN_INTEGRATION.md`
**Lignes à supprimer/modifier :**
- Ligne ~111-200 : Exemple `RangeTest.investigate()` complet
- Ligne ~287 : "3. `src/plugins/tests/range_test.py` : Implémenter `investigate()`"
- Ligne ~288 : "4. `src/plugins/tests/threshold_test.py` : Implémenter `investigate()`"
- Section "Fichiers à modifier" mentionne range_test et threshold_test

**Action :** Nettoyer les exemples et mentions de range/threshold, garder uniquement interval_check

---

#### `README_PATCH.md`
**Ligne 6 :**
```markdown
- `src/plugins/tests/range2_test.py` (nouvelle version auto-UI — l'ancienne reste intacte)
```

**Action :** Supprimer mention de range2_test

---

### 2. Fichiers Python - Investigation

#### `src/investigation.py`
**Méthodes à SUPPRIMER :**
- Ligne ~171 : `_investigate_aggregate()` - Pour métriques avg/min/max/std/sum
- Ligne ~229 : `_investigate_duplicates()` - Pour métrique duplicate_count  
- Ligne ~274 : `_investigate_unique()` - Pour métrique unique_count

**Méthode principale à NETTOYER :**
- Ligne ~65-77 : `generate_investigation_samples()` - Supprimer les elif pour aggregate/duplicates/unique

**Types de métriques supportés après nettoyage :**
- ✅ `missing_rate` - Ligne ~55-61 : `_investigate_missing_rate()`
- ✅ `count_where` - Ligne ~63-64 : `_investigate_count_where()`
- ❌ `avg`, `min`, `max`, `std`, `sum` - À SUPPRIMER
- ❌ `duplicate_count` - À SUPPRIMER
- ❌ `unique_count` - À SUPPRIMER

**Action :** Garder seulement missing_rate et count_where

---

### 3. Fichiers Python - Tests/Démos

#### `test_plugin_investigation.py`
**Ligne 24 :**
```python
import src.plugins.tests.range_test  # noqa: F401
```

**Action :** Supprimer ce fichier entier (test non fonctionnel pour le système de plugins)

---

#### `demo_missing_rate_filter_sales.py`
**Lignes 41-44 :**
```python
from src.plugins.tests.threshold_test import ThresholdTest
...
t = ThresholdTest()
```

**Action :** 
- Option 1 : Modifier pour utiliser interval_check
- Option 2 : Supprimer ce fichier démo si non utilisé

---

### 4. Fichiers de Test

#### `tests/test_plugin_system_old.py`
**Ligne 358 :**
```python
"type": "range",
```

**Action :** Modifier les tests pour utiliser "test.interval_check"

---

#### `tests/test_plugin_system.py`
**Lignes 359, 401 :**
```python
"type": "range",
...
{"id": "T-001", "type": "range", "params": {}}
```

**Action :** Modifier les tests pour utiliser "test.interval_check"

---

### 5. Fichiers Système

#### `src/plugins/virtual_catalog.py`
**Ligne 194 :**
```python
...     "type": "range",
```

**Action :** Mise à jour de la documentation/exemple inline

---

#### `src/plugins/sequencer.py`
**Lignes 39, 274 :**
```python
plugin_type: Type de plugin à exécuter (ex: "missing_rate", "range")
...
...         {"id": "T-001", "type": "range", "database": "virtual:M-001", ...}
```

**Action :** Remplacer "range" par "test.interval_check" dans les exemples

---

## 🎯 Plan d'Action Recommandé

### Phase 1 : Suppression des Fichiers de Plugins
```bash
# Tests à supprimer
rm src/plugins/tests/range_test.py
rm src/plugins/tests/range2_test.py
rm src/plugins/tests/threshold_test.py

# Conserver
# src/plugins/tests/interval_check.py ✅
# src/plugins/metrics/missing_rate.py ✅
```

### Phase 2 : Nettoyage de src/investigation.py
```python
# Supprimer ces méthodes :
- _investigate_aggregate()
- _investigate_duplicates()  
- _investigate_unique()

# Dans generate_investigation_samples(), garder seulement :
if metric_type == "missing_rate":
    return self._investigate_missing_rate(...)
elif metric_type == "count_where":
    return self._investigate_count_where(...)
else:
    return None
```

### Phase 3 : Mise à Jour des Tests
```bash
# Modifier pour utiliser interval_check au lieu de range
- tests/test_plugin_system_old.py
- tests/test_plugin_system.py
```

### Phase 4 : Nettoyage de la Documentation
```bash
# Supprimer mentions de range/threshold/aggregate/duplicate/unique
- INVESTIGATION_PLUGIN_INTEGRATION.md
- README_PATCH.md

# Mettre à jour les exemples dans :
- src/plugins/virtual_catalog.py
- src/plugins/sequencer.py
```

### Phase 5 : Fichiers Démo/Test à Décider
```bash
# À supprimer ou modifier :
- test_plugin_investigation.py (ne fonctionne pas, à supprimer)
- demo_missing_rate_filter_sales.py (utilise threshold_test)

# À conserver :
- test_interval_check_investigation_simple.py ✅ (fonctionne avec le système simple)
- demo_investigation.py (système simple)
- demo_investigation_real.py (système simple)
```

---

## 📊 Statistiques

### Fichiers à Supprimer : 4
- `src/plugins/tests/range_test.py`
- `src/plugins/tests/range2_test.py`
- `src/plugins/tests/threshold_test.py`
- `test_plugin_investigation.py`

### Fichiers à Nettoyer : 8
- `src/investigation.py` (supprimer 3 méthodes)
- `INVESTIGATION_PLUGIN_INTEGRATION.md`
- `README_PATCH.md`
- `tests/test_plugin_system_old.py`
- `tests/test_plugin_system.py`
- `src/plugins/virtual_catalog.py`
- `src/plugins/sequencer.py`
- `demo_missing_rate_filter_sales.py`

### Fichiers à Conserver : 2 plugins + 3 tests
**Plugins :**
- ✅ `src/plugins/metrics/missing_rate.py`
- ✅ `src/plugins/tests/interval_check.py`

**Tests fonctionnels :**
- ✅ `test_interval_check_investigation_simple.py`
- ✅ `demo_investigation.py`
- ✅ `demo_investigation_real.py`

---

## ✅ Validation

Après nettoyage, le projet ne doit contenir que :

**Métriques :**
- `missing_rate` uniquement

**Tests :**
- `interval_check` uniquement

**Investigation supportée pour :**
- `missing_rate` → Échantillonne lignes avec valeurs manquantes
- `count_where` → Échantillonne lignes respectant une condition
- `interval_check` (mode metric_value) → Remonte au dataset source de la métrique
- `interval_check` (mode dataset_columns) → Échantillonne valeurs hors limites

**Commandes de vérification post-nettoyage :**
```bash
# Vérifier qu'il ne reste aucune référence à range/threshold/duplicate/unique
grep -r "range_test\|RangeTest\|threshold_test\|ThresholdTest\|duplicate_count\|unique_count\|aggregate" --include="*.py" --include="*.md" .

# Vérifier la structure des plugins
ls src/plugins/tests/
# → Doit afficher : __init__.py, interval_check.py

ls src/plugins/metrics/
# → Doit afficher : __init__.py, missing_rate.py
```
