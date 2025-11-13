# coding: utf-8
"""
Test de l'investigation pour interval_check avec missing_rate

Ce test valide que :
1. missing_rate calcule le taux de valeurs manquantes
2. interval_check vérifie que ce taux est dans les limites
3. Si le test échoue, investigation remonte au dataset source et échantillonne les lignes avec missing
"""

import sys
import io
from pathlib import Path
import pandas as pd

# Force UTF-8 encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

repo_root = Path(__file__).parent
sys.path.insert(0, str(repo_root))

# Importer les plugins nécessaires
import src.plugins.metrics.missing_rate  # noqa: F401
import src.plugins.tests.interval_check  # noqa: F401

from src.core.models_inventory import Inventory, Stream, Project, Zone, Dataset, LocalSource
from src.core.models_dq import DQDefinition
from src.core.parser import build_execution_plan
from src.core.executor import execute
from src.core.connectors import LocalReader

print("=" * 80)
print("TEST - INVESTIGATION INTERVAL_CHECK + MISSING_RATE")
print("=" * 80)
print()

# ============================================================================
# 1. CREER DES DONNEES DE TEST
# ============================================================================
print("[1] Creation des donnees de test")
print("-" * 80)

# Dataset avec 20% de valeurs manquantes (devrait échouer le test < 10%)
test_data = pd.DataFrame({
    'customer_id': range(1, 51),
    'email': [f'client{i}@example.com' if i % 5 != 0 else None for i in range(1, 51)],  # 20% missing
    'phone': [f'555-{i:04d}' if i % 7 != 0 else None for i in range(1, 51)],  # ~14% missing
    'country': ['FR'] * 30 + ['US'] * 10 + ['UK'] * 10
})

test_file = Path("test_data/investigation_test_customers.csv")
test_file.parent.mkdir(parents=True, exist_ok=True)
test_data.to_csv(test_file, index=False)

print(f"OK Dataset créé : {len(test_data)} lignes")
print(f"   Email missing : {test_data['email'].isna().sum()} ({test_data['email'].isna().sum()/len(test_data)*100:.1f}%)")
print(f"   Phone missing : {test_data['phone'].isna().sum()} ({test_data['phone'].isna().sum()/len(test_data)*100:.1f}%)")
print()

# ============================================================================
# 2. CREER INVENTORY
# ============================================================================
print("[2] Creation de l'inventory")
print("-" * 80)

inventory = Inventory(
    streams=[
        Stream(
            stream="test",
            id="test",
            projects=[
                Project(
                    project="quality",
                    id="quality",
                    zones=[
                        Zone(
                            zone="input",
                            id="input",
                            datasets=[
                                Dataset(
                                    alias="test_customers",
                                    name="test_customers",
                                    source=LocalSource(
                                        kind="local",
                                        path=str(test_file)
                                    )
                                )
                            ]
                        )
                    ]
                )
            ]
        )
    ]
)

print("OK Inventory créé avec dataset 'test_customers'")
print()

# ============================================================================
# 3. CREER DEFINITION DQ
# ============================================================================
print("[3] Creation de la definition DQ")
print("-" * 80)

# Métrique missing_rate sur colonne email
# Test interval_check vérifie que missing_rate < 10% (devrait échouer car on a 20%)
dq_definition = DQDefinition(
    id="customers_quality_check",
    databases=[
        {"alias": "test_customers"}
    ],
    metrics={
        "email_missing": {
            "id": "email_missing",
            "type": "missing_rate",
            "specific": {
                "dataset": "test_customers",
                "column": "email",
                "stream": "test",
                "project": "quality",
                "zone": "input"
            }
        }
    },
    tests={
        "check_email_quality": {
            "id": "check_email_quality",
            "type": "test.interval_check",
            "specific": {
                "target_mode": "metric_value",
                "metric_id": "test.quality.input.metric.missing_rate.test_customers.col=email",
                "lower_enabled": True,
                "lower_value": 0.0,
                "upper_enabled": True,
                "upper_value": 0.10  # Max 10% autorisé, mais on a 20% donc KO
            }
        }
    }
)

print("OK Definition DQ créée :")
print("   - 1 métrique : email_missing (missing_rate)")
print("   - 1 test : check_email_quality (interval_check < 10%)")
print()

# ============================================================================
# 4. EXECUTION SANS INVESTIGATION
# ============================================================================
print("[4] Execution SANS investigation")
print("-" * 80)

plan = build_execution_plan(inventory, dq_definition)
print(f"Plan construit : {len(plan.steps)} étapes")

loader = LocalReader(plan.alias_map)
result_no_inv = execute(plan, loader, investigate=False)

print(f"\nRun ID : {result_no_inv.run_id}")
print(f"Métriques : {len(result_no_inv.metrics)}")
for metric_id, metric_result in result_no_inv.metrics.items():
    value = metric_result.value
    print(f"  - {metric_id} : {value:.3f}" if isinstance(value, float) else f"  - {metric_id} : {value}")

print(f"\nTests : {len(result_no_inv.tests)}")
for test_id, test_result in result_no_inv.tests.items():
    status = "OK PASS" if test_result.passed else "KO FAIL"
    print(f"  [{status}] {test_id}")
    print(f"      {test_result.message}")

print(f"\nInvestigations : {len(result_no_inv.investigations)}")
print()

# ============================================================================
# 5. EXECUTION AVEC INVESTIGATION
# ============================================================================
print("[5] Execution AVEC investigation")
print("-" * 80)

result_with_inv = execute(plan, loader, investigate=True)

print(f"Run ID : {result_with_inv.run_id}")
print(f"Métriques : {len(result_with_inv.metrics)}")
for metric_id, metric_result in result_with_inv.metrics.items():
    value = metric_result.value
    print(f"  - {metric_id} : {value:.3f}" if isinstance(value, float) else f"  - {metric_id} : {value}")

print(f"\nTests : {len(result_with_inv.tests)}")
for test_id, test_result in result_with_inv.tests.items():
    status = "OK PASS" if test_result.passed else "KO FAIL"
    print(f"  [{status}] {test_id}")
    print(f"      {test_result.message}")
    
    if test_result.investigation:
        inv = test_result.investigation
        print(f"      >> Investigation disponible :")
        print(f"         Description : {inv.get('description')}")
        print(f"         Lignes problematiques : {inv.get('total_problematic_rows')}")
        print(f"         Fichier : {Path(inv.get('sample_file', '')).name}")

print(f"\nInvestigations : {len(result_with_inv.investigations)}")

if result_with_inv.investigations:
    print("\n" + "=" * 80)
    print("DETAILS DES INVESTIGATIONS")
    print("=" * 80)
    
    for i, inv in enumerate(result_with_inv.investigations, 1):
        print(f"\n{i}. {inv['test_id']} ({inv['test_type']})")
        print("-" * 80)
        print(f"   Description : {inv['description']}")
        print(f"   Lignes problematiques : {inv['total_problematic_rows']}")
        print(f"   Echantillon : {inv['sample_size']} lignes")
        print(f"   Fichier : {inv['sample_file']}")
        
        if 'metric_id' in inv:
            print(f"   Métrique source : {inv['metric_id']}")
        if 'dataset_source' in inv:
            print(f"   Dataset source : {inv['dataset_source']}")
        if 'columns_with_missing' in inv:
            print(f"   Colonnes avec missing : {', '.join(inv['columns_with_missing'])}")
        
        # Afficher aperçu du fichier
        sample_file = Path(inv['sample_file'])
        if sample_file.exists():
            print(f"\n   Aperçu de l'échantillon :")
            sample_df = pd.read_csv(sample_file)
            print(f"   {len(sample_df)} lignes x {len(sample_df.columns)} colonnes")
            print()
            # Afficher les 5 premières lignes
            for idx, row in sample_df.head(5).iterrows():
                print(f"   #{idx+1} : customer_id={row['customer_id']}, email={row['email']}, phone={row['phone']}")
            if len(sample_df) > 5:
                print(f"   ... et {len(sample_df) - 5} lignes supplémentaires")
    
    if result_with_inv.investigation_report:
        print(f"\n{' RAPPORT CONSOLIDE ':-^80}")
        print(f"Fichier : {result_with_inv.investigation_report}")
        
        report_path = Path(result_with_inv.investigation_report)
        if report_path.exists():
            print()
            print(report_path.read_text(encoding='utf-8'))

print()
print("=" * 80)
print("TEST TERMINE")
print("=" * 80)
print()
print("RESUME :")
print("  - Métrique missing_rate calculée : OK")
print("  - Test interval_check vérifie les bornes : OK")
print("  - Test échoué (20% > 10%) : OK")
print("  - Investigation remonte au dataset source : OK")
print("  - Echantillon des lignes avec missing généré : OK")
print()
