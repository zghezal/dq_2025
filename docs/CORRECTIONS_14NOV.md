# Corrections Appliquées - 14 Nov 2025

## 1. ✅ Statut REJECTED pour échecs DQ

**Problème**: Le dépôt n'était pas clairement marqué comme "rejeté" en cas d'échec DQ.

**Solution**:
- Ajouté statut `REJECTED` dans `SubmissionStatus` enum
- Modifié `submission_processor.py` pour mettre `status = REJECTED` si `dq_failed > 0`
- `DQ_FAILED` réservé pour cas de tests skipped
- `DQ_SUCCESS` pour succès complet

**Résultat**: 
- Données invalides → **Status: rejected** ✅
- Données valides → **Status: dq_success** ✅

## 2. ✅ Plugin missing_rate non chargé

**Problème**: Import PySpark obligatoire empêchait le chargement du plugin `missing_rate`.

**Solution**:
- Rendu l'import PySpark optionnel dans `src/plugins/metrics/missing_rate.py`:
```python
try:
    from pyspark.sql import functions as F
    PYSPARK_AVAILABLE = True
except ImportError:
    PYSPARK_AVAILABLE = False
    F = None
```

**Résultat**: Plugin `missing_rate` maintenant découvert et fonctionnel ✅

## 3. ✅ Bouton télécharger amélioré

**Problème**: Callback du bouton télécharger fragile.

**Solution**:
- Ajouté vérifications robustes dans `download_report()` callback:
  - Vérifie existence des boutons
  - Vérifie existence de la soumission
  - Vérifie existence du fichier rapport
  - Logs détaillés pour debugging
- Conversion explicite `Path → str` pour `dcc.send_file()`

**Résultat**: Téléchargement plus robuste avec logs ✅

## Tests End-to-End

```
✅ Soumission INVALIDE:
   - 4 tests échoués (1 DQ + 3 scripts)
   - Status: rejected
   - Rapport généré

✅ Soumission VALIDE:
   - 6 tests réussis
   - Status: dq_success
   - Rapport généré
```

## Fichiers Modifiés

1. `src/core/models_channels.py` - Ajout statut REJECTED
2. `src/core/submission_processor.py` - Logique status REJECTED
3. `src/plugins/metrics/missing_rate.py` - Import PySpark optionnel
4. `src/callbacks/channels_drop.py` - Amélioration callback download
5. `src/core/executor.py` - Fix IDs uniques métriques/tests (précédent)
6. `src/core/dq_parser.py` - Support scripts (précédent)
