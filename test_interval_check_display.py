"""
Test script pour vérifier l'affichage des paramètres spécifiques 
du plugin interval_check avec les règles par colonne.
"""
import json
from src.callbacks.build import register_build_callbacks

# Exemple de test avec column_rules
test_with_rules = {
    "id": "TEST001",
    "type": "test.interval_check",
    "nature": {
        "name": "Test des bornes avec règles par colonne",
        "description": "Vérifie les intervalles avec des règles spécifiques"
    },
    "identification": {
        "test_id": "TEST001",
        "control_name": "Interval Check Test",
        "control_id": "IC001"
    },
    "general": {
        "criticality": "high",
        "on_fail": "raise_alert",
        "sample_on_fail": True
    },
    "specific": {
        "target_mode": "dataset_columns",
        "database": "sales_2024",
        "columns": ["amount", "quantity", "price"],
        "lower_enabled": True,
        "lower_value": 0,
        "upper_enabled": True,
        "upper_value": 1000,
        "column_rules": [
            {
                "columns": ["amount", "price"],
                "lower": 10,
                "upper": 500
            },
            {
                "columns": ["quantity"],
                "lower": 1,
                "upper": 100
            }
        ]
    }
}

# Test sans column_rules
test_without_rules = {
    "id": "TEST002",
    "type": "test.interval_check",
    "nature": {
        "name": "Test des bornes simples",
        "description": "Vérifie les intervalles sans règles spécifiques"
    },
    "identification": {
        "test_id": "TEST002",
        "control_name": "Simple Interval Check",
        "control_id": "IC002"
    },
    "general": {
        "criticality": "medium",
        "on_fail": "raise_alert",
        "sample_on_fail": False
    },
    "specific": {
        "target_mode": "metric_value",
        "metric_id": "completeness_rate",
        "lower_enabled": True,
        "lower_value": 0.95,
        "upper_enabled": True,
        "upper_value": 1.0
    }
}

print("=" * 80)
print("Test 1: Affichage avec règles par colonne")
print("=" * 80)
print(json.dumps(test_with_rules, indent=2, ensure_ascii=False))
print("\n")

print("=" * 80)
print("Test 2: Affichage sans règles par colonne")
print("=" * 80)
print(json.dumps(test_without_rules, indent=2, ensure_ascii=False))
print("\n")

print("✅ Les tests sont prêts à être affichés dans l'interface.")
print("   Lancez l'application Dash pour vérifier l'affichage dans le tableau.")
