"""Package utilities pour l'application DQ.

Expose les fonctions de `src.metrics` pour import direct depuis `src`.
"""
from .metrics import missing_rate, dq_test_range

__all__ = ["missing_rate", "dq_test_range"]

