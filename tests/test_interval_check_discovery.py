"""
Test pour vérifier que le plugin interval_check est bien découvert.
"""

print("=" * 60)
print("TEST: Découverte du plugin interval_check")
print("=" * 60)

# 1. Vérifier que le module peut être importé
print("\n[1] Import du module interval_check...")
try:
    from src.plugins.tests.interval_check import IntervalCheck
    print(f"    ✅ Module importé: {IntervalCheck}")
    print(f"    ✅ Plugin ID: {IntervalCheck.plugin_id}")
    print(f"    ✅ Label: {IntervalCheck.label}")
    print(f"    ✅ Group: {IntervalCheck.group}")
except Exception as e:
    print(f"    ❌ Erreur import: {e}")
    import traceback
    traceback.print_exc()

# 2. Vérifier le REGISTRY
print("\n[2] Vérification du REGISTRY...")
try:
    from src.plugins.base import REGISTRY
    print(f"    Nombre de plugins dans REGISTRY: {len(REGISTRY)}")
    
    if "interval_check" in REGISTRY:
        print(f"    ✅ interval_check trouvé dans REGISTRY")
        plugin_class = REGISTRY["interval_check"]
        print(f"       Classe: {plugin_class}")
        print(f"       Label: {plugin_class.label}")
    else:
        print(f"    ❌ interval_check NON trouvé dans REGISTRY")
        print(f"    Plugins disponibles: {list(REGISTRY.keys())}")
except Exception as e:
    print(f"    ❌ Erreur: {e}")
    import traceback
    traceback.print_exc()

# 3. Forcer la découverte
print("\n[3] Force discovery...")
try:
    from src.plugins.discovery import discover_all_plugins
    plugins = discover_all_plugins(verbose=True, force_rescan=True)
    
    if "interval_check" in plugins:
        print(f"    ✅ interval_check trouvé par discover_all_plugins")
        info = plugins["interval_check"]
        print(f"       Category: {info.category}")
        print(f"       Class: {info.plugin_class}")
    else:
        print(f"    ❌ interval_check NON trouvé par discover_all_plugins")
        print(f"    Plugins tests trouvés: {[k for k, v in plugins.items() if v.category == 'tests']}")
except Exception as e:
    print(f"    ❌ Erreur: {e}")
    import traceback
    traceback.print_exc()

# 4. Vérifier get_plugin
print("\n[4] Test get_plugin...")
try:
    from src.plugins.base import get_plugin
    
    plugin_class = get_plugin("interval_check")
    if plugin_class:
        print(f"    ✅ get_plugin('interval_check') retourne: {plugin_class}")
    else:
        print(f"    ❌ get_plugin('interval_check') retourne None")
except Exception as e:
    print(f"    ❌ Erreur: {e}")
    import traceback
    traceback.print_exc()

# 5. Vérifier les plugins de type test
print("\n[5] Liste de tous les plugins de type test...")
try:
    from src.plugins.discovery import get_plugins_by_category
    
    test_plugins = get_plugins_by_category("tests")
    print(f"    Nombre de plugins test: {len(test_plugins)}")
    
    for plugin_cls in test_plugins:
        print(f"    - {plugin_cls.plugin_id}: {plugin_cls.label}")
        
    if IntervalCheck in test_plugins:
        print(f"    ✅ IntervalCheck dans la liste")
    else:
        print(f"    ❌ IntervalCheck PAS dans la liste")
except Exception as e:
    print(f"    ❌ Erreur: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("TEST TERMINÉ")
print("=" * 60)
