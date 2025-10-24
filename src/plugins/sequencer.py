"""
Séquenceur d'exécution pour les configurations DQ.

Ce module construit le plan d'exécution optimal depuis une configuration DQ.
Il détecte automatiquement les dépendances et ordonne les steps correctement.

Principes:
- Métriques avant tests (règle naturelle)
- Ordre d'apparition dans le JSON (stable et prévisible)
- Dépendances implicites détectées automatiquement

Usage:
    from src.plugins.sequencer import build_execution_plan
    
    plan = build_execution_plan(config, catalog)
    for step in plan.steps:
        print(f"Execute {step.kind} {step.id}")
"""

from typing import List, Dict, Set, Optional, Any
from dataclasses import dataclass
from enum import Enum


class StepKind(str, Enum):
    """Type d'étape dans le plan d'exécution."""
    METRIC = "metric"
    TEST = "test"


@dataclass
class ExecutionStep:
    """
    Une étape dans le plan d'exécution.
    
    Attributes:
        kind: Type d'étape (metric ou test)
        id: Identifiant unique de l'item (ex: "M-001", "T-001")
        plugin_type: Type de plugin à exécuter (ex: "missing_rate", "range")
        params: Paramètres de configuration du plugin
        depends_on: Liste des IDs dont cette étape dépend
        level: Niveau d'exécution (0 = pas de dépendances, 1 = dépend du niveau 0, etc.)
    """
    kind: StepKind
    id: str
    plugin_type: str
    params: Dict[str, Any]
    depends_on: List[str]
    level: int = 0
    
    def __repr__(self):
        deps = f", depends_on={self.depends_on}" if self.depends_on else ""
        return f"<Step {self.kind.value}:{self.id} (plugin={self.plugin_type}, level={self.level}{deps})>"


@dataclass
class ExecutionPlan:
    """
    Plan d'exécution complet pour une configuration DQ.
    
    Attributes:
        steps: Liste ordonnée des steps à exécuter
        max_level: Niveau maximal (utile pour la parallélisation future)
        metrics_count: Nombre de métriques
        tests_count: Nombre de tests
    """
    steps: List[ExecutionStep]
    max_level: int
    metrics_count: int
    tests_count: int
    
    def get_steps_by_level(self, level: int) -> List[ExecutionStep]:
        """Retourne tous les steps d'un niveau donné."""
        return [s for s in self.steps if s.level == level]
    
    def get_steps_by_kind(self, kind: StepKind) -> List[ExecutionStep]:
        """Retourne tous les steps d'un type donné."""
        return [s for s in self.steps if s.kind == kind]
    
    def validate(self) -> List[str]:
        """
        Valide le plan d'exécution.
        
        Returns:
            Liste des erreurs de validation (vide si OK)
        """
        errors = []
        
        # Vérifier que tous les IDs sont uniques
        ids = [s.id for s in self.steps]
        if len(ids) != len(set(ids)):
            duplicates = [x for x in ids if ids.count(x) > 1]
            errors.append(f"IDs dupliqués: {set(duplicates)}")
        
        # Vérifier que les dépendances existent
        all_ids = set(ids)
        for step in self.steps:
            for dep_id in step.depends_on:
                if dep_id not in all_ids:
                    errors.append(f"Step {step.id} dépend de {dep_id} qui n'existe pas")
        
        # Vérifier qu'il n'y a pas de cycles
        if self._has_cycle():
            errors.append("Cycle détecté dans les dépendances")
        
        return errors
    
    def _has_cycle(self) -> bool:
        """Détecte les cycles dans le graphe de dépendances."""
        # Construire le graphe
        graph = {step.id: step.depends_on for step in self.steps}
        
        # DFS pour détecter les cycles
        visited = set()
        rec_stack = set()
        
        def has_cycle_util(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle_util(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        for node in graph:
            if node not in visited:
                if has_cycle_util(node):
                    return True
        
        return False


class DependencyDetector:
    """
    Détecte les dépendances implicites entre steps.
    
    Une dépendance existe quand:
    - Un test référence "virtual:M-XXX" → dépend de la métrique M-XXX
    - Un test référence "metric: M-XXX" → dépend de la métrique M-XXX
    """
    
    @staticmethod
    def detect_dependencies(test_config: Dict, metric_ids: Set[str]) -> List[str]:
        """
        Détecte les dépendances d'un test.
        
        Args:
            test_config: Configuration du test
            metric_ids: Ensemble des IDs de métriques disponibles
        
        Returns:
            Liste des IDs de métriques dont le test dépend
        """
        dependencies = []
        
        # Cas 1: Test référence un dataset virtuel "virtual:M-XXX"
        database = test_config.get("database", "")
        if database and database.startswith("virtual:"):
            metric_id = database.replace("virtual:", "")
            if metric_id in metric_ids:
                dependencies.append(metric_id)
        
        # Cas 2: Test référence directement une métrique
        metric_ref = test_config.get("metric")
        if metric_ref and metric_ref in metric_ids:
            dependencies.append(metric_ref)
        
        # Cas 3: Test référence un "value_from_metric"
        value_from = test_config.get("value_from_metric")
        if value_from and value_from in metric_ids:
            dependencies.append(value_from)
        
        # Cas 4: Chercher dans les params nested
        params = test_config.get("params", {})
        if isinstance(params, dict):
            # Chercher récursivement
            for key, value in params.items():
                if key in ("metric", "value_from_metric", "metric_id") and value in metric_ids:
                    dependencies.append(value)
        
        return list(set(dependencies))  # Dédupliquer


class LevelAssigner:
    """
    Assigne les niveaux d'exécution aux steps.
    
    Le niveau détermine l'ordre d'exécution:
    - Niveau 0: Pas de dépendances
    - Niveau 1: Dépend de niveau 0
    - Niveau N: Dépend d'au moins un step de niveau N-1
    """
    
    @staticmethod
    def assign_levels(steps: List[ExecutionStep]) -> int:
        """
        Assigne les niveaux à tous les steps.
        
        Modifie les steps in-place et retourne le niveau maximal.
        
        Args:
            steps: Liste des steps (seront modifiés)
        
        Returns:
            Niveau maximal atteint
        """
        # Construire un dict id -> step pour lookup rapide
        step_dict = {s.id: s for s in steps}
        
        # Fonction récursive pour calculer le niveau d'un step
        def compute_level(step: ExecutionStep, visited: Set[str]) -> int:
            # Détecter les cycles
            if step.id in visited:
                raise ValueError(f"Cycle détecté: {step.id} référencé de manière circulaire")
            
            # Si déjà calculé, retourner
            if step.level > 0 or not step.depends_on:
                return step.level
            
            visited.add(step.id)
            
            # Le niveau est 1 + max des niveaux des dépendances
            max_dep_level = -1
            for dep_id in step.depends_on:
                dep_step = step_dict.get(dep_id)
                if dep_step:
                    dep_level = compute_level(dep_step, visited.copy())
                    max_dep_level = max(max_dep_level, dep_level)
            
            step.level = max_dep_level + 1
            return step.level
        
        # Calculer les niveaux pour tous les steps
        max_level = 0
        for step in steps:
            level = compute_level(step, set())
            max_level = max(max_level, level)
        
        return max_level


def build_execution_plan(config: Dict, catalog=None) -> ExecutionPlan:
    """
    Construit le plan d'exécution depuis une configuration DQ.
    
    Le plan ordonne les steps en respectant:
    1. Métriques avant tests (règle naturelle)
    2. Ordre d'apparition dans le JSON (stable)
    3. Dépendances détectées automatiquement
    
    Args:
        config: Configuration DQ avec "metrics" et "tests"
        catalog: VirtualCatalog optionnel (pour validation supplémentaire)
    
    Returns:
        ExecutionPlan avec steps ordonnés et niveaux assignés
    
    Raises:
        ValueError: Si la configuration est invalide ou contient des cycles
    
    Example:
        >>> config = {
        ...     "metrics": [
        ...         {"id": "M-001", "type": "aggregation_by_column", "params": {...}},
        ...         {"id": "M-002", "type": "missing_rate", "params": {...}}
        ...     ],
        ...     "tests": [
        ...         {"id": "T-001", "type": "range", "database": "virtual:M-001", ...}
        ...     ]
        ... }
        >>> plan = build_execution_plan(config)
        >>> print(plan.steps)
        [<Step metric:M-001 (level=0)>, <Step metric:M-002 (level=0)>, <Step test:T-001 (level=1)>]
    """
    metrics = config.get("metrics", [])
    tests = config.get("tests", [])
    
    if not metrics and not tests:
        raise ValueError("Configuration vide: aucune métrique ni test")
    
    steps: List[ExecutionStep] = []
    metric_ids: Set[str] = set()
    
    # 1. Créer les steps pour les métriques (niveau 0 par défaut)
    for metric in metrics:
        metric_id = metric.get("id")
        metric_type = metric.get("type")
        
        if not metric_id or not metric_type:
            raise ValueError(f"Métrique invalide (id ou type manquant): {metric}")
        
        step = ExecutionStep(
            kind=StepKind.METRIC,
            id=metric_id,
            plugin_type=metric_type,
            params=metric.get("params", {}),
            depends_on=[],  # Les métriques n'ont pas de dépendances (pour l'instant)
            level=0
        )
        steps.append(step)
        metric_ids.add(metric_id)
    
    # 2. Créer les steps pour les tests avec détection des dépendances
    detector = DependencyDetector()
    
    for test in tests:
        test_id = test.get("id")
        test_type = test.get("type")
        
        if not test_id or not test_type:
            raise ValueError(f"Test invalide (id ou type manquant): {test}")
        
        # Détecter les dépendances
        dependencies = detector.detect_dependencies(test, metric_ids)
        
        step = ExecutionStep(
            kind=StepKind.TEST,
            id=test_id,
            plugin_type=test_type,
            params=test.get("params", {}),
            depends_on=dependencies,
            level=0  # Sera recalculé
        )
        steps.append(step)
    
    # 3. Assigner les niveaux d'exécution
    assigner = LevelAssigner()
    max_level = assigner.assign_levels(steps)
    
    # 4. Trier les steps par niveau puis par ordre d'apparition
    # (l'ordre d'apparition est déjà préservé car on a ajouté dans l'ordre)
    steps.sort(key=lambda s: (s.level, s.kind.value))
    
    # 5. Créer le plan
    plan = ExecutionPlan(
        steps=steps,
        max_level=max_level,
        metrics_count=len([s for s in steps if s.kind == StepKind.METRIC]),
        tests_count=len([s for s in steps if s.kind == StepKind.TEST])
    )
    
    # 6. Valider le plan
    validation_errors = plan.validate()
    if validation_errors:
        raise ValueError(f"Plan d'exécution invalide: {validation_errors}")
    
    return plan


def print_execution_plan(plan: ExecutionPlan):
    """
    Affiche un plan d'exécution de manière lisible.
    
    Args:
        plan: Plan à afficher
    """
    print("=" * 70)
    print("EXECUTION PLAN")
    print("=" * 70)
    print(f"Total steps: {len(plan.steps)}")
    print(f"  - Metrics: {plan.metrics_count}")
    print(f"  - Tests: {plan.tests_count}")
    print(f"Max level: {plan.max_level}")
    print()
    
    # Grouper par niveau
    for level in range(plan.max_level + 1):
        level_steps = plan.get_steps_by_level(level)
        if level_steps:
            print(f"[LEVEL {level}] {len(level_steps)} step(s)")
            print("-" * 70)
            for step in level_steps:
                deps_str = f" (depends: {', '.join(step.depends_on)})" if step.depends_on else ""
                print(f"  {step.kind.value:6s} {step.id:8s} → {step.plugin_type}{deps_str}")
            print()
    
    print("=" * 70)
