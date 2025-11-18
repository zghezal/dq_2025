"""
Test simple: charger le DQ et vérifier qu'il détecte les erreurs
"""
import pandas as pd
from pathlib import Path

# Charger les données invalides
df_invalid = pd.read_csv('data/sales_invalid_upload.csv')
print("=== DONNÉES INVALIDES ===")
print(df_invalid)
print(f"\nStatistiques:")
print(f"  - Lignes: {len(df_invalid)}")
print(f"  - customer_id avec NaN: {df_invalid['customer_id'].isna().sum()}")
print(f"  - amount négatif: {(df_invalid['amount'] < 0).sum()}")
print(f"  - amount > 10000: {(df_invalid['amount'] > 10000).sum()}")
print(f"  - IDs dupliqués: {df_invalid['transaction_id'].duplicated().sum()}")

print("\n=== DONNÉES VALIDES ===")
df_valid = pd.read_csv('data/sales_valid_upload.csv')
print(df_valid)
print(f"\nStatistiques:")
print(f"  - Lignes: {len(df_valid)}")
print(f"  - customer_id avec NaN: {df_valid['customer_id'].isna().sum()}")
print(f"  - amount négatif: {(df_valid['amount'] < 0).sum()}")
print(f"  - amount > 10000: {(df_valid['amount'] > 10000).sum()}")
print(f"  - IDs dupliqués: {df_valid['transaction_id'].duplicated().sum()}")

print("\n=== CONCLUSION ===")
print("INVALIDE doit échouer:")
print("  ✓ 1 customer_id manquant (ligne 4)")
print("  ✓ 1 amount négatif (ligne 2: -250.00)")
print("  ✓ 1 amount > 10000 (ligne 3: 15000.00)")
print("  ✓ 1 ID dupliqué (TXN001 lignes 1 et 6)")
print("  Total: 4 erreurs attendues")

print("\nVALIDE doit réussir:")
print("  ✓ Pas de NaN")
print("  ✓ Pas de négatifs")
print("  ✓ Tous les amounts entre 0.01 et 10000")
print("  ✓ Pas de duplicatas")
