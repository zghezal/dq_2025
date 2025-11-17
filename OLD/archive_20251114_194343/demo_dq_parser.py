"""
Exemple d'utilisation du parser DQ

Ce script montre comment utiliser le parser pour manipuler les configs DQ
"""

from src.core.dq_parser import load_dq_config, DQConfig
from pathlib import Path


def demo_parser():
    """Démonstration des capacités du parser"""
    
    print("=" * 80)
    print("DÉMONSTRATION DU PARSER DQ")
    print("=" * 80)
    
    # 1. Charger une configuration
    print("\n📂 1. CHARGEMENT D'UNE CONFIGURATION")
    print("-" * 80)
    
    config = load_dq_config("dq/definitions/sales_complete_quality.yaml")
    print(f"✅ Configuration chargée: {config.id}")
    print(f"   Label: {config.label}")
    print(f"   Metrics: {len(config.metrics)}")
    print(f"   Tests: {len(config.tests)}")
    
    # 2. Explorer le contexte
    print("\n🌍 2. CONTEXTE D'EXÉCUTION")
    print("-" * 80)
    
    if config.context:
        ctx = config.context
        print(f"   Stream:   {ctx.stream}")
        print(f"   Project:  {ctx.project}")
        print(f"   Zone:     {ctx.zone}")
        print(f"   DQ Point: {ctx.dq_point}")
    
    # 3. Lister les databases
    print("\n💾 3. DATABASES DISPONIBLES")
    print("-" * 80)
    
    for db in config.databases:
        print(f"   Alias: {db.alias:15} -> Dataset: {db.dataset or 'N/A'}")
    
    # 4. Explorer les métriques
    print("\n📊 4. MÉTRIQUES")
    print("-" * 80)
    
    for metric_id, metric in config.metrics.items():
        print(f"\n   [{metric_id}]")
        print(f"   Type: {metric.type}")
        
        if metric.nature:
            print(f"   Nom: {metric.nature.name}")
            if metric.nature.description:
                print(f"   Description: {metric.nature.description[:60]}...")
        
        if metric.general:
            print(f"   Export: {metric.general.export}")
            if metric.general.owner:
                print(f"   Owner: {metric.general.owner}")
        
        if metric.specific:
            spec = metric.specific
            if 'dataset' in spec:
                print(f"   Dataset: {spec['dataset']}")
            if 'column' in spec:
                print(f"   Column: {spec['column']}")
    
    # 5. Explorer les tests
    print("\n✅ 5. TESTS")
    print("-" * 80)
    
    for test_id, test in config.tests.items():
        print(f"\n   [{test_id}]")
        print(f"   Type: {test.type}")
        
        if test.nature:
            print(f"   Nom: {test.nature.name}")
            if test.nature.functional_category_1:
                print(f"   Catégorie: {test.nature.functional_category_1} / {test.nature.functional_category_2}")
        
        if test.general:
            print(f"   Sévérité: {test.general.severity}")
            print(f"   Stop on failure: {test.general.stop_on_failure}")
            print(f"   Action: {test.general.action_on_fail}")
            if test.general.associated_metric_id:
                print(f"   Métrique associée: {test.general.associated_metric_id}")
        
        if test.specific:
            spec = test.specific
            if 'target_mode' in spec:
                print(f"   Target mode: {spec['target_mode']}")
            if 'bounds' in spec:
                bounds = spec['bounds']
                print(f"   Bounds: [{bounds.get('lower', '-∞')}, {bounds.get('upper', '+∞')}]")
            if 'column_rules' in spec and spec['column_rules']:
                print(f"   Règles spécifiques par colonne: {len(spec['column_rules'])} règle(s)")
    
    # 6. Accès direct à des éléments
    print("\n🔍 6. ACCÈS DIRECT À DES ÉLÉMENTS")
    print("-" * 80)
    
    # Récupérer une métrique spécifique
    metric = config.get_metric("M_001_missing_date")
    if metric:
        print(f"\n   Métrique M_001_missing_date:")
        print(f"   - Type: {metric.type}")
        print(f"   - Dataset: {metric.specific.get('dataset')}")
        print(f"   - Column: {metric.specific.get('column')}")
    
    # Récupérer un test spécifique
    test = config.get_test("T_001_check_date_completeness")
    if test:
        print(f"\n   Test T_001_check_date_completeness:")
        print(f"   - Sévérité: {test.general.severity}")
        print(f"   - Métrique associée: {test.general.associated_metric_id}")
        print(f"   - Bornes: {test.specific.get('bounds')}")
    
    # Récupérer une database
    db = config.get_database("sales_2024")
    if db:
        print(f"\n   Database 'sales_2024':")
        print(f"   - Alias: {db.alias}")
        print(f"   - Dataset: {db.dataset}")
    
    # 7. Structure hiérarchique complète
    print("\n📋 7. STRUCTURE HIÉRARCHIQUE")
    print("-" * 80)
    print("\n   DQConfig")
    print("   ├── context (DQContext)")
    print("   ├── globals (DQGlobals)")
    print("   ├── databases (List[Database])")
    print("   ├── metrics (Dict[str, Metric])")
    print("   │   └── Metric")
    print("   │       ├── identification (MetricIdentification)")
    print("   │       ├── nature (MetricNature)")
    print("   │       ├── general (MetricGeneral)")
    print("   │       └── specific (Dict)")
    print("   └── tests (Dict[str, Test])")
    print("       └── Test")
    print("           ├── identification (TestIdentification)")
    print("           ├── nature (TestNature)")
    print("           ├── general (TestGeneral)")
    print("           └── specific (Dict)")
    
    # 8. Export de la config
    print("\n💾 8. EXPORT DE LA CONFIGURATION")
    print("-" * 80)
    
    # Exporter en JSON
    output_json = "dq/definitions/sales_complete_quality_export.json"
    config.to_json(output_json)
    print(f"   ✅ Exporté en JSON: {output_json}")
    
    # Exporter en YAML
    output_yaml = "dq/definitions/sales_complete_quality_export.yaml"
    config.to_yaml(output_yaml)
    print(f"   ✅ Exporté en YAML: {output_yaml}")
    
    # 9. Résumé
    print("\n" + "=" * 80)
    print(config.summary())
    print("=" * 80)
    
    print("\n✨ Démonstration terminée!")


if __name__ == "__main__":
    demo_parser()
