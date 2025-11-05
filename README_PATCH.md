# Patch: UI auto-générée & contrats (sans régression)

Ce paquet **n'écrase aucun fichier existant**. Il ajoute :
- `src/core/ui_meta.py`
- `src/plugins/base_models.py`
- `src/plugins/tests/range2_test.py` (nouvelle version auto-UI — l'ancienne reste intacte)
- `src/ui/form_builder.py` (générateur de formulaires)
- `tests/test_plugin_contracts.py` (contract tests)
- `tests/test_plugins_datadriven.py` + `tests/cases/tests_range2.yaml` (tests data-driven)

## Intégration dans le Builder (optionnelle, sans casser l'existant)

1. **Importer** le form builder dans `src/callbacks/build.py` :
```python
try:
    from src.ui.form_builder import build_form_from_model
except Exception:
    build_form_from_model = None
```

2. **Lors de la sélection d’un plugin** (métrique/test), si `build_form_from_model` est dispo et que le plugin a un `ParamsModel` :
```python
if build_form_from_model and hasattr(plugin_cls, "ParamsModel"):
    auto_form = build_form_from_model(plugin_cls.ParamsModel, context=your_context_object)
    # Utiliser auto_form à la place du formulaire manuel
else:
    # fallback: garder le comportement actuel
```

3. **Dépendances dynamiques** (ex: columns dépend de alias) : ajoute un petit callback qui lit la valeur de `{"role":"arg-data.alias"}`
et remplit les options de `{"role":"arg-data.columns"}` via votre inventaire (`inventory.list_columns(alias)` ou `context.columns_for(alias)`).

> Tant que tu n’actives pas l’auto-form, *rien ne change* dans l’UI.

## Tests

- `pytest -q` couvrira :
  - contrat des plugins (`tests/test_plugin_contracts.py`)
  - cas data-driven (`tests/test_plugins_datadriven.py`)

## Pourquoi c’est safe ?
- Aucune modification de fichiers existants → zéro régression par défaut.
- Les nouvelles briques sont **ajoutées** et activables à la demande.
