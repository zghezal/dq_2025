"""
Script de démonstration - Création d'un nouveau canal programmatiquement

Ce script montre comment créer un canal de dépôt sans passer par l'interface.
Utile pour l'automatisation ou les tests.
"""

from src.core.channel_manager import get_channel_manager
from src.core.models_channels import (
    DropChannel, FileSpecification, EmailConfig, FileFormat
)
from datetime import datetime


def create_demo_channel():
    """Crée un canal de démonstration pour l'équipe RH"""
    
    print("=" * 60)
    print("Création d'un nouveau canal: RH Mensuel")
    print("=" * 60)
    
    # 1. Définir les fichiers attendus
    file_specs = [
        FileSpecification(
            file_id="employees_data",
            name="Données Employés",
            description="Fichier mensuel des employés actifs",
            format=FileFormat.CSV,
            required=True,
            expected_columns=["employee_id", "name", "department", "hire_date", "salary"]
        ),
        FileSpecification(
            file_id="absences_data",
            name="Données Absences",
            description="Fichier des absences du mois",
            format=FileFormat.CSV,
            required=False,
            expected_columns=["employee_id", "absence_date", "reason", "duration"]
        )
    ]
    
    # 2. Configuration email
    email_config = EmailConfig(
        recipient_team_emails=["rh@example.com", "admin-rh@example.com"],
        admin_emails=["dq-admin@example.com"],
        success_subject="✅ Dépôt RH validé - {channel_name}",
        success_body_template="""
Bonjour l'équipe RH,

Votre dépôt mensuel a été traité avec succès.

Résumé:
- Date de dépôt: {submission_date}
- Fichiers traités: {file_count}
- Contrôles qualité: {dq_passed}/{dq_total} réussis

Les données sont maintenant disponibles dans le système.

Cordialement,
L'équipe Data Quality
""",
        failure_subject="⚠️ Dépôt RH - Anomalies détectées - {channel_name}",
        failure_body_template="""
Bonjour l'équipe RH,

Votre dépôt mensuel a été traité mais des anomalies ont été détectées.

Résumé:
- Date de dépôt: {submission_date}
- Fichiers traités: {file_count}
- Contrôles qualité: {dq_passed}/{dq_total} réussis
- Anomalies: {dq_failed} contrôle(s) en échec

Merci de consulter le rapport détaillé et de corriger les données.

Cordialement,
L'équipe Data Quality
"""
    )
    
    # 3. Créer le canal
    channel = DropChannel(
        channel_id="rh_monthly",
        name="Dépôt RH Mensuel",
        description="Canal pour les données RH mensuelles (employés et absences)",
        team_name="Ressources Humaines",
        file_specifications=file_specs,
        dq_configs=[],  # Peut être ajouté plus tard via l'interface
        email_config=email_config,
        active=True,
        created_by="script_demo"
    )
    
    # 4. Sauvegarder via le manager
    manager = get_channel_manager()
    
    try:
        # Vérifier si le canal existe déjà
        existing = manager.get_channel("rh_monthly")
        if existing:
            print("\n⚠️  Le canal 'rh_monthly' existe déjà!")
            print("   Pour le recréer, supprimez-le d'abord via l'interface admin.")
            return False
        
        # Créer le canal
        created = manager.create_channel(channel)
        
        print(f"\n✅ Canal créé avec succès!")
        print(f"   ID: {created.channel_id}")
        print(f"   Nom: {created.name}")
        print(f"   Équipe: {created.team_name}")
        print(f"   Fichiers: {len(created.file_specifications)}")
        print(f"   Statut: {'Actif' if created.active else 'Inactif'}")
        print(f"   Créé le: {created.created_at}")
        
        print("\n📋 Fichiers attendus:")
        for spec in created.file_specifications:
            requis = "✅ Requis" if spec.required else "⭕ Optionnel"
            print(f"   • {spec.name} ({spec.format.value.upper()}) - {requis}")
            if spec.expected_columns:
                print(f"     Colonnes: {', '.join(spec.expected_columns)}")
        
        print("\n📧 Notifications:")
        print(f"   Équipe: {', '.join(created.email_config.recipient_team_emails)}")
        print(f"   Admins: {', '.join(created.email_config.admin_emails)}")
        
        print("\n" + "=" * 60)
        print("Le canal est maintenant disponible dans l'interface!")
        print("=" * 60)
        print("\n🌐 URLs:")
        print("   • Admin: http://localhost:5002/channel-admin")
        print("   • Dépôt: http://localhost:5002/channel-drop")
        
        return True
        
    except ValueError as e:
        print(f"\n❌ Erreur: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Erreur inattendue: {e}")
        return False


def list_all_channels():
    """Liste tous les canaux existants"""
    print("\n" + "=" * 60)
    print("Liste de tous les canaux")
    print("=" * 60)
    
    manager = get_channel_manager()
    channels = manager.list_channels()
    
    if not channels:
        print("\nℹ️  Aucun canal configuré")
        return
    
    print(f"\n📊 Total: {len(channels)} canal(aux)")
    
    for i, channel in enumerate(channels, 1):
        status = "✅ Actif" if channel.active else "❌ Inactif"
        print(f"\n{i}. {channel.name} ({channel.channel_id})")
        print(f"   Équipe: {channel.team_name}")
        print(f"   Statut: {status}")
        print(f"   Fichiers: {len(channel.file_specifications)}")
        print(f"   DQ configs: {len(channel.dq_configs)}")
        
        # Stats
        stats = manager.get_channel_statistics(channel.channel_id)
        print(f"   Soumissions: {stats['total_submissions']} (succès: {stats['success_rate']:.0f}%)")


if __name__ == "__main__":
    print("\n🚀 Démonstration - Création de Canal\n")
    
    # Créer le nouveau canal
    success = create_demo_channel()
    
    # Lister tous les canaux
    list_all_channels()
    
    if success:
        print("\n" + "=" * 60)
        print("✨ Démo terminée avec succès!")
        print("=" * 60)
        print("\n💡 Conseil: Vous pouvez maintenant:")
        print("   1. Voir le canal dans l'interface admin")
        print("   2. L'éditer pour ajouter des configs DQ")
        print("   3. L'utiliser pour déposer des fichiers")
        print("   4. Le désactiver/supprimer si nécessaire")
