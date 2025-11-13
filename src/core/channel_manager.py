"""
Gestionnaire de canaux de dépôt (Drop Channels)

Ce module gère:
- CRUD des canaux
- Stockage persistant (JSON)
- Recherche et validation
"""

import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from src.core.models_channels import DropChannel, ChannelSubmission, FileSpecification


class ChannelManager:
    """Gestionnaire des canaux de dépôt"""
    
    def __init__(self, storage_path: str = "managed_folders/channels"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.channels_file = self.storage_path / "channels.json"
        self.submissions_file = self.storage_path / "submissions.json"
        
    def _load_channels(self) -> Dict[str, DropChannel]:
        """Charge tous les canaux depuis le fichier JSON"""
        if not self.channels_file.exists():
            return {}
        
        try:
            with open(self.channels_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return {cid: DropChannel.from_dict(cdata) for cid, cdata in data.items()}
        except Exception as e:
            print(f"Erreur chargement canaux: {e}")
            return {}
    
    def _save_channels(self, channels: Dict[str, DropChannel]):
        """Sauvegarde tous les canaux dans le fichier JSON"""
        try:
            data = {cid: channel.to_dict() for cid, channel in channels.items()}
            with open(self.channels_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Erreur sauvegarde canaux: {e}")
            raise
    
    def create_channel(self, channel: DropChannel) -> DropChannel:
        """Crée un nouveau canal"""
        channels = self._load_channels()
        
        if channel.channel_id in channels:
            raise ValueError(f"Canal {channel.channel_id} existe déjà")
        
        channel.created_at = datetime.now()
        channels[channel.channel_id] = channel
        self._save_channels(channels)
        
        return channel
    
    def update_channel(self, channel: DropChannel) -> DropChannel:
        """Met à jour un canal existant"""
        channels = self._load_channels()
        
        if channel.channel_id not in channels:
            raise ValueError(f"Canal {channel.channel_id} introuvable")
        
        channel.updated_at = datetime.now()
        channels[channel.channel_id] = channel
        self._save_channels(channels)
        
        return channel
    
    def delete_channel(self, channel_id: str) -> bool:
        """Supprime un canal"""
        channels = self._load_channels()
        
        if channel_id not in channels:
            return False
        
        del channels[channel_id]
        self._save_channels(channels)
        
        return True
    
    def get_channel(self, channel_id: str) -> Optional[DropChannel]:
        """Récupère un canal par son ID"""
        channels = self._load_channels()
        return channels.get(channel_id)
    
    def list_channels(self, active_only: bool = False, user_email: Optional[str] = None, 
                     user_groups: Optional[List[str]] = None) -> List[DropChannel]:
        """
        Liste tous les canaux
        
        Args:
            active_only: Ne retourner que les canaux actifs
            user_email: Email de l'utilisateur (pour filtrer selon permissions)
            user_groups: Groupes de l'utilisateur (pour filtrer selon permissions)
            
        Returns:
            Liste des canaux accessibles
        """
        channels = self._load_channels()
        channel_list = list(channels.values())
        
        if active_only:
            channel_list = [c for c in channel_list if c.active]
        
        # Filtrer selon les permissions si un utilisateur est spécifié
        if user_email or user_groups:
            channel_list = [c for c in channel_list if c.has_access(user_email, user_groups)]
        
        return sorted(channel_list, key=lambda c: c.created_at, reverse=True)
    
    def search_channels(self, team_name: Optional[str] = None, 
                       name_contains: Optional[str] = None) -> List[DropChannel]:
        """Recherche des canaux selon des critères"""
        channels = self.list_channels()
        
        if team_name:
            channels = [c for c in channels if c.team_name == team_name]
        
        if name_contains:
            channels = [c for c in channels 
                       if name_contains.lower() in c.name.lower()]
        
        return channels
    
    # Gestion des soumissions
    
    def _load_submissions(self) -> Dict[str, ChannelSubmission]:
        """Charge toutes les soumissions"""
        if not self.submissions_file.exists():
            return {}
        
        try:
            with open(self.submissions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return {sid: ChannelSubmission.from_dict(sdata) for sid, sdata in data.items()}
        except Exception as e:
            print(f"Erreur chargement soumissions: {e}")
            return {}
    
    def _save_submissions(self, submissions: Dict[str, ChannelSubmission]):
        """Sauvegarde toutes les soumissions"""
        try:
            data = {sid: sub.to_dict() for sid, sub in submissions.items()}
            with open(self.submissions_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Erreur sauvegarde soumissions: {e}")
            raise
    
    def create_submission(self, submission: ChannelSubmission) -> ChannelSubmission:
        """Crée une nouvelle soumission"""
        submissions = self._load_submissions()
        
        if submission.submission_id in submissions:
            raise ValueError(f"Soumission {submission.submission_id} existe déjà")
        
        submission.submitted_at = datetime.now()
        submissions[submission.submission_id] = submission
        self._save_submissions(submissions)
        
        return submission
    
    def update_submission(self, submission: ChannelSubmission) -> ChannelSubmission:
        """Met à jour une soumission"""
        submissions = self._load_submissions()
        
        if submission.submission_id not in submissions:
            raise ValueError(f"Soumission {submission.submission_id} introuvable")
        
        submissions[submission.submission_id] = submission
        self._save_submissions(submissions)
        
        return submission
    
    def get_submission(self, submission_id: str) -> Optional[ChannelSubmission]:
        """Récupère une soumission par son ID"""
        submissions = self._load_submissions()
        return submissions.get(submission_id)
    
    def list_submissions(self, channel_id: Optional[str] = None,
                        limit: int = 100) -> List[ChannelSubmission]:
        """Liste les soumissions"""
        submissions = self._load_submissions()
        submission_list = list(submissions.values())
        
        if channel_id:
            submission_list = [s for s in submission_list if s.channel_id == channel_id]
        
        # Trier par date (plus récent en premier)
        submission_list = sorted(submission_list, 
                                key=lambda s: s.submitted_at, 
                                reverse=True)
        
        return submission_list[:limit]
    
    def get_channel_statistics(self, channel_id: str) -> Dict[str, Any]:
        """Calcule des statistiques pour un canal"""
        submissions = self.list_submissions(channel_id=channel_id)
        
        total = len(submissions)
        pending = sum(1 for s in submissions if s.status.value == 'pending')
        processing = sum(1 for s in submissions if s.status.value == 'processing')
        success = sum(1 for s in submissions if s.status.value == 'dq_success')
        failed = sum(1 for s in submissions if s.status.value == 'dq_failed')
        error = sum(1 for s in submissions if s.status.value == 'error')
        
        return {
            "total_submissions": total,
            "pending": pending,
            "processing": processing,
            "dq_success": success,
            "dq_failed": failed,
            "error": error,
            "success_rate": (success / total * 100) if total > 0 else 0
        }


# Instance globale
_channel_manager = None

def get_channel_manager() -> ChannelManager:
    """Obtient l'instance du gestionnaire de canaux"""
    global _channel_manager
    if _channel_manager is None:
        _channel_manager = ChannelManager()
    return _channel_manager
