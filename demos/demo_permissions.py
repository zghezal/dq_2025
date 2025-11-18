"""
Script de démonstration du système de permissions des canaux

Ce script montre comment:
1. Créer des canaux publics et privés
2. Définir des permissions (utilisateurs et groupes)
3. Filtrer les canaux selon l'utilisateur connecté
"""

from src.core.channel_manager import get_channel_manager
from src.core.models_channels import (
    DropChannel, FileSpecification, EmailConfig, FileFormat
)


def demo_permissions():
    """Démonstration complète du système de permissions"""
    
    print("=" * 70)
    print("DÉMONSTRATION - Système de Permissions des Canaux")
    print("=" * 70)
    
    manager = get_channel_manager()
    
    # 1. Créer un canal PRIVÉ pour Finance
    print("\n📌 Étape 1: Création d'un canal PRIVÉ pour Finance")
    print("-" * 70)
    
    finance_private_channel = DropChannel(
        channel_id="finance_private",
        name="Finance - Données Confidentielles",
        description="Canal privé réservé à l'équipe Finance pour données sensibles",
        team_name="Finance",
        is_public=False,  # ← PRIVÉ
        allowed_users=["jean.dupont@finance.com", "marie.martin@finance.com"],
        allowed_groups=["Finance", "Direction"],
        file_specifications=[
            FileSpecification(
                file_id="salaries",
                name="Salaires",
                format=FileFormat.CSV,
                required=True
            )
        ],
        email_config=EmailConfig(
            recipient_team_emails=["finance@example.com"]
        ),
        active=True
    )
    
    try:
        existing = manager.get_channel("finance_private")
        if existing:
            manager.delete_channel("finance_private")
        manager.create_channel(finance_private_channel)
        print("✅ Canal privé 'Finance - Données Confidentielles' créé")
        print(f"   • Utilisateurs autorisés: {', '.join(finance_private_channel.allowed_users)}")
        print(f"   • Groupes autorisés: {', '.join(finance_private_channel.allowed_groups)}")
    except Exception as e:
        print(f"❌ Erreur: {e}")
    
    # 2. Créer un canal PRIVÉ pour RH
    print("\n📌 Étape 2: Création d'un canal PRIVÉ pour RH")
    print("-" * 70)
    
    rh_private_channel = DropChannel(
        channel_id="rh_confidential",
        name="RH - Recrutement Confidentiel",
        description="Canal privé pour données RH sensibles",
        team_name="Ressources Humaines",
        is_public=False,  # ← PRIVÉ
        allowed_users=["sophie.rh@example.com", "paul.recruteur@example.com"],
        allowed_groups=["RH", "Direction"],
        file_specifications=[
            FileSpecification(
                file_id="candidates",
                name="Candidats",
                format=FileFormat.EXCEL,
                required=True
            )
        ],
        email_config=EmailConfig(
            recipient_team_emails=["rh@example.com"]
        ),
        active=True
    )
    
    try:
        existing = manager.get_channel("rh_confidential")
        if existing:
            manager.delete_channel("rh_confidential")
        manager.create_channel(rh_private_channel)
        print("✅ Canal privé 'RH - Recrutement Confidentiel' créé")
        print(f"   • Utilisateurs autorisés: {', '.join(rh_private_channel.allowed_users)}")
        print(f"   • Groupes autorisés: {', '.join(rh_private_channel.allowed_groups)}")
    except Exception as e:
        print(f"❌ Erreur: {e}")
    
    # 3. Les canaux existants (marketing, rh_monthly) restent publics par défaut
    print("\n📌 Étape 3: Canaux publics existants")
    print("-" * 70)
    all_channels = manager.list_channels()
    public_channels = [c for c in all_channels if c.is_public]
    print(f"✅ {len(public_channels)} canal(aux) public(s) trouvé(s):")
    for ch in public_channels:
        print(f"   • {ch.name} ({ch.channel_id})")
    
    # 4. Tester le filtrage pour différents utilisateurs
    print("\n" + "=" * 70)
    print("TEST DE FILTRAGE PAR UTILISATEUR")
    print("=" * 70)
    
    test_users = [
        {
            "name": "Jean Dupont (Finance)",
            "email": "jean.dupont@finance.com",
            "groups": ["Finance"]
        },
        {
            "name": "Sophie RH",
            "email": "sophie.rh@example.com",
            "groups": ["RH"]
        },
        {
            "name": "Pierre Marketing",
            "email": "pierre@marketing.com",
            "groups": ["Marketing"]
        },
        {
            "name": "Directeur Général",
            "email": "dg@example.com",
            "groups": ["Direction"]
        },
        {
            "name": "Utilisateur Externe",
            "email": "externe@autre.com",
            "groups": []
        }
    ]
    
    for user in test_users:
        print(f"\n👤 Utilisateur: {user['name']}")
        print(f"   Email: {user['email']}")
        print(f"   Groupes: {', '.join(user['groups']) if user['groups'] else 'Aucun'}")
        print(f"   Canaux accessibles:")
        
        accessible_channels = manager.list_channels(
            active_only=True,
            user_email=user['email'],
            user_groups=user['groups']
        )
        
        if accessible_channels:
            for ch in accessible_channels:
                access_type = "🌐 Public" if ch.is_public else "🔒 Privé (autorisé)"
                print(f"      • {access_type} - {ch.name}")
        else:
            print("      ⚠️  Aucun canal accessible")
    
    # 5. Résumé
    print("\n" + "=" * 70)
    print("RÉSUMÉ")
    print("=" * 70)
    
    all_channels = manager.list_channels()
    public_count = sum(1 for c in all_channels if c.is_public)
    private_count = sum(1 for c in all_channels if not c.is_public)
    
    print(f"\n📊 Total des canaux: {len(all_channels)}")
    print(f"   • 🌐 Publics: {public_count}")
    print(f"   • 🔒 Privés: {private_count}")
    
    print("\n💡 Points clés:")
    print("   1. Les canaux PUBLICS sont visibles par tous")
    print("   2. Les canaux PRIVÉS sont visibles uniquement par:")
    print("      - Les utilisateurs dans 'allowed_users'")
    print("      - Les membres des groupes dans 'allowed_groups'")
    print("   3. Les admins voient tous les canaux dans l'interface admin")
    print("   4. Les utilisateurs ne voient que leurs canaux autorisés dans le dropdown")
    
    print("\n" + "=" * 70)
    print("✨ Démonstration terminée!")
    print("=" * 70)
    
    print("\n🌐 Pour tester dans l'interface:")
    print("   • Admin: http://localhost:5002/channel-admin")
    print("   • Drop: http://localhost:5002/channel-drop")
    print("\n📝 Note: Dans une vraie application, l'email/groupes de l'utilisateur")
    print("   viendraient de l'authentification (SSO, LDAP, etc.)")


if __name__ == "__main__":
    demo_permissions()
