# DQ Builder — Local Dash App (v3.6)

**Fixes ciblés :**
- **ID métrique**: champ stable (`debounce=True`, `autoComplete=off`, `persistence=session`). Le formulaire n'est *jamais* re-généré pendant la saisie.
- **Colonnes après choix de la base**: callbacks **sans `prevent_initial_call`** et petit **toast** si aucune colonne détectée.
- Boutons *Ajouter* gardent la reconstruction si la préview est vide.
