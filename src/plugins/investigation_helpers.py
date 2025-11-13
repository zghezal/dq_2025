"""
Helpers pour l'investigation de tests DQ échoués.

Ce module fournit des utilitaires réutilisables pour sauvegarder
des échantillons de données problématiques et générer des rapports.
"""

from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
import pandas as pd


def save_investigation_sample(
    df: pd.DataFrame, 
    test_id: str, 
    suffix: str,
    output_dir: str = "reports/investigations"
) -> Path:
    """
    Sauvegarde un DataFrame d'investigation en CSV.
    
    Args:
        df: DataFrame contenant l'échantillon à sauvegarder
        test_id: Identifiant du test (utilisé dans le nom de fichier)
        suffix: Suffixe descriptif (ex: "missing_values", "out_of_range")
        output_dir: Répertoire de destination
    
    Returns:
        Path du fichier CSV créé
    
    Exemple:
        >>> sample = df[df['age'] < 0]
        >>> path = save_investigation_sample(sample, "test_age", "invalid_ages")
        >>> print(path)
        reports/investigations/test_age_invalid_ages_20251108_120000.csv
    """
    inv_dir = Path(output_dir)
    inv_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{test_id}_{suffix}_{timestamp}.csv"
    file_path = inv_dir / filename
    
    df.to_csv(file_path, index=False)
    
    return file_path


def build_investigation_result(
    df: pd.DataFrame,
    sample_df: pd.DataFrame,
    description: str,
    test_id: str,
    suffix: str,
    output_dir: str = "reports/investigations",
    **extra_meta
) -> Dict[str, Any]:
    """
    Construit un dict d'investigation complet avec sauvegarde du CSV.
    
    Args:
        df: DataFrame complet (pour compter les lignes problématiques)
        sample_df: DataFrame échantillon à sauvegarder
        description: Description du problème détecté
        test_id: Identifiant du test
        suffix: Suffixe pour le nom de fichier
        output_dir: Répertoire de destination
        **extra_meta: Métadonnées additionnelles à inclure
    
    Returns:
        Dict standardisé pour Result.investigation
    
    Exemple:
        >>> problematic = df[df['value'] < 0]
        >>> sample = problematic.head(100)
        >>> inv = build_investigation_result(
        ...     df=problematic,
        ...     sample_df=sample,
        ...     description="Valeurs négatives détectées",
        ...     test_id="test_positive_values",
        ...     suffix="negative_values",
        ...     column="value"
        ... )
    """
    total_problematic = len(df)
    sample_size = len(sample_df)
    
    file_path = save_investigation_sample(
        sample_df, 
        test_id, 
        suffix, 
        output_dir
    )
    
    result = {
        "sample_df": sample_df,
        "description": description,
        "total_problematic_rows": total_problematic,
        "sample_size": sample_size,
        "sample_file": str(file_path),
        **extra_meta
    }
    
    return result


def generate_consolidated_report(
    investigations: List[Dict[str, Any]], 
    report_name: str = "investigation_report",
    output_dir: str = "reports/investigations"
) -> Path:
    """
    Génère un rapport consolidé au format texte listant toutes les investigations.
    
    Args:
        investigations: Liste des dicts d'investigation
        report_name: Nom de base du fichier rapport
        output_dir: Répertoire de destination
    
    Returns:
        Path du fichier rapport créé
    
    Exemple:
        >>> inv1 = {"test_id": "T1", "description": "...", ...}
        >>> inv2 = {"test_id": "T2", "description": "...", ...}
        >>> path = generate_consolidated_report([inv1, inv2], "my_dq_run")
    """
    inv_dir = Path(output_dir)
    inv_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = inv_dir / f"{report_name}_{timestamp}.txt"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("RAPPORT D'INVESTIGATION DQ\n")
        f.write("=" * 80 + "\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Nombre de tests investigués: {len(investigations)}\n\n")
        
        for i, inv in enumerate(investigations, 1):
            test_id = inv.get('test_id', 'unknown')
            f.write(f"\n{i}. Test: {test_id}\n")
            f.write("-" * 80 + "\n")
            
            if 'test_type' in inv:
                f.write(f"   Type de test: {inv['test_type']}\n")
            
            if 'description' in inv:
                f.write(f"   Description: {inv['description']}\n")
            
            if 'total_problematic_rows' in inv:
                f.write(f"   Lignes problématiques: {inv['total_problematic_rows']}\n")
            
            if 'sample_size' in inv:
                f.write(f"   Échantillon: {inv['sample_size']} lignes\n")
            
            if 'sample_file' in inv:
                f.write(f"   Fichier: {inv['sample_file']}\n")
            
            # Afficher les métadonnées spécifiques
            exclude_keys = {
                'test_id', 'test_type', 'description', 
                'total_problematic_rows', 'sample_size', 
                'sample_file', 'sample_df'
            }
            extra_keys = [k for k in inv.keys() if k not in exclude_keys]
            for key in extra_keys:
                value = inv[key]
                if isinstance(value, (str, int, float, bool)):
                    f.write(f"   {key}: {value}\n")
    
    return report_file
