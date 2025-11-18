"""
Script de test pour vérifier que les canaux sont bien chargés et affichés
"""

from src.core.channel_manager import get_channel_manager

def test_channels():
    """Test que les canaux sont bien chargés"""
    print("=" * 60)
    print("TEST: Chargement des canaux")
    print("=" * 60)
    
    manager = get_channel_manager()
    
    # Lister tous les canaux
    channels = manager.list_channels()
    print(f"\n✓ Nombre total de canaux: {len(channels)}")
    
    # Lister les canaux actifs
    active_channels = manager.list_channels(active_only=True)
    print(f"✓ Nombre de canaux actifs: {len(active_channels)}")
    
    print("\n" + "=" * 60)
    print("Détails des canaux:")
    print("=" * 60)
    
    for channel in channels:
        print(f"\n📢 Canal: {channel.name}")
        print(f"   ID: {channel.channel_id}")
        print(f"   Équipe: {channel.team_name}")
        print(f"   Statut: {'✅ Actif' if channel.active else '❌ Inactif'}")
        print(f"   Description: {channel.description or 'Aucune'}")
        print(f"   Fichiers attendus: {len(channel.file_specifications)}")
        
        for spec in channel.file_specifications:
            requis = "Requis" if spec.required else "Optionnel"
            print(f"     • {spec.name} ({spec.format.value.upper()}) - {requis}")
        
        print(f"   Configs DQ: {len(channel.dq_configs)}")
        for dq in channel.dq_configs:
            print(f"     • {dq}")
        
        print(f"   Emails équipe: {', '.join(channel.email_config.recipient_team_emails)}")
        print(f"   Créé le: {channel.created_at}")
        
        # Stats
        stats = manager.get_channel_statistics(channel.channel_id)
        print(f"   Statistiques:")
        print(f"     - Total soumissions: {stats['total_submissions']}")
        print(f"     - Taux de succès: {stats['success_rate']:.1f}%")
    
    print("\n" + "=" * 60)
    print("TEST TERMINÉ")
    print("=" * 60)
    
    return len(channels) > 0


if __name__ == "__main__":
    success = test_channels()
    if success:
        print("\n✅ Les canaux sont bien chargés!")
        print("\nPour tester l'interface:")
        print("1. Ouvrez http://localhost:5002/channel-admin pour voir la liste des canaux")
        print("2. Ouvrez http://localhost:5002/channel-drop pour déposer des fichiers")
    else:
        print("\n❌ Aucun canal trouvé!")
