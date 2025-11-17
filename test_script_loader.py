"""
Test du script_loader
"""

import sys
sys.path.insert(0, '.')

from dq.scripts.script_loader import list_scripts, get_script_options

print("=" * 60)
print("Test du Script Loader")
print("=" * 60)

# Test 1: Scripts génériques (definition/)
print("\n1. Scripts génériques (sans contexte):")
scripts = list_scripts()
for s in scripts:
    print(f"  - {s.id}: {s.label} ({s.execute_on})")

# Test 2: Scripts pour A/P1/raw
print("\n2. Scripts disponibles pour A/P1/raw:")
scripts = list_scripts(stream="A", project="P1", zone="raw")
for s in scripts:
    print(f"  - {s.id}: {s.label} ({s.execute_on})")
    print(f"    Path: {s.path}")
    print(f"    Tags: {', '.join(s.tags)}")

# Test 3: Options pour dropdown
print("\n3. Options pour dropdown (A/P1/raw):")
options = get_script_options(stream="A", project="P1", zone="raw")
for opt in options:
    print(f"  - {opt['label']}")

print("\n✅ Test terminé")
