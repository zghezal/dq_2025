"""
DQ Dependency Executor - Gestion de l'exécution avec dépendances

Ce module gère l'exécution des métriques et tests en respectant les dépendances.
Si une dépendance échoue, les éléments dépendants sont marqués comme SKIPPED.
"""

from typing import Dict, Any, List, Set
from datetime import datetime
from src.core.sequencer import ExecutionSequence, ExecutionCommand, CommandType


class ExecutionStatus:
    """Statuts d'exécution possibles"""
    SUCCESS = "SUCCESS"
    FAIL = "FAIL"
    ERROR = "ERROR"
    SKIPPED = "SKIPPED"  # Dépendances non satisfaites
    PENDING = "PENDING"


class DQExecutor:
    """
    Exécuteur qui respecte les dépendances.
    
    Si une commande échoue (status != SUCCESS), toutes les commandes
    qui en dépendent sont automatiquement SKIPPED.
    """
    
    def __init__(self, sequence: ExecutionSequence):
        self.sequence = sequence
        self.execution_results: Dict[str, Dict[str, Any]] = {}
        
    def execute(self, 
                execute_function,
                skip_on_dependency_failure: bool = True) -> Dict[str, Dict[str, Any]]:
        """
        Exécute la séquence en respectant les dépendances.
        
        Args:
            execute_function: Fonction qui prend (command) et retourne un dict
                             avec au minimum {'status': str, ...}
            skip_on_dependency_failure: Si True, skip les éléments dont les dépendances ont échoué
            
        Returns:
            Dict des résultats d'exécution {command_id: result_dict}
        """
        # Exécuter dans l'ordre topologique
        for command_id in self.sequence.execution_order:
            command = self.sequence.get_command(command_id)
            if not command:
                continue
            
            # Vérifier si les dépendances sont satisfaites
            if skip_on_dependency_failure:
                failed_deps = self._check_dependencies(command)
                if failed_deps:
                    # Dépendances non satisfaites -> SKIP
                    self.execution_results[command_id] = {
                        'status': ExecutionStatus.SKIPPED,
                        'error': f"Dépendances non satisfaites: {', '.join(failed_deps)}",
                        'timestamp': datetime.now(),
                        'failed_dependencies': failed_deps
                    }
                    continue
            
            # Exécuter la commande
            try:
                result = execute_function(command)
                result['timestamp'] = result.get('timestamp', datetime.now())
                self.execution_results[command_id] = result
            except Exception as e:
                self.execution_results[command_id] = {
                    'status': ExecutionStatus.ERROR,
                    'error': str(e),
                    'timestamp': datetime.now()
                }
        
        return self.execution_results
    
    def _check_dependencies(self, command: ExecutionCommand) -> List[str]:
        """
        Vérifie si toutes les dépendances d'une commande ont réussi.
        
        Returns:
            Liste des dépendances qui ont échoué (vide si tout ok)
        """
        failed_deps = []
        
        for dep_id in command.dependencies:
            if dep_id not in self.execution_results:
                failed_deps.append(f"{dep_id} (non exécuté)")
            else:
                dep_status = self.execution_results[dep_id].get('status')
                if dep_status != ExecutionStatus.SUCCESS:
                    failed_deps.append(f"{dep_id} ({dep_status})")
        
        return failed_deps
    
    def get_summary(self) -> Dict[str, int]:
        """Résumé des statuts d'exécution"""
        summary = {
            ExecutionStatus.SUCCESS: 0,
            ExecutionStatus.FAIL: 0,
            ExecutionStatus.ERROR: 0,
            ExecutionStatus.SKIPPED: 0,
            ExecutionStatus.PENDING: 0
        }
        
        for result in self.execution_results.values():
            status = result.get('status', ExecutionStatus.PENDING)
            summary[status] = summary.get(status, 0) + 1
        
        return summary
    
    def get_metrics_summary(self) -> Dict[str, int]:
        """Résumé pour les métriques uniquement"""
        summary = {status: 0 for status in [
            ExecutionStatus.SUCCESS, ExecutionStatus.FAIL, 
            ExecutionStatus.ERROR, ExecutionStatus.SKIPPED
        ]}
        
        for command_id, result in self.execution_results.items():
            command = self.sequence.get_command(command_id)
            if command and command.command_type == CommandType.METRIC:
                status = result.get('status')
                summary[status] = summary.get(status, 0) + 1
        
        return summary
    
    def get_tests_summary(self) -> Dict[str, int]:
        """Résumé pour les tests uniquement"""
        summary = {status: 0 for status in [
            ExecutionStatus.SUCCESS, ExecutionStatus.FAIL, 
            ExecutionStatus.ERROR, ExecutionStatus.SKIPPED
        ]}
        
        for command_id, result in self.execution_results.items():
            command = self.sequence.get_command(command_id)
            if command and command.command_type in [CommandType.TEST, CommandType.IMPLICIT_TEST]:
                status = result.get('status')
                # Pour les tests, SUCCESS signifie PASS
                summary[status] = summary.get(status, 0) + 1
        
        return summary
