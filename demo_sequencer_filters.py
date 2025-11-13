"""
Démonstration du séquenceur avec filtres

Ce script montre le séquenceur en action avec des tests qui utilisent des filtres,
déclenchant la génération de tests implicites.
"""

from src.core.dq_parser import DQConfig, load_dq_config
from src.core.sequencer import build_execution_sequence, DQSequencer


def create_config_with_filters():
    """Crée une config avec des tests utilisant des filtres"""
    # Charger la config de base
    config = load_dq_config("dq/definitions/sales_complete_quality.yaml")
    
    # Ajouter manuellement un test avec filtre pour la démo
    from src.core.dq_parser import Test, TestIdentification, TestNature, TestGeneral
    
    # Test avec filtre: vérifier les montants pour la région North seulement
    test_with_filter = Test(
        test_id="T_007_check_amounts_north_region",
        type="interval_check",
        identification=TestIdentification(
            test_id="T_007_check_amounts_north_region",
            control_name="Amount validation for North region",
            control_id="CTRL_007"
        ),
        nature=TestNature(
            name="Validation montants région North",
            description="Vérifie que les montants de la région North sont dans la plage valide",
            functional_category_1="Cohérence",
            functional_category_2="Données régionales",
            category="business_rule"
        ),
        general=TestGeneral(
            severity="medium",
            stop_on_failure=False,
            action_on_fail="alert"
        ),
        specific={
            'value_from_dataset': 'sales_2024',
            'target_mode': 'dataset',
            'where': "region = 'North' AND date > '2024-01-01'",  # FILTRE!
            'bounds': {
                'lower': 50,
                'upper': 300
            },
            'column_rules': []
        }
    )
    
    # Test avec filtre complexe
    test_with_complex_filter = Test(
        test_id="T_008_check_high_value_products",
        type="interval_check",
        identification=TestIdentification(
            test_id="T_008_check_high_value_products",
            control_name="High value products validation",
            control_id="CTRL_008"
        ),
        nature=TestNature(
            name="Validation produits haute valeur",
            description="Vérifie les quantités pour les produits à haute valeur",
            functional_category_1="Cohérence",
            functional_category_2="Produits premium",
            category="business_rule"
        ),
        general=TestGeneral(
            severity="high",
            stop_on_failure=False,
            action_on_fail="alert"
        ),
        specific={
            'value_from_dataset': 'sales_2024',
            'target_mode': 'dataset',
            'where': "amount > 200 AND product_id LIKE 'P%' AND quantity >= 5",  # FILTRE COMPLEXE!
            'bounds': {
                'lower': 5,
                'upper': 50
            },
            'column_rules': []
        }
    )
    
    # Ajouter les tests à la config
    config.tests[test_with_filter.test_id] = test_with_filter
    config.tests[test_with_complex_filter.test_id] = test_with_complex_filter
    
    return config


def demo_sequencer():
    """Démonstration complète du séquenceur"""
    
    print("=" * 80)
    print("DÉMONSTRATION DU SÉQUENCEUR DQ AVEC FILTRES")
    print("=" * 80)
    
    # Créer une config avec filtres
    print("\n📝 Création d'une configuration avec tests filtrés...")
    config = create_config_with_filters()
    print(f"   Métriques: {len(config.metrics)}")
    print(f"   Tests: {len(config.tests)}")
    
    # Afficher les tests avec filtres
    print("\n🔍 Tests avec filtres détectés:")
    for test_id, test in config.tests.items():
        if test.specific and test.specific.get('where'):
            print(f"   - {test_id}")
            print(f"     Filtre: {test.specific['where']}")
    
    # Construire la séquence
    print("\n" + "=" * 80)
    sequencer = DQSequencer(config)
    sequence = sequencer.build_sequence()
    
    # Afficher le résumé
    print("\n" + sequence.summary())
    
    # Afficher les détails des tests implicites
    print("\n" + "=" * 80)
    print("DÉTAILS DES TESTS IMPLICITES GÉNÉRÉS")
    print("=" * 80)
    
    implicit_tests = [cmd for cmd in sequence.commands if cmd.command_type.value == 'implicit_test']
    
    if implicit_tests:
        for implicit in implicit_tests:
            print(f"\n📌 {implicit.command_id}")
            print(f"   Type: {implicit.implicit_type.value}")
            print(f"   Généré pour: {implicit.parent_test_id}")
            print(f"   Dataset: {implicit.parameters.get('dataset')}")
            
            if 'required_columns' in implicit.parameters:
                print(f"   Colonnes requises: {implicit.parameters['required_columns']}")
            elif 'columns' in implicit.parameters:
                print(f"   Colonnes à vérifier: {implicit.parameters['columns']}")
            
            print(f"   Description: {implicit.metadata.get('description')}")
    else:
        print("\nℹ️  Aucun test implicite généré")
    
    # Afficher le graphe de dépendances
    print(sequencer.visualize_dependencies())
    
    # Afficher l'ordre d'exécution détaillé
    print("\n" + "=" * 80)
    print("ORDRE D'EXÉCUTION DÉTAILLÉ")
    print("=" * 80)
    
    for i, cmd_id in enumerate(sequence.execution_order, 1):
        cmd = sequence.get_command(cmd_id)
        if cmd:
            print(f"\n{i:2d}. {cmd.command_id}")
            print(f"    Type: {cmd.command_type.value} ({cmd.element_type})")
            
            if cmd.dependencies:
                print(f"    Dépendances: {', '.join(cmd.dependencies)}")
            
            # Afficher des infos spécifiques selon le type
            if cmd.command_type.value == 'metric':
                dataset = cmd.parameters.get('dataset')
                column = cmd.parameters.get('column')
                if dataset:
                    print(f"    Dataset: {dataset}")
                if column:
                    print(f"    Column: {column}")
            
            elif cmd.command_type.value == 'test':
                bounds = cmd.parameters.get('bounds')
                where = cmd.parameters.get('where')
                if bounds:
                    print(f"    Bounds: [{bounds.get('lower')}, {bounds.get('upper')}]")
                if where:
                    print(f"    Filtre: {where}")
            
            elif cmd.command_type.value == 'implicit_test':
                print(f"    Type implicite: {cmd.implicit_type.value}")
                print(f"    Parent: {cmd.parent_test_id}")
    
    print("\n" + "=" * 80)
    print("✨ Démonstration terminée!")
    print("=" * 80)


if __name__ == "__main__":
    demo_sequencer()
