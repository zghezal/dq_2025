"""
Démonstration du système de canaux de dépôt

Ce script montre comment:
1. Créer des canaux
2. Soumettre des données
3. Traiter automatiquement
4. Générer des rapports
"""

import sys
from pathlib import Path
from datetime import datetime
import uuid

# Ajouter le répertoire racine au path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.models_channels import (
    DropChannel, FileSpecification, EmailConfig, FileFormat,
    ChannelSubmission, FileMapping, SubmissionStatus
)
from src.core.channel_manager import ChannelManager
from src.core.submission_processor import SubmissionProcessor


def demo_create_channels():
    """Crée des canaux d'exemple"""
    
    print("=" * 80)
    print("CRÉATION DE CANAUX D'EXEMPLE")
    print("=" * 80)
    
    manager = ChannelManager()
    
    # Canal 1: Finance mensuel
    print("\n📡 Création du canal Finance...")
    
    finance_channel = DropChannel(
        channel_id="finance_monthly",
        name="Dépôt Finance Mensuel",
        description="Canal pour les données financières mensuelles de l'équipe Finance",
        team_name="Finance",
        file_specifications=[
            FileSpecification(
                file_id="sales_data",
                name="Données de Ventes",
                description="Fichier contenant toutes les transactions de vente du mois",
                format=FileFormat.CSV,
                required=True,
                expected_columns=["date", "amount", "product_id", "customer_id"]
            ),
            FileSpecification(
                file_id="refunds_data",
                name="Données de Remboursements",
                description="Fichier des remboursements effectués",
                format=FileFormat.CSV,
                required=False,
                expected_columns=["date", "amount", "order_id", "reason"]
            )
        ],
        dq_configs=[
            "dq/definitions/sales_complete_quality.yaml"
        ],
        email_config=EmailConfig(
            recipient_team_emails=["finance@example.com"],
            admin_emails=["dq-admin@example.com"]
        )
    )
    
    try:
        manager.create_channel(finance_channel)
        print(f"  ✅ Canal créé: {finance_channel.name}")
        print(f"     ID: {finance_channel.channel_id}")
        print(f"     Fichiers attendus: {len(finance_channel.file_specifications)}")
        print(f"     Configs DQ: {len(finance_channel.dq_configs)}")
    except Exception as e:
        print(f"  ⚠️  Canal existe déjà ou erreur: {e}")
    
    # Canal 2: Marketing hebdomadaire
    print("\n📡 Création du canal Marketing...")
    
    marketing_channel = DropChannel(
        channel_id="marketing_weekly",
        name="Dépôt Marketing Hebdomadaire",
        description="Canal pour les KPIs marketing hebdomadaires",
        team_name="Marketing",
        file_specifications=[
            FileSpecification(
                file_id="campaigns_data",
                name="Données Campagnes",
                description="Métriques des campagnes marketing",
                format=FileFormat.EXCEL,
                required=True,
                expected_columns=["campaign_id", "impressions", "clicks", "conversions", "cost"]
            )
        ],
        dq_configs=[],  # Pas de DQ pour l'exemple
        email_config=EmailConfig(
            recipient_team_emails=["marketing@example.com"],
            admin_emails=["dq-admin@example.com"]
        )
    )
    
    try:
        manager.create_channel(marketing_channel)
        print(f"  ✅ Canal créé: {marketing_channel.name}")
    except Exception as e:
        print(f"  ⚠️  Canal existe déjà ou erreur: {e}")
    
    # Lister tous les canaux
    print("\n📋 Canaux actifs:")
    channels = manager.list_channels(active_only=True)
    for channel in channels:
        print(f"  • {channel.name} ({channel.channel_id}) - Équipe: {channel.team_name}")


def demo_submit_data():
    """Simule une soumission de données"""
    
    print("\n" + "=" * 80)
    print("SOUMISSION DE DONNÉES")
    print("=" * 80)
    
    manager = ChannelManager()
    
    # Créer une soumission pour le canal Finance
    submission_id = f"sub_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    
    print(f"\n📤 Création de la soumission {submission_id}...")
    
    submission = ChannelSubmission(
        submission_id=submission_id,
        channel_id="finance_monthly",
        submitted_by="jean.dupont@finance.example.com",
        file_mappings=[
            FileMapping(
                file_spec_id="sales_data",
                provided_path="sourcing/input/sales_2024.csv",  # Utiliser fichier existant
                provided_name="sales_2024.csv"
            ),
            FileMapping(
                file_spec_id="refunds_data",
                provided_path="sourcing/input/refunds.csv",
                provided_name="refunds.csv"
            )
        ]
    )
    
    try:
        manager.create_submission(submission)
        print(f"  ✅ Soumission créée")
        print(f"     ID: {submission.submission_id}")
        print(f"     Canal: {submission.channel_id}")
        print(f"     Fichiers: {len(submission.file_mappings)}")
        print(f"     Par: {submission.submitted_by}")
        
        return submission
        
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
        return None


def demo_process_submission(submission: ChannelSubmission):
    """Traite une soumission"""
    
    print("\n" + "=" * 80)
    print("TRAITEMENT AUTOMATIQUE")
    print("=" * 80)
    
    manager = ChannelManager()
    processor = SubmissionProcessor(manager)
    
    print(f"\n⚙️  Traitement de la soumission {submission.submission_id}...")
    print(f"   Statut initial: {submission.status.value}")
    
    # Traiter
    processed = processor.process_submission(submission)
    
    print(f"\n✅ Traitement terminé!")
    print(f"   Statut final: {processed.status.value}")
    print(f"   Durée: {(processed.processing_completed_at - processed.processing_started_at).total_seconds():.2f}s")
    print(f"\n📊 Résultats DQ:")
    print(f"   Total: {processed.dq_total}")
    print(f"   Réussis: {processed.dq_passed}")
    print(f"   Échoués: {processed.dq_failed}")
    print(f"   Ignorés: {processed.dq_skipped}")
    
    if processed.dq_report_path:
        print(f"\n📄 Rapport généré: {processed.dq_report_path}")
    
    if processed.email_sent:
        print(f"📧 Email envoyé à: {processed.email_sent_at}")
    
    if processed.errors:
        print(f"\n⚠️  Erreurs:")
        for error in processed.errors:
            print(f"   • {error}")


def demo_list_submissions():
    """Liste les soumissions"""
    
    print("\n" + "=" * 80)
    print("HISTORIQUE DES SOUMISSIONS")
    print("=" * 80)
    
    manager = ChannelManager()
    
    submissions = manager.list_submissions(limit=10)
    
    print(f"\n📋 {len(submissions)} soumissions récentes:")
    
    for sub in submissions:
        status_icon = {
            'pending': '⏳',
            'processing': '⚙️ ',
            'dq_success': '✅',
            'dq_failed': '⚠️ ',
            'error': '❌'
        }.get(sub.status.value, '❓')
        
        print(f"\n  {status_icon} {sub.submission_id}")
        print(f"     Canal: {sub.channel_id}")
        print(f"     Date: {sub.submitted_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"     Par: {sub.submitted_by}")
        print(f"     Statut: {sub.status.value}")
        if sub.dq_total > 0:
            print(f"     DQ: {sub.dq_passed}/{sub.dq_total} réussis")


def demo_channel_statistics():
    """Affiche les statistiques des canaux"""
    
    print("\n" + "=" * 80)
    print("STATISTIQUES DES CANAUX")
    print("=" * 80)
    
    manager = ChannelManager()
    
    channels = manager.list_channels(active_only=True)
    
    for channel in channels:
        print(f"\n📊 {channel.name}")
        
        stats = manager.get_channel_statistics(channel.channel_id)
        
        print(f"   Soumissions totales: {stats['total_submissions']}")
        print(f"   En attente: {stats['pending']}")
        print(f"   En traitement: {stats['processing']}")
        print(f"   Réussies: {stats['dq_success']}")
        print(f"   Échouées: {stats['dq_failed']}")
        print(f"   Erreurs: {stats['error']}")
        print(f"   Taux de succès: {stats['success_rate']:.1f}%")


def main():
    """Démonstration complète"""
    
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "SYSTÈME DE CANAUX DE DÉPÔT" + " " * 32 + "║")
    print("║" + " " * 78 + "║")
    print("║" + "  Démonstration du workflow complet de réception et traitement" + " " * 15 + "║")
    print("╚" + "=" * 78 + "╝")
    
    # 1. Créer les canaux
    demo_create_channels()
    
    # 2. Soumettre des données
    submission = demo_submit_data()
    
    if submission:
        # 3. Traiter la soumission
        demo_process_submission(submission)
    
    # 4. Lister les soumissions
    demo_list_submissions()
    
    # 5. Statistiques
    demo_channel_statistics()
    
    print("\n" + "=" * 80)
    print("✅ Démonstration terminée!")
    print("=" * 80)
    print("\nFichiers générés:")
    print("  • managed_folders/channels/channels.json")
    print("  • managed_folders/channels/submissions.json")
    print("  • reports/channel_submissions/*.xlsx")
    print("\n")


if __name__ == "__main__":
    main()
