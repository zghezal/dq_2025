"""
Démonstration du système d'investigation DQ

Ce script montre comment l'investigation automatique génère des échantillons
de données problématiques lorsqu'un test DQ échoue.
"""

import sys
from pathlib import Path
import pandas as pd
import json

# Ajouter le repo au path
repo_root = Path(__file__).parent
sys.path.insert(0, str(repo_root))

from src.dq_runner import run_dq_config

print("=" * 80)
print("DÉMONSTRATION - INVESTIGATION AUTOMATIQUE DQ")
print("=" * 80)
print()

# ============================================================================
# 1. CRÉER DES DONNÉES AVEC PROBLÈMES DE QUALITÉ
# ============================================================================
print("📊 ÉTAPE 1 : Création de données avec problèmes de qualité")
print("-" * 80)

# Dataset avec problèmes variés
data = pd.DataFrame({
    'id': range(1, 51),
    'name': [f'Client_{i}' if i % 5 != 0 else None for i in range(1, 51)],  # 20% missing
    'email': [f'client{i}@example.com' if i % 7 != 0 else None for i in range(1, 51)],  # ~14% missing
    'age': [20 + i if i % 10 != 0 else -1 for i in range(1, 51)],  # Quelques valeurs invalides
    'revenue': [1000 + i * 10 if i % 3 != 0 else 0 for i in range(1, 51)],  # Quelques zéros
    'country': ['FR'] * 30 + ['US'] * 10 + ['UK'] * 5 + ['DE'] * 5
})

print(f"✅ Dataset créé : {len(data)} lignes, {len(data.columns)} colonnes")
print(f"   Colonnes : {list(data.columns)}")
print()

# Afficher quelques statistiques
print("📈 Statistiques :")
print(f"   - Missing 'name' : {data['name'].isna().sum()} lignes ({data['name'].isna().sum()/len(data)*100:.1f}%)")
print(f"   - Missing 'email' : {data['email'].isna().sum()} lignes ({data['email'].isna().sum()/len(data)*100:.1f}%)")
print(f"   - Âges négatifs : {(data['age'] < 0).sum()} lignes")
print(f"   - Revenue = 0 : {(data['revenue'] == 0).sum()} lignes")
print()

# ============================================================================
# 2. DÉFINIR UNE CONFIG DQ AVEC PLUSIEURS TESTS
# ============================================================================
print("📋 ÉTAPE 2 : Définition des tests DQ")
print("-" * 80)

dq_config = {
    "id": "demo_investigation",
    "metrics": [
        {
            "id": "name_missing_rate",
            "type": "missing_rate",
            "column": "name"
        },
        {
            "id": "email_missing_rate",
            "type": "missing_rate",
            "column": "email"
        },
        {
            "id": "invalid_ages",
            "type": "count_where",
            "filter": "age < 0"
        },
        {
            "id": "zero_revenues",
            "type": "count_where",
            "filter": "revenue == 0"
        }
    ],
    "tests": [
        {
            "id": "test_name_quality",
            "type": "range",
            "metric": "name_missing_rate",
            "low": 0,
            "high": 0.05,  # Max 5% autorisé, mais on a 20% donc FAIL
            "inclusive": True
        },
        {
            "id": "test_email_quality",
            "type": "range",
            "metric": "email_missing_rate",
            "low": 0,
            "high": 0.10,  # Max 10% autorisé, mais on a 14% donc FAIL
            "inclusive": True
        },
        {
            "id": "test_no_invalid_ages",
            "type": "range",
            "metric": "invalid_ages",
            "low": 0,
            "high": 0,  # Aucun âge invalide autorisé donc FAIL
            "inclusive": True
        },
        {
            "id": "test_no_zero_revenues",
            "type": "range",
            "metric": "zero_revenues",
            "low": 0,
            "high": 5,  # Max 5 zéros autorisés, on a plus donc FAIL
            "inclusive": True
        }
    ]
}

print(f"✅ Config DQ définie :")
print(f"   - {len(dq_config['metrics'])} métriques")
print(f"   - {len(dq_config['tests'])} tests")
for test in dq_config['tests']:
    print(f"     • {test['id']}")
print()

# ============================================================================
# 3. EXÉCUTER SANS INVESTIGATION (mode classique)
# ============================================================================
print("⚙️  ÉTAPE 3 : Exécution SANS investigation")
print("-" * 80)

results_no_inv = run_dq_config(data, dq_config, investigate=False)

print("📊 Résultats des métriques :")
for metric_id, metric_result in results_no_inv['metrics'].items():
    value = metric_result.get('value', 'N/A')
    print(f"   - {metric_id}: {value}")

print("\n🧪 Résultats des tests :")
for test_id, test_result in results_no_inv['tests'].items():
    passed = test_result.get('passed', False)
    status = "✅ PASS" if passed else "❌ FAIL"
    message = test_result.get('message', '')
    print(f"   {status} {test_id}")
    if not passed:
        print(f"      → {message}")

print()
print("⚠️  Mode classique : Aucun échantillon généré")
print()

# ============================================================================
# 4. EXÉCUTER AVEC INVESTIGATION
# ============================================================================
print("🔍 ÉTAPE 4 : Exécution AVEC investigation")
print("-" * 80)

results_with_inv = run_dq_config(
    data, 
    dq_config, 
    investigate=True,
    investigation_dir="reports/investigations"
)

print("📊 Résultats des métriques :")
for metric_id, metric_result in results_with_inv['metrics'].items():
    value = metric_result.get('value', 'N/A')
    print(f"   - {metric_id}: {value}")

print("\n🧪 Résultats des tests :")
failed_tests = []
for test_id, test_result in results_with_inv['tests'].items():
    passed = test_result.get('passed', False)
    status = "✅ PASS" if passed else "❌ FAIL"
    message = test_result.get('message', '')
    print(f"   {status} {test_id}")
    if not passed:
        print(f"      → {message}")
        failed_tests.append(test_id)

print()

# ============================================================================
# 5. AFFICHER LES INVESTIGATIONS
# ============================================================================
if 'investigations' in results_with_inv:
    print("=" * 80)
    print("🔍 INVESTIGATIONS GÉNÉRÉES")
    print("=" * 80)
    print()
    
    investigations = results_with_inv['investigations']
    print(f"Nombre d'investigations : {len(investigations)}")
    print()
    
    for i, inv in enumerate(investigations, 1):
        print(f"{i}. Investigation : {inv['test_id']}")
        print("-" * 80)
        print(f"   Type de métrique : {inv.get('metric_type', 'N/A')}")
        print(f"   Valeur métrique : {inv.get('metric_value', 'N/A')}")
        
        if 'total_problematic_rows' in inv:
            print(f"   Lignes problématiques : {inv['total_problematic_rows']}")
        
        if 'total_matching_rows' in inv:
            print(f"   Lignes correspondantes : {inv['total_matching_rows']}")
        
        if 'filter_condition' in inv:
            print(f"   Condition : {inv['filter_condition']}")
        
        print(f"   Échantillon : {inv.get('sample_size', 0)} lignes")
        print(f"   Fichier : {inv.get('sample_file', 'N/A')}")
        print(f"   Description : {inv.get('description', 'N/A')}")
        print()
    
    # Rapport consolidé
    if 'investigation_report' in results_with_inv:
        print("📄 Rapport consolidé généré :")
        print(f"   {results_with_inv['investigation_report']}")
        print()

else:
    print("⚠️  Aucune investigation générée (tous les tests ont passé ou erreur)")
    print()

# ============================================================================
# 6. AFFICHER LE CONTENU D'UN ÉCHANTILLON
# ============================================================================
if 'investigations' in results_with_inv and len(results_with_inv['investigations']) > 0:
    print("=" * 80)
    print("📁 APERÇU D'UN ÉCHANTILLON")
    print("=" * 80)
    print()
    
    # Prendre la première investigation
    first_inv = results_with_inv['investigations'][0]
    sample_file = first_inv.get('sample_file')
    
    if sample_file and Path(sample_file).exists():
        print(f"Fichier : {sample_file}")
        print()
        
        # Lire et afficher les premières lignes
        sample_df = pd.read_csv(sample_file)
        print(f"Contenu ({len(sample_df)} lignes) :")
        print()
        print(sample_df.head(10).to_string())
        print()
        if len(sample_df) > 10:
            print(f"... et {len(sample_df) - 10} lignes supplémentaires")
            print()

# ============================================================================
# 7. RÉSUMÉ
# ============================================================================
print("=" * 80)
print("📊 RÉSUMÉ")
print("=" * 80)
print()

print("Avant investigation :")
print(f"  - Métriques calculées : {len(results_no_inv['metrics'])}")
print(f"  - Tests exécutés : {len(results_no_inv['tests'])}")
print(f"  - Fichiers générés : 0")
print()

print("Avec investigation :")
print(f"  - Métriques calculées : {len(results_with_inv['metrics'])}")
print(f"  - Tests exécutés : {len(results_with_inv['tests'])}")
if 'investigations' in results_with_inv:
    print(f"  - Investigations : {len(results_with_inv['investigations'])}")
    print(f"  - Fichiers CSV générés : {len(results_with_inv['investigations'])}")
    print(f"  - Rapport consolidé : 1")
else:
    print(f"  - Investigations : 0")
print()

print("📁 Tous les fichiers sont dans : reports/investigations/")
print()

print("=" * 80)
print("✅ DÉMONSTRATION TERMINÉE")
print("=" * 80)
print()
print("💡 Avantages de l'investigation automatique :")
print("   1. Identification immédiate des lignes problématiques")
print("   2. Gain de temps d'analyse (pas besoin de requêter manuellement)")
print("   3. Échantillons prêts à partager avec les équipes métier")
print("   4. Traçabilité complète (fichiers horodatés)")
print()
