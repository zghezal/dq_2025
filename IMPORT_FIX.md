# Correction du conflit de modules

## Problème rencontré

```
ImportError: cannot import name 'list_dq_files' from 'src.utils'
```

## Cause

Conflit de noms entre :
- **Fichier** : `src/utils.py` (contient les fonctions utilitaires principales)
- **Dossier** : `src/utils/` (créé pour le module auth_demo)

Python privilégie le package (dossier) sur le module (fichier), donc `import src.utils` chargeait `src/utils/__init__.py` au lieu de `src/utils.py`.

## Solution appliquée

1. **Renommer le dossier** `src/utils/` en `src/auth/`
   ```powershell
   Move-Item -Path "src/utils" -Destination "src/auth"
   ```

2. **Mettre à jour les imports** dans `src/callbacks/channels_drop.py`
   ```python
   # Avant
   from src.utils.auth_demo import get_demo_users_list, get_user_permissions
   
   # Après
   from src.auth.auth_demo import get_demo_users_list, get_user_permissions
   ```

## Résultat

✅ L'application démarre correctement sur http://127.0.0.1:5002
✅ Tous les imports fonctionnent (src.utils.py pour les fonctions, src.auth.auth_demo pour l'authentification)
✅ Le système de permissions est opérationnel

## Structure finale

```
src/
  ├── utils.py              # Fonctions utilitaires principales
  ├── auth/                 # Module d'authentification
  │   ├── __init__.py
  │   └── auth_demo.py      # 8 utilisateurs de démo
  └── ...
```

## Avertissement mineur

Un warning apparaît au démarrage (non bloquant) :
```
Field name "schema" in "VirtualDataset" shadows an attribute in parent "BaseModel"
```
→ À corriger dans `src/plugins/output_schema.py` en renommant le champ `schema`.
