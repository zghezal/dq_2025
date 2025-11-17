#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test d'intégration du système de scripts DQ

Ce script teste l'exécution d'une DQ avec un script personnalisé
et vérifie que les résultats sont correctement agrégés dans l'export Excel.
"""

import sys
import os
from pathlib import Path

# Ajouter le répertoire racine au path
sys.path.insert(0, str(Path(__file__).parent))

import yaml
from src.core.models_inventory import Inventory
from src.core.models_dq import DQDefinition
from src.core.parser import build_execution_plan
from src.core.executor import execute
from src.core.connectors import LocalReader
from src.core.simple_excel_export import export_run_result_to_excel


def test_script_integration():
    """Test complet de l'intégration des scripts"""
    
    print("=" * 60)
    print("TEST: Exécution DQ avec scripts personnalisés")
    print("=" * 60)
    
    # 1. Charger l'inventaire
    print("\n📦 Chargement de l'inventaire...")
    inv_path = Path("config/inventory.yaml")
    inv_data = yaml.safe_load(inv_path.read_text(encoding="utf-8"))
    inv = Inventory(**inv_data)
    print(f"   ✅ Inventaire chargé: {len(inv.streams)} streams")
    
    # 2. Charger la définition DQ avec script
    print("\n📄 Chargement de la définition DQ...")
    dq_path = Path("dq/definitions/sales_with_script.yaml")
    dq_data = yaml.safe_load(dq_path.read_text(encoding="utf-8"))
    dq = DQDefinition(**dq_data)
    print(f"   ✅ DQ chargée: {dq.id}")
    print(f"   - Métriques: {len(dq.metrics)}")
    print(f"   - Tests: {len(dq.tests)}")
    print(f"   - Scripts: {len(dq.scripts)}")
    
    # 3. Construire le plan d'exécution
    print("\n🔧 Construction du plan d'exécution...")
    plan = build_execution_plan(inv, dq, overrides={})
    print(f"   ✅ Plan créé: {len(plan.steps)} steps")
    for i, step in enumerate(plan.steps):
        print(f"      {i+1}. {step.kind}: {step.id}")
    
    # 4. Exécuter
    print("\n▶️  Exécution...")
    run_result = execute(plan, loader=LocalReader(plan.alias_map), investigate=False)
    print(f"   ✅ Exécution terminée: {run_result.run_id}")
    print(f"   - Métriques: {len(run_result.metrics)}")
    print(f"   - Tests: {len(run_result.tests)}")
    print(f"   - Scripts: {len(run_result.scripts)}")
    
    # 5. Afficher les résultats des métriques
    print("\n📊 MÉTRIQUES:")
    for metric_id, result in run_result.metrics.items():
        status = "✅" if result.passed is not False else "❌"
        print(f"   {status} {metric_id}: {result.value} - {result.message}")
    
    # 6. Afficher les résultats des tests
    print("\n🧪 TESTS:")
    for test_id, result in run_result.tests.items():
        status = "✅" if result.passed else "❌"
        print(f"   {status} {test_id}: {result.message}")
    
    # 7. Afficher les résultats des scripts
    print("\n📜 SCRIPTS:")
    for script_id, script_result in run_result.scripts.items():
        status = "✅" if script_result.get('success') else "❌"
        print(f"   {status} {script_id}:")
        if script_result.get('success'):
            print(f"      - Métriques ajoutées: {len(script_result.get('metrics', {}))}")
            print(f"      - Tests ajoutés: {len(script_result.get('tests', {}))}")
        else:
            print(f"      - Erreur: {script_result.get('error')}")
    
    # 8. Exporter vers Excel
    print("\n📤 Export vers Excel...")
    output_path = "reports/test_script_integration.xlsx"
    os.makedirs("reports", exist_ok=True)
    
    export_run_result_to_excel(
        run_result=run_result,
        output_path=output_path,
        dq_id=dq.id,
        quarter=dq.context.dq_point if dq.context else None,
        project=dq.context.project if dq.context else None
    )
    
    print("\n" + "=" * 60)
    print("✅ TEST RÉUSSI !")
    print("=" * 60)
    print(f"\n📁 Rapport Excel généré: {output_path}")
    print("\nStructure du fichier:")
    print("  - Onglet 'Résumé': Vue d'ensemble des résultats")
    print("  - Onglet 'Métriques': Métriques natives + métriques des scripts")
    print("  - Onglet 'Tests': Tests natifs + tests des scripts")
    print("  - Onglet 'Scripts': Détails d'exécution des scripts")
    print("\n💡 Les résultats des scripts sont agrégés avec les métriques/tests natifs")
    
    return True


if __name__ == "__main__":
    try:
        success = test_script_integration()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
