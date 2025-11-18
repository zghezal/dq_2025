# coding: utf-8
"""
Script de vérification des plugins non autorisés

Vérifie qu'il ne reste que :
- missing_rate (métrique)
- interval_check (test)
"""

import sys
from pathlib import Path
import re

repo_root = Path(__file__).parent

print("=" * 80)
print("AUDIT - VERIFICATION DES PLUGINS NON AUTORISES")
print("=" * 80)
print()

# Plugins autorisés
ALLOWED_PLUGINS = {
    "metrics": ["missing_rate"],
    "tests": ["interval_check"]
}

# Patterns à rechercher (plugins non autorisés)
FORBIDDEN_PATTERNS = [
    (r'\brange_test\b', "range_test (plugin)"),
    (r'\bRangeTest\b', "RangeTest (classe)"),
    (r'\brange2_test\b', "range2_test (plugin)"),
    (r'\bRangeTest2\b', "RangeTest2 (classe)"),
    (r'\bthreshold_test\b', "threshold_test (plugin)"),
    (r'\bThresholdTest\b', "ThresholdTest (classe)"),
    (r'\bduplicate_count\b', "duplicate_count (métrique)"),
    (r'\bunique_count\b', "unique_count (métrique)"),
    (r'_investigate_aggregate\b', "_investigate_aggregate (méthode)"),
    (r'_investigate_duplicates\b', "_investigate_duplicates (méthode)"),
    (r'_investigate_unique\b', "_investigate_unique (méthode)"),
    (r'plugin_id\s*=\s*["\'](?:range|test\.range2|test\.threshold)["\']', "plugin_id non autorisé"),
]

# Fichiers à ignorer
IGNORE_PATTERNS = [
    "AUDIT_PLUGINS_A_SUPPRIMER.md",
    "verify_plugins.py",
    ".git/",
    "__pycache__/",
    "*.pyc",
]

def should_ignore(file_path):
    """Vérifie si le fichier doit être ignoré"""
    path_str = str(file_path)
    for pattern in IGNORE_PATTERNS:
        if pattern in path_str:
            return True
    return False

# ============================================================================
# 1. VERIFICATION DES FICHIERS DE PLUGINS
# ============================================================================
print("[1] Verification des fichiers de plugins")
print("-" * 80)

plugins_dir = repo_root / "src" / "plugins"

# Vérifier les métriques
metrics_dir = plugins_dir / "metrics"
if metrics_dir.exists():
    metric_files = [f for f in metrics_dir.glob("*.py") if f.name != "__init__.py"]
    print(f"Metriques trouvees : {len(metric_files)}")
    for f in metric_files:
        name = f.stem
        status = "OK" if name in ALLOWED_PLUGINS["metrics"] else "KO NON AUTORISE"
        print(f"  [{status}] {name}.py")

# Vérifier les tests
tests_dir = plugins_dir / "tests"
if tests_dir.exists():
    test_files = [f for f in tests_dir.glob("*.py") if f.name != "__init__.py"]
    print(f"\nTests trouves : {len(test_files)}")
    for f in test_files:
        name = f.stem
        status = "OK" if name in ALLOWED_PLUGINS["tests"] else "KO NON AUTORISE"
        print(f"  [{status}] {name}.py")

print()

# ============================================================================
# 2. RECHERCHE DE PATTERNS INTERDITS
# ============================================================================
print("[2] Recherche de patterns interdits dans le code")
print("-" * 80)

issues_found = {}

# Parcourir tous les fichiers Python et Markdown
for ext in ["*.py", "*.md"]:
    for file_path in repo_root.rglob(ext):
        if should_ignore(file_path):
            continue
        
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            
            for pattern, description in FORBIDDEN_PATTERNS:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    # Calculer le numéro de ligne
                    line_num = content[:match.start()].count('\n') + 1
                    
                    # Get the full line for context checking
                    lines = content.split('\n')
                    full_line = lines[line_num - 1] if line_num <= len(lines) else ""
                    
                    # Skip if line contains explanatory context about removal
                    exclude_keywords = [
                        'supprimé', 'supprimés', 'supprimées',
                        'obsolète', 'obsolètes', 
                        'titre d\'exemple', 
                        'ont été supprimés',
                        'références.*obsolètes'
                    ]
                    if any(keyword in full_line.lower() for keyword in exclude_keywords):
                        continue
                    
                    if file_path not in issues_found:
                        issues_found[file_path] = []
                    
                    issues_found[file_path].append({
                        "line": line_num,
                        "description": description,
                        "match": match.group()
                    })
        
        except Exception as e:
            print(f"Erreur lecture {file_path}: {e}")

# Afficher les résultats
if issues_found:
    print(f"KO - {len(issues_found)} fichiers avec references interdites :")
    print()
    
    for file_path, issues in sorted(issues_found.items()):
        rel_path = file_path.relative_to(repo_root)
        print(f"  {rel_path} ({len(issues)} occurrences)")
        
        # Grouper par description
        by_desc = {}
        for issue in issues:
            desc = issue['description']
            if desc not in by_desc:
                by_desc[desc] = []
            by_desc[desc].append(f"L{issue['line']}")
        
        for desc, lines in sorted(by_desc.items()):
            lines_str = ", ".join(lines[:5])
            if len(lines) > 5:
                lines_str += f"... (+{len(lines)-5})"
            print(f"    - {desc}: {lines_str}")
        print()
else:
    print("OK - Aucune reference interdite trouvee")
    print()

# ============================================================================
# 3. FICHIERS A SUPPRIMER
# ============================================================================
print("[3] Fichiers de plugins a supprimer")
print("-" * 80)

files_to_delete = []

# Plugins de tests non autorisés
if tests_dir.exists():
    for f in tests_dir.glob("*.py"):
        if f.name != "__init__.py" and f.stem not in ALLOWED_PLUGINS["tests"]:
            files_to_delete.append(f)

# Fichiers de test non fonctionnels
test_files = [
    repo_root / "test_plugin_investigation.py"
]
for f in test_files:
    if f.exists():
        files_to_delete.append(f)

if files_to_delete:
    print(f"Fichiers a supprimer : {len(files_to_delete)}")
    for f in files_to_delete:
        rel_path = f.relative_to(repo_root)
        print(f"  - {rel_path}")
else:
    print("Aucun fichier a supprimer")

print()

# ============================================================================
# 4. RESUME
# ============================================================================
print("=" * 80)
print("RESUME")
print("=" * 80)

status = "OK" if not issues_found and not files_to_delete else "KO"
print(f"Statut global : {status}")
print()

if issues_found:
    print(f"KO - {len(issues_found)} fichiers avec references a nettoyer")
    print("     Voir details ci-dessus")
else:
    print("OK - Aucune reference interdite dans le code")

if files_to_delete:
    print(f"KO - {len(files_to_delete)} fichiers de plugins a supprimer")
    print("     Voir liste ci-dessus")
else:
    print("OK - Aucun fichier de plugin non autorise")

print()
print("Plugins autorises :")
print(f"  - Metriques : {', '.join(ALLOWED_PLUGINS['metrics'])}")
print(f"  - Tests : {', '.join(ALLOWED_PLUGINS['tests'])}")
print()

if status == "KO":
    print("Actions requises :")
    print("  1. Consulter AUDIT_PLUGINS_A_SUPPRIMER.md pour le plan complet")
    print("  2. Supprimer les fichiers de plugins non autorises")
    print("  3. Nettoyer les references dans le code")
    print("  4. Relancer ce script pour verification")
    print()
    sys.exit(1)
else:
    print("Projet conforme ! Seuls missing_rate et interval_check sont presents.")
    print()
    sys.exit(0)
