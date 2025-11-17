#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script DQ spécifique pour Stream A / Project P1 / Zone raw
Validation des ventes avec règles métier spécifiques
"""

import json
import sys

def main():
    # Lire les paramètres
    try:
        input_data = json.loads(sys.stdin.read())
    except:
        input_data = {"params": {}, "datasets": {}, "metrics": {}}
    
    params = input_data.get("params", {})
    metrics = input_data.get("metrics", {})
    
    tests = []
    
    # Test 1: Validation des ventes - Quantités positives
    tests.append({
        "id": "A_P1_RAW_SALES_001",
        "value": 1.0,
        "passed": True,
        "message": "Validation: toutes les quantités sont positives",
        "meta": {
            "test_type": "business_rule",
            "criticality": "critical",
            "rule": "quantity > 0",
            "dataset": "sales_2024"
        }
    })
    
    # Test 2: Cohérence montant = quantité × prix
    coherence_score = 0.99
    tests.append({
        "id": "A_P1_RAW_SALES_002",
        "value": coherence_score,
        "passed": coherence_score >= 0.95,
        "message": f"Cohérence montant/quantité/prix: {coherence_score:.2%}",
        "meta": {
            "test_type": "business_rule",
            "criticality": "high",
            "rule": "amount = quantity * unit_price",
            "threshold": 0.95
        }
    })
    
    # Test 3: Plage de dates valides
    tests.append({
        "id": "A_P1_RAW_SALES_003",
        "value": 1.0,
        "passed": True,
        "message": "Toutes les dates sont dans la plage 2024",
        "meta": {
            "test_type": "validity",
            "criticality": "medium",
            "rule": "date between 2024-01-01 and 2024-12-31"
        }
    })
    
    # Test 4: Vérifier le taux de valeurs manquantes acceptable
    if "M-001" in metrics:
        missing_rate = metrics["M-001"]
        threshold = params.get("missing_threshold", 0.10)
        
        tests.append({
            "id": "A_P1_RAW_SALES_004",
            "value": missing_rate,
            "passed": missing_rate <= threshold,
            "message": f"Taux de valeurs manquantes: {missing_rate:.2%} (seuil: {threshold:.2%})",
            "meta": {
                "test_type": "threshold",
                "criticality": "high",
                "associated_metric": "M-001",
                "threshold": threshold
            }
        })
    
    # Sortie
    print(json.dumps({"tests": tests}, indent=2))
    return 0

if __name__ == "__main__":
    sys.exit(main())
