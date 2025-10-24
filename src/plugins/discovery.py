"""
Système de découverte automatique des plugins.

Ce module scanne les dossiers src/plugins/metrics/ et src/plugins/tests/,
importe tous les fichiers Python, et enregistre automatiquement les plugins
trouvés dans le REGISTRY global.

Usage:
    from src.plugins.discovery import discover_all_plugins
    
    # Découvre et enregistre tous les plugins
    plugins = discover_all_plugins()
    print(f"Trouvé {len(plugins)} plugins")
"""

import os
import sys
import importlib
import importlib.util
from pathlib import Path
from typing import Dict, List, Type
from src.plugins.base import BasePlugin, REGISTRY


class PluginInfo:
    """
    Informations sur un plugin découvert.
    
    Attributes:
        plugin_id: Identifiant unique du plugin
        plugin_class: Classe Python du plugin
        module_path: Chemin du fichier .py contenant le plugin
        category: "metric" ou "test"
    """
    def __init__(self, plugin_id: str, plugin_class: Type[BasePlugin], 
                 module_path: str, category: str):
        self.plugin_id = plugin_id
        self.plugin_class = plugin_class
        self.module_path = module_path
        self.category = category
    
    def __repr__(self):
        return f"<PluginInfo {self.category}:{self.plugin_id} from {self.module_path}>"


def _get_plugin_directories() -> Dict[str, Path]:
    """
    Retourne les chemins des dossiers contenant les plugins.
    
    Returns:
        Dict avec clés "metrics" et "tests" pointant vers les dossiers
    """
    # Trouver la racine du projet (où se trouve src/)
    current_file = Path(__file__).resolve()
    plugins_dir = current_file.parent  # src/plugins/
    
    return {
        "metrics": plugins_dir / "metrics",
        "tests": plugins_dir / "tests"
    }


def _import_module_from_path(module_path: Path) -> object:
    """
    Importe dynamiquement un module Python depuis un chemin de fichier.
    
    Args:
        module_path: Chemin vers le fichier .py à importer
    
    Returns:
        Module Python importé
    
    Raises:
        ImportError: Si l'import échoue
    """
    module_name = f"_dynamic_{module_path.stem}_{id(module_path)}"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    
    if spec is None or spec.loader is None:
        raise ImportError(f"Impossible de créer spec pour {module_path}")
    
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    
    return module


def discover_all_plugins(verbose: bool = True, force_rescan: bool = False) -> Dict[str, PluginInfo]:
    """
    Découvre tous les plugins dans src/plugins/metrics/ et src/plugins/tests/.
    
    Cette fonction utilise un cache pour éviter de scanner plusieurs fois.
    Si les plugins ont déjà été découverts, retourne le cache.
    
    Args:
        verbose: Si True, affiche les logs de découverte
        force_rescan: Si True, force un nouveau scan même si cache existe
    
    Returns:
        Dict mapping plugin_id -> PluginInfo pour tous les plugins découverts
    
    Example:
        >>> plugins = discover_all_plugins()
        >>> print(plugins.keys())
        dict_keys(['missing_rate', 'range', 'aggregation_by_region'])
    """
    global _discovery_cache
    
    # Utiliser le cache si disponible et pas de force_rescan
    if _discovery_cache is not None and not force_rescan:
        return _discovery_cache
    
    # Scanner
    if not verbose:
        # Désactiver temporairement les prints
        import io
        import contextlib
        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            result = _discover_all_plugins_impl()
    else:
        result = _discover_all_plugins_impl()
    
    # Mettre en cache
    _discovery_cache = result
    return result


def _discover_all_plugins_impl() -> Dict[str, PluginInfo]:
    """Implémentation interne de discover_all_plugins."""
    # Tracker les fichiers scannés pour savoir quelle catégorie ils appartiennent
    file_to_category: Dict[str, str] = {}
    
    directories = _get_plugin_directories()
    
    print("=" * 60)
    print("PLUGIN DISCOVERY START")
    print("=" * 60)
    
    # Scanner tous les dossiers et importer les modules
    for category, directory in directories.items():
        print(f"\n[INFO] Scanning {category} directory: {directory}")
        
        if not directory.exists():
            print(f"[WARN] Directory {directory} n'existe pas, skip")
            continue
        
        # Lister tous les fichiers .py (sauf __init__.py)
        python_files = [
            f for f in directory.glob("*.py")
            if f.name != "__init__.py"
        ]
        
        for py_file in python_files:
            try:
                # Importer le module (ça va populer REGISTRY via @register)
                module = _import_module_from_path(py_file)
                file_to_category[str(py_file)] = category
                print(f"[OK] Imported {py_file.name}")
            except Exception as e:
                print(f"[ERROR] Failed to import {py_file}: {e}")
                continue
    
    # Maintenant construire le dict de PluginInfo depuis REGISTRY
    # On ne peut pas vraiment savoir quel fichier a créé quel plugin,
    # donc on va juste catégoriser par convention de nommage
    all_discovered: Dict[str, PluginInfo] = {}
    
    for plugin_id, plugin_class in REGISTRY.items():
        # Essayer de deviner la catégorie depuis le group ou le plugin_id
        group = getattr(plugin_class, 'group', '').lower()
        if 'validation' in group or 'test' in group or plugin_id.startswith('test.'):
            category = "tests"
        else:
            category = "metrics"
        
        # On ne connaît pas vraiment le module_path, mettre un placeholder
        module_path = f"<discovered from {category}>"
        
        info = PluginInfo(
            plugin_id=plugin_id,
            plugin_class=plugin_class,
            module_path=module_path,
            category=category
        )
        all_discovered[plugin_id] = info
        print(f"[OK] Registered {category} plugin: {plugin_id}")
    
    print("\n" + "=" * 60)
    print(f"DISCOVERY COMPLETE: {len(all_discovered)} plugins found")
    print("=" * 60)
    
    # Afficher un résumé
    metrics_count = sum(1 for p in all_discovered.values() if p.category == "metrics")
    tests_count = sum(1 for p in all_discovered.values() if p.category == "tests")
    print(f"  - Metrics: {metrics_count}")
    print(f"  - Tests: {tests_count}")
    
    return all_discovered


def get_plugins_by_category(category: str) -> List[Type[BasePlugin]]:
    """
    Retourne tous les plugins d'une catégorie donnée.
    
    Args:
        category: "metrics" ou "tests"
    
    Returns:
        Liste des classes de plugins
    
    Note:
        Appelle discover_all_plugins() automatiquement si pas encore fait
    """
    if not REGISTRY:
        discover_all_plugins(verbose=False)
    
    # On ne peut pas stocker la catégorie dans REGISTRY directement,
    # donc on va re-scanner (c'est pas idéal mais simple)
    discovered = discover_all_plugins(verbose=False)
    
    return [
        info.plugin_class
        for info in discovered.values()
        if info.category == category
    ]


def get_plugin_info(plugin_id: str) -> PluginInfo | None:
    """
    Récupère les informations d'un plugin par son ID.
    
    Args:
        plugin_id: Identifiant du plugin
    
    Returns:
        PluginInfo ou None si non trouvé
    """
    discovered = discover_all_plugins(verbose=False)
    return discovered.get(plugin_id)


# Cache pour éviter de re-scanner à chaque appel
_discovery_cache: Dict[str, PluginInfo] | None = None


def ensure_plugins_discovered():
    """
    S'assure que les plugins ont été découverts au moins une fois.
    
    Utilise un cache interne pour éviter de re-scanner à chaque appel.
    """
    global _discovery_cache
    if _discovery_cache is None:
        _discovery_cache = discover_all_plugins(verbose=True)