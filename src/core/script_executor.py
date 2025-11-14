"""
Script Executor pour DQ

Ce module permet d'exécuter des scripts personnalisés associés à une définition DQ.
Les scripts produisent des résultats au format compatible avec le backlog automatisé.
"""

import importlib.util
import sys
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

from src.core.models_dq import ScriptDefinition


class ScriptResult:
    """Résultat de l'exécution d'un script"""
    
    def __init__(
        self,
        script_id: str,
        status: str,
        metrics: Dict[str, Any] = None,
        tests: Dict[str, Any] = None,
        investigations: List[Dict[str, Any]] = None,
        error: str = None,
        duration: float = 0.0
    ):
        self.script_id = script_id
        self.status = status  # success | failed | error
        self.metrics = metrics or {}
        self.tests = tests or {}
        self.investigations = investigations or []
        self.error = error
        self.duration = duration
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire"""
        return {
            "script_id": self.script_id,
            "status": self.status,
            "metrics": self.metrics,
            "tests": self.tests,
            "investigations": self.investigations,
            "error": self.error,
            "duration": self.duration,
            "timestamp": self.timestamp.isoformat()
        }


def validate_script_output(result: Dict[str, Any], script_id: str) -> None:
    """
    Valide que le résultat d'un script respecte le contrat attendu
    
    Args:
        result: Dictionnaire retourné par le script
        script_id: ID du script pour les messages d'erreur
        
    Raises:
        ValueError: Si le format est invalide
    """
    if not isinstance(result, dict):
        raise ValueError(f"Script {script_id}: doit retourner un dictionnaire")
    
    # Champs obligatoires
    if "script_id" not in result:
        raise ValueError(f"Script {script_id}: champ 'script_id' manquant")
    
    if "status" not in result:
        raise ValueError(f"Script {script_id}: champ 'status' manquant")
    
    # Valider le status
    valid_statuses = ["success", "failed", "error"]
    if result["status"] not in valid_statuses:
        raise ValueError(
            f"Script {script_id}: status '{result['status']}' invalide. "
            f"Valeurs acceptées: {valid_statuses}"
        )
    
    # Champs optionnels mais recommandés
    for field in ["metrics", "tests"]:
        if field in result and not isinstance(result[field], dict):
            raise ValueError(f"Script {script_id}: '{field}' doit être un dictionnaire")
    
    if "investigations" in result and not isinstance(result["investigations"], list):
        raise ValueError(f"Script {script_id}: 'investigations' doit être une liste")


def execute_script(
    script: ScriptDefinition,
    context: Any,
    repo_root: Path = None
) -> ScriptResult:
    """
    Exécute un script personnalisé et retourne le résultat
    
    Args:
        script: Définition du script à exécuter
        context: Contexte d'exécution (accès aux datasets via context.load())
        repo_root: Racine du repository (par défaut: parent du fichier actuel)
        
    Returns:
        ScriptResult avec les résultats du script
    """
    if not script.enabled:
        return ScriptResult(
            script_id=script.id,
            status="skipped",
            error="Script désactivé"
        )
    
    # Déterminer la racine du repo
    if repo_root is None:
        repo_root = Path(__file__).parent.parent.parent
    
    script_path = repo_root / script.path
    
    if not script_path.exists():
        return ScriptResult(
            script_id=script.id,
            status="error",
            error=f"Script introuvable: {script_path}"
        )
    
    start_time = datetime.now()
    
    try:
        # Charger le module Python dynamiquement
        spec = importlib.util.spec_from_file_location(script.id, script_path)
        if spec is None or spec.loader is None:
            raise ValueError(f"Impossible de charger le module depuis {script_path}")
        
        module = importlib.util.module_from_spec(spec)
        
        # Ajouter au sys.modules temporairement pour permettre les imports relatifs
        sys.modules[script.id] = module
        
        try:
            spec.loader.exec_module(module)
        finally:
            # Nettoyer sys.modules
            sys.modules.pop(script.id, None)
        
        # Vérifier que le script expose une fonction run()
        if not hasattr(module, "run"):
            raise ValueError(
                f"Script {script_path} doit définir une fonction run(context, params)"
            )
        
        # Exécuter le script
        result = module.run(context, script.params)
        
        # Valider le format de sortie
        validate_script_output(result, script.id)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        return ScriptResult(
            script_id=result["script_id"],
            status=result["status"],
            metrics=result.get("metrics", {}),
            tests=result.get("tests", {}),
            investigations=result.get("investigations", []),
            duration=duration
        )
        
    except Exception as e:
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        return ScriptResult(
            script_id=script.id,
            status="error",
            error=f"{type(e).__name__}: {str(e)}",
            duration=duration
        )


def execute_scripts(
    scripts: List[ScriptDefinition],
    context: Any,
    execute_phase: str = "post_dq"
) -> List[ScriptResult]:
    """
    Exécute tous les scripts pour une phase donnée
    
    Args:
        scripts: Liste des scripts définis dans la DQ
        context: Contexte d'exécution
        execute_phase: Phase d'exécution ("pre_dq", "post_dq", "independent")
        
    Returns:
        Liste des résultats d'exécution
    """
    results = []
    
    # Filtrer les scripts pour cette phase
    scripts_to_run = [s for s in scripts if s.execute_on == execute_phase]
    
    if not scripts_to_run:
        return results
    
    print(f"\n[Scripts] Exécution de {len(scripts_to_run)} script(s) en phase '{execute_phase}'")
    
    for script in scripts_to_run:
        print(f"  - Exécution: {script.id} ({script.label or 'sans label'})")
        
        result = execute_script(script, context)
        results.append(result)
        
        # Log du résultat
        if result.status == "success":
            print(f"    ✓ Succès ({result.duration:.2f}s)")
            print(f"      Métriques: {len(result.metrics)}, Tests: {len(result.tests)}")
        elif result.status == "error":
            print(f"    ✗ Erreur: {result.error}")
        else:
            print(f"    ⚠ Status: {result.status}")
    
    return results
