"""
DQ Sequencer - Ordonnancement et génération de séquence d'exécution

Ce module analyse une configuration DQ et génère une séquence d'exécution ordonnée
en tenant compte des dépendances entre métriques et tests.

Fonctionnalités:
- Résolution des dépendances entre métriques et tests
- Ordonnancement topologique
- Détection des cycles de dépendances
- Génération de tests techniques implicites pour les filtres
- Création de la séquence d'exécution finale
"""

from typing import Dict, List, Set, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import re
from src.core.dq_parser import DQConfig, Metric, Test


class CommandType(Enum):
    """Type de commande à exécuter"""
    METRIC = "metric"
    TEST = "test"
    IMPLICIT_TEST = "implicit_test"  # Tests techniques générés automatiquement


class ImplicitTestType(Enum):
    """Types de tests implicites générés pour les filtres"""
    FILTER_COLUMNS_PRESENCE = "filter_columns_presence"
    FILTER_COLUMNS_TYPE_MATCH = "filter_columns_type_match"
    PARAMETERS_TYPE_VALIDATION = "parameters_type_validation"


@dataclass
class ExecutionCommand:
    """Commande d'exécution pour une métrique ou un test"""
    command_id: str
    command_type: CommandType
    element_id: str  # ID de la métrique ou du test
    element_type: str  # Type technique (missing_rate, interval_check, etc.)
    dependencies: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __repr__(self):
        deps = f", deps={self.dependencies}" if self.dependencies else ""
        return f"<{self.command_type.value}:{self.element_id}{deps}>"


@dataclass
class ImplicitTestCommand(ExecutionCommand):
    """Commande pour un test technique implicite généré automatiquement"""
    implicit_type: ImplicitTestType = None
    parent_test_id: str = None  # Test qui a généré ce test implicite
    
    def __repr__(self):
        return f"<implicit_test:{self.implicit_type.value} for {self.parent_test_id}>"


@dataclass
class ExecutionSequence:
    """Séquence d'exécution complète"""
    commands: List[ExecutionCommand] = field(default_factory=list)
    dependency_graph: Dict[str, List[str]] = field(default_factory=dict)
    execution_order: List[str] = field(default_factory=list)
    
    def add_command(self, command: ExecutionCommand):
        """Ajoute une commande à la séquence"""
        self.commands.append(command)
    
    def get_command(self, command_id: str) -> Optional[ExecutionCommand]:
        """Récupère une commande par son ID"""
        return next((cmd for cmd in self.commands if cmd.command_id == command_id), None)
    
    def summary(self) -> str:
        """Résumé de la séquence"""
        metrics_count = sum(1 for c in self.commands if c.command_type == CommandType.METRIC)
        tests_count = sum(1 for c in self.commands if c.command_type == CommandType.TEST)
        implicit_count = sum(1 for c in self.commands if c.command_type == CommandType.IMPLICIT_TEST)
        
        lines = [
            "=" * 80,
            "SÉQUENCE D'EXÉCUTION DQ",
            "=" * 80,
            f"Total commandes: {len(self.commands)}",
            f"  - Métriques: {metrics_count}",
            f"  - Tests: {tests_count}",
            f"  - Tests implicites: {implicit_count}",
            "",
            "Ordre d'exécution:",
        ]
        
        for i, cmd_id in enumerate(self.execution_order, 1):
            cmd = self.get_command(cmd_id)
            if cmd:
                deps_str = f" [après: {', '.join(cmd.dependencies)}]" if cmd.dependencies else ""
                lines.append(f"  {i:2d}. {cmd.command_id:40s} ({cmd.command_type.value}){deps_str}")
        
        lines.append("=" * 80)
        return "\n".join(lines)


class DQSequencer:
    """
    Séquenceur DQ - Analyse les dépendances et génère la séquence d'exécution
    """
    
    def __init__(self, config: DQConfig):
        self.config = config
        self.sequence = ExecutionSequence()
        self._metric_commands: Dict[str, ExecutionCommand] = {}
        self._test_commands: Dict[str, ExecutionCommand] = {}
        
    def build_sequence(self) -> ExecutionSequence:
        """
        Construit la séquence d'exécution complète
        
        Étapes:
        0. Valider l'unicité des IDs
        1. Créer les commandes pour les métriques
        2. Créer les commandes pour les tests
        3. Générer les tests implicites pour les filtres
        4. Résoudre les dépendances
        5. Ordonner topologiquement
        """
        print("\n🔄 Construction de la séquence d'exécution...")
        
        # 0. Valider l'unicité des IDs
        self._validate_unique_ids()
        
        # 1. Créer les commandes métriques
        self._create_metric_commands()
        
        # 2. Créer les commandes tests
        self._create_test_commands()
        
        # 3. Générer les tests implicites pour les filtres
        self._generate_implicit_tests()
        
        # 4. Générer les tests de validation des paramètres
        self._generate_parameter_validation_tests()
        
        # 5. Résoudre les dépendances
        self._resolve_dependencies()
        
        # 6. Ordonner topologiquement
        self._topological_sort()
        
        print(f"✅ Séquence construite: {len(self.sequence.commands)} commandes")
        
        return self.sequence
    
    def _validate_unique_ids(self):
        """
        Valide l'unicité des IDs de métriques et tests
        
        Vérifie:
        1. Pas de doublons dans les IDs de métriques
        2. Pas de doublons dans les IDs de tests
        3. Pas de collision entre IDs de métriques et tests
        """
        print("\n🔍 Validation de l'unicité des IDs...")
        
        # Vérifier les métriques
        metric_ids = list(self.config.metrics.keys())
        metric_duplicates = [id for id in metric_ids if metric_ids.count(id) > 1]
        metric_duplicates = list(set(metric_duplicates))  # Dédupliquer
        
        if metric_duplicates:
            error_msg = f"❌ IDs de métriques dupliqués: {metric_duplicates}"
            print(error_msg)
            raise ValueError(error_msg)
        
        # Vérifier les tests
        test_ids = list(self.config.tests.keys())
        test_duplicates = [id for id in test_ids if test_ids.count(id) > 1]
        test_duplicates = list(set(test_duplicates))  # Dédupliquer
        
        if test_duplicates:
            error_msg = f"❌ IDs de tests dupliqués: {test_duplicates}"
            print(error_msg)
            raise ValueError(error_msg)
        
        # Vérifier les collisions entre métriques et tests
        all_ids = set(metric_ids)
        collisions = [id for id in test_ids if id in all_ids]
        
        if collisions:
            error_msg = f"❌ Collision d'IDs entre métriques et tests: {collisions}"
            print(error_msg)
            raise ValueError(error_msg)
        
        print(f"  ✅ {len(metric_ids)} métriques uniques")
        print(f"  ✅ {len(test_ids)} tests uniques")
        print(f"  ✅ Aucune collision d'IDs détectée")
    
    def _create_metric_commands(self):
        """Crée les commandes pour toutes les métriques"""
        print(f"\n📊 Création des commandes métriques ({len(self.config.metrics)})...")
        
        for metric_id, metric in self.config.metrics.items():
            command = ExecutionCommand(
                command_id=metric_id,
                command_type=CommandType.METRIC,
                element_id=metric_id,
                element_type=metric.type,
                parameters=metric.specific.copy() if metric.specific else {},
                metadata={
                    'nature': metric.nature.to_dict() if metric.nature else {},
                    'general': metric.general.to_dict() if metric.general else {},
                    'identification': metric.identification.to_dict() if metric.identification else {}
                }
            )
            
            self._metric_commands[metric_id] = command
            self.sequence.add_command(command)
            print(f"  ✓ {metric_id} ({metric.type})")
    
    def _create_test_commands(self):
        """Crée les commandes pour tous les tests"""
        print(f"\n✅ Création des commandes tests ({len(self.config.tests)})...")
        
        for test_id, test in self.config.tests.items():
            command = ExecutionCommand(
                command_id=test_id,
                command_type=CommandType.TEST,
                element_id=test_id,
                element_type=test.type,
                parameters=test.specific.copy() if test.specific else {},
                metadata={
                    'nature': test.nature.to_dict() if test.nature else {},
                    'general': test.general.to_dict() if test.general else {},
                    'identification': test.identification.to_dict() if test.identification else {}
                }
            )
            
            self._test_commands[test_id] = command
            self.sequence.add_command(command)
            print(f"  ✓ {test_id} ({test.type})")
    
    def _generate_implicit_tests(self):
        """
        Génère les tests techniques implicites pour les tests avec filtres
        
        Pour chaque test avec un filtre (where clause), on génère:
        1. Test de présence des colonnes du filtre
        2. Test de type des colonnes du filtre
        """
        print("\n🔧 Génération des tests implicites pour les filtres...")
        
        implicit_count = 0
        
        for test_id, test_cmd in self._test_commands.items():
            # Vérifier si le test a un filtre dans ses paramètres ou specific
            has_filter = self._test_has_filter(test_cmd)
            
            if has_filter:
                filter_info = self._extract_filter_info(test_cmd)
                
                if filter_info:
                    # Générer les tests implicites
                    implicit_tests = self._create_implicit_tests_for_filter(
                        test_id, 
                        filter_info
                    )
                    
                    for implicit_test in implicit_tests:
                        self.sequence.add_command(implicit_test)
                        implicit_count += 1
                        print(f"  ✓ {implicit_test.command_id} pour {test_id}")
        
        if implicit_count == 0:
            print("  ℹ️  Aucun filtre détecté, pas de tests implicites générés")
    
    def _generate_parameter_validation_tests(self):
        """
        Génère les tests de validation des paramètres pour les métriques et tests
        
        Vérifie que les paramètres peuvent être castés dans les types attendus
        par les signatures des plugins (métriques et tests).
        """
        print("\n🔍 Génération des tests de validation des paramètres...")
        
        validation_count = 0
        
        # Validation des paramètres des métriques
        for metric_id, metric_cmd in self._metric_commands.items():
            validation_test = self._create_parameter_validation_test(
                parent_id=metric_id,
                parent_type="metric",
                element_type=metric_cmd.element_type,
                parameters=metric_cmd.parameters
            )
            
            if validation_test:
                self.sequence.add_command(validation_test)
                validation_count += 1
                print(f"  ✓ {validation_test.command_id} pour {metric_id}")
        
        # Validation des paramètres des tests
        for test_id, test_cmd in self._test_commands.items():
            validation_test = self._create_parameter_validation_test(
                parent_id=test_id,
                parent_type="test",
                element_type=test_cmd.element_type,
                parameters=test_cmd.parameters
            )
            
            if validation_test:
                self.sequence.add_command(validation_test)
                validation_count += 1
                print(f"  ✓ {validation_test.command_id} pour {test_id}")
        
        if validation_count == 0:
            print("  ℹ️  Aucun paramètre à valider")
    
    def _create_parameter_validation_test(
        self,
        parent_id: str,
        parent_type: str,
        element_type: str,
        parameters: Dict[str, Any]
    ) -> Optional[ImplicitTestCommand]:
        """
        Crée un test de validation des paramètres
        
        Vérifie que tous les paramètres peuvent être castés dans les types
        attendus par la signature du plugin (métrique ou test).
        """
        if not parameters:
            return None
        
        return ImplicitTestCommand(
            command_id=f"{parent_id}_implicit_param_validation",
            command_type=CommandType.IMPLICIT_TEST,
            element_id=f"{parent_id}_implicit_param_validation",
            element_type="parameter_type_validation",
            implicit_type=ImplicitTestType.PARAMETERS_TYPE_VALIDATION,
            parent_test_id=parent_id,
            parameters={
                'parent_type': parent_type,
                'element_type': element_type,
                'parameters_to_validate': parameters.copy()
            },
            metadata={
                'description': f"Vérifie que les paramètres de {parent_id} sont castables dans les types attendus par {element_type}",
                'generated_for': parent_id,
                'validation_scope': 'parameter_types'
            }
        )
    
    def _test_has_filter(self, test_cmd: ExecutionCommand) -> bool:
        """Vérifie si un test utilise un filtre"""
        params = test_cmd.parameters
        
        # Vérifier les patterns courants de filtres
        filter_keys = ['where', 'filter', 'condition', 'filter_condition']
        
        for key in filter_keys:
            if key in params and params[key]:
                return True
        
        return False
    
    def _extract_filter_info(self, test_cmd: ExecutionCommand) -> Optional[Dict[str, Any]]:
        """Extrait les informations du filtre d'un test"""
        params = test_cmd.parameters
        
        filter_expr = None
        dataset = None
        
        # Extraire l'expression du filtre
        for key in ['where', 'filter', 'condition', 'filter_condition']:
            if key in params and params[key]:
                filter_expr = params[key]
                break
        
        if not filter_expr:
            return None
        
        # Extraire le dataset cible
        dataset = params.get('value_from_dataset') or params.get('dataset')
        
        if not dataset:
            # Essayer de trouver via la métrique associée
            associated_metric = test_cmd.metadata.get('general', {}).get('associated_metric_id')
            if associated_metric and associated_metric in self._metric_commands:
                metric_cmd = self._metric_commands[associated_metric]
                dataset = metric_cmd.parameters.get('dataset')
        
        if not dataset:
            return None
        
        # Extraire les colonnes utilisées dans le filtre
        columns = self._extract_columns_from_filter(filter_expr)
        
        return {
            'filter_expr': filter_expr,
            'dataset': dataset,
            'columns': columns
        }
    
    def _extract_columns_from_filter(self, filter_expr: str) -> List[str]:
        """
        Extrait les noms de colonnes d'une expression de filtre
        
        Exemples:
        - "amount > 100" -> ["amount"]
        - "region = 'North' AND quantity > 5" -> ["region", "quantity"]
        """
        # Pattern pour identifier les noms de colonnes
        # Simplifié: un mot suivi d'un opérateur
        pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:=|>|<|!=|>=|<=|IN|LIKE|IS)'
        
        matches = re.findall(pattern, filter_expr, re.IGNORECASE)
        
        # Filtrer les mots-clés SQL courants
        sql_keywords = {'AND', 'OR', 'NOT', 'NULL', 'TRUE', 'FALSE'}
        columns = [m for m in matches if m.upper() not in sql_keywords]
        
        return list(set(columns))  # Dédupliquer
    
    def _create_implicit_tests_for_filter(
        self, 
        parent_test_id: str, 
        filter_info: Dict[str, Any]
    ) -> List[ImplicitTestCommand]:
        """
        Crée les tests implicites pour un filtre
        
        Génère:
        1. Test de présence des colonnes
        2. Test de type des colonnes
        """
        implicit_tests = []
        dataset = filter_info['dataset']
        columns = filter_info['columns']
        
        # 1. Test de présence des colonnes
        presence_test = ImplicitTestCommand(
            command_id=f"{parent_test_id}_implicit_columns_presence",
            command_type=CommandType.IMPLICIT_TEST,
            element_id=f"{parent_test_id}_implicit_columns_presence",
            element_type="filter_columns_presence",
            implicit_type=ImplicitTestType.FILTER_COLUMNS_PRESENCE,
            parent_test_id=parent_test_id,
            parameters={
                'dataset': dataset,
                'required_columns': columns,
                'filter_expr': filter_info['filter_expr']
            },
            metadata={
                'description': f"Vérifie la présence des colonnes {columns} dans {dataset}",
                'generated_for': parent_test_id
            }
        )
        implicit_tests.append(presence_test)
        
        # 2. Test de type des colonnes
        type_test = ImplicitTestCommand(
            command_id=f"{parent_test_id}_implicit_columns_type",
            command_type=CommandType.IMPLICIT_TEST,
            element_id=f"{parent_test_id}_implicit_columns_type",
            element_type="filter_columns_type_match",
            implicit_type=ImplicitTestType.FILTER_COLUMNS_TYPE_MATCH,
            parent_test_id=parent_test_id,
            parameters={
                'dataset': dataset,
                'columns': columns,
                'filter_expr': filter_info['filter_expr']
            },
            metadata={
                'description': f"Vérifie la compatibilité des types des colonnes {columns} dans {dataset}",
                'generated_for': parent_test_id
            }
        )
        implicit_tests.append(type_test)
        
        return implicit_tests
    
    def _resolve_dependencies(self):
        """
        Résout les dépendances entre commandes
        
        Règles:
        1. Un test dépend de sa métrique associée si spécifié
        2. Un test avec filtre dépend de ses tests implicites
        3. Les tests implicites dépendent du dataset source
        """
        print("\n🔗 Résolution des dépendances...")
        
        for command in self.sequence.commands:
            if command.command_type == CommandType.METRIC:
                # Dépendance sur son test de validation de paramètres
                param_validation = [
                    cmd for cmd in self.sequence.commands
                    if isinstance(cmd, ImplicitTestCommand) 
                    and cmd.implicit_type == ImplicitTestType.PARAMETERS_TYPE_VALIDATION
                    and cmd.parent_test_id == command.command_id
                ]
                
                for validation_test in param_validation:
                    command.dependencies.append(validation_test.command_id)
                    print(f"  {command.command_id} -> {validation_test.command_id} (param_validation)")
            
            elif command.command_type == CommandType.TEST:
                # Dépendance sur la métrique associée
                associated_metric = command.metadata.get('general', {}).get('associated_metric_id')
                if associated_metric and associated_metric in self._metric_commands:
                    command.dependencies.append(associated_metric)
                    print(f"  {command.command_id} -> {associated_metric}")
                
                # Dépendance sur son test de validation de paramètres
                param_validation = [
                    cmd for cmd in self.sequence.commands
                    if isinstance(cmd, ImplicitTestCommand) 
                    and cmd.implicit_type == ImplicitTestType.PARAMETERS_TYPE_VALIDATION
                    and cmd.parent_test_id == command.command_id
                ]
                
                for validation_test in param_validation:
                    command.dependencies.append(validation_test.command_id)
                    print(f"  {command.command_id} -> {validation_test.command_id} (param_validation)")
                
                # Dépendance sur les tests implicites de filtre
                implicit_tests = [
                    cmd for cmd in self.sequence.commands
                    if isinstance(cmd, ImplicitTestCommand) 
                    and cmd.parent_test_id == command.command_id
                    and cmd.implicit_type in [
                        ImplicitTestType.FILTER_COLUMNS_PRESENCE,
                        ImplicitTestType.FILTER_COLUMNS_TYPE_MATCH
                    ]
                ]
                
                for implicit_test in implicit_tests:
                    command.dependencies.append(implicit_test.command_id)
                    print(f"  {command.command_id} -> {implicit_test.command_id} (implicit)")
            
            elif command.command_type == CommandType.IMPLICIT_TEST:
                # Les tests implicites n'ont pas de dépendances
                # (ils s'exécutent en premier ou juste avant le test parent)
                pass
        
        # Construire le graphe de dépendances pour debug
        for command in self.sequence.commands:
            self.sequence.dependency_graph[command.command_id] = command.dependencies.copy()
    
    def _topological_sort(self):
        """
        Ordonnancement topologique des commandes
        
        Algorithme: Kahn's algorithm
        - Traite d'abord les éléments sans dépendances
        - Retire progressivement les dépendances satisfaites
        - Détecte les cycles
        """
        print("\n📋 Ordonnancement topologique...")
        
        # Calculer les degrés entrants (nombre de dépendances)
        in_degree = {cmd.command_id: 0 for cmd in self.sequence.commands}
        
        for command in self.sequence.commands:
            for dep in command.dependencies:
                in_degree[command.command_id] += 1
        
        # File des commandes prêtes (sans dépendances)
        ready_queue = [cmd.command_id for cmd in self.sequence.commands if in_degree[cmd.command_id] == 0]
        
        execution_order = []
        
        while ready_queue:
            # Prendre la prochaine commande prête (ordre d'entrée si pas de dépendances)
            current_id = ready_queue.pop(0)
            execution_order.append(current_id)
            
            # Réduire le degré des commandes qui dépendaient de celle-ci
            for command in self.sequence.commands:
                if current_id in command.dependencies:
                    in_degree[command.command_id] -= 1
                    
                    # Si toutes les dépendances sont satisfaites, ajouter à la file
                    if in_degree[command.command_id] == 0:
                        ready_queue.append(command.command_id)
        
        # Vérifier s'il y a un cycle (des commandes non traitées)
        if len(execution_order) != len(self.sequence.commands):
            remaining = [cmd.command_id for cmd in self.sequence.commands if cmd.command_id not in execution_order]
            raise ValueError(f"Cycle de dépendances détecté! Commandes bloquées: {remaining}")
        
        self.sequence.execution_order = execution_order
        print(f"  ✅ Ordre calculé: {len(execution_order)} commandes")
    
    def visualize_dependencies(self) -> str:
        """Visualise le graphe de dépendances"""
        lines = [
            "\n" + "=" * 80,
            "GRAPHE DE DÉPENDANCES",
            "=" * 80,
        ]
        
        for cmd_id, deps in self.sequence.dependency_graph.items():
            cmd = self.sequence.get_command(cmd_id)
            if cmd:
                lines.append(f"\n{cmd_id} ({cmd.command_type.value})")
                if deps:
                    for dep in deps:
                        dep_cmd = self.sequence.get_command(dep)
                        dep_type = dep_cmd.command_type.value if dep_cmd else "?"
                        lines.append(f"  ← {dep} ({dep_type})")
                else:
                    lines.append("  (aucune dépendance)")
        
        lines.append("\n" + "=" * 80)
        return "\n".join(lines)


# Fonction helper
def build_execution_sequence(config: DQConfig) -> ExecutionSequence:
    """
    Construit la séquence d'exécution pour une config DQ
    
    Args:
        config: Configuration DQ parsée
        
    Returns:
        Séquence d'exécution ordonnée
        
    Example:
        >>> config = load_dq_config("config.yaml")
        >>> sequence = build_execution_sequence(config)
        >>> print(sequence.summary())
    """
    sequencer = DQSequencer(config)
    return sequencer.build_sequence()


if __name__ == "__main__":
    from src.core.dq_parser import load_dq_config
    
    print("=" * 80)
    print("DQ SEQUENCER - Test")
    print("=" * 80)
    
    # Charger la config
    config = load_dq_config("dq/definitions/sales_complete_quality.yaml")
    
    # Construire la séquence
    sequencer = DQSequencer(config)
    sequence = sequencer.build_sequence()
    
    # Afficher le résumé
    print(sequence.summary())
    
    # Afficher le graphe de dépendances
    print(sequencer.visualize_dependencies())
