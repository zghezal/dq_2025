"""
Executor - Exécute les plans de séquençage.

Ce module prend un ExecutionPlan et l'exécute step par step, en respectant
les niveaux et les dépendances. Il stocke les résultats et gère les erreurs.

Usage:
    from src.plugins.executor import Executor
    
    executor = Executor(context)
    result = executor.execute(plan)
    
    print(f"Success: {result.success}")
    print(f"Metrics: {result.metrics}")
    print(f"Tests: {result.tests}")
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import traceback

from src.plugins.sequencer import ExecutionPlan, ExecutionStep, StepKind
from src.plugins.base import REGISTRY, Result
from src.plugins.output_schema import OutputSchema


class ExecutionStatus(str, Enum):
    """Statut d'exécution d'un step."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StepResult:
    """
    Résultat de l'exécution d'un step.
    
    Attributes:
        step: Le step exécuté
        status: Statut d'exécution
        result: Result du plugin (si succès)
        error: Message d'erreur (si échec)
        duration_ms: Durée d'exécution en millisecondes
        started_at: Timestamp de début
        finished_at: Timestamp de fin
    """
    step: ExecutionStep
    status: ExecutionStatus
    result: Optional[Result] = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    
    def __repr__(self):
        status_icon = {
            ExecutionStatus.SUCCESS: "✅",
            ExecutionStatus.FAILED: "❌",
            ExecutionStatus.SKIPPED: "⏭️",
            ExecutionStatus.RUNNING: "▶️",
            ExecutionStatus.PENDING: "⏸️"
        }
        icon = status_icon.get(self.status, "?")
        duration_str = f" ({self.duration_ms:.0f}ms)" if self.duration_ms > 0 else ""
        return f"{icon} {self.step.id} [{self.status.value}]{duration_str}"


@dataclass
class ExecutionResult:
    """
    Résultat complet de l'exécution d'un plan.
    
    Attributes:
        plan: Le plan exécuté
        success: True si tout a réussi
        step_results: Résultats de chaque step
        metrics: Valeurs des métriques (scalaires)
        dataframes: DataFrames produits par les métriques
        tests: Résultats des tests
        total_duration_ms: Durée totale
        started_at: Timestamp de début
        finished_at: Timestamp de fin
    """
    plan: ExecutionPlan
    success: bool
    step_results: List[StepResult] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    dataframes: Dict[str, Any] = field(default_factory=dict)  # metric_id -> DataFrame
    tests: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    total_duration_ms: float = 0.0
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    
    def get_step_result(self, step_id: str) -> Optional[StepResult]:
        """Récupère le résultat d'un step par son ID."""
        return next((sr for sr in self.step_results if sr.step.id == step_id), None)
    
    def get_failed_steps(self) -> List[StepResult]:
        """Retourne tous les steps qui ont échoué."""
        return [sr for sr in self.step_results if sr.status == ExecutionStatus.FAILED]
    
    def get_successful_steps(self) -> List[StepResult]:
        """Retourne tous les steps qui ont réussi."""
        return [sr for sr in self.step_results if sr.status == ExecutionStatus.SUCCESS]
    
    def summary(self) -> str:
        """Retourne un résumé textuel du résultat."""
        total = len(self.step_results)
        success_count = len(self.get_successful_steps())
        failed_count = len(self.get_failed_steps())
        
        lines = [
            "=" * 70,
            "EXECUTION SUMMARY",
            "=" * 70,
            f"Total steps: {total}",
            f"  ✅ Success: {success_count}",
            f"  ❌ Failed: {failed_count}",
            f"Duration: {self.total_duration_ms:.0f}ms",
            f"Overall: {'✅ SUCCESS' if self.success else '❌ FAILED'}",
        ]
        
        if failed_count > 0:
            lines.append("\nFailed steps:")
            for sr in self.get_failed_steps():
                lines.append(f"  {sr.step.id}: {sr.error}")
        
        lines.append("=" * 70)
        return "\n".join(lines)


class ExecutionContext:
    """
    Contexte d'exécution qui donne accès aux datasets et aux résultats intermédiaires.
    
    Le Context est l'objet passé à chaque plugin.run(). Il fournit:
    - load(alias): Charge un dataset
    - Les valeurs des métriques déjà calculées
    - Les DataFrames des métriques d'agrégation
    
    Attributes:
        loader: Fonction qui charge un dataset par son alias
        metrics_values: Valeurs scalaires des métriques
        metrics_dataframes: DataFrames produits par les métriques
        datasets: Cache des datasets chargés
    """
    
    def __init__(self, loader):
        """
        Initialise le contexte.
        
        Args:
            loader: Fonction (alias: str) -> pd.DataFrame
        """
        self.loader = loader
        self.metrics_values: Dict[str, Any] = {}
        self.metrics_dataframes: Dict[str, Any] = {}  # metric_id -> DataFrame
        self.datasets: Dict[str, Any] = {}  # alias -> DataFrame (cache)
    
    def load(self, alias: str):
        """
        Charge un dataset par son alias.
        
        Si le dataset a déjà été chargé, retourne la version en cache.
        Si l'alias commence par "virtual:", retourne le DataFrame de la métrique.
        
        Args:
            alias: Alias du dataset (ex: "sales_2024" ou "virtual:M-001")
        
        Returns:
            DataFrame
        """
        # Cas 1: Virtual dataset (produit par une métrique)
        if alias.startswith("virtual:"):
            metric_id = alias.replace("virtual:", "")
            if metric_id in self.metrics_dataframes:
                return self.metrics_dataframes[metric_id]
            raise ValueError(f"Virtual dataset '{alias}' non trouvé. "
                           f"La métrique {metric_id} n'a pas produit de DataFrame.")
        
        # Cas 2: Dataset normal
        if alias not in self.datasets:
            self.datasets[alias] = self.loader(alias)
        
        return self.datasets[alias]


class Executor:
    """
    Exécute un ExecutionPlan avec gestion des dépendances et des erreurs.
    
    L'executor:
    1. Exécute les steps niveau par niveau
    2. Stocke les résultats intermédiaires
    3. Gère les erreurs (continue ou stop selon la config)
    4. Valide les schémas de sortie des métriques
    
    Attributes:
        context: ExecutionContext pour accès aux datasets
        fail_fast: Si True, arrête dès le premier échec
    """
    
    def __init__(self, context: ExecutionContext, fail_fast: bool = False):
        """
        Initialise l'executor.
        
        Args:
            context: Context d'exécution
            fail_fast: Si True, arrête à la première erreur
        """
        self.context = context
        self.fail_fast = fail_fast
    
    def execute(self, plan: ExecutionPlan) -> ExecutionResult:
        """
        Exécute un plan d'exécution complet.
        
        Args:
            plan: Plan à exécuter
        
        Returns:
            ExecutionResult avec tous les résultats
        """
        exec_result = ExecutionResult(
            plan=plan,
            success=True,
            started_at=datetime.now()
        )
        
        print("=" * 70)
        print("🚀 STARTING EXECUTION")
        print("=" * 70)
        print(f"Total steps: {len(plan.steps)}")
        print(f"Max level: {plan.max_level}")
        print()
        
        # Exécuter niveau par niveau
        for level in range(plan.max_level + 1):
            level_steps = plan.get_steps_by_level(level)
            if not level_steps:
                continue
            
            print(f"[LEVEL {level}] Executing {len(level_steps)} step(s)")
            print("-" * 70)
            
            for step in level_steps:
                # Vérifier si on doit skip (dépendances échouées)
                if self._should_skip_step(step, exec_result):
                    step_result = StepResult(
                        step=step,
                        status=ExecutionStatus.SKIPPED,
                        error="Dépendance(s) échouée(s)"
                    )
                    exec_result.step_results.append(step_result)
                    print(f"  {step_result}")
                    continue
                
                # Exécuter le step
                step_result = self._execute_step(step)
                exec_result.step_results.append(step_result)
                
                # Stocker le résultat
                if step_result.status == ExecutionStatus.SUCCESS and step_result.result:
                    self._store_result(step, step_result.result, exec_result)
                
                print(f"  {step_result}")
                
                # Fail fast?
                if step_result.status == ExecutionStatus.FAILED:
                    exec_result.success = False
                    if self.fail_fast:
                        print("\n❌ Fail-fast mode: stopping execution")
                        break
            
            # Si fail-fast et on a déjà échoué, sortir
            if self.fail_fast and not exec_result.success:
                break
            
            print()
        
        exec_result.finished_at = datetime.now()
        exec_result.total_duration_ms = (
            (exec_result.finished_at - exec_result.started_at).total_seconds() * 1000
        )
        
        print(exec_result.summary())
        
        return exec_result
    
    def _should_skip_step(self, step: ExecutionStep, exec_result: ExecutionResult) -> bool:
        """
        Vérifie si un step doit être skippé (dépendances échouées).
        
        Args:
            step: Step à vérifier
            exec_result: Résultat d'exécution en cours
        
        Returns:
            True si le step doit être skippé
        """
        for dep_id in step.depends_on:
            dep_result = exec_result.get_step_result(dep_id)
            if dep_result and dep_result.status != ExecutionStatus.SUCCESS:
                return True
        return False
    
    def _execute_step(self, step: ExecutionStep) -> StepResult:
        """
        Exécute un step unique.
        
        Args:
            step: Step à exécuter
        
        Returns:
            StepResult avec le résultat
        """
        step_result = StepResult(
            step=step,
            status=ExecutionStatus.RUNNING,
            started_at=datetime.now()
        )
        
        try:
            # Récupérer le plugin
            plugin_class = REGISTRY.get(step.plugin_type)
            if not plugin_class:
                raise ValueError(f"Plugin '{step.plugin_type}' introuvable dans REGISTRY")
            
            # Instancier et exécuter
            plugin = plugin_class()
            result = plugin.run(self.context, **step.params)
            
            # Valider le schéma de sortie pour les métriques
            if step.kind == StepKind.METRIC:
                self._validate_output_schema(step, result, plugin_class)
            
            step_result.result = result
            step_result.status = ExecutionStatus.SUCCESS
            
        except Exception as e:
            step_result.status = ExecutionStatus.FAILED
            step_result.error = str(e)
            # Stocker le traceback complet pour debug
            step_result.result = Result(
                passed=False,
                message=f"Execution error: {e}",
                meta={"traceback": traceback.format_exc()}
            )
        
        finally:
            step_result.finished_at = datetime.now()
            step_result.duration_ms = (
                (step_result.finished_at - step_result.started_at).total_seconds() * 1000
            )
        
        return step_result
    
    def _validate_output_schema(self, step: ExecutionStep, result: Result, plugin_class):
        """
        Valide que le résultat correspond au schéma de sortie déclaré.
        
        Args:
            step: Step exécuté
            result: Result du plugin
            plugin_class: Classe du plugin
        
        Raises:
            ValueError: Si le schéma ne correspond pas
        """
        # Récupérer le schéma déclaré
        schema = plugin_class.output_schema(step.params)
        
        if schema is None:
            # Métrique scalaire, pas de validation de schéma
            return
        
        # La métrique devrait avoir produit un DataFrame
        if result.dataframe is None:
            raise ValueError(
                f"Métrique {step.id} déclare un output_schema mais n'a pas produit de DataFrame"
            )
        
        df = result.get_dataframe()
        if df is None:
            raise ValueError(f"Métrique {step.id}: DataFrame invalide")
        
        # Valider les colonnes
        actual_columns = list(df.columns)
        errors = schema.validate_actual_output(actual_columns)
        
        if errors:
            raise ValueError(
                f"Métrique {step.id}: schéma de sortie invalide - {errors}"
            )
    
    def _store_result(self, step: ExecutionStep, result: Result, exec_result: ExecutionResult):
        """
        Stocke le résultat d'un step dans le contexte et dans ExecutionResult.
        
        Args:
            step: Step exécuté
            result: Result du plugin
            exec_result: ExecutionResult en cours
        """
        if step.kind == StepKind.METRIC:
            # Stocker la valeur scalaire (si présente)
            if result.value is not None:
                self.context.metrics_values[step.id] = result.value
                exec_result.metrics[step.id] = result.value
            
            # Stocker le DataFrame (si présent)
            if result.dataframe is not None:
                df = result.get_dataframe()
                self.context.metrics_dataframes[step.id] = df
                exec_result.dataframes[step.id] = df
        
        elif step.kind == StepKind.TEST:
            # Stocker le résultat du test
            exec_result.tests[step.id] = {
                "passed": result.passed,
                "message": result.message,
                "value": result.value,
                "meta": result.meta
            }


def print_execution_result(exec_result: ExecutionResult):
    """
    Affiche un résultat d'exécution de manière détaillée.
    
    Args:
        exec_result: Résultat à afficher
    """
    print("\n" + "=" * 70)
    print("📊 DETAILED RESULTS")
    print("=" * 70)
    
    # Métriques
    if exec_result.metrics:
        print("\n[METRICS]")
        print("-" * 70)
        for metric_id, value in exec_result.metrics.items():
            print(f"  {metric_id}: {value}")
    
    # DataFrames
    if exec_result.dataframes:
        print("\n[DATAFRAMES]")
        print("-" * 70)
        for metric_id, df in exec_result.dataframes.items():
            print(f"  {metric_id}: {len(df)} rows x {len(df.columns)} columns")
            print(f"    Columns: {list(df.columns)}")
    
    # Tests
    if exec_result.tests:
        print("\n[TESTS]")
        print("-" * 70)
        for test_id, test_result in exec_result.tests.items():
            status = "✅ PASS" if test_result["passed"] else "❌ FAIL"
            print(f"  {test_id}: {status}")
            if test_result.get("message"):
                print(f"    Message: {test_result['message']}")
    
    print("\n" + "=" * 70)
