"""
Package des plugins de métriques.

Les fichiers .py dans ce dossier sont automatiquement découverts et
enregistrés par le système de discovery.

Pour ajouter une nouvelle métrique:
1. Créer un fichier .py dans ce dossier
2. Définir une classe qui hérite de BasePlugin
3. Décorer avec @register
4. La métrique sera automatiquement disponible dans l'UI

Aucune modification du reste du code n'est nécessaire.
"""
