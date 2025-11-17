#!/usr/bin/env python3
"""
Script pour identifier et déplacer les fichiers de démo/test vers un dossier OLD.
"""

import shutil
from pathlib import Path
from datetime import datetime

# Créer le dossier OLD
old_dir = Path("OLD")
old_dir.mkdir(exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
archive_dir = old_dir / f"archive_{timestamp}"
archive_dir.mkdir(exist_ok=True)

print("=" * 80)
print(f"ARCHIVAGE DES FICHIERS NON ESSENTIELS")
print(f"Destination: {archive_dir}")
print("=" * 80)

# Fichiers à déplacer (démos, tests, documentation temporaire)
files_to_move = [
    # Fichiers de démo
    "demo.py",
    "demo_channels.py",
    "demo_create_channel.py",
    "demo_data_sources.py",
    "demo_dq_parser.py",
    "demo_end_to_end.py",
    "demo_excel_complete.py",
    "demo_excel_export.py",
    "demo_investigation.py",
    "demo_investigation_real.py",
    "demo_missing_rate_filter_sales.py",
    "demo_permissions.py",
    "demo_sequencer.py",
    "demo_sequencer_filters.py",
    "demo_spark_plugins.py",
    "demo_validation_ids.py",
    
    # Tests rapides
    "quick_test (1).py",
    "quick_test (2).py",
    "quick_test (4).py",
    "test_channels_display.py",
    "test_end_to_end_channels.py",
    "test_interval_check_display.py",
    "test_interval_check_investigation.py",
    "test_interval_check_investigation_simple.py",
    "test_refunds_execution.py",
    "test_yaml_duplicates.py",
    "debug_refunds.py",
    
    # Scripts temporaires
    "fix_upload.py",
    "list_channels.py",
    "patch.py",
    "verify_plugins.py",
    "generate_test_data.py",
    
    # Documentation temporaire/en cours
    "AUDIT_PLUGINS_A_SUPPRIMER.md",
    "CHANGES_DQ_STRUCTURE.md",
    "CHANNELS_READY.md",
    "DATA_SOURCES_DOC.md",
    "DATA_SOURCES_READY.md",
    "DATA_SOURCES_SUMMARY.md",
    "DEPENDENCY_EXECUTION_DOC.md",
    "DQ_PARSER_DOC.md",
    "EXCEL_EXPORT_DOC.md",
    "EXCEL_STRUCTURE_DOC.md",
    "GUIDE_CANAUX.md",
    "GUIDE_PERMISSIONS.md",
    "IMPLEMENTATION_COMPLETE.md",
    "IMPLICIT_TESTS_DOC.md",
    "IMPORT_FIX.md",
    "INTERVAL_CHECK_IMPROVEMENTS.md",
    "INVESTIGATION_PLUGIN_INTEGRATION.md",
    "INVESTIGATION_SYSTEM.md",
    "MIGRATION_GUIDE.md",
    "PERMISSIONS_READY.md",
    "QUICKSTART_SOURCES.md",
    "README_PATCH.md",
    "TEST_CHANNELS_UI.md",
    "VALIDATION_UNIQUE_IDS.md",
    
    # Fichiers de configuration obsolètes
    "replit.md",
    ".replit",
    
    # Dossiers de test
    "test_data",
]

moved_count = 0
not_found_count = 0

for file_path_str in files_to_move:
    file_path = Path(file_path_str)
    
    if file_path.exists():
        dest = archive_dir / file_path.name
        try:
            if file_path.is_dir():
                shutil.copytree(file_path, dest)
                shutil.rmtree(file_path)
            else:
                shutil.copy2(file_path, dest)
                file_path.unlink()
            print(f"✅ Déplacé: {file_path}")
            moved_count += 1
        except Exception as e:
            print(f"❌ Erreur {file_path}: {e}")
    else:
        not_found_count += 1

print("\n" + "=" * 80)
print("RÉSUMÉ")
print("=" * 80)
print(f"✅ {moved_count} fichiers/dossiers déplacés")
print(f"⏭️  {not_found_count} fichiers non trouvés (déjà supprimés ?)")
print(f"\n📁 Archive créée: {archive_dir}")

print("\n" + "=" * 80)
print("FICHIERS ESSENTIELS CONSERVÉS")
print("=" * 80)

essential_files = [
    "run.py",
    "app.py",
    "requirements.txt",
    "README.md",
    "config/inventory.yaml",
    "dq/definitions/",
    "src/",
    "tests/",
    "tools/",
    "managed_folders/",
    "data/ (fichiers de test upload)",
    "scripts/ (validation)",
]

for ef in essential_files:
    print(f"  📌 {ef}")

print("\n✅ Nettoyage terminé ! L'application reste fonctionnelle.")
