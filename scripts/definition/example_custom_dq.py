#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script DQ personnalisé - Exemple
Ce script produit des tests au format compatible avec le système DQ.

Entrée (stdin): JSON avec {"params": {...}, "datasets": {...}, "metrics": {...}}
Sortie (stdout): JSON avec {"tests": [...]}

Format de test:
{
    "id": "TEST_ID",
    "value": 0.95,
    "passed": true,
    "message": "Description du test",
    "meta": {
        "test_type": "custom",
        "criticality": "high",
        ...
    }
}
"""

import json
import sys

def main():
    # Lire les paramètres depuis stdin
    try:
        input_data = json.loads(sys.stdin.read())
    except:
        input_data = {"params": {}, "datasets": {}, "metrics": {}}
    
    params = input_data.get("params", {})
    datasets = input_data.get("datasets", {})
    existing_metrics = input_data.get("metrics", {})
    
    # Liste des tests à produire
    tests = []
    
    # ===== EXEMPLE 1: Test de seuil simple =====
    tests.append({
        "id": "CUSTOM_TEST_001",
        "value": 0.95,
        "passed": True,
        "message": "Score de qualité global: 95%",
        "meta": {
            "test_type": "quality_score",
            "criticality": "high",
            "dataset": "sales_2024"
        }
    })
    
    # ===== EXEMPLE 2: Test basé sur une métrique existante =====
    if "M-001" in existing_metrics:
        missing_rate = existing_metrics["M-001"]
        tests.append({
            "id": "CUSTOM_TEST_002",
            "value": missing_rate,
            "passed": missing_rate <= 0.10,
            "message": f"Taux de valeurs manquantes: {missing_rate:.2%} ({'OK' if missing_rate <= 0.10 else 'ÉCHEC'})",
            "meta": {
                "test_type": "threshold",
                "criticality": "medium",
                "threshold": 0.10,
                "associated_metric": "M-001"
            }
        })
    
    # ===== EXEMPLE 3: Test de cohérence inter-datasets =====
    tests.append({
        "id": "CUSTOM_TEST_003",
        "value": 0.98,
        "passed": True,
        "message": "Cohérence entre datasets validée (98%)",
        "meta": {
            "test_type": "coherence",
            "criticality": "high",
            "datasets": list(datasets.keys())
        }
    })
    
    # ===== EXEMPLE 4: Test de règle métier =====
    business_rule_ok = True
    tests.append({
        "id": "CUSTOM_TEST_004",
        "value": 1.0 if business_rule_ok else 0.0,
        "passed": business_rule_ok,
        "message": "Règle métier: montants cohérents avec quantités",
        "meta": {
            "test_type": "business_rule",
            "criticality": "critical",
            "rule": "amount = quantity * unit_price"
        }
    })
    
    # ===== EXEMPLE 5: Test avec paramètres =====
    threshold = params.get("threshold", 0.90)
    completeness = 0.95
    tests.append({
        "id": "CUSTOM_TEST_005",
        "value": completeness,
        "passed": completeness >= threshold,
        "message": f"Complétude: {completeness:.2%} (seuil: {threshold:.2%})",
        "meta": {
            "test_type": "completeness",
            "criticality": "medium",
            "threshold": threshold,
            "actual": completeness
        }
    })
    
    # Produire la sortie JSON
    output = {
        "tests": tests
    }
    
    print(json.dumps(output, indent=2))
    return 0

if __name__ == "__main__":
    sys.exit(main())
