# Modifications de la structure DQ

## Résumé des changements

### 1. ✅ Ajout de `zone` au contexte

Le contexte contient maintenant :
```yaml
context:
  stream: "A"
  project: "P1"
  zone: "raw"           # ✅ NOUVEAU
  dq_point: "quality_check"
```

### 2. ✅ Suppression de `run_context`

- Supprimé de la génération de config
- Supprimé de `cfg_template()`
- Le contexte d'exécution est maintenant intégré directement dans `context`

### 3. ✅ Suppression de `orchestration`

- Section `orchestration` supprimée du template
- L'ordre d'exécution sera géré différemment

### 4. ✅ Structure des metrics et tests en dictionnaire

**Avant** (liste):
```yaml
metrics:
  - id: "missing_rate"
    params:
      dataset: "sales_2024"
```

**Après** (dictionnaire avec ID comme clé):
```yaml
metrics:
  missing_rate_sales:
    type: "missing_rate"
    specific:
      dataset: "sales_2024"
```

### 5. ✅ Suppression de paramètres de métriques

Paramètres supprimés lors de l'export :
- `dataset` (maintenant dans `specific`)
- `column` (maintenant dans `specific`)
- `where` (maintenant dans `specific`)
- `expr` (maintenant dans `specific`)

### 6. ✅ Suppression de `lower_enabled` et `upper_enabled` des tests

**Avant**:
```yaml
specific:
  lower_enabled: true
  lower_value: 0.0
  upper_enabled: true
  upper_value: 0.2
```

**Après**:
```yaml
specific:
  bounds:
    lower: 0.0
    upper: 0.2
```

Ces champs sont supprimés automatiquement lors de l'export de la configuration.

## Fichiers modifiés

1. **src/core/models_dq.py**
   - Ajout de la classe `DQContext` avec `zone`
   - Changement de `metrics` et `tests` de `List` à `Dict`

2. **src/utils.py**
   - `cfg_template()` : `metrics` et `tests` sont maintenant des dictionnaires
   - Suppression de la section `orchestration`

3. **src/callbacks/build.py**
   - `render_cfg_preview()` : conversion des metrics/tests en dictionnaires
   - Ajout de `zone` au contexte
   - Suppression de `run_context` et `orchestration`
   - Filtrage de `lower_enabled` et `upper_enabled` lors de l'export
   - `format_interval_bounds_display()` : utilisation de la nouvelle structure `bounds`

4. **dq/definitions/sales_quality_v1.yaml** (exemple)
   - Nouvelle structure avec metrics en dictionnaire
   - Ajout de `zone` au contexte
   - Utilisation de `bounds` pour interval_check

5. **dq/definitions/refunds_quality.yaml** (exemple)
   - Même structure que sales_quality_v1.yaml

## Migration des fichiers existants

Pour migrer vos anciens fichiers YAML :

1. **Ajouter `zone` au contexte**
2. **Convertir `metrics` de liste en dictionnaire**
3. **Convertir `tests` de liste en dictionnaire**
4. **Remplacer `lower_enabled`/`upper_enabled` par `bounds`**
5. **Supprimer `run_context` et `orchestration`**

### Exemple de migration

**Ancien format**:
```yaml
context:
  stream: "A"
  project: "P1"
run_context:
  quarter: "2025Q1"
metrics:
  - id: "metric_1"
    params:
      dataset: "sales"
tests:
  - id: "test_1"
    params:
      lower_enabled: true
      lower_value: 0
```

**Nouveau format**:
```yaml
context:
  stream: "A"
  project: "P1"
  zone: "raw"
metrics:
  metric_1:
    type: "missing_rate"
    specific:
      dataset: "sales"
tests:
  test_1:
    type: "interval_check"
    specific:
      bounds:
        lower: 0
```

## Notes importantes

- L'UI conserve temporairement `lower_enabled` et `upper_enabled` pour la compatibilité
- Ces champs sont automatiquement filtrés lors de l'export YAML/JSON
- La prévisualisation affiche déjà la structure finale sans ces champs
