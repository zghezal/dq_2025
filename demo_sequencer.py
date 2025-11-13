"""
Démonstration simple du séquenceur DQ
"""

from src.core.dq_parser import load_dq_config
from src.core.sequencer import DQSequencer


def main():
    """Démo basique du séquenceur"""
    
    print("=" * 80)
    print("DÉMONSTRATION DU SÉQUENCEUR DQ")
    print("=" * 80)
    
    # Charger la config
    print("\n📝 Chargement de la configuration...")
    config = load_dq_config("dq/definitions/sales_complete_quality.yaml")
    print(f"   Config: {config.label}")
    print(f"   Métriques: {len(config.metrics)}")
    print(f"   Tests: {len(config.tests)}")
    
    # Construire la séquence
    print("\n🔄 Construction de la séquence d'exécution...")
    sequencer = DQSequencer(config)
    sequence = sequencer.build_sequence()
    
    # Afficher les résultats
    print("\n" + sequence.summary())
    print(sequencer.visualize_dependencies())
    
    print("\n✨ Démonstration terminée!")
    print("\nℹ️  Pour voir une démo avec filtres et tests implicites:")
    print("   python demo_sequencer_filters.py")


if __name__ == "__main__":
    main()
