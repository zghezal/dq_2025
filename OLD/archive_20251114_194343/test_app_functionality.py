#!/usr/bin/env python3
"""
Script de test pour vérifier que toutes les fonctionnalités principales marchent.
"""

import sys
import traceback
from pathlib import Path

print("=" * 80)
print("TEST DES FONCTIONNALITÉS DE L'APPLICATION")
print("=" * 80)

errors = []
warnings = []

# Test 1: Imports principaux
print("\n1️⃣  TEST DES IMPORTS PRINCIPAUX")
print("-" * 80)

# try:
#     import app
#     print("✅ app.py s'importe correctement")
# except Exception as e:
#     errors.append(f"❌ Erreur import app: {e}")
#     print(f"❌ Erreur import app: {e}")

print("⏭️  Sauté: import app (démarre le serveur)")

try:
    from src.core.channel_manager import get_channel_manager
    manager = get_channel_manager()
    channels = manager.list_channels()
    print(f"✅ Channel Manager: {len(channels)} canaux disponibles")
except Exception as e:
    errors.append(f"❌ Erreur Channel Manager: {e}")
    print(f"❌ Erreur Channel Manager: {e}")

try:
    from src.core.submission_processor import SubmissionProcessor
    print("✅ Submission Processor s'importe correctement")
except Exception as e:
    errors.append(f"❌ Erreur Submission Processor: {e}")
    print(f"❌ Erreur Submission Processor: {e}")

try:
    from src.core.dq_parser import load_dq_config
    print("✅ DQ Parser s'importe correctement")
except Exception as e:
    errors.append(f"❌ Erreur DQ Parser: {e}")
    print(f"❌ Erreur DQ Parser: {e}")

# Test 2: Fichiers DQ
print("\n2️⃣  TEST DES DÉFINITIONS DQ")
print("-" * 80)

dq_dir = Path("dq/definitions")
if dq_dir.exists():
    dq_files = list(dq_dir.glob("*.yaml"))
    print(f"📁 Trouvé {len(dq_files)} fichiers DQ")
    
    for dq_file in dq_files:
        try:
            config = load_dq_config(str(dq_file))
            print(f"  ✅ {dq_file.name}: {len(config.metrics)} métriques, {len(config.tests)} tests")
        except Exception as e:
            warnings.append(f"⚠️  {dq_file.name}: {str(e)[:50]}")
            print(f"  ⚠️  {dq_file.name}: {str(e)[:50]}")
else:
    errors.append("❌ Dossier dq/definitions introuvable")

# Test 3: Canaux
print("\n3️⃣  TEST DES CANAUX")
print("-" * 80)

try:
    for channel in channels:
        dq_count = len(channel.dq_configs) if channel.dq_configs else 0
        file_count = len(channel.file_specifications)
        status = "🟢" if channel.active else "🔴"
        print(f"  {status} {channel.name}")
        print(f"      - {file_count} fichier(s), {dq_count} DQ config(s)")
except Exception as e:
    errors.append(f"❌ Erreur listage canaux: {e}")

# Test 4: Layouts
print("\n4️⃣  TEST DES LAYOUTS")
print("-" * 80)

layouts = [
    "src.layouts.home",
    "src.layouts.channel_drop",
    "src.layouts.dq_runner",
]

for layout_module in layouts:
    try:
        __import__(layout_module)
        print(f"  ✅ {layout_module}")
    except Exception as e:
        errors.append(f"❌ {layout_module}: {e}")
        print(f"  ❌ {layout_module}: {e}")

# Test 5: Callbacks
print("\n5️⃣  TEST DES CALLBACKS")
print("-" * 80)

callback_modules = [
    "src.callbacks.navigation",
    "src.callbacks.channels_drop",
    "src.callbacks.dq",
]

for cb_module in callback_modules:
    try:
        __import__(cb_module)
        print(f"  ✅ {cb_module}")
    except Exception as e:
        errors.append(f"❌ {cb_module}: {e}")
        print(f"  ❌ {cb_module}: {e}")

# Test 6: Fichiers de test
print("\n6️⃣  TEST DES FICHIERS DE TEST")
print("-" * 80)

test_files = [
    "data/sales_invalid_upload.csv",
    "data/sales_valid_upload.csv",
    "scripts/validation/business_checks.py",
]

for test_file in test_files:
    if Path(test_file).exists():
        print(f"  ✅ {test_file}")
    else:
        warnings.append(f"⚠️  {test_file} manquant")
        print(f"  ⚠️  {test_file} manquant")

# Résumé
print("\n" + "=" * 80)
print("RÉSUMÉ")
print("=" * 80)

if errors:
    print(f"\n❌ {len(errors)} ERREUR(S) CRITIQUE(S):")
    for err in errors:
        print(f"   {err}")

if warnings:
    print(f"\n⚠️  {len(warnings)} AVERTISSEMENT(S):")
    for warn in warnings:
        print(f"   {warn}")

if not errors:
    print("\n✅ TOUS LES TESTS CRITIQUES PASSÉS")
    print("   L'application devrait fonctionner correctement")
else:
    print(f"\n❌ {len(errors)} problème(s) à corriger avant utilisation")

print("\n" + "=" * 80)

sys.exit(0 if not errors else 1)
