"""
Module d'investigation pour les tests DQ

Génère des échantillons de données problématiques lorsqu'un test échoue.
Permet d'identifier rapidement les lignes causant les problèmes de qualité.
"""

from typing import Dict, Any, Optional, List
import pandas as pd
from pathlib import Path
from datetime import datetime


class DQInvestigator:
    """Générateur d'échantillons d'investigation pour les tests DQ qui échouent"""
    
    def __init__(self, output_dir: str = "reports/investigations"):
        """
        Args:
            output_dir: Répertoire où sauvegarder les fichiers d'investigation
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_investigation_samples(
        self,
        df: pd.DataFrame,
        test_id: str,
        test_config: Dict[str, Any],
        metric_config: Optional[Dict[str, Any]] = None,
        metric_value: Optional[Any] = None,
        max_samples: int = 100
    ) -> Optional[Dict[str, Any]]:
        """
        Génère des échantillons de lignes problématiques pour un test qui échoue
        
        Args:
            df: DataFrame source
            test_id: Identifiant du test
            test_config: Configuration du test
            metric_config: Configuration de la métrique associée
            metric_value: Valeur de la métrique calculée
            max_samples: Nombre maximum de lignes à échantillonner
            
        Returns:
            Dict avec les informations d'investigation ou None si pas applicable
        """
        if metric_config is None:
            return None
        
        metric_type = metric_config.get('type')
        
        # Dispatcher selon le type de métrique
        if metric_type == 'missing_rate':
            return self._investigate_missing_rate(
                df, test_id, test_config, metric_config, metric_value, max_samples
            )
        
        elif metric_type in ['count_where', 'count_condition']:
            return self._investigate_count_where(
                df, test_id, test_config, metric_config, metric_value, max_samples
            )
        
        # Seules missing_rate et count_where sont supportées
        return None
    
    def _investigate_missing_rate(
        self,
        df: pd.DataFrame,
        test_id: str,
        test_config: Dict[str, Any],
        metric_config: Dict[str, Any],
        metric_value: Optional[float],
        max_samples: int
    ) -> Dict[str, Any]:
        """Génère échantillon pour missing_rate"""
        column = metric_config.get('column')
        
        if column is None:
            # Missing rate global - prendre les lignes avec au moins une valeur manquante
            mask = df.isna().any(axis=1)
            sample_df = df[mask].head(max_samples)
            description = "Lignes contenant au moins une valeur manquante"
        else:
            # Missing rate sur une colonne spécifique
            if column not in df.columns:
                return {
                    'test_id': test_id,
                    'error': f"Colonne '{column}' introuvable"
                }
            
            mask = df[column].isna()
            sample_df = df[mask].head(max_samples)
            description = f"Lignes avec valeurs manquantes dans la colonne '{column}'"
        
        total_problematic = mask.sum()
        
        # Sauvegarder l'échantillon
        filename = self._save_sample(sample_df, test_id, 'missing_values')
        
        return {
            'test_id': test_id,
            'metric_type': 'missing_rate',
            'metric_value': metric_value,
            'total_problematic_rows': int(total_problematic),
            'sample_size': len(sample_df),
            'description': description,
            'sample_file': str(filename),
            'columns_analyzed': [column] if column else list(df.columns)
        }
    
    def _investigate_count_where(
        self,
        df: pd.DataFrame,
        test_id: str,
        test_config: Dict[str, Any],
        metric_config: Dict[str, Any],
        metric_value: Optional[int],
        max_samples: int
    ) -> Dict[str, Any]:
        """Génère échantillon pour count_where (lignes matchant une condition)"""
        filter_condition = metric_config.get('filter')
        
        if not filter_condition:
            return {
                'test_id': test_id,
                'error': 'Pas de condition filter définie'
            }
        
        try:
            # Évaluer la condition
            mask = df.eval(filter_condition)
            sample_df = df[mask].head(max_samples)
            
            total_matches = mask.sum()
            
            # Sauvegarder
            filename = self._save_sample(sample_df, test_id, 'condition_matches')
            
            return {
                'test_id': test_id,
                'metric_type': 'count_where',
                'metric_value': metric_value,
                'filter_condition': filter_condition,
                'total_matching_rows': int(total_matches),
                'sample_size': len(sample_df),
                'description': f"Lignes respectant la condition: {filter_condition}",
                'sample_file': str(filename)
            }
        
        except Exception as e:
            return {
                'test_id': test_id,
                'error': f"Erreur d'évaluation de la condition: {e}"
            }
    
    def _save_sample(
        self,
        df: pd.DataFrame,
        test_id: str,
        category: str
    ) -> Path:
        """
        Sauvegarde un échantillon dans un fichier CSV
        
        Args:
            df: DataFrame à sauvegarder
            test_id: ID du test
            category: Catégorie d'investigation
            
        Returns:
            Path du fichier créé
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{test_id}_{category}_{timestamp}.csv"
        filepath = self.output_dir / filename
        
        # Sauvegarder avec encodage UTF-8
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        
        return filepath
    
    def generate_investigation_report(
        self,
        investigations: List[Dict[str, Any]],
        report_name: str = "investigation_report"
    ) -> Path:
        """
        Génère un rapport consolidé des investigations
        
        Args:
            investigations: Liste des résultats d'investigation
            report_name: Nom du rapport
            
        Returns:
            Path du fichier de rapport
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{report_name}_{timestamp}.txt"
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("RAPPORT D'INVESTIGATION DQ\n")
            f.write("=" * 80 + "\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Nombre de tests investigués: {len(investigations)}\n")
            f.write("\n")
            
            for i, inv in enumerate(investigations, 1):
                f.write(f"\n{i}. Test: {inv.get('test_id', 'N/A')}\n")
                f.write("-" * 80 + "\n")
                
                if 'error' in inv:
                    f.write(f"   ❌ Erreur: {inv['error']}\n")
                    continue
                
                f.write(f"   Type de métrique: {inv.get('metric_type', 'N/A')}\n")
                f.write(f"   Valeur métrique: {inv.get('metric_value', 'N/A')}\n")
                f.write(f"   Description: {inv.get('description', 'N/A')}\n")
                
                if 'total_problematic_rows' in inv:
                    f.write(f"   Lignes problématiques: {inv['total_problematic_rows']}\n")
                
                if 'total_matching_rows' in inv:
                    f.write(f"   Lignes correspondantes: {inv['total_matching_rows']}\n")
                
                if 'filter_condition' in inv:
                    f.write(f"   Condition: {inv['filter_condition']}\n")
                
                f.write(f"   Échantillon: {inv.get('sample_size', 0)} lignes\n")
                f.write(f"   Fichier: {inv.get('sample_file', 'N/A')}\n")
                
                if 'column_stats' in inv:
                    f.write(f"   Statistiques:\n")
                    for stat, value in inv['column_stats'].items():
                        f.write(f"      {stat}: {value}\n")
        
        return filepath
