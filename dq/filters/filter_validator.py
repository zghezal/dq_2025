# dq/filters/filter_validator.py
from __future__ import annotations

from typing import Dict, Tuple, Any, List, Optional

FilterDict = Dict[Tuple[Optional[str], str, Any], bool]

_TEXT   = {"string", "str", "object", "varchar", "char", "text"}
_INT    = {"int", "integer", "bigint", "smallint", "tinyint"}
_FLOAT  = {"float", "double", "decimal", "real", "numeric"}
_BOOL   = {"bool", "boolean"}
_DATE   = {"date", "datetime", "timestamp"}

def _type_code_matches(actual: str, expected_code: str) -> bool:
    a = (actual or "").lower()
    e = expected_code.upper()
    if e == "S": return a in _TEXT
    if e == "I": return a in _INT
    if e == "F": return a in _FLOAT
    if e == "N": return (a in _INT) or (a in _FLOAT)
    if e in {"T", "D"}: return a in _DATE
    if e == "B": return a in _BOOL
    return False

def validate_filter_against_schema(filter_dict: FilterDict, dataset_schema: Dict[str, str]) -> List[str]:
    """Vérifie : unicité du else, valeurs bool, colonnes présentes, types compatibles."""
    errors: List[str] = []

    else_keys = [
        k for k in filter_dict
        if isinstance(k, tuple) and len(k) == 3 and k[0] is None and str(k[1]).lower() == "else" and k[2] is None
    ]
    if len(else_keys) == 0:
        errors.append("Le filtre doit contenir une règle par défaut: (None, 'else', None).")
    elif len(else_keys) > 1:
        errors.append("Le filtre contient plusieurs règles 'else' (une seule attendue).")

    for k, v in filter_dict.items():
        if not isinstance(v, bool):
            errors.append(f"La valeur de {k} doit être booléenne (True/False).")

    for (col, cond_spec, _), _res in filter_dict.items():
        if col is None:
            continue
        if col not in dataset_schema:
            errors.append(f"Colonne '{col}' absente du dataset.")
            continue
        if not (isinstance(cond_spec, str) and "=" in cond_spec):
            errors.append(f"Spécification invalide pour '{col}': '{cond_spec}' (format attendu 'D=CODE').")
            continue
        prefix, expected_code = cond_spec.split("=", 1)
        if prefix != "D" or not expected_code:
            errors.append(f"Spécification invalide pour '{col}': '{cond_spec}'.")
            continue
        actual_type = dataset_schema[col]
        if not _type_code_matches(actual_type, expected_code):
            errors.append(f"Type incompatible pour '{col}': attendu {expected_code}, obtenu {actual_type}.")
    return errors

def _mk_control_id(prefix: str, seq: int, kind: str = "T") -> str:
    return f"{prefix}_{kind}-{seq:03d}"

def build_filter_precheck_tests(
    filter_name: str,
    filter_dict: FilterDict,
    dataset_schema: Dict[str, str],
    *,
    stream: str,
    zone: str,
    project: Optional[str] = None,
    start_seq: int = 1,
    criticality: str = "High",
) -> List[dict]:
    """Fabrique une liste de tests techniques (format DQ) pour la traçabilité UI."""
    prefix = f"{(stream or '')[:3].upper()}_{(zone or '')[:3].upper()}"
    tests: List[dict] = []
    seq = start_seq

    for (col, cond_spec, val), result in filter_dict.items():
        if col is None:
            continue
        expected_code = cond_spec.split("=", 1)[1] if "=" in cond_spec else "?"
        tests.append({
            "control_id": _mk_control_id(prefix, seq, "T"),
            "control_name": f"[FILTER: {filter_name}] {col}::{cond_spec}",
            "associated_metric_id": None,
            "functional_category_1": "Integrity",
            "functional_category_2": "Technical",
            "category": "filter_precheck",
            "description": f"Vérifie que la colonne '{col}' existe et matche {cond_spec}.",
            "preliminary_comments": f"Filter '{filter_name}' — exemple valeur: {val!r}",
            "parameters": {
                "column": col,
                "expected_type_code": expected_code,
                "filter_value_example": val,
                "filter_result_if_matches": result
            },
            "criticality": criticality,
            "result": None,
            "result_comments": None,
            "project": project,
            "stream": stream,
            "zone": zone
        })
        seq += 1

    if (None, "else", None) in filter_dict:
        tests.append({
            "control_id": _mk_control_id(prefix, seq, "T"),
            "control_name": f"[FILTER: {filter_name}] ELSE default",
            "associated_metric_id": None,
            "functional_category_1": "Integrity",
            "functional_category_2": "Technical",
            "category": "filter_precheck",
            "description": "Présence d'un cas par défaut 'else'.",
            "preliminary_comments": None,
            "parameters": {"has_else": True},
            "criticality": criticality,
            "result": None,
            "result_comments": None,
            "project": project,
            "stream": stream,
            "zone": zone
        })
    return tests

def evaluate_prechecks_and_block(precheck_tests: List[dict], filter_errors: List[str]) -> dict:
    blocked = False
    comments = None
    if filter_errors:
        blocked = True
        comments = " ; ".join(filter_errors)
        for t in precheck_tests:
            t["result"] = "Fail"
            t["result_comments"] = comments
    else:
        for t in precheck_tests:
            t["result"] = "Pass"
            t["result_comments"] = "Pré-vérifications OK."
    return {"blocked": blocked, "reason": comments or "OK"}
