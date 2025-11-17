"""
Test de la validation avec un fichier YAML contenant des doublons
"""

from src.core.dq_parser import load_dq_config
from src.core.sequencer import DQSequencer


def main():
    print("=" * 80)
    print("TEST: Chargement d'un fichier YAML avec collision d'IDs")
    print("=" * 80)
    
    try:
        # Charger la config avec doublons
        print("\n📝 Chargement de test_duplicate_ids.yaml...")
        config = load_dq_config("dq/definitions/test_duplicate_ids.yaml")
        
        print(f"   Métriques chargées: {list(config.metrics.keys())}")
        print(f"   Tests chargés: {list(config.tests.keys())}")
        
        # Essayer de construire la séquence
        print("\n🔄 Construction de la séquence...")
        sequencer = DQSequencer(config)
        sequence = sequencer.build_sequence()
        
        print("\n❌ ERREUR: La validation n'a pas détecté la collision!")
        
    except ValueError as e:
        print(f"\n✅ Collision détectée correctement!")
        print(f"   Erreur: {e}")
    
    except Exception as e:
        print(f"\n⚠️  Autre erreur: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
