"""Métriques et tests DQ simples.

Contient :
- missing_rate(df, column=None): retourne le taux de valeurs manquantes (0..1)
- count_where(df, filter): compte le nombre de lignes vérifiant une condition
- test_range(value, low, high, inclusive=True): test si value est entre low et high

Fonctions conçues pour être petites, testables et faciles à intégrer dans l'application.
"""
from typing import Optional, Any, Dict

import pandas as pd


def missing_rate(df: pd.DataFrame, column: Optional[str] = None) -> float:
    """Calcule le taux de valeurs manquantes.

    Args:
        df: DataFrame à analyser.
        column: nom de la colonne à analyser. Si None, calcule sur toutes les colonnes (taux global).

    Returns:
        float: taux de valeurs manquantes entre 0.0 et 1.0.

    Raises:
        TypeError: si df n'est pas un DataFrame.
        KeyError: si la colonne demandée n'existe pas.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")

    if column is None:
        total_cells = df.size
        if total_cells == 0:
            return 0.0
        missing = df.isna().sum().sum()
        return float(missing) / float(total_cells)

    if column not in df.columns:
        raise KeyError(f"Column '{column}' not found in DataFrame")

    total = len(df)
    if total == 0:
        return 0.0
    missing = df[column].isna().sum()
    return float(missing) / float(total)


def count_where(df: pd.DataFrame, filter: str) -> int:
    """Compte le nombre de lignes vérifiant une condition.

    Args:
        df: DataFrame à analyser.
        filter: expression pandas à évaluer (ex: "age < 0", "revenue == 0").

    Returns:
        int: nombre de lignes vérifiant la condition.

    Raises:
        TypeError: si df n'est pas un DataFrame.
        ValueError: si l'expression filter est invalide.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")

    if not filter or not isinstance(filter, str):
        raise ValueError("filter must be a non-empty string")

    try:
        mask = df.eval(filter)
        if not isinstance(mask, pd.Series):
            raise ValueError(f"Filter '{filter}' did not return a boolean Series")
        return int(mask.sum())
    except Exception as e:
        raise ValueError(f"Invalid filter expression '{filter}': {e}")



def dq_test_range(value: Any, low: Any, high: Any, inclusive: bool = True) -> Dict[str, Any]:
    """Teste qu'une valeur scalaire est entre deux bornes.

    Args:
        value: valeur à tester (supporte types comparables: numbers, str, pd.Timestamp...)
        low: borne inférieure.
        high: borne supérieure.
        inclusive: si True, utilise <= et >=, sinon < et >.

    Returns:
        dict: {"passed": bool, "message": str, "value": value, "low": low, "high": high}

    Notes:
        - Ne lève pas d'exception pour des comparaisons impossibles : renvoie passed=False et message explicite.
    """
    result = {"value": value, "low": low, "high": high}
    try:
        if inclusive:
            passed = (value >= low) and (value <= high)
        else:
            passed = (value > low) and (value < high)
    except Exception as e:
        return {**result, "passed": False, "message": f"Incomparable types: {e}"}

    message = "ok" if passed else f"value {value} out of range [{low}, {high}]" if inclusive else f"value {value} out of range ({low}, {high})"
    return {**result, "passed": bool(passed), "message": message}
