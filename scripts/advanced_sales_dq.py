#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script DQ avancé - Accès aux données réelles

Ce script montre comment:
- Accéder aux datasets via leurs chemins
- Calculer des métriques complexes  
- Effectuer des tests de cohérence inter-datasets
"""

import json
import sys
import pandas as pd
from pathlib import Path

def main():
    # Lire les paramètres
    try:
        input_data = json.loads(sys.stdin.read())
    except:
        input_data = {"params": {}, "datasets": {}, "metrics": {}}
    
    params = input_data.get("params", {})
    datasets_aliases = input_data.get("datasets", {})
    existing_metrics = input_data.get("metrics", {})
    
    metrics = {}
    tests = {}
    
    # ===== EXEMPLE 1: Charger un dataset et calculer une métrique =====
    # Dans un vrai script, vous pouvez charger les données
    # Pour cet exemple, on simule le chargement
    
    try:
        # Chercher le dataset sales_2024
        sales_path = "sourcing/input/sales_2024.csv"
        if Path(sales_path).exists():
            df = pd.read_csv(sales_path)
            
            # Métrique: Nombre total de lignes
            metrics["SCRIPT_TOTAL_ROWS"] = {
                "value": len(df),
                "passed": True,
                "message": f"Dataset contient {len(df)} lignes"
            }
            
            # Métrique: Valeur totale des ventes
            if 'total' in df.columns:
                total_sales = df['total'].sum()
                metrics["SCRIPT_TOTAL_SALES"] = {
                    "value": round(total_sales, 2),
                    "passed": total_sales > 0,
                    "message": f"Total des ventes: {total_sales:,.2f}"
                }
            
            # Test: Vérifier qu'il n'y a pas de valeurs négatives
            if 'total' in df.columns:
                negative_count = (df['total'] < 0).sum()
                tests["SCRIPT_NO_NEGATIVE_SALES"] = {
                    "value": negative_count,
                    "passed": negative_count == 0,
                    "message": f"Trouvé {negative_count} ventes négatives" if negative_count > 0 
                              else "Aucune vente négative"
                }
            
            # Test: Cohérence quantité vs montant
            if 'quantity' in df.columns and 'total' in df.columns:
                invalid = ((df['quantity'] > 0) & (df['total'] <= 0)).sum()
                tests["SCRIPT_QUANTITY_AMOUNT_COHERENCE"] = {
                    "value": invalid,
                    "passed": invalid == 0,
                    "message": f"Trouvé {invalid} incohérences quantité/montant" if invalid > 0
                              else "Cohérence quantité/montant OK"
                }
        else:
            metrics["SCRIPT_FILE_ERROR"] = {
                "value": 0,
                "passed": False,
                "message": f"Fichier non trouvé: {sales_path}"
            }
    
    except Exception as e:
        metrics["SCRIPT_ERROR"] = {
            "value": 0,
            "passed": False,
            "message": f"Erreur lors du chargement: {e}"
        }
    
    # ===== EXEMPLE 2: Utiliser les métriques existantes =====
    # Créer un test basé sur une métrique calculée par le DQ
    if "M-001" in existing_metrics:
        missing_rate = existing_metrics["M-001"]
        threshold = params.get("missing_rate_threshold", 0.05)
        
        tests["SCRIPT_MISSING_RATE_CHECK"] = {
            "value": missing_rate,
            "passed": missing_rate <= threshold,
            "message": f"Missing rate {missing_rate:.2%} vs seuil {threshold:.2%}"
        }
    
    # ===== EXEMPLE 3: Règle métier complexe =====
    # Exemple: vérifier la distribution des ventes par catégorie
    try:
        if Path(sales_path).exists():
            df = pd.read_csv(sales_path)
            if 'category' in df.columns:
                category_dist = df['category'].value_counts(normalize=True)
                max_concentration = category_dist.max()
                
                tests["SCRIPT_CATEGORY_DISTRIBUTION"] = {
                    "value": round(max_concentration, 3),
                    "passed": max_concentration < 0.8,  # Pas plus de 80% dans une catégorie
                    "message": f"Concentration max: {max_concentration:.1%} - " + 
                              ("OK" if max_concentration < 0.8 else "Trop concentré")
                }
    except:
        pass
    
    # Sortie JSON
    output = {"metrics": metrics, "tests": tests}
    print(json.dumps(output, indent=2))
    return 0

if __name__ == "__main__":
    sys.exit(main())
