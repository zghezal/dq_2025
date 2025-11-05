# Fonctions utilitaires

import re
import urllib.parse as urlparse
from src.config import DATASET_MAPPING, project

try:
    import dataiku
except Exception:
    import dataiku_stub as dataiku


def list_project_datasets(stream=None, projet=None, dq_point=None):
    """Liste les datasets filtrés par contexte (stream, projet, dq_point)"""
    try:
        # Si contexte fourni, utiliser le mapping
        if stream and projet and dq_point:
            key = (stream, projet, dq_point)
            mapped_datasets = DATASET_MAPPING.get(key, [])
            if mapped_datasets:
                return mapped_datasets
        
        # Sinon, retourner tous les datasets disponibles
        return [d["name"] for d in project.list_datasets()]
    except Exception:
        return []


def get_columns_for_dataset(ds_name):
    """
    Récupère les colonnes d'un dataset dynamiquement depuis Spark.
    
    Ordre de priorité:
    1. SparkDQContext (si disponible) - RECOMMANDÉ pour lecture dynamique
    2. Dataiku Dataset (production)
    3. Lecture fichier local (fallback)
    
    Args:
        ds_name: Nom ou alias du dataset
    
    Returns:
        Liste des noms de colonnes
    """
    # 1. Essayer avec SparkDQContext (recommandé)
    try:
        from flask import current_app
        spark_ctx = getattr(current_app, 'spark_context', None)
        
        if spark_ctx and ds_name in spark_ctx.catalog:
            print(f"[DEBUG] ✅ Colonnes récupérées depuis Spark pour '{ds_name}'")
            return spark_ctx.get_columns(ds_name)
    except Exception as e:
        print(f"[DEBUG] Spark lookup failed for '{ds_name}': {e}")
    
    # 2. Essayer avec Dataiku (production)
    try:
        ds = dataiku.Dataset(ds_name)
        schema = ds.read_schema() or []
        columns = [c.get("name") for c in schema if c.get("name")]
        if columns:
            print(f"[DEBUG] Colonnes récupérées depuis Dataiku pour '{ds_name}'")
            return columns
    except Exception as e:
        print(f"[DEBUG] Dataiku lookup failed for '{ds_name}': {e}")
    
    # 3. Fallback: lecture fichier local
    import csv
    import os
    
    possible_paths = [
        f"sourcing/input/{ds_name}",  # Inventory path with extension
        f"./datasets/{ds_name}",       # Legacy path with extension  
        f"sourcing/input/{ds_name}.csv",  # Inventory path + .csv
        f"./datasets/{ds_name}.csv",      # Legacy path + .csv
        f"sourcing/input/{ds_name}.parquet",  # Inventory path + .parquet
        f"./datasets/{ds_name}.parquet",      # Legacy path + .parquet
    ]
    
    for file_path in possible_paths:
        if os.path.exists(file_path):
            # Handle parquet files
            if file_path.endswith('.parquet'):
                try:
                    import pandas as pd
                    df = pd.read_parquet(file_path)
                    print(f"[DEBUG] Colonnes récupérées depuis fichier Parquet: {file_path}")
                    return df.columns.tolist()
                except Exception as e:
                    print(f"[DEBUG] Error reading parquet {file_path}: {e}")
                    continue
            
            # Handle CSV files
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    headers = next(reader, [])
                    if headers:  # Only return if we found headers
                        print(f"[DEBUG] Colonnes récupérées depuis fichier CSV: {file_path}")
                        return headers
            except Exception as e:
                print(f"[DEBUG] Error reading CSV {file_path}: {e}")
                continue
    
    print(f"[DEBUG] ⚠️ Aucune colonne trouvée pour: {ds_name}")
    return []


def safe_id(s):
    """Nettoie une chaîne pour en faire un identifiant valide"""
    return re.sub(r"[^a-zA-Z0-9_]+", "_", s).lower()


def cfg_template():
    """Template de configuration DQ"""
    return {
        "version": "1.0",
        "globals": {
            "default_severity": "medium",
            "sample_size": 10,
            "fail_fast": False,
            "timezone": "Europe/Paris"
        },
        "context": {},
        "databases": [],
        "metrics": [],
        "tests": [],
        "orchestration": {"order": [], "dependencies": []}
    }


def parse_query(search: str):
    """Parse les paramètres d'URL"""
    if not search:
        return {}
    q = urlparse.parse_qs(search.lstrip("?"))
    return {k: (v[0] if isinstance(v, list) and v else v) for k, v in q.items()}


def list_dq_files(folder_id="dq_params", stream=None, project=None, dq_point=None):
    """Liste les fichiers DQ dans un folder Dataiku filtrés par contexte"""
    try:
        folder = dataiku.Folder(folder_id)
    except Exception:
        folder = None
    import os
    path = getattr(folder, "path", None) if folder is not None else None
    
    if path and os.path.isdir(path):
        all_files = [
            fn for fn in os.listdir(path)
            if fn.startswith("dq_config_") and (fn.endswith(".json") or fn.endswith(".yaml"))
        ]
    else:
        all_files = []

    # Also include local definitions from repo `dq/definitions` so templates stored
    # in the repository are visible alongside dataiku folder entries.
    try:
        from pathlib import Path
        # repo root is one level above 'src' in this repository layout
        repo_defs = Path(__file__).resolve().parents[1] / "dq" / "definitions"
        if repo_defs.exists():
            for p in sorted(repo_defs.glob("*.yaml")):
                # Represent local definitions as a path-like name so callers can
                # distinguish them if needed (we use the relative repo path).
                # store as 'dq/definitions/<file>' so read_dq_file can resolve it
                all_files.append(str("dq/definitions/" + p.name))
    except Exception:
        pass
    
    # Si aucun filtre, retourner tous les fichiers
    if not stream and not project and not dq_point:
        return sorted(all_files)

    # Filtrer par contexte. Note: si le fichier n'a pas de clé `context` ou si
    # la clé est vide pour un sous-champ, on considère cela comme un wildcard
    # (applicable partout). Ainsi un template sans contexte s'applique à tous.
    filtered_files = []
    for fn in all_files:
        # For local repo definitions we stored names like 'definitions/xxx.yaml'
        try:
            config = read_dq_file(fn, folder_id)
        except Exception:
            config = None
        if not config:
            continue

        ctx = config.get('context') or {}

        match = True
        # Only enforce match when the template provides a non-empty value
        if stream:
            if ctx.get('stream') and ctx.get('stream') != stream:
                match = False
        if project:
            if ctx.get('project') and ctx.get('project') != project:
                match = False
        if dq_point:
            if ctx.get('dq_point') and ctx.get('dq_point') != dq_point:
                match = False

        if match:
            filtered_files.append(fn)

    return sorted(filtered_files)


def first(val):
    """Helper pour extraire la première valeur d'une liste ou d'une chaîne (gestion pattern matching Dash)"""
    if val is None:
        return None
    if isinstance(val, list):
        return val[0] if val else None
    return val


def get_dq_folder_path(folder_id="dq_params"):
    """Retourne le chemin du folder DQ"""
    try:
        folder = dataiku.Folder(folder_id)
        path = getattr(folder, "path", None)
        return path if path else None
    except Exception:
        return None


def read_dq_file(filename, folder_id="dq_params"):
    """Lit le contenu d'un fichier DQ"""
    import os
    import json
    import yaml
    # If filename looks like a repo-local definition path (e.g. 'dq/definitions/foo.yaml'
    # or 'definitions/foo.yaml'), open it relative to the repo. This allows callers
    # that receive combined lists (dataiku + repo definitions) to read local files.
    try:
        from pathlib import Path
        # repo root is one level above 'src'
        repo_root = Path(__file__).resolve().parents[1]
        # Normalize
        norm_fn = filename.replace('\\', '/') if isinstance(filename, str) else ''
        if norm_fn.startswith('dq/definitions') or norm_fn.startswith('definitions/') or ('/definitions/' in norm_fn):
            candidate = repo_root / norm_fn
            if candidate.exists():
                try:
                    with open(candidate, 'r', encoding='utf-8') as f:
                        if norm_fn.endswith('.json'):
                            return json.load(f)
                        elif norm_fn.endswith('.yaml') or norm_fn.endswith('.yml'):
                            return yaml.safe_load(f)
                except Exception:
                    return None

        # Otherwise, try reading from the configured Dataiku folder path
        path = get_dq_folder_path(folder_id)
        if not path:
            return None

        filepath = os.path.join(path, filename)
        if not os.path.exists(filepath):
            return None

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                if filename.endswith('.json'):
                    return json.load(f)
                elif filename.endswith('.yaml') or filename.endswith('.yml'):
                    return yaml.safe_load(f)
        except Exception:
            return None
    except Exception:
        return None
    return None


def write_dq_file(filename, content, folder_id="dq_params"):
    """Écrit un fichier DQ"""
    import os
    import json
    import yaml
    
    path = get_dq_folder_path(folder_id)
    if not path:
        return False
    
    filepath = os.path.join(path, filename)
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            if filename.endswith('.json'):
                json.dump(content, f, ensure_ascii=False, indent=2)
            elif filename.endswith('.yaml') or filename.endswith('.yml'):
                yaml.dump(content, f, allow_unicode=True, default_flow_style=False)
        return True
    except Exception:
        return False


def delete_dq_file(filename, folder_id="dq_params"):
    """Supprime un fichier DQ"""
    import os
    
    path = get_dq_folder_path(folder_id)
    if not path:
        return False
    
    filepath = os.path.join(path, filename)
    if not os.path.exists(filepath):
        return False
    
    try:
        os.remove(filepath)
        return True
    except Exception:
        return False


def rename_dq_file(old_filename, new_filename, folder_id="dq_params"):
    """Renomme un fichier DQ"""
    import os
    
    path = get_dq_folder_path(folder_id)
    if not path:
        return False
    
    old_path = os.path.join(path, old_filename)
    new_path = os.path.join(path, new_filename)
    
    if not os.path.exists(old_path):
        return False
    if os.path.exists(new_path):
        return False
    
    try:
        os.rename(old_path, new_path)
        return True
    except Exception:
        return False


def duplicate_dq_file(filename, new_filename, folder_id="dq_params"):
    """Duplique un fichier DQ"""
    content = read_dq_file(filename, folder_id)
    if content is None:
        return False
    return write_dq_file(new_filename, content, folder_id)


def sanitize_metric(m: dict) -> dict:
    """Nettoie/normalise une définition de métrique.

    - Assure les clés attendues et types.
    - Normalise les types connus (ajoute 'missing_rate').
    - Retourne une nouvelle dict sans modifications destructives.
    """
    if not isinstance(m, dict):
        return {}

    # Ne plus restreindre les types statiquement : on accepte tout type fourni
    specific = m.get("specific") or {}
    out = {
        "id": m.get("id") or None,
        "type": m.get("type") or "unknown",
        # Pour la compatibilité avec le séquenceur, on fournit les paramètres sous la clé 'params'
        "params": {
            "dataset": m.get("database") or m.get("dataset") or specific.get("dataset") or "",
            "column": None,
            "where": m.get("where") or "",
            "expr": m.get("expr") or "",
        }
    }

    column_value = m.get("column") or specific.get("column") or specific.get("columns") or ""
    if isinstance(column_value, list):
        out["params"]["column"] = [c for c in column_value if c not in (None, "")]
    elif column_value not in (None, ""):
        out["params"]["column"] = column_value
    else:
        out["params"]["column"] = ""
    specific = m.get("specific")
    if specific:
        out["specific"] = specific
    for key in ["nature", "identification", "general", "condition", "export", "database", "column", "where", "expr", "columns", "database_filter"]:
        if key in m and m[key] not in (None, ""):
            out[key] = m[key]
    return out


def sanitize_test(t: dict) -> dict:
    """Nettoie/normalise une définition de test.

    - Assure les clés attendues, cast des valeurs numériques (threshold, min, max).
    - Définit des valeurs par défaut pour severity et sample_on_fail.
    """
    if not isinstance(t, dict):
        return {}

    # Accept any provided test type (discovery/registry will validate later)
    # Prefer general block for operational flags
    general_block = t.get("general") or {}
    severity_val = general_block.get("criticality") or t.get("severity") or "medium"
    sample_flag = bool(general_block.get("sample_on_fail") or t.get("sample_on_fail") or False)

    out = {
        "id": t.get("id") or None,
        "type": t.get("type") or "unknown",
        "severity": severity_val,
        "sample_on_fail": sample_flag,
    }

    # Preserve structured blocks if present
    for key in ["nature", "identification", "general"]:
        if key in t and t[key] not in (None, ""):
            out[key] = t[key]

    # Prefer 'specific' block for source details; fallback to legacy root keys for compatibility
    specific = t.get("specific")
    if isinstance(specific, dict) and specific:
        out["specific"] = specific
    else:
        # Source: metric or database/column (legacy)
        if t.get("metric"):
            out["metric"] = t.get("metric")
        else:
            out["database"] = t.get("database") or ""
            out["column"] = t.get("column") or ""
        if t.get("columns"):
            cols = t.get("columns")
            if isinstance(cols, (list, tuple, set)):
                out["columns"] = [c for c in cols if c]
            else:
                out["columns"] = cols

    # Threshold normalization
    thr = t.get("threshold")
    if isinstance(thr, dict):
        op = thr.get("op")
        val = thr.get("value")
        try:
            val_cast = float(val) if val is not None and val != "" else None
        except Exception:
            val_cast = val
        out["threshold"] = {"op": op, "value": val_cast}
    elif thr is not None:
        try:
            out["threshold"] = {"op": "=", "value": float(thr)}
        except Exception:
            out["threshold"] = {"op": "=", "value": thr}

    # Range params
    if t.get("min") is not None or t.get("max") is not None:
        try:
            vmin = float(t.get("min")) if t.get("min") not in (None, "") else None
        except Exception:
            vmin = t.get("min")
        try:
            vmax = float(t.get("max")) if t.get("max") not in (None, "") else None
        except Exception:
            vmax = t.get("max")
        out["min"] = vmin
        out["max"] = vmax

    # Regex pattern
    if t.get("pattern"):
        out["pattern"] = t.get("pattern")

    # Foreign key ref
    if t.get("ref"):
        out["ref"] = t.get("ref")

    specific = t.get("specific")
    if isinstance(specific, dict):
        out["specific"] = specific
    mode = t.get("mode")
    if mode:
        out["mode"] = mode

    return out


def sanitize_metrics(metrics_list: list) -> list:
    """Sanitize a list of metric dicts."""
    if not metrics_list:
        return []
    out = []
    for m in metrics_list:
        sm = sanitize_metric(m)
        if sm:
            out.append(sm)
    return out


def sanitize_tests(tests_list: list) -> list:
    """Sanitize a list of test dicts."""
    if not tests_list:
        return []
    out = []
    for t in tests_list:
        st = sanitize_test(t)
        if st:
            out.append(st)
    return out


def validate_metric_against_meta(metric: dict, meta: dict) -> list:
    """Validate a single metric dict against its meta. Returns list of issues (empty if ok)."""
    issues = []
    if not isinstance(metric, dict):
        issues.append("Metric is not a dict")
        return issues
    mtype = metric.get("type")
    if mtype != meta.get("label") and mtype not in (meta.get("label"),):
        # allow same
        pass
    # database requirement
    if meta.get("requires_database") and not metric.get("database"):
        issues.append(f"Metric '{metric.get('id')}' requires a database")
    if meta.get("requires_column") and not metric.get("column"):
        issues.append(f"Metric '{metric.get('id')}' requires a column")
    return issues


def validate_test(t: dict, metric_ids: list) -> list:
    issues = []
    if not isinstance(t, dict):
        issues.append("Test is not a dict")
        return issues
    ttype = t.get("type")
    if ttype is None:
        issues.append(f"Test '{t.get('id')}' missing type")
        return issues
    # If test references a metric, ensure it exists
    if t.get("metric") and t.get("metric") not in (metric_ids or []):
        issues.append(f"Test '{t.get('id')}' references unknown metric '{t.get('metric')}'")
    # For database-based tests, require database and column
    if not t.get("metric"):
        if not t.get("database"):
            issues.append(f"Test '{t.get('id')}' requires a database")
        if not t.get("column"):
            issues.append(f"Test '{t.get('id')}' requires a column")
    # Validate threshold numeric if present
    thr = t.get("threshold")
    if isinstance(thr, dict) and thr.get("value") is not None:
        try:
            float(thr.get("value"))
        except Exception:
            issues.append(f"Test '{t.get('id')}' threshold value is not numeric: {thr.get('value')}")
    return issues


def validate_cfg(cfg: dict) -> list:
    """Validate a whole DQ config dict. Returns list of issues (empty if ok)."""
    issues = []
    metrics = cfg.get("metrics", []) or []
    tests = cfg.get("tests", []) or []
    metric_ids = [m.get("id") for m in metrics if m.get("id")]

    # Use registry meta to validate metrics where possible
    try:
        from src.metrics_registry import METRICS as REG_METRICS
    except Exception:
        REG_METRICS = {}

    for m in metrics:
        mtype = m.get("type")
        meta = REG_METRICS.get(mtype, {})
        issues.extend(validate_metric_against_meta(m, meta))

    for t in tests:
        issues.extend(validate_test(t, metric_ids))

    return issues
