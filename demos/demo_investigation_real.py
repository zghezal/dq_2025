"""
Démonstration du système d'investigation avec les données réelles du projet
"""

import sys
from pathlib import Path
import pandas as pd

# Ajouter le repo au path
repo_root = Path(__file__).parent
sys.path.insert(0, str(repo_root))

from src.dq_runner import run_dq_config

print("=" * 80)
print("INVESTIGATION SUR DONNÉES RÉELLES - customers.csv")
print("=" * 80)
print()

# ============================================================================
# 1. CHARGER LES DONNÉES CUSTOMERS (avec erreurs intentionnelles)
# ============================================================================
print("📂 Chargement des données customers.csv")
print("-" * 80)

customers_path = Path("test_data/channels/customers.csv")
if not customers_path.exists():
    print(f"❌ Fichier non trouvé : {customers_path}")
    print("   Exécutez d'abord : python test_end_to_end_channels.py")
    sys.exit(1)

df = pd.read_csv(customers_path)
print(f"✅ {len(df)} lignes chargées")
print(f"   Colonnes : {list(df.columns)}")
print()

# Afficher quelques stats
print("📊 Statistiques des données :")
print(f"   - Total lignes : {len(df)}")
for col in df.columns:
    missing = df[col].isna().sum()
    if missing > 0:
        print(f"   - Missing '{col}' : {missing} ({missing/len(df)*100:.1f}%)")

# Compter les âges invalides
invalid_ages = (df['age'] < 18).sum() if 'age' in df.columns else 0
print(f"   - Âges < 18 : {invalid_ages}")
print()

# ============================================================================
# 2. DÉFINIR CONFIG DQ
# ============================================================================
print("📋 Définition des tests DQ")
print("-" * 80)

dq_config = {
    "id": "customers_quality_check",
    "metrics": [
        {
            "id": "email_missing_rate",
            "type": "missing_rate",
            "column": "email"
        },
        {
            "id": "invalid_ages_count",
            "type": "count_where",
            "filter": "age < 18"
        }
    ],
    "tests": [
        {
            "id": "test_email_completeness",
            "type": "range",
            "metric": "email_missing_rate",
            "low": 0,
            "high": 0.05,  # Max 5% autorisé
            "inclusive": True
        },
        {
            "id": "test_valid_ages",
            "type": "range",
            "metric": "invalid_ages_count",
            "low": 0,
            "high": 0,  # Aucun âge invalide autorisé
            "inclusive": True
        }
    ]
}

print(f"✅ Config DQ définie :")
print(f"   - {len(dq_config['metrics'])} métriques")
print(f"   - {len(dq_config['tests'])} tests")
print()

# ============================================================================
# 3. EXÉCUTION AVEC INVESTIGATION
# ============================================================================
print("🔍 Exécution avec investigation")
print("-" * 80)

results = run_dq_config(
    df, 
    dq_config, 
    investigate=True,
    investigation_dir="reports/investigations"
)

print("\n📊 Résultats :")
print("-" * 80)

print("\nMétriques :")
for metric_id, metric_result in results['metrics'].items():
    value = metric_result.get('value', 'N/A')
    print(f"  ✓ {metric_id}: {value}")

print("\nTests :")
failed_count = 0
for test_id, test_result in results['tests'].items():
    passed = test_result.get('passed', False)
    status = "✅ PASS" if passed else "❌ FAIL"
    message = test_result.get('message', '')
    print(f"  {status} {test_id}")
    if not passed:
        print(f"      → {message}")
        failed_count += 1

print()
print(f"Bilan : {len(results['tests']) - failed_count}/{len(results['tests'])} tests réussis")
print()

# ============================================================================
# 4. AFFICHER LES INVESTIGATIONS
# ============================================================================
if 'investigations' in results:
    print("=" * 80)
    print("🔍 INVESTIGATIONS GÉNÉRÉES")
    print("=" * 80)
    print()
    
    investigations = results['investigations']
    
    for i, inv in enumerate(investigations, 1):
        print(f"Investigation #{i} : {inv['test_id']}")
        print("-" * 80)
        print(f"  Type de métrique : {inv.get('metric_type', 'N/A')}")
        print(f"  Valeur : {inv.get('metric_value', 'N/A')}")
        
        if 'filter_condition' in inv:
            print(f"  Condition : {inv['filter_condition']}")
            print(f"  Lignes correspondantes : {inv.get('total_matching_rows', 'N/A')}")
        elif 'total_problematic_rows' in inv:
            print(f"  Lignes problématiques : {inv['total_problematic_rows']}")
        
        print(f"  Échantillon sauvegardé : {inv.get('sample_size', 0)} lignes")
        print(f"  Fichier : {Path(inv.get('sample_file', '')).name}")
        print()
    
    # Rapport consolidé
    if 'investigation_report' in results:
        report_path = Path(results['investigation_report'])
        print(f"📄 Rapport consolidé : {report_path.name}")
        print(f"   Chemin complet : {report_path}")
        print()
        
        # Afficher le contenu du rapport
        if report_path.exists():
            print("Contenu du rapport :")
            print("-" * 80)
            print(report_path.read_text(encoding="utf-8"))

else:
    print("✅ Aucune investigation nécessaire (tous les tests ont passé)")
    print()

print("=" * 80)
print("✅ DÉMONSTRATION TERMINÉE")
print("=" * 80)
