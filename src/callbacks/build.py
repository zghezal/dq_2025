# Callbacks de la page Build (wizard de création DQ)

import json
import os
import urllib.parse as urlparse
from datetime import datetime
from dash import html, dcc, Input, Output, State, ALL, MATCH, no_update, callback_context
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import yaml
import re
import copy

try:
    import dataiku
except Exception:
    import dataiku_stub as dataiku

from src.utils import (
    list_project_datasets,
    get_columns_for_dataset,
    safe_id,
    cfg_template,
    parse_query,
    first,
    sanitize_metrics,
    sanitize_tests,
    sanitize_metric,
    validate_cfg
)
from src.metrics_registry import get_metric_options, get_metric_meta
from src.inventory import get_project_tag, get_zone_tag
from dq.filters.filter_loader import list_filters, DEFAULT_ROOT
from src.dq_runner import run_dq_config
import pandas as pd
from dash import dash_table
from src.plugins.discovery import discover_all_plugins, ensure_plugins_discovered
from src.plugins.base import REGISTRY
from src.context.spark_context import SparkDQContext
from src.plugins.sequencer import build_execution_plan
from src.plugins.executor import Executor, ExecutionContext
import traceback
from uuid import uuid4


def _resolve_context(search, inventory_store):
    """Retourne (stream, project, zone) en combinant URL et store inventory."""
    q = parse_query(search or "") if search else {}
    stream = q.get("stream")
    project = q.get("project")
    zone = q.get("zone")

    inv_data = {} if inventory_store is no_update else (inventory_store or {})
    if (not stream or not project or not zone) and isinstance(inv_data, dict):
        datasets = inv_data.get("datasets") or []
        for item in datasets:
            if not isinstance(item, dict):
                continue
            stream = stream or item.get("stream")
            project = project or item.get("project")
            zone = zone or item.get("zone")
            if stream and project and zone:
                break
    if not zone and isinstance(inv_data, dict):
        zone = inv_data.get("zone") or zone
    return stream, project, zone


def build_id_prefix_from_context(search, inventory_store, kind: str):
    """Construit un préfixe d'ID à partir du contexte URL/inventory.

    kind: 'metric' or 'test'
    Retourne une chaîne comme 'ALMT_MACH_METRIC_'
    """
    stream, project, zone = _resolve_context(search, inventory_store)
    proj_tag = get_project_tag(stream or "", project or "") if project else (str(project).upper() + "_")
    zone_tag = get_zone_tag(stream or "", project or "", zone or "") if zone else (str(zone).upper() + "_")
    kind_tag = "METRIC_" if kind == "metric" else "TEST_"
    # ensure tags end with underscore
    if proj_tag and not proj_tag.endswith("_"):
        proj_tag = proj_tag + "_"
    if zone_tag and not zone_tag.endswith("_"):
        zone_tag = zone_tag + "_"
    return f"{proj_tag}{zone_tag}{kind_tag}".replace("__", "_")


def _resolve_filter_path(name, stream, project, zone):
    """Retourne le chemin JSON du filtre en respectant l'ordre de recherche."""
    candidates = []
    if stream and project and zone:
        candidates.append(os.path.join(DEFAULT_ROOT, stream, project, zone, f"{name}.json"))
    candidates.append(os.path.join(DEFAULT_ROOT, "definition", f"{name}.json"))
    candidates.append(os.path.join(DEFAULT_ROOT, f"{name}.json"))
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def _get_metric_output_columns(metric_id, metrics_store):
    """Retourne les colonnes produites par la métrique sélectionnée."""
    if not metric_id or not metrics_store:
        return []
    metric_def = None
    for item in metrics_store or []:
        if item and item.get("id") == metric_id:
            metric_def = copy.deepcopy(item)
            break
    if not metric_def:
        return []
    metric_type = metric_def.get("type")
    if not metric_type:
        return []
    try:
        ensure_plugins_discovered()
        plugins = discover_all_plugins(verbose=False)
        info = plugins.get(metric_type)
        plugin_class = getattr(info, "plugin_class", None) if info else None
        if plugin_class is None:
            raise ValueError("Plugin introuvable")
        schema = plugin_class.output_schema(metric_def)
        if schema and getattr(schema, "columns", None):
            return [c.name for c in schema.columns if getattr(c, "name", None)]
    except Exception:
        pass
    specific = metric_def.get("specific") or {}
    # Fallback sur la configuration si aucun schéma disponible
    column_field = specific.get("column")
    if not column_field:
        column_field = specific.get("columns")
    if isinstance(column_field, list):
        return [c for c in column_field if c]
    if isinstance(column_field, str) and column_field:
        return [column_field]
    return []


def generate_metric_description(metric):
    """Génère une description condensée d'une métrique"""
    parts = []
    
    # Type et database
    specific = metric.get("specific") or {}
    db = metric.get("database") or specific.get("dataset") or ""
    if db:
        parts.append(f"Base: {db}")
    
    # Colonnes
    col_candidate = metric.get("column")
    if not col_candidate:
        col_candidate = specific.get("column") or specific.get("columns") or []
    if isinstance(col_candidate, list) and col_candidate:
        parts.append(f"Colonnes: {', '.join(col_candidate)}")
    elif col_candidate:
        parts.append(f"Colonne: {col_candidate}")
    
    # Filtre WHERE / spécifique
    where = metric.get("where", "")
    filter_name = specific.get("filter")
    if where:
        parts.append(f"Filtre: {where}")
    elif filter_name:
        parts.append(f"Filtre: {filter_name}")
    
    # Expression
    expr = metric.get("expr", "")
    if expr:
        parts.append(f"Expr: {expr}")

    # Informations générales
    general = metric.get("general") or {}
    if metric.get("export") or general.get("export"):
        parts.append("Exportée")

    return " • ".join(parts) if parts else "-"


def _cast_optional_number(value):
    """Convertit une valeur en float si possible, sinon laisse None ou la valeur d'origine."""
    if value in (None, "", [], {}):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return value


def _parse_interval_rules(raw_value):
    """Parse la configuration JSON des bornes spécifiques à l'Interval Check."""
    if raw_value in (None, "", []):
        return []

    if isinstance(raw_value, list):
        parsed = raw_value
    elif isinstance(raw_value, str):
        text = raw_value.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
        except Exception as exc:
            raise ValueError(f"JSON invalide: {exc}") from exc
    else:
        raise ValueError("Format non supporté pour column_rules (attendu JSON ou liste)")

    if not isinstance(parsed, list):
        raise ValueError("Le JSON doit représenter une liste d'objets")

    rules = []
    for idx, item in enumerate(parsed, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Entrée #{idx} doit être un objet")

        columns = item.get("columns")
        if isinstance(columns, str):
            columns = [c.strip() for c in columns.split(",") if c.strip()]
        elif isinstance(columns, (list, tuple, set)):
            columns = [str(c).strip() for c in columns if c not in (None, "")]
        else:
            columns = []
        if not columns:
            raise ValueError(f"Entrée #{idx} : 'columns' est vide")

        lower = item.get("lower")
        if lower is None and "lower_value" in item:
            lower = item.get("lower_value")
        upper = item.get("upper")
        if upper is None and "upper_value" in item:
            upper = item.get("upper_value")

        rules.append({
            "columns": columns,
            "lower": _cast_optional_number(lower),
            "upper": _cast_optional_number(upper)
        })

    return rules


def _build_params_for_virtual_schema(metric: dict) -> dict:
    """Prépare les paramètres à fournir au plugin pour calculer le schéma virtuel."""
    sanitized = sanitize_metric(metric or {})
    params: dict = {}

    # Point de départ : params déjà présents (bruts ou sanitisés)
    for source in (metric.get("params"), sanitized.get("params")):
        if isinstance(source, dict):
            for key, value in source.items():
                if value in (None, "", [], {}):
                    continue
                params[key] = value

    # Bloc specific (nécessaire pour certains plugins comme missing_rate)
    specific_block = metric.get("specific") or sanitized.get("specific")
    if isinstance(specific_block, dict) and specific_block:
        params.setdefault("specific", specific_block)

    # Colonnes multiples (optionnelles)
    columns_value = metric.get("columns") or sanitized.get("columns")
    if columns_value not in (None, "", [], {}):
        params.setdefault("columns", columns_value)

    # Filtre dataset associé (legacy)
    database_filter = metric.get("database_filter") or sanitized.get("database_filter")
    if database_filter not in (None, "", [], {}):
        params.setdefault("database_filter", database_filter)

    skip_keys = {
        "id", "type", "params", "general", "nature", "identification",
        "specific", "columns", "database", "column", "where", "expr",
        "condition", "export", "database_filter"
    }

    for key, value in (metric or {}).items():
        if key in skip_keys:
            continue
        if value in (None, "", [], {}):
            continue
        params.setdefault(key, value)

    return params


def generate_test_description(test):
    """Construit une description lisible d'un test pour l'aperçu tableau."""
    if not isinstance(test, dict):
        return "-"

    parts: list[str] = []
    general = test.get("general") or {}
    severity = general.get("criticality") or test.get("severity")
    if severity:
        parts.append(f"Sévérité: {severity}")

    action = general.get("on_fail") if isinstance(general, dict) else None
    if action:
        parts.append(f"Action: {action}")

    spec = test.get("specific") or {}
    mode = spec.get("target_mode") or test.get("mode")
    if mode:
        parts.append(f"Mode: {mode}")

    if mode == "metric_value":
        metric_id = spec.get("metric_id") or test.get("metric")
        if metric_id:
            parts.append(f"Métrique: {metric_id}")
    else:
        database = spec.get("database") or test.get("database")
        if database:
            parts.append(f"Base: {database}")
        columns = spec.get("columns") or test.get("columns")
        if columns:
            if isinstance(columns, (list, tuple, set)):
                cols = ", ".join(str(c) for c in columns if c)
            else:
                cols = str(columns)
            if cols:
                parts.append(f"Colonnes: {cols}")

    lower_enabled = spec.get("lower_enabled")
    upper_enabled = spec.get("upper_enabled")
    lower_val = spec.get("lower_value") if lower_enabled else None
    upper_val = spec.get("upper_value") if upper_enabled else None
    if lower_val is not None or upper_val is not None:
        lower_display = lower_val if lower_val is not None else "-∞"
        upper_display = upper_val if upper_val is not None else "+∞"
        parts.append(f"Intervalle général: [{lower_display}, {upper_display}]")
    
    # Ajouter les règles par colonne pour interval_check
    column_rules = spec.get("column_rules") or []
    if column_rules:
        rules_count = len([r for r in column_rules if r.get("columns")])
        if rules_count > 0:
            parts.append(f"+ {rules_count} règle(s) par colonne")

    pattern = test.get("pattern")
    if pattern:
        parts.append(f"Pattern: {pattern}")

    return " • ".join(parts) if parts else "-"


def register_build_callbacks(app):
    """Enregistre tous les callbacks de la page Build"""
    
    # ===== Contexte et Datasets =====

    @app.callback(
        Output("run-context-store", "data"),
        Output({"role": "run-context", "field": "quarter"}, "value"),
        Output({"role": "run-context", "field": "stream"}, "value"),
        Output({"role": "run-context", "field": "project"}, "value"),
        Output({"role": "run-context", "field": "zone"}, "value"),
        Input("url", "search"),
        State("run-context-store", "data"),
        prevent_initial_call=False
    )
    def sync_run_context_from_url(search, current):
        data = dict(current or {})
        for key in ["quarter", "stream", "project", "zone"]:
            data.setdefault(key, "")
        q = parse_query(search) if search else {}
        # Pré-remplir stream/project/zone depuis l'URL si absents
        for key in ["stream", "project", "zone"]:
            if q.get(key) and not data.get(key):
                data[key] = q.get(key)
        return (
            data,
            data.get("quarter", ""),
            data.get("stream", ""),
            data.get("project", ""),
            data.get("zone", ""),
        )

    @app.callback(
        Output("run-context-store", "data", allow_duplicate=True),
        Input({"role": "run-context", "field": ALL}, "value"),
        State("run-context-store", "data"),
        prevent_initial_call=True
    )
    def persist_run_context(input_values, current):
        data = dict(current or {})
        fields = ["quarter", "stream", "project", "zone"]
        for field, value in zip(fields, input_values or []):
            data[field] = value or ""
        return data
    
    @app.callback(
        Output("ctx-banner", "children"),
        Input("url", "search")
    )
    def update_ctx_banner(search):
        """Affiche le contexte (Stream/Project/DQ Point) extrait de l'URL"""
        q = parse_query(search) if search else {}
        
        if not q.get("stream") or not q.get("project"):
            return dbc.Alert(
                "Contexte non défini (utilise l'accueil pour choisir un Stream et un Projet).",
                color="warning",
                className="mb-3"
            )
        zone_text = f" • Zone = {q['zone']}" if q.get("zone") else ""
        return dbc.Alert(
            f"Contexte: Stream = {q['stream']} • Projet = {q['project']}{zone_text}",
            color="info",
            className="mb-3"
        )

    @app.callback(
        Output("store_datasets", "data", allow_duplicate=True),
        Output("store_metrics", "data", allow_duplicate=True),
        Output("store_tests", "data", allow_duplicate=True),
        Output("metrics-list", "children", allow_duplicate=True),
        Output("tests-list", "children", allow_duplicate=True),
        Output("save-datasets-status", "children", allow_duplicate=True),
        Output("ds-picker", "value", allow_duplicate=True),
        Input("url", "pathname"),
        Input("url", "search"),
        prevent_initial_call='initial_duplicate'
    )
    def load_config_from_url(pathname, search):
        """Charge une configuration existante si load_config est présent dans l'URL"""
        from src.utils import read_dq_file
        
        # Ne traiter que si on est sur la page Build
        if pathname != "/build":
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update
        
        q = parse_query(search) if search else {}
        
        print(f"DEBUG load_config_from_url: pathname={pathname}, search={search}, q={q}")
        
        # Si load_config est présent, charger la configuration
        if q.get("load_config"):
            filename = q["load_config"]
            print(f"DEBUG: Chargement de la config {filename}")
            config = read_dq_file(filename, "dq_params")
            
            if config:
                # Extraire les données pour chaque store
                datasets = config.get("databases", [])
                # sanitize incoming metrics/tests
                metrics = sanitize_metrics(config.get("metrics", []) or [])
                tests = sanitize_tests(config.get("tests", []) or [])
                
                print(f"DEBUG: Config chargée - {len(datasets)} datasets, {len(metrics)} métriques, {len(tests)} tests")
                
                # Créer les listes visuelles pour métriques
                metrics_items = [
                    html.Pre(
                        json.dumps(m, ensure_ascii=False, indent=2),
                        className="p-2 mb-2",
                        style={"background": "#111", "color": "#eee"}
                    ) for m in metrics
                ]
                
                # Créer les listes visuelles pour tests
                tests_items = [
                    html.Pre(
                        json.dumps(t, ensure_ascii=False, indent=2),
                        className="p-2 mb-2",
                        style={"background": "#111", "color": "#eee"}
                    ) for t in tests
                ]
                
                # Extraire les datasets sélectionnés pour mettre à jour ds-picker
                selected_datasets = [d.get("dataset") for d in datasets if d.get("dataset")]
                
                status_msg = f"✅ Configuration chargée: {len(datasets)} dataset(s), {len(metrics)} métrique(s), {len(tests)} test(s)"
                
                return datasets, metrics, tests, html.Div(metrics_items), html.Div(tests_items), status_msg, selected_datasets
        
        # Sinon, ne pas mettre à jour (no_update)
        print("DEBUG: Pas de load_config dans l'URL")
        return no_update, no_update, no_update, no_update, no_update, no_update, no_update

    @app.callback(
        Output("ds-picker", "options"),
        Output("store_datasets", "data", allow_duplicate=True),
        Input("url", "search"),
        Input("inventory-datasets-store", "data"),
        State("store_datasets", "data"),
    prevent_initial_call='initial_duplicate'
    )
    def update_dataset_options(search, inv_store_data, current_data):
        """
        Met à jour les datasets disponibles selon le contexte et auto-charge le store.
        
        Flux:
        1. Si inventory store disponible → Utiliser les données du store
        2. Sinon, charger directement depuis l'URL (stream/project/zone) via inventory
        """
        from src.inventory import get_datasets_for_zone
        from flask import current_app
        from src.spark_inventory_adapter import register_inventory_datasets_in_spark
        
        print(f"[DEBUG] ⭐ update_dataset_options APPELÉ !")
        print(f"[DEBUG]   - search={search}")
        print(f"[DEBUG]   - inv_store_data={inv_store_data}")
        print(f"[DEBUG]   - current_data={current_data}")
        
        q = parse_query(search) if search else {}

        stream = q.get("stream")
        projet = q.get("project") 
        zone = q.get("zone")
        
        print(f"[DEBUG]   - Parsed: stream={stream}, project={projet}, zone={zone}")
        
        # Cas 1: Store disponible → Utiliser directement
        if inv_store_data and isinstance(inv_store_data, dict):
            items = inv_store_data.get("datasets", []) or []
            inv_zone = inv_store_data.get("zone")
            
            # derive dataset display names (prefer 'name', fallback to alias)
            names = [it.get("name") or it.get("alias") for it in items]
            options = [{"label": n, "value": n} for n in names]

            print(f"[DEBUG] ✅ Inventory store has {len(items)} datasets: {[it.get('alias') for it in items]}")

            # Auto-load datasets when:
            # 1. Store is empty (first load)
            # 2. Zone in URL matches zone in inventory (zone changed, force reload)
            should_auto_load = (
                stream and projet and zone and names and
                (not current_data or zone == inv_zone)
            )
            
            if should_auto_load:
                auto_data = []
                for it, name in zip(items, names):
                    alias = it.get("alias") or (name and name.split(".")[0].lower())
                    # Utiliser l'alias pour "dataset" aussi, car il sera résolu via l'inventaire
                    auto_data.append({"alias": alias, "dataset": alias})
                print(f"[DEBUG] Auto-loading {len(auto_data)} datasets from inventory into Builder: {auto_data}")
                return options, auto_data

            print(f"[DEBUG] Returning {len(options)} options from inventory, current_data unchanged")
            return options, current_data or no_update

        # Cas 2: Store vide mais URL contient stream/project/zone → Charger depuis inventory
        if stream and projet and zone:
            print(f"[DEBUG] 🔄 Store vide, chargement depuis inventory: {stream}/{projet}/{zone}")
            datasets = get_datasets_for_zone(zone, stream_id=stream, project_id=projet) or []
            
            if datasets:
                # Enregistrer dans Spark
                spark_ctx = getattr(current_app, 'spark_context', None)
                if spark_ctx:
                    try:
                        register_inventory_datasets_in_spark(spark_ctx, datasets)
                        print(f"[DEBUG] ✅ {len(datasets)} datasets enregistrés dans Spark catalog")
                    except Exception as e:
                        print(f"[DEBUG] ⚠️ Erreur lors de l'enregistrement Spark: {e}")
                
                # Construire options et auto-load
                names = [d.get("name") or d.get("alias") for d in datasets]
                options = [{"label": n, "value": n} for n in names]
                
                auto_data = []
                for d, name in zip(datasets, names):
                    alias = d.get("alias") or (name and name.split(".")[0].lower())
                    # Utiliser l'alias pour "dataset" aussi, car il sera résolu via l'inventaire
                    auto_data.append({"alias": alias, "dataset": alias})
                
                print(f"[DEBUG] ✅ Chargement direct réussi: {len(auto_data)} datasets depuis inventory")
                return options, auto_data

        # Aucune donnée disponible
        print(f"[DEBUG] ⚠️ No inventory data available, returning empty options")
        return [], current_data or no_update

    @app.callback(
        Output("alias-mapper", "children"),
        Input("ds-picker", "value")
    )
    def render_alias_mapper(selected):
        """Affiche les champs d'alias pour les datasets sélectionnés"""
        if not selected:
            return html.Div([html.Em("Sélectionne au moins un dataset.")])
        rows = []
        for ds in selected:
            rows.append(dbc.Row([
                dbc.Col(
                    html.Div([
                        html.Span(ds, className="me-2"),
                        dbc.Button(
                            "👁️ Schéma",
                            id={"role": "dataset-preview", "ds": ds},
                            color="info",
                            size="sm",
                            outline=True,
                            className="py-0"
                        )
                    ], className="d-flex align-items-center"),
                    md=5
                ),
                dbc.Col(dcc.Input(
                    id={"role": "alias-input", "ds": ds},
                    type="text",
                    value=ds.lower(),
                    style={"width": "100%"},
                    persistence=True,
                    persistence_type="session",
                    autoComplete="off"
                ), md=7)
            ], className="py-1 border-bottom"))
        return dbc.Container(rows, fluid=True)

    @app.callback(
        Output("save-datasets-status", "children"),
        Output("store_datasets", "data", allow_duplicate=True),
        Input("save-datasets", "n_clicks"),
        State("ds-picker", "value"),
        State({"role": "alias-input", "ds": ALL}, "value"),
        State({"role": "alias-input", "ds": ALL}, "id"),
        prevent_initial_call=True
    )
    def save_datasets(n, selected, alias_values, alias_ids):
        """Enregistre les datasets et leurs alias"""
        if not n:
            return "", None
        if not selected:
            return "Aucun dataset sélectionné.", None
        alias_map = {}
        if alias_values and alias_ids:
            for v, i in zip(alias_values, alias_ids):
                alias_map[i["ds"]] = v or i["ds"].lower()
        data = [{"alias": alias_map.get(ds, ds.lower()), "dataset": ds} for ds in selected]
        return f"{len(data)} dataset(s) enregistrés.", data

    # === Aperçu Schéma (Builder) ===
    @app.callback(
        Output("dataset-schema-modal-body", "children"),
        Output("dataset-schema-modal", "is_open", allow_duplicate=True),
        Output("dataset-schema-modal-title", "children"),
        Input({"role": "dataset-preview", "ds": ALL}, "n_clicks"),
        Input({"role": "metric-db-preview"}, "n_clicks"),
        State({"role": "metric-db"}, "value"),
        State("store_datasets", "data"),
        prevent_initial_call=True
    )
    def open_schema_modal(dataset_clicks, metric_click, selected_alias, store_datasets):
        """Ouvre le modal de schéma depuis l'alias mapper ou le formulaire métrique."""
        from flask import current_app
        ctx = callback_context
        triggered = getattr(ctx, "triggered_id", None)
        if not triggered:
            # Fallback for older Dash versions
            if not ctx.triggered:
                return no_update, no_update, no_update
            import json as _json
            try:
                triggered = _json.loads(ctx.triggered[0]["prop_id"].split(".")[0])
            except Exception:
                triggered = ctx.triggered[0]["prop_id"].split(".")[0]

        alias = None
        if isinstance(triggered, dict) and triggered.get("role") == "dataset-preview":
            alias = triggered.get("ds")
        elif isinstance(triggered, dict) and triggered.get("role") == "metric-db-preview":
            alias = selected_alias
        else:
            return no_update, no_update, no_update

        original_label = alias

        if not alias:
            return html.Div("Aucun dataset sélectionné.", className="text-muted"), True, "Erreur"

        # Resolve alias vs dataset name mapping using store
        resolved = None
        dataset_name = None
        if store_datasets and isinstance(store_datasets, list):
            for item in store_datasets:
                if not isinstance(item, dict):
                    continue
                store_alias = item.get("alias")
                store_dataset = item.get("dataset")
                if alias == store_alias or alias == store_dataset:
                    resolved = store_alias or alias
                    dataset_name = store_dataset or alias
                    break

        alias = resolved or alias

        spark_ctx = getattr(current_app, 'spark_context', None)
        if not spark_ctx:
            message = html.Div([
                html.P("⚠️ Prévisualisation du schéma non disponible", className="text-warning mb-2"),
                html.Small("Le contexte Spark n'est pas initialisé. Cette fonctionnalité nécessite un environnement Spark configuré.", 
                          className="text-muted")
            ])
            return message, True, f"Schéma: {alias}"

        try:
            catalog = getattr(spark_ctx, "catalog", {})
            catalog_source = catalog.get(alias)
            if catalog_source is None and dataset_name:
                catalog_source = catalog.get(dataset_name)

            # Fallbacks: tester différentes variantes du nom pour retrouver la source
            candidates_for_source = []
            if alias:
                candidates_for_source.append(alias)
            if dataset_name:
                candidates_for_source.append(dataset_name)
            if dataset_name and "." in dataset_name:
                base_name = dataset_name.rsplit(".", 1)[0]
                candidates_for_source.append(base_name)

            resolved_source = catalog_source
            for candidate in candidates_for_source:
                if resolved_source is None:
                    resolved_source = catalog.get(candidate)

            if isinstance(resolved_source, pd.DataFrame):
                source_desc = "Source : Pandas DataFrame (en mémoire)"
            elif isinstance(resolved_source, str):
                if resolved_source.endswith('.csv'):
                    source_desc = f"Source : Fichier CSV ({resolved_source})"
                elif resolved_source.endswith('.parquet'):
                    source_desc = f"Source : Fichier Parquet ({resolved_source})"
                else:
                    source_desc = f"Source : Table SQL/Spark ({resolved_source})"
            elif resolved_source is None:
                if dataset_name:
                    source_desc = f"Source : inconnue (alias enregistré: {alias}, dataset: {dataset_name})"
                else:
                    source_desc = "Source : inconnue (non enregistrée dans le catalog)"
            else:
                source_desc = f"Source : {type(resolved_source).__name__}"

            schema_rows = []
            schema_error = None
            sample_card = html.Div()
            df = None
            load_error = None

            load_candidates = []
            if alias:
                load_candidates.append(alias)
            if dataset_name and dataset_name not in load_candidates:
                load_candidates.append(dataset_name)
            if dataset_name and "." in dataset_name:
                base_name = dataset_name.rsplit(".", 1)[0]
                if base_name not in load_candidates:
                    load_candidates.append(base_name)

            load_errors = []
            for candidate in load_candidates:
                try:
                    df = spark_ctx.load(candidate, cache=False)
                    alias = candidate  # mémorise l'alias qui fonctionne
                    break
                except Exception as load_exc:
                    load_errors.append(str(load_exc))

            if df is None and load_errors:
                load_error = "; ".join(load_errors)

            if df is not None:
                schema_rows = [
                    {"Colonne": field.name, "Type": field.dataType.simpleString()}
                    for field in df.schema.fields
                ]
                try:
                    sample_pdf = df.limit(10).toPandas()
                    table = dash_table.DataTable(
                        data=sample_pdf.to_dict(orient='records'),
                        columns=[{"name": c, "id": c} for c in sample_pdf.columns],
                        page_size=5,
                        style_table={'overflowX': 'auto'},
                        style_cell={'textAlign': 'left'}
                    )
                    sample_card = html.Div([html.H6("Aperçu (10 premières lignes)", className="mt-2"), table])
                except Exception as sample_exc:
                    sample_card = html.Div(
                        f"Aucun aperçu disponible ({sample_exc}).",
                        className="text-muted small"
                    )
            else:
                try:
                    cols = None
                    peek_candidates = load_candidates or [alias]
                    for candidate in peek_candidates:
                        try:
                            cols = spark_ctx.peek_schema(candidate)
                            alias = candidate
                            break
                        except Exception:
                            continue
                    if cols is None:
                        raise ValueError(load_error or "Schéma introuvable")
                    schema_rows = [{"Colonne": col, "Type": "?"} for col in cols]
                except Exception as schema_exc:
                    schema_error = schema_exc

            if not schema_rows:
                schema_section = html.Div(
                    f"Impossible de récupérer le schéma ({schema_error or load_error}).",
                    className="text-danger"
                )
            else:
                schema_section = dash_table.DataTable(
                    data=schema_rows,
                    columns=[
                        {"name": "Colonne", "id": "Colonne"},
                        {"name": "Type", "id": "Type"}
                    ],
                    style_table={'overflowX': 'auto'},
                    style_cell={'textAlign': 'left', 'padding': '6px'},
                    page_size=20
                )

            card = html.Div([
                html.Div(source_desc, className="text-muted mb-2"),
                html.H6("Schéma", className="mt-1"),
                schema_section,
                sample_card
            ])
            title_label = original_label or alias
            if dataset_name and dataset_name != title_label:
                title_label = f"{title_label} ({dataset_name})"
            title = f"Prévisualisation — {title_label}"
            return card, True, title
        except Exception as e:
            err = html.Div(f"Erreur lors de la lecture du dataset: {e}", className="text-danger")
            return err, True, "Erreur"

    @app.callback(
        Output("dataset-schema-modal", "is_open", allow_duplicate=True),
        Input("dataset-schema-modal-close", "n_clicks"),
        State("dataset-schema-modal", "is_open"),
        prevent_initial_call=True,
    )
    def close_schema_modal(n, is_open):
        if not n:
            return is_open
        return False

    # ===== Métriques =====
    
    @app.callback(
        Output("metric-params", "children"),
        Input("metric-type", "value"),
        State("store_datasets", "data"),
        State("url", "search"),
        State("inventory-datasets-store", "data"),
        State("store_metrics", "data"),
        State("run-context-store", "data")
    )
    def render_metric_form(metric_type, ds_data, search, inventory_store, stored_metrics, run_context_data):
        """Affiche le formulaire de création de métrique selon le type avec groupes visuels"""
        if not metric_type:
            return dbc.Alert("Choisis un type de métrique.", color="light")
        quarter_value = (run_context_data or {}).get("quarter")
        if not quarter_value:
            return dbc.Alert("Sélectionne d'abord un quarter dans le contexte avant de configurer une métrique.", color="warning")
        ds_aliases = [d["alias"] for d in (ds_data or [])]
        # Si pas de datasets dans le store, on continue quand même (auto-chargement en cours)

        stream_ctx, project_ctx, zone_ctx = _resolve_context(search, inventory_store)

        available_filters = []
        filters_error = None
        if metric_type == "missing_rate":
            try:
                available_filters = list_filters(
                    stream=stream_ctx,
                    project=project_ctx,
                    zone=zone_ctx,
                )
            except Exception as exc:
                filters_error = str(exc)

        filters_context_label = None
        if stream_ctx or project_ctx or zone_ctx:
            filters_context_label = "/".join([
                stream_ctx or "?",
                project_ctx or "?",
                zone_ctx or "?",
            ])

        meta = get_metric_meta(metric_type)
        metric_label = meta.get("name") if meta else ""
        metric_description = meta.get("description") if meta else ""

        # build id prefix and propose a number
        prefix = build_id_prefix_from_context(search, inventory_store, "metric")
        proposed_num = 1
        try:
            existing = stored_metrics or []
            pattern = re.compile(rf"^{re.escape(prefix)}(\d+)$")
            nums = [int(m.group(1)) for m in (pattern.match(x.get("id" or "") or "") for x in existing) if m]
            if nums:
                proposed_num = max(nums) + 1
        except Exception:
            proposed_num = 1

        nature_card = dbc.Card([
            dbc.CardHeader("📘 Nature de la métrique"),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label("Choix de la métrique"),
                        dcc.Input(
                            id={"role": "metric-nature", "field": "name"},
                            type="text",
                            value=metric_label,
                            placeholder="Sélectionné automatiquement",
                            className="form-control",
                            disabled=True,
                            style={"backgroundColor": "#f8f9fa"},
                            persistence=True,
                            persistence_type="session",
                            autoComplete="off"
                        )
                    ], md=6),
                    dbc.Col([
                        html.Label("Commentaires préliminaires"),
                        dcc.Textarea(
                            id={"role": "metric-nature", "field": "comments"},
                            placeholder="Hypothèses, prérequis, périmètre…",
                            className="form-control",
                            style={"minHeight": "90px"},
                            persistence=True,
                            persistence_type="session"
                        )
                    ], md=6)
                ]),
                html.Label("Description", className="mt-3"),
                dcc.Textarea(
                    id={"role": "metric-nature", "field": "description"},
                    value=metric_description or "",
                    placeholder="Explique l'objectif de la métrique",
                    className="form-control",
                    style={"minHeight": "100px"},
                    persistence=True,
                    persistence_type="session"
                )
            ])
        ], className="mb-3")

        identification_card = dbc.Card([
            dbc.CardHeader("🪪 Identification de la métrique"),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label("Quarter (contexte)"),
                        dcc.Input(
                            id={"role": "metric-id-quarter"},
                            type="text",
                            value=quarter_value,
                            disabled=True,
                            className="form-control",
                            style={"backgroundColor": "#f8f9fa"}
                        )
                    ], md=4)
                ], className="mb-3"),
                dbc.Row([
                    dbc.Col([
                        html.Label("Préfixe"),
                        dcc.Input(
                            id={"role": "metric-id-prefix"},
                            type="text",
                            value=prefix,
                            disabled=True,
                            className="form-control",
                            persistence=True,
                            persistence_type="session",
                            style={"backgroundColor": "#f8f9fa"}
                        )
                    ], md=6),
                    dbc.Col([
                        html.Label("Numéro"),
                        dcc.Input(
                            id={"role": "metric-id"},
                            type="number",
                            value=None,
                            placeholder=f"Proposé: {proposed_num}",
                            style={"width": "100%"},
                            persistence=True,
                            persistence_type="session",
                            min=1
                        ),
                        html.Small(
                            "Saisis seulement le numéro. Le préfixe est verrouillé.",
                            className="text-muted"
                        )
                    ], md=6)
                ])
            ])
        ], className="mb-3")

        general_card = dbc.Card([
            dbc.CardHeader("🧩 Paramétrage général"),
            dbc.CardBody([
                html.Label("Exporter la métrique"),
                dbc.Checklist(
                    id={"role": "metric-general", "field": "export"},
                    options=[{"label": " Oui, inclure cette métrique dans les exports", "value": "export"}],
                    value=["export"],
                    persistence=True,
                    persistence_type="session",
                    className="mt-2"
                ),
                html.Small("Décoche si la métrique doit rester interne", className="text-muted")
            ])
        ], className="mb-3")

        # Groupe 2: Sélection Dataset & Filtre
        db_visible = meta.get("requires_database", True)

        dataset_columns = [
            dbc.Col([
                html.Label("Dataset (alias)"),
                html.Div([
                    dcc.Dropdown(
                        id={"role": "metric-db"},
                        options=[{"label": a, "value": a} for a in ds_aliases],
                        value=ds_aliases[0] if ds_aliases else None,
                        clearable=False,
                        persistence=True,
                        persistence_type="session",
                        style={"flex": 1}
                    ),
                    dbc.Button(
                        "👁️ Schéma",
                        id={"role": "metric-db-preview"},
                        color="info",
                        outline=True,
                        size="sm",
                        className="ms-2",
                        disabled=not bool(ds_aliases)
                    )
                ], className="d-flex align-items-center", style={"display": "flex" if db_visible else "none"})
            ], md=6, style={"display": "block" if db_visible else "none"})
        ]
        if metric_type == "missing_rate":
            filter_controls = [html.Label("Filtre JSON (banque)")]
            if available_filters:
                filter_controls.append(dcc.Dropdown(
                    id={"role": "missing-rate-filter", "name": "missing_rate"},
                    options=[{"label": f"{name}.json", "value": name} for name in available_filters],
                    placeholder="Sélectionne un filtre JSON",
                    clearable=True,
                    persistence=True,
                    persistence_type="session",
                ))
                helper = f"{len(available_filters)} filtre(s) disponibles"
                if filters_context_label:
                    helper += f" pour {filters_context_label}"
                filter_controls.append(html.Small(helper, className="text-muted d-block mb-2"))
            else:
                msg = "Aucun filtre détecté pour le contexte courant."
                if filters_context_label:
                    msg += f" ({filters_context_label})"
                filter_controls.append(dbc.Alert(msg, color="warning", className="mb-2"))
                if filters_error:
                    filter_controls.append(dbc.Alert(
                        f"Erreur lors du chargement des filtres : {filters_error}",
                        color="danger",
                        className="mb-2"
                    ))
            filter_controls.append(html.Div(
                "Sélectionne un filtre pour afficher son contenu.",
                id={"role": "missing-rate-filter-preview", "name": "missing_rate"},
                className="text-muted small border rounded p-2",
                style={"whiteSpace": "pre-wrap", "fontFamily": "monospace"}
            ))
            dataset_columns.append(dbc.Col(filter_controls, md=6))
            dataset_columns.append(
                dbc.Col([
                    html.Label("Colonnes à analyser"),
                    dcc.Dropdown(
                        id={"role": "metric-column", "form": "metric"},
                        options=[],
                        multi=True,
                        placeholder="Choisir une ou plusieurs colonnes",
                        clearable=True,
                        persistence=True,
                        persistence_type="session"
                    ),
                    html.Small(
                        "Laisse vide pour utiliser toutes les colonnes du dataset.",
                        className="text-muted"
                    )
                ], md=6)
            )
        else:
            dataset_columns.append(
                dbc.Col([
                    html.Label("Filtre (WHERE clause)"),
                    dcc.Input(
                        id={"role": "metric-where"},
                        type="text",
                        placeholder="Ex: status = 'active'",
                        className="form-control",
                        persistence=True,
                        persistence_type="session"
                    ),
                    html.Small("Optionnel : condition SQL pour filtrer les données", className="text-muted")
                ], md=6)
            )

        dataset_header = "🧩 Paramétrage spécifique" if metric_type == "missing_rate" else "📊 Sélection Dataset & Filtre"
        dataset_row = [
            dbc.CardHeader(dataset_header),
            dbc.CardBody([
                html.Small("Sélectionnez parmi les datasets configurés à l'étape 1 (Datasets)", className="text-muted d-block mb-2"),
                dbc.Row(dataset_columns)
            ])
        ]

        dataset_card = dbc.Card(dataset_row, className="mb-3")

        # Groupe 3: Sélection de Colonne et Options
        column_visible = meta.get("requires_column", False)
        
        column_content = []
        if column_visible:
            column_content.append(html.Label("Colonne(s)"))
            column_content.append(dcc.Dropdown(
                id={"role": "metric-column", "form": "metric"},
                options=[],
                multi=True,  # Permettre sélection multiple
                placeholder="Choisir une ou plusieurs colonnes",
                clearable=True,
                persistence=True,
                persistence_type="session"
            ))
            column_content.append(html.Small("Sélectionnez une ou plusieurs colonnes pour la métrique", className="text-muted d-block mb-3"))
            column_content.append(html.Div(id="metric-helper", className="text-muted small"))
        
        # Paramètres supplémentaires (hors dataset et columns)
        params = meta.get("params", []) if meta else []
        for p in params:
            if isinstance(p, str):
                p = {"name": p, "label": p, "type": "text"}
            p_type = p.get("type") or "text"
            
            # Ignorer dataset et columns (déjà gérés)
            if p_type in ["dataset", "columns"]:
                continue

            p_name = p.get("name")
            if p_name == "specific":
                continue
                
            # text param
            if p_type == "text":
                p_label = p.get("label") or p_name
                column_content.append(html.Label(p_label))
                column_content.append(dcc.Input(
                    id={"role": f"metric-param", "name": p_name},
                    type="text",
                    value=p.get("default", ""),
                    placeholder=p.get("placeholder", ""),
                    className="form-control mb-2",
                    persistence=True,
                    persistence_type="session",
                    autoComplete="off"
                ))
                column_content.append(html.Small(p.get("help", ""), className="text-muted d-block mb-3"))

        options_card = dbc.Card([
            dbc.CardHeader("🔧 Sélection de Colonne et Options"),
            dbc.CardBody(column_content if column_content else [html.P("Aucune colonne ou option pour ce type de métrique", className="text-muted")])
        ], className="mb-3")

        # Prévisualisation
        preview = dbc.Card([
            dbc.CardHeader("👁️ Prévisualisation"),
            dbc.CardBody([
                html.Pre(
                    id={"role": "metric-preview"},
                    style={"background": "#222", "color": "#eee", "padding": "0.75rem"}
                )
            ])
        ])
        
        cards = [nature_card, identification_card, general_card, dataset_card]
        if metric_type != "missing_rate":
            cards.append(options_card)
        cards.append(preview)
        return html.Div(cards)

    @app.callback(
        Output({"role": "missing-rate-filter-preview", "name": MATCH}, "children"),
        Input({"role": "missing-rate-filter", "name": MATCH}, "value"),
        State("url", "search"),
        State("inventory-datasets-store", "data"),
        prevent_initial_call=False
    )
    def update_missing_rate_filter_preview(filter_value, search, inventory_store):
        stream_ctx, project_ctx, zone_ctx = _resolve_context(search, inventory_store)
        if not filter_value:
            return html.Span("Sélectionne un filtre JSON pour afficher son contenu.", className="text-muted")
        path = _resolve_filter_path(filter_value, stream_ctx, project_ctx, zone_ctx)
        if not path:
            label = f"{filter_value}.json"
            return dbc.Alert(f"Filtre '{label}' introuvable pour ce contexte.", color="warning", className="mb-0")
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except Exception as exc:
            return dbc.Alert(f"Impossible de lire le filtre: {exc}", color="danger", className="mb-0")
        pretty = json.dumps(data, indent=2, ensure_ascii=False)
        return html.Pre(
            pretty,
            className="bg-dark text-light p-2 rounded",
            style={"whiteSpace": "pre-wrap", "margin": 0}
        )

    @app.callback(
        Output({"role": "metric-column", "form": "metric"}, "options"),
        Output("toast", "is_open", allow_duplicate=True),
        Output("toast", "children", allow_duplicate=True),
        Input({"role": "metric-db"}, "value", ALL),
        State("store_datasets", "data"),
        prevent_initial_call=True
    )
    def fill_metric_columns(db_values, ds_data):
        """Remplit les options de colonnes pour une métrique selon la base sélectionnée"""
        db_alias = first(db_values)
        print(f"DEBUG fill_metric_columns: db_values={db_values}, ds_data_present={bool(ds_data)}")
        # Prefer mapping via store_datasets when available
        ds_name = None
        if ds_data:
            ds_name = next((d["dataset"] for d in ds_data if d["alias"] == db_alias), None)

        # Fallback: if no mapping, try to use the alias/db value as dataset name or use ds-picker
        if not ds_name:
            try:
                from src.utils import first as _first
            except Exception:
                _first = lambda x: x[0] if isinstance(x, list) and x else None
            # try direct alias as dataset name
            ds_name = db_alias
            # If still None, return empty options
            if not ds_name:
                return [], False, ""

        # Try to read columns; if not found, attempt to locate a csv filename that matches
        cols = get_columns_for_dataset(ds_name)
        if not cols:
            # try to search datasets folder for a matching filename (best-effort)
            try:
                import os
                candidates = [f for f in os.listdir("./datasets") if f.lower().startswith(str(ds_name).lower())]
                if candidates:
                    # pick first candidate without extension
                    fname = candidates[0]
                    base = os.path.splitext(fname)[0]
                    cols = get_columns_for_dataset(base)
            except Exception:
                cols = []
        print(f"DEBUG fill_metric_columns: ds_name={ds_name}, cols_found={len(cols) if cols else 0}")

        if not cols:
            return [], True, f"Aucune colonne lisible pour « {ds_name} ». Vérifie le CSV."
        opts = [{"label": c, "value": c} for c in cols]
        return opts, False, ""


    @app.callback(
        Output({"role": "metric-param", "name": ALL}, "options"),
        Input({"role": "metric-db"}, "value", ALL),
        Input({"role": "metric-param", "name": ALL}, "value"),
        State("store_datasets", "data"),
        prevent_initial_call=True
    )
    def fill_param_columns(db_values, param_values, ds_data):
        """Remplit les options de tout param 'columns' déclarés en metric-param en fonction du dataset sélectionné
        Retourne une liste d'options (ou []) correspondant à chaque metric-param présent dans le DOM.
        """
        print(f"DEBUG fill_param_columns: db_values={db_values}, param_values={param_values}, ds_data_present={bool(ds_data)}")
        # Determine selected db alias: prefer explicit param dataset if provided, else main metric-db
        selected_db = first(param_values) or first(db_values)
        # If no datasets stored yet or no selected db, return empty lists for all params
        if not ds_data or not selected_db:
            return [[] for _ in param_values]

        ds_name = None
        if ds_data:
            ds_name = next((d["dataset"] for d in ds_data if d["alias"] == selected_db), None)
        if not ds_name:
            ds_name = selected_db

        cols = get_columns_for_dataset(ds_name) or []
        if not cols:
            try:
                import os
                candidates = [f for f in os.listdir("./datasets") if f.lower().startswith(str(ds_name).lower())]
                if candidates:
                    base = os.path.splitext(candidates[0])[0]
                    cols = get_columns_for_dataset(base) or []
            except Exception:
                cols = []
        print(f"DEBUG fill_param_columns: ds_name={ds_name}, cols_found={len(cols) if cols else 0}")
        opts = [{"label": c, "value": c} for c in cols]
        # Replicate same options for each requested param dropdown
        return [opts for _ in param_values]

    @app.callback(
        Output("metric-helper", "children"),
        Input({"role": "metric-column", "form": "metric"}, "options")
    )
    def metric_helper(opts):
        """Affiche un message d'aide pour les colonnes de métrique"""
        if opts is None:
            return ""
        if len(opts) == 0:
            return "Aucune colonne détectée. Assure-toi d'avoir cliqué « Enregistrer les datasets » à l'étape 1."
        return f"{len(opts)} colonne(s) disponibles."

    @app.callback(
        Output({"role": "metric-preview"}, "children"),
        Output("toast", "is_open", allow_duplicate=True),
        Output("toast", "children", allow_duplicate=True),
        Input("force-metric-preview", "n_clicks"),
        Input("metric-type", "value"),
        Input({"role": "metric-id"}, "value", ALL),
        Input({"role": "metric-db"}, "value", ALL),
        Input({"role": "metric-column", "form": "metric"}, "value", ALL),
        Input({"role": "metric-where"}, "value", ALL),
        Input({"role": "metric-expr"}, "value", ALL),
        Input({"role": "metric-general", "field": "export"}, "value"),
        State({"role": "metric-nature", "field": "name"}, "value"),
        State({"role": "metric-nature", "field": "description"}, "value"),
        State({"role": "metric-nature", "field": "comments"}, "value"),
        State({"role": "metric-param", "name": ALL}, "value"),
        State({"role": "missing-rate-filter", "name": ALL}, "value"),
        State("url", "search"),
        State("inventory-datasets-store", "data"),
        State("store_metrics", "data"),
        prevent_initial_call=True
    )
    def preview_metric(
        force,
        mtype,
        mid_list,
        mdb_list,
        mcol_list,
        mwhere_list,
        mexpr_list,
        general_export_values,
        metric_name,
        metric_description,
        metric_comments,
        mparam_values,
        missing_filter_values,
        search,
        inventory_store,
        metrics
    ):
        """Génère la prévisualisation JSON de la métrique"""
        if not mtype:
            return "", False, ""
        mid = first(mid_list)
        mdb = first(mdb_list)
        # Extraire la sélection de colonnes (multi-dropdown -> liste de colonnes)
        mcol = first(mcol_list)
        mwhere = first(mwhere_list)
        mexpr = first(mexpr_list)
        # metric params values come as a list corresponding to declared params order
        mparams = (mparam_values or [])

        # Build prefix from context and format id if numeric provided
        prefix = build_id_prefix_from_context(search, inventory_store, "metric")
        display_id = None
        try:
            if isinstance(mid, (int, float)) or (isinstance(mid, str) and str(mid).isdigit()):
                num = int(mid)
                display_id = f"{prefix}{num}"
        except Exception:
            display_id = None
        export_selection = general_export_values or []
        if isinstance(export_selection, (list, tuple, set)):
            export_flag = "export" in export_selection
        else:
            export_flag = bool(export_selection)
        obj = {"id": (display_id or "(auto)"), "type": mtype}
        meta = get_metric_meta(mtype) or {}
        params = meta.get("params", [])
        nature = {
            "name": (metric_name or meta.get("name") or ""),
            "description": metric_description or "",
            "preliminary_comments": metric_comments or ""
        }
        if any(nature.values()):
            obj["nature"] = nature
        obj["identification"] = {"metric_id": obj.get("id")}
        general_payload = {"export": export_flag}
        obj["general"] = general_payload
        # Populate known params
        if "database" in params or meta.get("requires_database"):
            obj["database"] = mdb or ""
        selected_columns = []
        for entry in (mcol_list or []):
            if isinstance(entry, list):
                selected_columns.extend([c for c in entry if c not in (None, "")])
            elif entry not in (None, ""):
                selected_columns.append(entry)

        if "column" in params or meta.get("requires_column"):
            if selected_columns:
                obj["column"] = selected_columns if len(selected_columns) > 1 else selected_columns[0]
            else:
                obj["column"] = ""
        # Handle registered params: dataset/columns/where/expr
        # Look for params declared in meta and pull values from the form via pattern ids
        # Collect metric-param values from the DOM using dcc pattern ids is handled in add_metric via State
        if params:
            declared = [p.get('name') if isinstance(p, dict) else p for p in params]
            for name, val in zip(declared, mparams):
                if not name:
                    continue
                if name == 'columns':
                    obj['columns'] = val or []
                elif name == 'dataset_filter' or name == 'dataset':
                    obj['database_filter'] = val or ''
                else:
                    obj[name] = val
        if "where" in params:
            if mwhere:
                obj["where"] = mwhere
        if "expr" in params:
            obj["expr"] = mexpr or ""
        
        # Capture export value
        if mtype == "missing_rate":
            selected_filter = first(missing_filter_values)
            spec = {}
            dataset_value = obj.get("database") or mdb
            if dataset_value:
                spec["dataset"] = dataset_value
            effective_columns = list(selected_columns)
            if not effective_columns:
                col_value = obj.get("column")
                if isinstance(col_value, list):
                    effective_columns = [c for c in col_value if c not in (None, "")]
                elif col_value not in (None, ""):
                    effective_columns = [col_value]

            spec.pop("column", None)
            spec.pop("columns", None)
            if effective_columns:
                if len(effective_columns) == 1:
                    spec["column"] = effective_columns[0]
                else:
                    spec["column"] = effective_columns
            if selected_filter:
                spec["filter"] = selected_filter
            if spec:
                obj["specific"] = spec
            obj.pop("condition", None)
            obj.pop("where", None)
            obj.pop("database", None)
            obj.pop("column", None)
        obj.pop("export", None)

        preview_obj = copy.deepcopy(obj)
        preview_obj.pop("id", None)
        preview_obj.pop("type", None)
        
        # If a concrete display_id was provided, check whether it already exists for this prefix
        if display_id:
            existing_ids = {x.get("id") for x in (metrics or []) if x.get("id")}
            if display_id in existing_ids:
                msg = f"Le numéro {display_id} est déjà utilisé. Un ID unique sera attribué automatiquement si nécessaire."
                return json.dumps(preview_obj, ensure_ascii=False, indent=2), True, msg
        return json.dumps(preview_obj, ensure_ascii=False, indent=2), False, ""

    @app.callback(
        Output("add-metric-status", "children"),
        Output("store_metrics", "data"),
        Output("metrics-list", "children"),
        Output("metric-tabs", "active_tab"),
        Output("store_edit_metric", "data"),
        Input("add-metric", "n_clicks"),
        State({"role": "metric-preview"}, "children", ALL),
        State("store_metrics", "data"),
        State("metric-type", "value"),
    State({"role": "metric-id"}, "value", ALL),
    State({"role": "metric-db"}, "value", ALL),
    State({"role": "metric-column", "form": "metric"}, "value", ALL),
    State({"role": "metric-where"}, "value", ALL),
    State({"role": "metric-expr"}, "value", ALL),
    State({"role": "metric-param", "name": ALL}, "value"),
    State({"role": "metric-general", "field": "export"}, "value"),
        State({"role": "metric-nature", "field": "name"}, "value"),
        State({"role": "metric-nature", "field": "description"}, "value"),
        State({"role": "metric-nature", "field": "comments"}, "value"),
        State({"role": "missing-rate-filter", "name": ALL}, "value"),
        State("url", "search"),
        State("inventory-datasets-store", "data"),
        State("store_edit_metric", "data"),
    )
    def add_metric(
        n,
        preview_list,
        metrics,
        mtype,
        mid_list,
        mdb_list,
        mcol_list,
        mwhere_list,
        mexpr_list,
        mparam_values,
        general_export_values,
        metric_name,
        metric_description,
        metric_comments,
        missing_filter_values,
        search,
        inventory_store,
        edit_metric_data
    ):
        """Ajoute ou modifie une métrique au store et met à jour la liste"""
        if not n:
            return "", metrics, "", no_update, no_update
        
        # Vérifier si on est en mode édition
        edit_mode = edit_metric_data and isinstance(edit_metric_data, dict) and "metric" in edit_metric_data
        edit_index = edit_metric_data.get("index") if edit_mode else None
        
        stream_ctx, project_ctx, zone_ctx = _resolve_context(search, inventory_store)
        selected_filter = first(missing_filter_values)
        mid_raw = first(mid_list)
        mdb = first(mdb_list)
        # Extraire la sélection de colonnes (multi-dropdown -> liste de colonnes)
        mcol = first(mcol_list)
        mwhere = first(mwhere_list)
        mexpr = first(mexpr_list)
        if not mtype:
            return "Prévisualisation vide/invalide.", metrics, no_update, no_update
        # Determine meta/params for this metric type
        meta = get_metric_meta(mtype) or {}
        params = meta.get("params", [])

        # Normalize ID using prefix + numeric suffix. The prefix is locked and derived from context.
        prefix = build_id_prefix_from_context(search, inventory_store, "metric")
        m = {"id": None, "type": mtype}
        candidate_id = None
        if mid_raw is not None and mid_raw != "":
            try:
                mnum = int(mid_raw)
                candidate_id = f"{prefix}{mnum}"
            except Exception:
                candidate_id = None

        # Populate known params
        if "database" in params or meta.get("requires_database"):
            m["database"] = mdb or ""
        selected_columns = []
        for entry in (mcol_list or []):
            if isinstance(entry, list):
                selected_columns.extend([c for c in entry if c not in (None, "")])
            elif entry not in (None, ""):
                selected_columns.append(entry)

        if "column" in params or meta.get("requires_column"):
            if selected_columns:
                m["column"] = selected_columns if len(selected_columns) > 1 else selected_columns[0]
            else:
                m["column"] = ""
        if "where" in params and mwhere:
            m["where"] = mwhere
        if "expr" in params:
            m["expr"] = mexpr or ""

        # Metric-param values: map declared param names to provided values
        try:
            declared = [p.get('name') if isinstance(p, dict) else p for p in params]
            for name, val in zip(declared, (mparam_values or [])):
                if name is None:
                    continue
                if name == 'columns':
                    m['columns'] = val or []
                elif name == 'dataset_filter' or name == 'dataset':
                    m['database_filter'] = val or ''
                else:
                    m[name] = val
        except Exception:
            pass
        m["general"] = {"export": False}
        export_selection = general_export_values or []
        if isinstance(export_selection, (list, tuple, set)):
            export_flag = "export" in export_selection
        else:
            export_flag = bool(export_selection)
        existing_general = dict(m.get("general") or {})
        existing_general["export"] = export_flag
        m["general"] = existing_general
        m.pop("export", None)
        
        if metric_name or metric_description or metric_comments:
            m["nature"] = {
                "name": metric_name or "",
                "description": metric_description or "",
                "preliminary_comments": metric_comments or ""
            }
        m.setdefault("identification", {})
        m["identification"]["metric_id"] = m.get("id")

        if mtype == "missing_rate":
            spec = dict(m.get("specific") or {})
            dataset_value = m.get("database") or first(mdb_list)
            if dataset_value:
                spec["dataset"] = dataset_value
            effective_columns = list(selected_columns)
            if not effective_columns:
                col_value = m.get("column")
                if isinstance(col_value, list):
                    effective_columns = [c for c in col_value if c not in (None, "")]
                elif col_value not in (None, ""):
                    effective_columns = [col_value]

            spec.pop("column", None)
            spec.pop("columns", None)
            if effective_columns:
                if len(effective_columns) == 1:
                    spec["column"] = effective_columns[0]
                else:
                    spec["column"] = effective_columns
            if selected_filter:
                spec["filter"] = selected_filter
            spec = {k: v for k, v in spec.items() if v not in (None, "", [])}
            if spec:
                m["specific"] = spec
            m.pop("where", None)
            m.pop("database", None)
            m.pop("column", None)
            m.pop("condition", None)

        metrics = (metrics or [])
        
        # En mode édition, garder l'ID original
        if edit_mode and edit_metric_data.get("metric"):
            original_metric = edit_metric_data.get("metric")
            m["id"] = original_metric.get("id")
        else:
            # Mode ajout: générer un ID unique
            existing_ids = {x.get("id") for x in metrics}
            
            if not m.get("id") or m.get("id") in existing_ids:
                # Extraire les numéros existants
                existing_numbers = []
                for metric in metrics:
                    metric_id = metric.get("id", "")
                    m_match = re.match(r"^M-(\d+)$", str(metric_id))
                    if m_match:
                        try:
                            num = int(m_match.group(1))
                            existing_numbers.append(num)
                        except (ValueError, IndexError):
                            pass

                # Trouver le prochain numéro disponible
                next_num = 1
                while next_num in existing_numbers:
                    next_num += 1

                m["id"] = f"M-{next_num:03d}"

        if m.get("identification") is None:
            m["identification"] = {}
        if isinstance(m.get("identification"), dict):
            m["identification"]["metric_id"] = m.get("id")
        
        # Mode édition: remplacer la métrique existante
        if edit_mode and edit_index is not None and 0 <= edit_index < len(metrics):
            metrics[edit_index] = m
            status_message = f"✅ Métrique modifiée: {m['id']}"
        else:
            # Mode ajout: ajouter une nouvelle métrique
            metrics.append(m)
            status_message = f"✅ Métrique ajoutée: {m['id']}"
        
        items = [
            html.Pre(
                json.dumps(x, ensure_ascii=False, indent=2),
                className="p-2 mb-2",
                style={"background": "#111", "color": "#eee"}
            ) for x in metrics
        ]
        
        # Réinitialiser le store d'édition après l'ajout/modification
        return status_message, metrics, html.Div(items), "tab-metric-viz", None

    @app.callback(
        Output("metrics-table-container", "children"),
        Input("store_metrics", "data")
    )
    def display_metrics_table(metrics):
        """Affiche les métriques dans un tableau structuré avec actions"""
        if not metrics:
            return dbc.Alert("Aucune métrique créée. Utilisez l'onglet 'Créer' pour ajouter des métriques.", color="info")
        
        # Helper pour formater les paramètres spécifiques
        def _describe_specific(spec: dict) -> str:
            if not isinstance(spec, dict) or not spec:
                return "-"
            parts = []
            for key, value in spec.items():
                if value in (None, "", [], {}):
                    continue
                if isinstance(value, list):
                    rendered = ", ".join(map(str, value))
                elif isinstance(value, dict):
                    rendered = json.dumps(value, ensure_ascii=False)
                else:
                    rendered = str(value)
                parts.append(f"{key}: {rendered}")
            return " | ".join(parts) if parts else "-"

        # Créer les lignes du tableau avec boutons d'action
        table_rows = []
        
        # En-tête
        header = html.Tr([
            html.Th("ID"),
            html.Th("Type"),
            html.Th("Nom"),
            html.Th("Description"),
            html.Th("Commentaires"),
            html.Th("Export"),
            html.Th("Paramétrage spécifique"),
            html.Th("Actions", style={"width": "200px"})
        ])
        
        # Lignes de données
        for idx, m in enumerate(metrics):
            metric_id = m.get("id", "N/A")
            metric_type = m.get("type", "-")
            
            general = m.get("general") or {}
            specific = m.get("specific") or {}
            nature = m.get("nature") or {}
            
            name = nature.get("name") or "-"
            description = nature.get("description") or "-"
            comments = nature.get("preliminary_comments") or "-"
            export_flag = "Oui" if bool(general.get("export")) else "Non"
            owner = general.get("owner") or "-"
            specific_summary = _describe_specific(specific)
            
            actions = html.Div([
                dbc.Button(
                    "✏️", 
                    id={"type": "edit-metric", "index": idx},
                    color="warning",
                    size="sm",
                    className="me-1",
                    title="Modifier"
                ),
                dbc.Button(
                    "📋", 
                    id={"type": "duplicate-metric", "index": idx},
                    color="info",
                    size="sm",
                    className="me-1",
                    title="Dupliquer"
                ),
                dbc.Button(
                    "🗑️", 
                    id={"type": "delete-metric", "index": idx},
                    color="danger",
                    size="sm",
                    title="Supprimer"
                )
            ])
            
            row = html.Tr([
                html.Td(metric_id),
                html.Td(metric_type),
                html.Td(name, style={"maxWidth": "150px"}),
                html.Td(description, style={"fontSize": "0.85em", "maxWidth": "200px"}),
                html.Td(comments, style={"fontSize": "0.85em", "maxWidth": "200px"}),
                html.Td(export_flag),
                html.Td(specific_summary, style={"fontSize": "0.9em"}),
                html.Td(actions)
            ], style={"backgroundColor": "#f8f9fa" if idx % 2 else "white"})
            table_rows.append(row)
        
        table = dbc.Table(
            [html.Thead(header), html.Tbody(table_rows)],
            bordered=True,
            hover=True,
            responsive=True,
            striped=False
        )

        # Calculer les datasets virtuels (colonnes produites)
        ensure_plugins_discovered()
        virtual_items = []
        error_items = []

        for m in metrics:
            metric_id = m.get("id") or "?"
            metric_type = m.get("type") or "?"
            plugin_class = REGISTRY.get(metric_type)
            if not plugin_class:
                continue

            params_for_schema = _build_params_for_virtual_schema(m)

            try:
                virtual_ds = plugin_class.create_virtual_dataset(metric_id, params_for_schema)
            except Exception as exc:
                error_items.append(html.Li(
                    f"{metric_id} ({metric_type}) → erreur récupération schéma: {exc}",
                    className="text-danger"
                ))
                continue

            if not virtual_ds:
                continue

            columns_rows = []
            for col in virtual_ds.schema.columns:
                columns_rows.append({
                    "Nom": col.name,
                    "Type": col.dtype,
                    "Nullable": "Oui" if col.nullable else "Non",
                    "Description": col.description or ""
                })

            schema_table = dash_table.DataTable(
                data=columns_rows,
                columns=[
                    {"name": "Nom", "id": "Nom"},
                    {"name": "Type", "id": "Type"},
                    {"name": "Nullable", "id": "Nullable"},
                    {"name": "Description", "id": "Description"},
                ],
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'left', 'padding': '6px'},
                page_size=max(len(columns_rows), 1)
            )

            meta_bits = []
            source_dataset = (
                m.get("database")
                or (m.get("params") or {}).get("dataset")
                or (m.get("specific") or {}).get("dataset")
            )
            if source_dataset:
                meta_bits.append(html.Div(f"Dataset source : {source_dataset}", className="text-muted mb-1"))
            if virtual_ds.schema.estimated_row_count is not None:
                meta_bits.append(html.Div(
                    f"Volume estimé : ~{virtual_ds.schema.estimated_row_count} lignes",
                    className="text-muted mb-2"
                ))

            accordion_body = [
                html.Div(f"Alias virtuel : {virtual_ds.alias}", className="text-muted"),
                *(meta_bits or []),
                html.H6("Colonnes exposées", className="mt-2"),
                schema_table
            ]

            virtual_items.append(
                dbc.AccordionItem(
                    accordion_body,
                    title=f"{metric_id} • {metric_type}",
                    item_id=str(metric_id)
                )
            )

        extra_blocks = []
        if error_items:
            extra_blocks.append(
                dbc.Alert([
                    html.Strong("Erreurs schéma virtuel"),
                    html.Ul(error_items, className="mb-0")
                ], color="danger", className="mt-4")
            )

        if virtual_items:
            extra_blocks.append(html.Hr(className="my-4"))
            extra_blocks.append(html.H6("Datasets virtuels générés", className="mb-2"))
            extra_blocks.append(
                dbc.Accordion(
                    virtual_items,
                    always_open=False,
                    flush=True,
                    id="metrics-virtual-accordion"
                )
            )
        else:
            extra_blocks.append(
                dbc.Alert(
                    "Aucune métrique ne produit de dataset virtuel pour le moment.",
                    color="secondary",
                    className="mt-4"
                )
            )

        return html.Div([
            html.H6(f"📊 {len(metrics)} métrique(s) configurée(s)", className="mb-3"),
            table,
            html.Div(id="metric-action-status", className="mt-2"),
            *extra_blocks
        ])

    # ===== Tests =====
    
    @app.callback(
        Output("test-params", "children"),
        Input("test-type", "value"),
        State("store_datasets", "data"),
        State("store_metrics", "data"),
        State("url", "search"),
        State("inventory-datasets-store", "data"),
        State("store_tests", "data"),
        State("run-context-store", "data")
    )
    def render_test_form(test_type, ds_data, metrics, search, inventory_store, stored_tests, run_context_data):
        """Affiche le formulaire de création de test selon le type avec groupes visuels"""
        if not test_type:
            return dbc.Alert("Choisis un type de test.", color="light")
        quarter_value = (run_context_data or {}).get("quarter")
        if not quarter_value:
            return dbc.Alert("Sélectionne d'abord un quarter dans le contexte avant de configurer un test.", color="warning")
        ds_aliases = [d["alias"] for d in (ds_data or [])]
        if not ds_aliases:
            return dbc.Alert("Enregistre d'abord des datasets.", color="warning")

        metric_ids = [m.get("id") for m in (metrics or []) if m.get("id")]

        plugin_label = ""
        try:
            plugins = discover_all_plugins(verbose=False)
            info = plugins.get(test_type)
            if info:
                plugin_label = getattr(info.plugin_class, "label", test_type)
        except Exception:
            plugin_label = test_type
        plugin_label = plugin_label or test_type

        nature_card = dbc.Card([
            dbc.CardHeader("📘 Nature du test"),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label("Nom du test"),
                        dcc.Input(
                            id={"role": "test-nature", "field": "name"},
                            type="text",
                            value=plugin_label,
                            placeholder="Sélectionné automatiquement",
                            className="form-control",
                            disabled=True,
                            style={"backgroundColor": "#f8f9fa"},
                            persistence=True,
                            persistence_type="session",
                            autoComplete="off"
                        )
                    ], md=4)
                ], className="mb-3"),
                dbc.Row([
                    dbc.Col([
                        html.Label("Functional category 1"),
                        dcc.Input(
                            id={"role": "test-nature", "field": "functional_category_1"},
                            type="text",
                            placeholder="Catégorie principale",
                            className="form-control",
                            persistence=True,
                            persistence_type="session",
                            autoComplete="off"
                        )
                    ], md=4),
                    dbc.Col([
                        html.Label("Functional category 2"),
                        dcc.Input(
                            id={"role": "test-nature", "field": "functional_category_2"},
                            type="text",
                            placeholder="Sous-catégorie",
                            className="form-control",
                            persistence=True,
                            persistence_type="session",
                            autoComplete="off"
                        )
                    ], md=4),
                    dbc.Col([
                        html.Label("Category"),
                        dcc.Input(
                            id={"role": "test-nature", "field": "category"},
                            type="text",
                            placeholder="Type de contrôle",
                            className="form-control",
                            persistence=True,
                            persistence_type="session",
                            autoComplete="off"
                        )
                    ], md=4)
                ]),
                html.Label("Description", className="mt-3"),
                dcc.Textarea(
                    id={"role": "test-nature", "field": "description"},
                    placeholder="Décris le contrôle et l'objectif du test",
                    className="form-control",
                    style={"minHeight": "100px"},
                    persistence=True,
                    persistence_type="session"
                ),
                html.Label("Commentaires préliminaires", className="mt-3"),
                dcc.Textarea(
                    id={"role": "test-nature", "field": "comments"},
                    placeholder="Notes, hypothèses, périmètre...",
                    className="form-control",
                    style={"minHeight": "80px"},
                    persistence=True,
                    persistence_type="session"
                )
            ])
        ], className="mb-3")

        # build id prefix and propose a number
        prefix = build_id_prefix_from_context(search, inventory_store, "test")
        proposed_num = 1
        try:
            existing = stored_tests or []
            pattern = re.compile(rf"^{re.escape(prefix)}(\d+)$")
            nums = [int(m.group(1)) for m in (pattern.match(x.get("id" or "") or "") for x in existing) if m]
            if nums:
                proposed_num = max(nums) + 1
        except Exception:
            proposed_num = 1

        identification_card = dbc.Card([
            dbc.CardHeader("🪪 Identification du test"),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label("Quarter (contexte)"),
                        dcc.Input(
                            id={"role": "test-id-quarter"},
                            type="text",
                            value=quarter_value,
                            disabled=True,
                            className="form-control",
                            style={"backgroundColor": "#f8f9fa"}
                        )
                    ], md=4)
                ], className="mb-3"),
                dbc.Row([
                    dbc.Col([
                        html.Label("Préfixe"),
                        dcc.Input(
                            id={"role": "test-id-prefix"},
                            type="text",
                            value=prefix,
                            disabled=True,
                            className="form-control",
                            persistence=True,
                            persistence_type="session",
                            style={"backgroundColor": "#f8f9fa"}
                        )
                    ], md=3),
                    dbc.Col([
                        html.Label("Numéro"),
                        dcc.Input(
                            id={"role": "test-id"},
                            type="number",
                            value=None,
                            placeholder=f"Proposé: {proposed_num}",
                            style={"width": "100%"},
                            persistence=True,
                            persistence_type="session",
                            min=1,
                            autoComplete="off"
                        ),
                        html.Small("Saisis seulement le numéro. Le préfixe est verrouillé.", className="text-muted")
                    ], md=3),
                    dbc.Col([
                        html.Label("Control name"),
                        dcc.Input(
                            id={"role": "test-identification", "field": "control_name"},
                            type="text",
                            placeholder="Nom du contrôle",
                            className="form-control",
                            persistence=True,
                            persistence_type="session",
                            autoComplete="off",
                            disabled=True,
                            style={"backgroundColor": "#f8f9fa"}
                        )
                    ], md=3),
                    dbc.Col([
                        html.Label("Control ID"),
                        dcc.Input(
                            id={"role": "test-identification", "field": "control_id"},
                            type="text",
                            placeholder="Identifiant externe",
                            className="form-control",
                            persistence=True,
                            persistence_type="session",
                            autoComplete="off",
                            disabled=True,
                            style={"backgroundColor": "#f8f9fa"}
                        )
                    ], md=3),
                    dbc.Col([
                        html.Label("Associated metric"),
                        dcc.Dropdown(
                            id={"role": "test-identification", "field": "associated_metric_id"},
                            options=[{"label": mid, "value": mid} for mid in metric_ids],
                            placeholder="Sélectionne une métrique",
                            clearable=True,
                            persistence=True,
                            persistence_type="session"
                        )
                    ], md=3)
                ])
            ])
        ], className="mb-3")

        general_card = dbc.Card([
            dbc.CardHeader("🧩 Paramétrage général"),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label("Degré de criticité"),
                        dcc.Dropdown(
                            id={"role": "test-sev"},
                            options=[{"label": label, "value": value} for label, value in [
                                ("Faible", "low"),
                                ("Moyen", "medium"),
                                ("Élevé", "high")
                            ]],
                            value="medium",
                            clearable=False,
                            persistence=True,
                            persistence_type="session"
                        )
                    ], md=4),
                    dbc.Col([
                        html.Label("Action en cas de KO"),
                        dcc.Dropdown(
                            id={"role": "test-action"},
                            options=[
                                {"label": "Arrêter le pipeline", "value": "stop_pipeline"},
                                {"label": "Alerter", "value": "raise_alert"},
                                {"label": "Loguer uniquement", "value": "log_only"}
                            ],
                            value="raise_alert",
                            clearable=False,
                            persistence=True,
                            persistence_type="session"
                        )
                    ], md=4),
                    dbc.Col([
                        html.Label("Échantillon si échec"),
                        dcc.Checklist(
                            id={"role": "test-sof"},
                            options=[{"label": " Oui", "value": "yes"}],
                            value=["yes"],
                            persistence=True,
                            persistence_type="session"
                        )
                    ], md=4)
                ])
            ])
        ], className="mb-3")

        if test_type == "range":
            source_section = html.Div([
                html.H6("🎯 Source des données", className="mb-3"),
                html.Label("Type de source", className="mb-2"),
                dcc.RadioItems(
                    id={"role": "test-source-type"},
                    options=[
                        {"label": " 📁 Base de données (colonne)", "value": "database"},
                        {"label": " 📊 Métrique", "value": "metric"}
                    ],
                    value="database",
                    persistence=True,
                    persistence_type="session",
                    className="mb-3"
                ),
                html.Div(id={"role": "test-source-inputs"})
            ], className="mb-4")

            params_content = []
            if test_type == "range":
                params_content = [
                    dbc.Row([
                        dbc.Col([
                            html.Label("Valeur Min (low)"),
                            dcc.Input(
                                id={"role": "test-low"},
                                type="text",
                                value="0",
                                placeholder="Ex: 0",
                                persistence=True,
                                persistence_type="session",
                                autoComplete="off"
                            )
                        ], md=6),
                        dbc.Col([
                            html.Label("Valeur Max (high)"),
                            dcc.Input(
                                id={"role": "test-high"},
                                type="text",
                                value="100",
                                placeholder="Ex: 100",
                                persistence=True,
                                persistence_type="session",
                                autoComplete="off"
                            )
                        ], md=6),
                    ])
                ]
            elif test_type == "regex":
                params_content = [
                    dbc.Row([dbc.Col([
                        html.Label("Pattern (expression régulière)"),
                        dcc.Input(
                            id={"role": "test-pattern"},
                            type="text",
                            value=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
                            placeholder="Ex: ^[A-Z]{3}[0-9]{3}$",
                            style={"width": "100%"},
                            persistence=True,
                            persistence_type="session",
                            autoComplete="off"
                        ),
                        html.Small("Valeur par défaut: regex email", className="text-muted")
                    ], md=12)])
                ]

            params_section = html.Div([
                html.H6("⚙️ Paramétrage spécifique", className="mb-3"),
                *(params_content or [html.P("Aucun paramètre spécifique pour ce type", className="text-muted")])
            ])

            specific_card = dbc.Card([
                dbc.CardHeader("⚙️ Paramétrage spécifique"),
                dbc.CardBody([
                    source_section,
                    params_section
                ])
            ], className="mb-3")

            preview = dbc.Card([
                dbc.CardHeader("👁️ Prévisualisation"),
                dbc.CardBody([
                    html.Pre(
                        id={"role": "test-preview"},
                        style={"background": "#222", "color": "#eee", "padding": "0.75rem"}
                    )
                ])
            ])
            
            return html.Div([nature_card, identification_card, general_card, specific_card, preview])

        if test_type == "interval_check":
            source_section = html.Div([
                html.H6("🎯 Source des données", className="mb-3"),
                html.Label("Type de source", className="mb-2"),
                dcc.RadioItems(
                    id={"role": "test-source-type"},
                    options=[
                        {"label": " 📊 Valeur de métrique", "value": "metric"},
                        {"label": " 📁 Colonnes de dataset", "value": "database"},
                    ],
                    value="metric",
                    persistence=True,
                    persistence_type="session",
                    className="mb-3"
                ),
                html.Div(id={"role": "test-source-inputs"})
            ], className="mb-4")

            bounds_section = html.Div([
                html.H6("⚖️ Contrôle des bornes", className="mb-3"),
                html.Div(
                    dbc.Row([
                        dbc.Col([
                            dbc.Checkbox(
                                id={"role": "interval-lower-enabled"},
                                value=False,
                                label="Activer borne minimale (>=)"
                            ),
                            dcc.Input(
                                id={"role": "interval-lower-value"},
                                type="number",
                                placeholder="Ex: 0",
                                className="form-control mt-2"
                            )
                        ], md=6),
                        dbc.Col([
                            dbc.Checkbox(
                                id={"role": "interval-upper-enabled"},
                                value=False,
                                label="Activer borne maximale (<=)"
                            ),
                            dcc.Input(
                                id={"role": "interval-upper-value"},
                                type="number",
                                placeholder="Ex: 100",
                                className="form-control mt-2"
                            )
                        ], md=6)
                    ], className="g-3"),
                    id="interval-general-bounds",
                    className="mb-3"
                ),
                dcc.Store(id="interval-rules-store", data=[], storage_type="session"),
                html.Div([
                    html.Div("Configure des règles spécifiques par colonne pour appliquer des bornes minimales et maximales.", className="text-muted mb-2"),
                    dbc.Button(
                        "➕ Ajouter une règle",
                        id="interval-add-rule",
                        size="sm",
                        outline=True,
                        color="secondary",
                        className="mb-2"
                    ),
                    html.Div(id="interval-rules-container"),
                    html.Small(
                        "Chaque règle peut cibler une ou plusieurs colonnes et définir des bornes min/max.",
                        className="text-muted d-block mt-2"
                    )
                ], id="interval-rules-wrapper")
            ])

            specific_card = dbc.Card([
                dbc.CardHeader("⚙️ Paramétrage spécifique"),
                dbc.CardBody([
                    source_section,
                    bounds_section
                ])
            ], className="mb-3")

            preview = dbc.Card([
                dbc.CardHeader("👁️ Prévisualisation"),
                dbc.CardBody([
                    html.Pre(
                        id={"role": "test-preview"},
                        style={"background": "#222", "color": "#eee", "padding": "0.75rem"}
                    )
                ])
            ])

            return html.Div([nature_card, identification_card, general_card, specific_card, preview])

        return dbc.Alert("Type non géré pour l'instant.", color="warning")

    @app.callback(
        Output({"role": "test-source-inputs"}, "children"),
        Input({"role": "test-source-type"}, "value", ALL),
        State("store_datasets", "data"),
        State("store_metrics", "data"),
        State("test-type", "value")
    )
    def update_test_source_inputs(source_type_list, ds_data, metrics, current_test_type):
        """Affiche les champs appropriés selon le choix database/metric"""
        source_type = first(source_type_list) or "database"
        ds_aliases = [d["alias"] for d in (ds_data or [])]
        metric_ids = [m.get("id") for m in (metrics or []) if m.get("id")]
        is_interval = current_test_type == "interval_check"
        
        if source_type == "database":
            return dbc.Row([
                dbc.Col([
                    html.Label("Base de données (alias)"),
                    dcc.Dropdown(
                        id={"role": "test-db"},
                        options=[{"label": a, "value": a} for a in ds_aliases],
                        value=ds_aliases[0] if ds_aliases else None,
                        clearable=False,
                        persistence=True,
                        persistence_type="session"
                    )
                ], md=6),
                dbc.Col([
                    html.Label("Colonnes" if is_interval else "Colonne"),
                    dcc.Dropdown(
                        id={"role": "test-col"},
                        options=[],
                        placeholder="Choisir une ou plusieurs colonnes" if is_interval else "Choisir une colonne",
                        clearable=True if is_interval else False,
                        multi=is_interval,
                        persistence=True,
                        persistence_type="session"
                    ),
                    html.Small("Sélection multiple autorisée." if is_interval else "", className="text-muted")
                ], md=6)
            ])
        else:  # metric
            return dbc.Row([
                dbc.Col([
                    html.Label("Métrique"),
                    dcc.Dropdown(
                        id={"role": "test-metric"},
                        options=[{"label": f"📊 {mid}", "value": mid} for mid in metric_ids],
                        placeholder="Choisir une métrique",
                        clearable=False,
                        persistence=True,
                        persistence_type="session"
                    )
                ], md=12)
            ])
    
    @app.callback(
        Output({"role": "test-col"}, "options"),
        Output("toast", "is_open", allow_duplicate=True),
        Output("toast", "children", allow_duplicate=True),
        Input({"role": "test-db"}, "value", ALL),
        State("store_datasets", "data"),
        prevent_initial_call=True
    )
    def fill_test_columns(db_values, ds_data):
        """Remplit les options de colonnes pour un test selon la base sélectionnée"""
        db_alias = first(db_values)
        if not db_alias or not ds_data:
            return [], False, ""
        ds_name = next((d["dataset"] for d in ds_data if d["alias"] == db_alias), None)
        if not ds_name:
            return [], True, f"Aucun dataset associé à l'alias « {db_alias} »."
        cols = get_columns_for_dataset(ds_name)
        if not cols:
            return [], True, f"Aucune colonne lisible pour « {ds_name} ». Vérifie le CSV."
        opts = [{"label": c, "value": c} for c in cols]
        return opts, False, ""

    @app.callback(
        Output("interval-rules-store", "data", allow_duplicate=True),
        Input("interval-add-rule", "n_clicks"),
        State("interval-rules-store", "data"),
        State("test-type", "value"),
        prevent_initial_call=True,
    )
    def add_interval_rule(n_clicks, store_data, current_test_type):
        """Ajoute une nouvelle règle vide au store (utilisé pour rendre un bloc de paramètres)."""
        if not n_clicks:
            raise PreventUpdate
        if current_test_type != "interval_check":
            raise PreventUpdate
        data = list(store_data or [])
        new_id = uuid4().hex
        data.append({
            "id": new_id,
            "columns": [],
            "lower_value": None,
            "upper_value": None,
        })
        return data


    @app.callback(
        Output("interval-rules-container", "children"),
        Input("interval-rules-store", "data"),
        State({"role": "test-db"}, "value", ALL),
        State("store_datasets", "data"),
        State({"role": "test-metric"}, "value", ALL),
        State("store_metrics", "data"),
        State({"role": "test-source-type"}, "value", ALL),
    )
    def render_interval_rules(store_data, db_values, ds_data, metric_values, metrics_store, source_type_values):
        """Rend les blocs éditables pour chaque règle stockée."""
        if not store_data:
            store_data = []
        source_type = first(source_type_values) or "database"
        opts = []
        if source_type == "metric":
            metric_id = first(metric_values)
            columns = _get_metric_output_columns(metric_id, metrics_store)
            opts = [{"label": c, "value": c} for c in (columns or [])]
        else:
            # Determine dataset name from test-db if possible
            db_alias = first(db_values)
            ds_name = None
            if ds_data and db_alias:
                ds_name = next((d["dataset"] for d in ds_data if d.get("alias") == db_alias), None)
            if not ds_name:
                ds_name = db_alias

            cols = get_columns_for_dataset(ds_name) if ds_name else []
            opts = [{"label": c, "value": c} for c in (cols or [])]

        children = []
        for idx, rule in enumerate(store_data):
            rid = rule.get("id") or f"r{idx}"
            card = dbc.Card([
                dbc.CardHeader(html.Div([
                    html.Strong(f"Règle {idx+1}"),
                    dbc.Button("Supprimer", id={"role": "interval-remove", "index": rid}, size="sm", color="danger", outline=True, className="ms-2")
                ])),
                dbc.CardBody([
                    dcc.Dropdown(
                        id={"role": "interval-rule-columns", "index": rid},
                        options=opts,
                        value=rule.get("columns") or [],
                        multi=True,
                        placeholder="Choisir colonnes",
                        clearable=True,
                    ),
                    dbc.Row([
                        dbc.Col([
                            html.Label("Borne minimale (>=)", className="small text-muted"),
                            dcc.Input(id={"role": "interval-rule-lower-value", "index": rid}, type="number", value=rule.get("lower_value"), placeholder="aucune", className="form-control")
                        ], md=6),
                        dbc.Col([
                            html.Label("Borne maximale (<=)", className="small text-muted"),
                            dcc.Input(id={"role": "interval-rule-upper-value", "index": rid}, type="number", value=rule.get("upper_value"), placeholder="aucune", className="form-control")
                        ], md=6)
                    ], className="mt-3")
                ])
            ], className="mb-2")
            children.append(card)
        return children


    @app.callback(
        Output("interval-general-bounds", "style", allow_duplicate=True),
        Output("interval-rules-wrapper", "style", allow_duplicate=True),
        Output("interval-add-rule", "disabled", allow_duplicate=True),
        Input({"role": "test-source-type"}, "value", ALL),
        prevent_initial_call="initial_duplicate"
    )
    def toggle_interval_sections(source_type_values):
        source_type = first(source_type_values) or "metric"
        if source_type in {"metric", "database"}:
            return {"display": "none"}, {}, False
        return {"display": "none"}, {}, False


    def _update_interval_rule_entry(store_data, rid, **updates):
        if not store_data or not rid:
            return store_data or [], False
        updated = []
        changed = False
        for item in store_data:
            if item.get("id") == rid:
                new_item = dict(item)
                for key, value in updates.items():
                    new_item[key] = value
                updated.append(new_item)
                changed = True
            else:
                updated.append(item)
        return updated, changed


    def _resolve_rule_value(values_list, store_data, rid):
        if not store_data or not isinstance(store_data, list):
            return None
        for idx, item in enumerate(store_data):
            if item.get("id") == rid and idx < len(values_list):
                return values_list[idx]
        return None


    def _normalize_interval_rules(store_rules):
        """Convertit le store des règles en structure exportable pour la prévisualisation."""
        normalized = []
        for entry in store_rules or []:
            columns = [c for c in (entry.get("columns") or []) if c]
            if not columns:
                continue
            lower_val = _cast_optional_number(entry.get("lower_value", entry.get("lower")))
            upper_val = _cast_optional_number(entry.get("upper_value", entry.get("upper")))
            if lower_val is None and upper_val is None:
                continue
            normalized.append({
                "columns": columns,
                "lower": lower_val,
                "upper": upper_val,
            })
        return normalized


    @app.callback(
        Output("interval-rules-store", "data", allow_duplicate=True),
        Input({"role": "interval-rule-columns", "index": ALL}, "value"),
        State("interval-rules-store", "data"),
        prevent_initial_call=True,
    )
    def sync_interval_rule_columns(new_columns_list, store_data):
        triggered = callback_context.triggered_id
        if not isinstance(triggered, dict):
            raise PreventUpdate
        rid = triggered.get("index")
        new_columns = _resolve_rule_value(new_columns_list or [], store_data or [], rid)
        if new_columns is None:
            raise PreventUpdate
        normalized = []
        if isinstance(new_columns, (list, tuple, set)):
            normalized = [c for c in new_columns if c not in (None, "")]
        elif new_columns not in (None, ""):
            normalized = [new_columns]
        updated, changed = _update_interval_rule_entry(store_data, rid, columns=normalized)
        if not changed:
            raise PreventUpdate
        return updated


    @app.callback(
        Output("interval-rules-store", "data", allow_duplicate=True),
        Input({"role": "interval-rule-lower-value", "index": ALL}, "value"),
        State("interval-rules-store", "data"),
        prevent_initial_call=True,
    )
    def sync_interval_rule_lower_value(value_list, store_data):
        triggered = callback_context.triggered_id
        if not isinstance(triggered, dict):
            raise PreventUpdate
        rid = triggered.get("index")
        raw_value = _resolve_rule_value(value_list or [], store_data or [], rid)
        updates = {"lower_value": _cast_optional_number(raw_value)}
        updated, changed = _update_interval_rule_entry(store_data, rid, **updates)
        if not changed:
            raise PreventUpdate
        return updated


    @app.callback(
        Output("interval-rules-store", "data", allow_duplicate=True),
        Input({"role": "interval-rule-upper-value", "index": ALL}, "value"),
        State("interval-rules-store", "data"),
        prevent_initial_call=True,
    )
    def sync_interval_rule_upper_value(value_list, store_data):
        triggered = callback_context.triggered_id
        if not isinstance(triggered, dict):
            raise PreventUpdate
        rid = triggered.get("index")
        raw_value = _resolve_rule_value(value_list or [], store_data or [], rid)
        updates = {"upper_value": _cast_optional_number(raw_value)}
        updated, changed = _update_interval_rule_entry(store_data, rid, **updates)
        if not changed:
            raise PreventUpdate
        return updated


    @app.callback(
        Output("interval-rules-store", "data", allow_duplicate=True),
        Input({"role": "interval-remove", "index": ALL}, "n_clicks"),
        State("interval-rules-store", "data"),
        prevent_initial_call=True,
    )
    def remove_interval_rule(remove_clicks, store_data):
        """Supprime la règle correspondant au bouton cliqué."""
        if not store_data:
            return []
        triggered = callback_context.triggered_id
        if not triggered:
            return store_data
        # triggered is a dict with role/index
        rid = triggered.get("index")
        new_store = [r for r in store_data if r.get("id") != rid]
        return new_store


    @app.callback(
        Output({"role": "test-identification", "field": "control_name"}, "value"),
        Input("test-type", "value")
    )
    def sync_control_name_from_test(test_type_value):
        """Associe automatiquement le control name au libellé du test sélectionné."""
        if not test_type_value:
            return ""
        try:
            ensure_plugins_discovered()
            plugins = discover_all_plugins(verbose=False)
            info = plugins.get(test_type_value)
            if not info:
                return ""
            label = getattr(info.plugin_class, "label", None) or getattr(info, "name", "")
            return label or ""
        except Exception:
            return ""


    @app.callback(
        Output({"role": "test-identification", "field": "control_id"}, "value"),
        Input({"role": "test-id-prefix"}, "value"),
        Input({"role": "test-id"}, "value")
    )
    def sync_control_id_from_prefix(prefix_value, number_value):
        """Concatène automatiquement le préfixe et le numéro pour le Control ID."""
        prefix_value = prefix_value or ""
        if number_value in (None, ""):
            return prefix_value
        try:
            number_int = int(number_value)
            return f"{prefix_value}{number_int}"
        except Exception:
            return prefix_value

    @app.callback(
        Output({"role": "test-preview"}, "children"),
        Output("toast", "is_open", allow_duplicate=True),
        Output("toast", "children", allow_duplicate=True),
        Input("force-test-preview", "n_clicks"),
        Input("test-type", "value"),
        Input({"role": "test-id"}, "value", ALL),
        Input({"role": "test-sev"}, "value", ALL),
        Input({"role": "test-sof"}, "value", ALL),
    State({"role": "test-action"}, "value"),
    State({"role": "test-nature", "field": "name"}, "value"),
    State({"role": "test-nature", "field": "functional_category_1"}, "value"),
    State({"role": "test-nature", "field": "functional_category_2"}, "value"),
    State({"role": "test-nature", "field": "category"}, "value"),
    State({"role": "test-nature", "field": "description"}, "value"),
    State({"role": "test-nature", "field": "comments"}, "value"),
    State({"role": "test-identification", "field": "control_name"}, "value"),
    State({"role": "test-identification", "field": "control_id"}, "value"),
    State({"role": "test-identification", "field": "associated_metric_id"}, "value"),
    Input({"role": "test-source-type"}, "value", ALL),
        Input({"role": "test-db"}, "value", ALL),
        Input({"role": "test-col"}, "value", ALL),
        Input({"role": "test-metric"}, "value", ALL),
        Input({"role": "test-low"}, "value", ALL),
        Input({"role": "test-high"}, "value", ALL),
        Input({"role": "test-pattern"}, "value", ALL),
        Input({"role": "test-ref-db"}, "value", ALL),
        Input({"role": "test-ref-col"}, "value", ALL),
        Input("interval-rules-store", "data"),
        Input({"role": "interval-lower-enabled"}, "value", ALL),
        Input({"role": "interval-lower-value"}, "value", ALL),
        Input({"role": "interval-upper-enabled"}, "value", ALL),
        Input({"role": "interval-upper-value"}, "value", ALL),
        State("store_tests", "data"),
        State("url", "search"),
        State("inventory-datasets-store", "data"),
        prevent_initial_call=True
    )
    def preview_test(force, ttype, tid_list, sev_list, sof_list, action_on_fail, nature_name, func_cat1, func_cat2, cat, desc, comments, control_name, control_id, associated_metric_id, source_mode_list, db_list, col_list, metric_list, low_list, high_list, pat_list, refdb_list, refcol_list, rules_store, lower_enabled_list, lower_value_list, upper_enabled_list, upper_value_list, tests, search, inventory_store):
        """Génère la prévisualisation JSON du test"""
        if not ttype:
            return "", False, ""
        
        def first_with_default(val, default=None):
            if val is None:
                return default
            if isinstance(val, list):
                return val[0] if val else default
            return val
        
        tid_raw, sev, sof = first_with_default(tid_list), first_with_default(sev_list, "medium"), first_with_default(sof_list, [])
        # Build prefix from context and format id if numeric provided
        prefix = build_id_prefix_from_context(search, inventory_store, "test")
        tid = None
        try:
            if isinstance(tid_raw, (int, float)) or (isinstance(tid_raw, str) and str(tid_raw).isdigit()):
                tid = f"{prefix}{int(tid_raw)}"
        except Exception:
            tid = None
        source_mode = first_with_default(source_mode_list, "database")
        db, col = first_with_default(db_list), first_with_default(col_list)
        metric = first_with_default(metric_list)
        low, high = first_with_default(low_list), first_with_default(high_list)
        pat = first_with_default(pat_list)
        lower_enabled = bool(first_with_default(lower_enabled_list, False))
        upper_enabled = bool(first_with_default(upper_enabled_list, False))
        lower_raw = first_with_default(lower_value_list)
        upper_raw = first_with_default(upper_value_list)
        rules_store = rules_store or []

        def normalize_columns(value):
            if value is None:
                return []
            if isinstance(value, (list, tuple, set)):
                return [v for v in value if v not in (None, "")]
            return [value] if value not in (None, "") else []
        # Root should be limited: keep id/type for compatibility, move others into structured blocks
        obj = {
            "id": tid or "(auto)",
            "type": ttype
        }

        def prune_dict(block, keep_empty_lists=None):
            keep_empty_lists = set(keep_empty_lists or [])
            cleaned = {}
            for key, value in (block or {}).items():
                if isinstance(value, list):
                    if not value and key not in keep_empty_lists:
                        continue
                    cleaned[key] = value
                    continue
                if isinstance(value, bool):
                    cleaned[key] = value
                    continue
                if value in (None, "", {}, []):
                    continue
                cleaned[key] = value
            return cleaned

        nature_payload = prune_dict({
            "name": nature_name or ttype or "",
            "functional_category_1": func_cat1 or "",
            "functional_category_2": func_cat2 or "",
            "category": cat or "",
            "description": desc or "",
            "preliminary_comments": comments or ""
        })
        if nature_payload:
            obj["nature"] = nature_payload
        identification_payload = prune_dict({
            "test_id": tid or "(auto)",
            "control_name": control_name or "",
            "control_id": control_id or "",
            "associated_metric_id": associated_metric_id or ""
        })
        if identification_payload:
            obj["identification"] = identification_payload
        general_payload = {
            "criticality": sev or "medium",
            "on_fail": action_on_fail or "raise_alert",
            "sample_on_fail": bool("yes" in (sof or []))
        }
        obj["general"] = general_payload

        # Build specific block depending on type. Avoid polluting root with dataset/metric/columns/seuils
        if ttype == "range":
            if metric:
                specific = {
                    "target_mode": "metric_value",
                    "metric_id": metric,
                    "columns": normalize_columns(col),
                    "low": low,
                    "high": high,
                    "inclusive": True
                }
            else:
                specific = {
                    "target_mode": "dataset_columns",
                    "database": db or "",
                    "columns": normalize_columns(col),
                    "low": low,
                    "high": high,
                    "inclusive": True
                }
            obj["specific"] = prune_dict(specific, keep_empty_lists={"columns"})
        elif ttype == "interval_check":
            target_mode = "metric_value" if source_mode == "metric" else "dataset_columns"
            lower_value = _cast_optional_number(lower_raw)
            upper_value = _cast_optional_number(upper_raw)
            column_rules = _normalize_interval_rules(rules_store)
            specific = {
                "target_mode": target_mode,
                "metric_id": metric if target_mode == "metric_value" else None,
                "database": db if target_mode == "dataset_columns" else None,
                "columns": normalize_columns(col) if target_mode == "dataset_columns" else [],
                "lower_enabled": lower_enabled,
                "lower_value": lower_value,
                "upper_enabled": upper_enabled,
                "upper_value": upper_value,
            }
            if column_rules:
                specific["column_rules"] = column_rules
            obj["specific"] = prune_dict(specific, keep_empty_lists={"columns"})
        # If tid provided, check whether it's already used for this prefix
        if tid:
            existing_ids = {x.get("id") for x in (tests or []) if x.get("id")}
            if tid in existing_ids:
                msg = f"Le numéro {tid} est déjà utilisé. Un ID unique sera attribué automatiquement si nécessaire."
                preview_obj = {k: obj[k] for k in ("nature", "identification", "general", "specific") if obj.get(k)}
                return json.dumps(preview_obj, ensure_ascii=False, indent=2), True, msg

        preview_obj = {k: obj[k] for k in ("nature", "identification", "general", "specific") if obj.get(k)}
        return json.dumps(preview_obj, ensure_ascii=False, indent=2), False, ""

    @app.callback(
        Output("add-test-status", "children"),
        Output("store_tests", "data"),
        Output("tests-list", "children"),
        Output("test-tabs", "active_tab"),
        Input("add-test", "n_clicks"),
        State({"role": "test-preview"}, "children", ALL),
        State("store_tests", "data"),
        State("test-type", "value"),
        State({"role": "test-id"}, "value", ALL),
        State({"role": "test-sev"}, "value", ALL),
        State({"role": "test-sof"}, "value", ALL),
        State({"role": "test-action"}, "value"),
    State({"role": "test-nature", "field": "name"}, "value"),
    State({"role": "test-nature", "field": "functional_category_1"}, "value"),
        State({"role": "test-nature", "field": "functional_category_2"}, "value"),
        State({"role": "test-nature", "field": "category"}, "value"),
        State({"role": "test-nature", "field": "description"}, "value"),
        State({"role": "test-nature", "field": "comments"}, "value"),
        State({"role": "test-identification", "field": "control_name"}, "value"),
        State({"role": "test-identification", "field": "control_id"}, "value"),
        State({"role": "test-identification", "field": "associated_metric_id"}, "value"),
        State({"role": "test-source-type"}, "value", ALL),
        State({"role": "test-db"}, "value", ALL),
        State({"role": "test-col"}, "value", ALL),
        State({"role": "test-metric"}, "value", ALL),
        State({"role": "test-low"}, "value", ALL),
        State({"role": "test-high"}, "value", ALL),
        State({"role": "test-pattern"}, "value", ALL),
        State({"role": "test-ref-db"}, "value", ALL),
        State({"role": "test-ref-col"}, "value", ALL),
        State({"role": "interval-lower-enabled"}, "value", ALL),
        State({"role": "interval-lower-value"}, "value", ALL),
        State({"role": "interval-upper-enabled"}, "value", ALL),
        State({"role": "interval-upper-value"}, "value", ALL),
        State("interval-rules-store", "data"),
        State("url", "search"),
        State("inventory-datasets-store", "data"),
    )
    def add_test(n, preview_list, tests, ttype, tid_list, sev_list, sof_list, action_on_fail, nature_name, func_cat1, func_cat2, cat, desc, comments, control_name, control_id, associated_metric_id, source_mode_list, db_list, col_list, metric_list, low_list, high_list, pat_list, refdb_list, refcol_list, lower_enabled_list, lower_value_list, upper_enabled_list, upper_value_list, rules_store, search, inventory_store):
        """Ajoute un test au store et met à jour la liste"""
        if not n:
            return "", tests, "", no_update

        def first_with_default(val, default=None):
            if val is None:
                return default
            if isinstance(val, list):
                return val[0] if val else default
            return val

        def normalize_columns(value):
            if value is None:
                return []
            if isinstance(value, (list, tuple, set)):
                return [v for v in value if v not in (None, "")]
            return [value] if value not in (None, "") else []

        preview_text = first_with_default(preview_list)
        tid_raw = first_with_default(tid_list)
        sev = first_with_default(sev_list, "medium")
        sof_raw = first_with_default(sof_list, [])
        source_mode = first_with_default(source_mode_list, "database")
        db = first_with_default(db_list)
        col = first_with_default(col_list)
        metric = first_with_default(metric_list)
        low = first_with_default(low_list)
        high = first_with_default(high_list)
        pat = first_with_default(pat_list)
        lower_enabled = bool(first_with_default(lower_enabled_list, False))
        upper_enabled = bool(first_with_default(upper_enabled_list, False))
        lower_raw = first_with_default(lower_value_list)
        upper_raw = first_with_default(upper_value_list)
        interval_rules = _normalize_interval_rules(rules_store or [])

        parsed_preview = {}
        if preview_text:
            try:
                candidate = json.loads(preview_text)
                if isinstance(candidate, dict):
                    parsed_preview = candidate
            except Exception:
                parsed_preview = {}

        def prune_dict(block, keep_empty_lists=None):
            keep_empty_lists = set(keep_empty_lists or [])
            cleaned = {}
            for key, value in (block or {}).items():
                if isinstance(value, list):
                    if not value and key not in keep_empty_lists:
                        continue
                    cleaned[key] = value
                    continue
                if isinstance(value, bool):
                    cleaned[key] = value
                    continue
                if value in (None, "", {}, []):
                    continue
                cleaned[key] = value
            return cleaned

        # Build prefix and format candidate id
        prefix = build_id_prefix_from_context(search, inventory_store, "test")
        formatted_tid = None
        try:
            if tid_raw not in (None, "") and (isinstance(tid_raw, (int, float)) or (isinstance(tid_raw, str) and str(tid_raw).isdigit())):
                formatted_tid = f"{prefix}{int(tid_raw)}"
        except Exception:
            formatted_tid = None

        if not ttype:
            return "Prévisualisation vide/invalide.", tests, no_update, no_update

        t = {
            "id": formatted_tid,
            "type": ttype
        }

        nature_payload = prune_dict({
            "name": nature_name or parsed_preview.get("nature", {}).get("name") or "",
            "functional_category_1": func_cat1 or parsed_preview.get("nature", {}).get("functional_category_1") or "",
            "functional_category_2": func_cat2 or parsed_preview.get("nature", {}).get("functional_category_2") or "",
            "category": cat or parsed_preview.get("nature", {}).get("category") or "",
            "description": desc or parsed_preview.get("nature", {}).get("description") or "",
            "preliminary_comments": comments or parsed_preview.get("nature", {}).get("preliminary_comments") or ""
        })
        if nature_payload:
            t["nature"] = nature_payload

        identification_payload = prune_dict({
            "test_id": formatted_tid or parsed_preview.get("identification", {}).get("test_id"),
            "control_name": control_name or parsed_preview.get("identification", {}).get("control_name") or "",
            "control_id": control_id or parsed_preview.get("identification", {}).get("control_id") or "",
            "associated_metric_id": associated_metric_id or parsed_preview.get("identification", {}).get("associated_metric_id") or ""
        })
        if identification_payload:
            t["identification"] = identification_payload

        sample_flag = bool("yes" in (sof_raw or []))
        existing_general = parsed_preview.get("general", {}) if isinstance(parsed_preview.get("general"), dict) else {}
        general_payload = {
            "criticality": sev or existing_general.get("criticality") or "medium",
            "on_fail": action_on_fail or existing_general.get("on_fail") or "raise_alert",
            "sample_on_fail": sample_flag
        }
        t["general"] = general_payload

        specific_payload = {}
        if ttype == "range":
            if metric:
                specific_payload = {
                    "target_mode": "metric_value",
                    "metric_id": metric,
                    "columns": normalize_columns(col),
                    "low": low,
                    "high": high,
                    "inclusive": True
                }
            else:
                specific_payload = {
                    "target_mode": "dataset_columns",
                    "database": db or "",
                    "columns": normalize_columns(col),
                    "low": low,
                    "high": high,
                    "inclusive": True
                }
            specific_payload = prune_dict(specific_payload, keep_empty_lists={"columns"})
        elif ttype == "regex":
            specific_payload = prune_dict({
                "target_mode": "metric_value" if metric else "dataset_columns",
                "metric_id": metric if metric else None,
                "database": db or None,
                "column": col or None,
                "pattern": pat or None
            })
        elif ttype == "interval_check":
            target_mode = "metric_value" if source_mode == "metric" else "dataset_columns"
            columns = normalize_columns(col)
            lower_value = _cast_optional_number(lower_raw)
            upper_value = _cast_optional_number(upper_raw)
            specific_payload = prune_dict({
                "target_mode": target_mode,
                "metric_id": metric if target_mode == "metric_value" else None,
                "database": db if target_mode == "dataset_columns" else None,
                "columns": columns if target_mode == "dataset_columns" else [],
                "lower_enabled": lower_enabled,
                "lower_value": lower_value,
                "upper_enabled": upper_enabled,
                "upper_value": upper_value,
            }, keep_empty_lists={"columns"})
            column_rules_from_preview = parsed_preview.get("specific", {}).get("column_rules") if isinstance(parsed_preview.get("specific"), dict) else None
            # Ensure we keep column_rules even if the rest of the specific payload was pruned to empty
            if interval_rules or column_rules_from_preview:
                if not isinstance(specific_payload, dict):
                    specific_payload = {}
                # prefer dynamic interval_rules (from UI) over previewed column_rules
                specific_payload["column_rules"] = interval_rules if interval_rules else column_rules_from_preview
        else:
            specific_payload = prune_dict(parsed_preview.get("specific")) if isinstance(parsed_preview.get("specific"), dict) else {}

        if specific_payload:
            t["specific"] = specific_payload
        
        tests = (tests or [])
        existing_ids = {x.get("id") for x in tests}

        # Decide final ID: if candidate provided and unique, use it; otherwise compute next available numeric suffix for this prefix
        if formatted_tid and formatted_tid not in existing_ids:
            t["id"] = formatted_tid
        else:
            existing_numbers = []
            try:
                pattern = re.compile(rf"^{re.escape(prefix)}(\d+)$")
                for test in tests:
                    test_id = str(test.get("id", ""))
                    m_match = pattern.match(test_id)
                    if m_match:
                        try:
                            num = int(m_match.group(1))
                            existing_numbers.append(num)
                        except (ValueError, IndexError):
                            pass
            except Exception:
                existing_numbers = []

            next_num = 1
            while next_num in existing_numbers:
                next_num += 1

            t["id"] = f"{prefix}{next_num}"

        if t.get("identification"):
            ident_block = dict(t["identification"])
        else:
            ident_block = {}
        ident_block["test_id"] = t.get("id")
        t["identification"] = ident_block
        
        tests.append(t)
        items = [
            html.Pre(
                json.dumps(x, ensure_ascii=False, indent=2),
                className="p-2 mb-2",
                style={"background": "#111", "color": "#eee"}
            ) for x in tests
        ]
        return f"Test ajouté: {t['id']}", tests, html.Div(items), "tab-test-viz"

    # ===== Publication =====
    
    @app.callback(
        Output("cfg-preview", "children"),
        Input("store_datasets", "data"),
        Input("store_metrics", "data"),
        Input("store_tests", "data"),
        Input("store_scripts", "data"),
        Input("fmt", "value"),
        State("url", "search"),
        State("run-context-store", "data")
    )
    def render_cfg_preview(datasets, metrics, tests, scripts, fmt, search, run_context):
        """Génère la prévisualisation de la configuration finale"""
        q = parse_query(search or "")
        cfg = cfg_template()
        
        # Context avec quarter au lieu de dq_point
        quarter_value = (run_context or {}).get("quarter") if run_context else None
        cfg["context"] = {
            "stream": q.get("stream"),
            "project": q.get("project"),
            "zone": q.get("zone"),
            "quarter": quarter_value
        }
        
        cfg["databases"] = datasets or []
        
        # Convertir metrics en dictionnaire avec ID comme clé
        metrics_dict = {}
        for m in (metrics or []):
            metric_id = m.get("id")
            if metric_id:
                # Retirer les paramètres dataset, column, where, expr du niveau params
                metric_copy = {k: v for k, v in m.items() if k != "id"}
                # Nettoyer les params non désirés
                if "params" in metric_copy:
                    metric_copy["params"] = {k: v for k, v in metric_copy["params"].items() 
                                            if k not in ["dataset", "column", "where", "expr"]}
                metrics_dict[metric_id] = metric_copy
        
        # Convertir tests en dictionnaire avec ID comme clé
        tests_dict = {}
        for t in (tests or []):
            test_id = t.get("id")
            if test_id:
                test_copy = {k: v for k, v in t.items() if k != "id"}
                # Supprimer lower_enabled et upper_enabled du specific
                if "specific" in test_copy:
                    test_copy["specific"] = {k: v for k, v in test_copy["specific"].items() 
                                           if k not in ["lower_enabled", "upper_enabled"]}
                tests_dict[test_id] = test_copy
        
        cfg["metrics"] = metrics_dict
        cfg["tests"] = tests_dict
        cfg["scripts"] = scripts or []
        try:
            if fmt == "yaml":
                return yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True)
            else:
                return json.dumps(cfg, ensure_ascii=False, indent=2)
        except Exception as e:
            return f"Erreur de sérialisation: {e}"

    # ===== Tableaux de visualisation =====
    
    def format_interval_bounds_display(spec_block):
        """
        Formate l'affichage des bornes pour les tests interval_check.
        Inclut les bornes générales et les règles par colonne.
        """
        if not spec_block:
            return "-"
        
        lines = []
        
        # Bornes générales (nouvelle structure avec bounds)
        bounds = spec_block.get("bounds", {})
        lower_val = bounds.get("lower")
        upper_val = bounds.get("upper")
        
        if lower_val is not None or upper_val is not None:
            lower_display = str(lower_val) if lower_val is not None else "-∞"
            upper_display = str(upper_val) if upper_val is not None else "+∞"
            lines.append(html.Div([
                html.Strong("Général: "),
                html.Span(f"[{lower_display}, {upper_display}]")
            ]))
        
        # Règles par colonne
        column_rules = spec_block.get("column_rules") or []
        if column_rules:
            lines.append(html.Div(html.Strong("Règles par colonne:"), className="mt-2"))
            for idx, rule in enumerate(column_rules):
                cols = rule.get("columns") or []
                lower = rule.get("lower")
                upper = rule.get("upper")
                
                if not cols:
                    continue
                    
                cols_str = ", ".join(str(c) for c in cols)
                lower_display = str(lower) if lower is not None else "-∞"
                upper_display = str(upper) if upper is not None else "+∞"
                
                lines.append(html.Div([
                    html.Span(f"  • {cols_str}: ", className="text-muted"),
                    html.Span(f"[{lower_display}, {upper_display}]")
                ], style={"fontSize": "0.9em", "marginLeft": "1em"}))
        
        return html.Div(lines) if lines else "-"
    
    @app.callback(
        Output("tests-table-container", "children"),
        Input("store_tests", "data")
    )
    def display_tests_table(tests):
        """Affiche le tableau de visualisation des tests avec actions"""
        if not tests:
            return dbc.Alert("Aucun test défini. Utilisez l'onglet 'Créer' pour en ajouter.", color="info")
        
        # Créer les lignes du tableau avec boutons d'action
        table_rows = []
        
        # En-tête
        header = html.Tr([
            html.Th("ID"),
            html.Th("Type"),
            html.Th("Source"),
            html.Th("Sévérité"),
            html.Th("Range"),
            html.Th("Description"),
            html.Th("Échantillon"),
            html.Th("Actions", style={"width": "200px"})
        ])
        
        # Lignes de données
        for idx, t in enumerate(tests):
            test_id = t.get("id", "N/A")
            
            # Déterminer la source (préférer bloc 'specific' si présent)
            spec = t.get("specific") or {}
            if spec:
                mode = spec.get("target_mode")
                if mode == "metric_value":
                    metric_id = spec.get("metric_id") or t.get("metric") or "-"
                    source_info = f"📊 {metric_id}"
                else:
                    database = spec.get("database") or t.get("database") or "-"
                    source_info = database
            else:
                # Legacy fallback
                if t.get("metric"):
                    source_info = f"📊 {t.get('metric')}"
                else:
                    source_info = t.get("database", "-")
            
            # Extraire low/high pour les tests range
            range_info = "-"
            if t.get("type") == "range":
                # Prefer specific block
                spec = t.get("specific") or {}
                low_val = spec.get("low") if spec.get("low") is not None else t.get("low", "?")
                high_val = spec.get("high") if spec.get("high") is not None else t.get("high", "?")
                range_info = f"[{low_val}, {high_val}]"
            elif t.get("type") == "interval_check":
                spec = t.get("specific") or {}
                # Utiliser la fonction dédiée pour formater les bornes avec l'arborescence des règles
                range_info = format_interval_bounds_display(spec)
            
            actions = html.Div([
                dbc.Button(
                    "✏️", 
                    id={"type": "edit-test", "index": idx},
                    color="warning",
                    size="sm",
                    className="me-1",
                    title="Modifier"
                ),
                dbc.Button(
                    "🗑️", 
                    id={"type": "delete-test", "index": idx},
                    color="danger",
                    size="sm",
                    className="me-1",
                    title="Supprimer"
                ),
                dbc.Button(
                    "📥", 
                    id={"type": "export-test", "index": idx},
                    color="info",
                    size="sm",
                    title="Exporter JSON"
                )
            ])
            
            description = generate_test_description(t)

            general_block = t.get("general") or {}
            sample_flag = general_block.get("sample_on_fail") if isinstance(general_block, dict) else False
            severity_display = general_block.get("criticality") if isinstance(general_block, dict) else t.get("severity")

            row = html.Tr([
                html.Td(test_id),
                html.Td(t.get("type", "N/A")),
                html.Td(source_info),
                html.Td(severity_display or "-"),
                html.Td(range_info),
                html.Td(description),
                html.Td("Oui" if sample_flag else "Non"),
                html.Td(actions)
            ], style={"backgroundColor": "#f8f9fa" if idx % 2 else "white"})
            table_rows.append(row)
        
        table = dbc.Table(
            [html.Thead(header), html.Tbody(table_rows)],
            bordered=True,
            hover=True,
            responsive=True,
            striped=False
        )
        
        return html.Div([
            html.H6(f"✅ {len(tests)} test(s) configuré(s)", className="mb-3"),
            table,
            html.Div(id="test-action-status", className="mt-2")
        ])
    
    # ===== Actions sur les métriques =====
    
    @app.callback(
        [Output("store_metrics", "data", allow_duplicate=True),
         Output("store_tests", "data", allow_duplicate=True),
         Output("metric-action-status", "children", allow_duplicate=True)],
        Input({"type": "delete-metric", "index": ALL}, "n_clicks"),
        [State("store_metrics", "data"),
         State("store_tests", "data")],
        prevent_initial_call=True
    )
    def delete_metric(n_clicks_list, metrics, tests):
        """Supprime une métrique et les tests associés"""
        if not any(n_clicks_list):
            return no_update, no_update, no_update
        
        # Trouver quel bouton a été cliqué
        clicked_idx = None
        for idx, n in enumerate(n_clicks_list):
            if n:
                clicked_idx = idx
                break
        
        if clicked_idx is None or not metrics:
            return no_update, no_update, no_update
        
        # Récupérer la métrique à supprimer
        metric_to_delete = metrics[clicked_idx]
        metric_id = metric_to_delete.get("id")
        
        # Supprimer la métrique
        new_metrics = [m for i, m in enumerate(metrics) if i != clicked_idx]
        
        # Aucun test ne référence les métriques dans le type "range"
        new_tests = tests or []
        
        # Message de statut
        status_msg = f"✅ Métrique '{metric_id}' supprimée."
        
        return new_metrics, new_tests, dbc.Alert(status_msg, color="success", dismissable=True, duration=4000)
    
    @app.callback(
        [Output("store_metrics", "data", allow_duplicate=True),
         Output("metric-tabs", "active_tab", allow_duplicate=True),
         Output("metric-action-status", "children", allow_duplicate=True)],
        Input({"type": "duplicate-metric", "index": ALL}, "n_clicks"),
        State("store_metrics", "data"),
        prevent_initial_call=True
    )
    def duplicate_metric(n_clicks_list, metrics):
        """Duplique une métrique avec un nouvel ID"""
        if not any(n_clicks_list):
            return no_update, no_update, no_update
        
        clicked_idx = None
        for idx, n in enumerate(n_clicks_list):
            if n:
                clicked_idx = idx
                break
        
        if clicked_idx is None or not metrics or clicked_idx >= len(metrics):
            return no_update, no_update, no_update
        
        # Copier la métrique
        metric_to_duplicate = copy.deepcopy(metrics[clicked_idx])
        original_id = metric_to_duplicate.get("id", "metric")
        
        # Générer un nouvel ID unique en gardant le numéro original
        existing_ids = {m.get("id") for m in metrics}
        
        # Si l'ID se termine déjà par _copy ou _copy2, etc., on retire ce suffixe pour revenir à la base
        if "_copy" in original_id:
            base_id = original_id.split("_copy")[0]
        else:
            base_id = original_id
        
        # Générer un nouvel ID avec _copy, _copy2, _copy3, etc.
        counter = 1
        new_id = f"{base_id}_copy"
        while new_id in existing_ids:
            counter += 1
            new_id = f"{base_id}_copy{counter}"
        
        # Mettre à jour l'ID
        metric_to_duplicate["id"] = new_id
        if metric_to_duplicate.get("identification"):
            metric_to_duplicate["identification"]["metric_id"] = new_id
        
        # Ajouter au store
        new_metrics = metrics + [metric_to_duplicate]
        
        status_msg = f"✅ Métrique dupliquée: '{original_id}' → '{new_id}'"
        
        return new_metrics, "tab-metric-viz", dbc.Alert(status_msg, color="success", dismissable=True, duration=4000)
    
    @app.callback(
        [Output("metric-type", "value", allow_duplicate=True),
         Output("store_edit_metric", "data", allow_duplicate=True),
         Output("metric-tabs", "active_tab", allow_duplicate=True),
         Output("metric-action-status", "children", allow_duplicate=True)],
        Input({"type": "edit-metric", "index": ALL}, "n_clicks"),
        State("store_metrics", "data"),
        prevent_initial_call=True
    )
    def edit_metric(n_clicks_list, metrics):
        """Active le mode édition et charge le type de métrique"""
        if not any(n_clicks_list):
            return no_update, no_update, no_update, no_update
        
        # Trouver quel bouton a été cliqué
        clicked_idx = None
        for idx, n in enumerate(n_clicks_list):
            if n:
                clicked_idx = idx
                break
        
        if clicked_idx is None or not metrics or clicked_idx >= len(metrics):
            return no_update, no_update, no_update, no_update
        
        # Récupérer la métrique à modifier
        metric = metrics[clicked_idx]
        metric_id = metric.get("id", "")
        metric_type = metric.get("type", "")
        
        # Stocker toute la métrique pour le mode édition
        edit_data = {
            "index": clicked_idx,
            "metric": copy.deepcopy(metric)
        }
        
        status_msg = f"✏️ Mode édition: Métrique '{metric_id}' en cours de chargement..."
        
        return (
            metric_type,  # Déclenche la génération du formulaire
            edit_data,    # Stocke la métrique complète
            "tab-metric-create",
            dbc.Alert(status_msg, color="warning", dismissable=True, duration=4000)
        )
    
    @app.callback(
        [Output({"role": "metric-id"}, "value", allow_duplicate=True),
         Output({"role": "metric-db"}, "value", allow_duplicate=True),
         Output({"role": "metric-column", "form": "metric"}, "value", allow_duplicate=True),
         Output({"role": "metric-where"}, "value", allow_duplicate=True),
         Output({"role": "metric-expr"}, "value", allow_duplicate=True),
         Output({"role": "metric-nature", "field": "description"}, "value", allow_duplicate=True),
         Output({"role": "metric-nature", "field": "comments"}, "value", allow_duplicate=True),
         Output({"role": "metric-general", "field": "export"}, "value", allow_duplicate=True),
         Output("metric-action-status", "children", allow_duplicate=True)],
        Input("metric-params", "children"),
        State("store_edit_metric", "data"),
        prevent_initial_call=True
    )
    def populate_edit_form(form_content, edit_data):
        """Remplit le formulaire une fois qu'il est généré"""
        if not edit_data or not isinstance(edit_data, dict) or "metric" not in edit_data:
            return [no_update] * 9
        
        metric = edit_data.get("metric", {})
        metric_id = metric.get("id", "")
        
        # Extraire le numéro de l'ID
        id_number = ""
        if metric_id.startswith("M-"):
            id_number = metric_id[2:].lstrip("0") or "0"
        
        # Extraire les valeurs
        database = metric.get("database", "")
        
        # Gérer les colonnes
        column_value = metric.get("column", "")
        if isinstance(column_value, list):
            column = column_value
        else:
            column = column_value if column_value else ""
        
        where = metric.get("where", "")
        expr = metric.get("expr", "")
        
        # Extraire les informations de nature
        nature = metric.get("nature", {})
        description = nature.get("description", "") if nature else ""
        comments = nature.get("preliminary_comments", "") if nature else ""
        
        # Extraire l'export
        general = metric.get("general", {})
        export_value = ["export"] if general.get("export", False) else []
        
        status_msg = f"✏️ Métrique '{metric_id}' chargée. Modifiez et cliquez sur 'Ajouter' pour enregistrer."
        
        return (
            id_number,
            database,
            column,
            where,
            expr,
            description,
            comments,
            export_value,
            dbc.Alert(status_msg, color="info", dismissable=True, duration=5000)
        )
    
    @app.callback(
        Output("add-metric", "children"),
        Input("store_edit_metric", "data")
    )
    def update_metric_button_text(edit_data):
        """Change le texte du bouton selon le mode (ajout/édition)"""
        if edit_data and isinstance(edit_data, dict) and "metric" in edit_data:
            return "💾 Enregistrer les modifications"
        return "✅ Ajouter la métrique"
    
    @app.callback(
        Output("metric-action-status", "children", allow_duplicate=True),
        Input({"type": "print-metric", "index": ALL}, "n_clicks"),
        State("store_metrics", "data"),
        prevent_initial_call=True
    )
    def print_metric(n_clicks_list, metrics):
        """Active le flag print pour une métrique"""
        if not any(n_clicks_list):
            return no_update
        
        # Trouver quel bouton a été cliqué
        clicked_idx = None
        for idx, n in enumerate(n_clicks_list):
            if n:
                clicked_idx = idx
                break
        
        if clicked_idx is None or not metrics or clicked_idx >= len(metrics):
            return no_update
        
        metric = metrics[clicked_idx]
        metric_id = metric.get("id")
        
        # Note: Le flag print devrait être ajouté à la structure de la métrique
        # Pour l'instant, on affiche juste un message
        return dbc.Alert(f"🖨️ Print activé pour la métrique '{metric_id}'. Cette fonctionnalité sera implémentée dans la publication.", 
                        color="info", dismissable=True, duration=4000)
    
    # ===== Actions sur les tests =====
    
    @app.callback(
        [Output("store_tests", "data", allow_duplicate=True),
         Output("test-action-status", "children", allow_duplicate=True)],
        Input({"type": "delete-test", "index": ALL}, "n_clicks"),
        State("store_tests", "data"),
        prevent_initial_call=True
    )
    def delete_test(n_clicks_list, tests):
        """Supprime un test"""
        if not any(n_clicks_list):
            return no_update, no_update
        
        # Trouver quel bouton a été cliqué
        clicked_idx = None
        for idx, n in enumerate(n_clicks_list):
            if n:
                clicked_idx = idx
                break
        
        if clicked_idx is None or not tests:
            return no_update, no_update
        
        # Récupérer le test à supprimer
        test_to_delete = tests[clicked_idx]
        test_id = test_to_delete.get("id")
        
        # Supprimer le test
        new_tests = [t for i, t in enumerate(tests) if i != clicked_idx]
        
        # Message de statut
        status_msg = f"✅ Test '{test_id}' supprimé."
        
        return new_tests, dbc.Alert(status_msg, color="success", dismissable=True, duration=4000)
    
    @app.callback(
        [Output("test-type", "value", allow_duplicate=True),
         Output("test-tabs", "active_tab", allow_duplicate=True),
         Output("test-action-status", "children", allow_duplicate=True)],
        Input({"type": "edit-test", "index": ALL}, "n_clicks"),
        State("store_tests", "data"),
        prevent_initial_call=True
    )
    def edit_test(n_clicks_list, tests):
        """Charge le test pour modification"""
        if not any(n_clicks_list):
            return no_update, no_update, no_update
        
        # Trouver quel bouton a été cliqué
        clicked_idx = None
        for idx, n in enumerate(n_clicks_list):
            if n:
                clicked_idx = idx
                break
        
        if clicked_idx is None or not tests or clicked_idx >= len(tests):
            return no_update, no_update, no_update
        
        # Récupérer le test à modifier
        test = tests[clicked_idx]
        
        # Créer un message détaillé avec toutes les valeurs
        threshold = test.get("threshold", {})
        ref = test.get("ref", {})
        
        general_block = test.get("general") or {}
        values_list = [
            html.Li(f"Type: {test.get('type', 'N/A')}"),
            html.Li(f"ID: {test.get('id', 'N/A')}"),
            html.Li(f"Sévérité: {general_block.get('criticality', test.get('severity', 'medium'))}"),
            html.Li(f"Échantillon si échec: {'Oui' if general_block.get('sample_on_fail') else 'Non'}"),
        ]
        
        specific_block = test.get("specific") or {}
        if specific_block.get('target_mode') == 'metric_value':
            metric_id = specific_block.get('metric_id') or test.get('metric')
            if metric_id:
                values_list.append(html.Li(f"Métrique: {metric_id}"))
        else:
            database_val = specific_block.get('database') or test.get('database')
            columns_val = specific_block.get('columns') or test.get('column')
            if database_val:
                values_list.append(html.Li(f"Database: {database_val}"))
            if columns_val:
                if isinstance(columns_val, (list, tuple, set)):
                    cols_str = ", ".join(str(c) for c in columns_val if c)
                else:
                    cols_str = str(columns_val)
                if cols_str:
                    values_list.append(html.Li(f"Colonnes: {cols_str}"))
        if threshold:
            values_list.append(html.Li(f"Seuil: {threshold.get('op', '')} {threshold.get('value', '')}"))
        if test.get('min') is not None:
            values_list.append(html.Li(f"Min: {test.get('min')}"))
        if test.get('max') is not None:
            values_list.append(html.Li(f"Max: {test.get('max')}"))
        if test.get('pattern'):
            values_list.append(html.Li(f"Pattern: {test.get('pattern')}"))
        if ref:
            if ref.get('metric'):
                values_list.append(html.Li(f"Référence: metric:{ref.get('metric')}"))
            elif ref.get('database'):
                values_list.append(html.Li(f"Référence DB: {ref.get('database')}, Colonne: {ref.get('column', 'N/A')}"))
        
        values_text = html.Div([
            html.P(f"✏️ Pour modifier le test '{test.get('id')}', utilisez les valeurs suivantes :", className="mb-2"),
            html.Ul(values_list),
            html.P("📝 Saisissez ces valeurs dans le formulaire, puis cliquez sur 'Ajouter' pour mettre à jour.", className="mt-2 text-primary")
        ])
        
        return (
            test.get("type", ""),  # Pré-sélectionner le type
            "tab-test-create",  # Basculer vers l'onglet de création
            dbc.Alert(values_text, color="info", dismissable=True)
        )
    
    @app.callback(
        Output("test-action-status", "children", allow_duplicate=True),
        Input({"type": "export-test", "index": ALL}, "n_clicks"),
        State("store_tests", "data"),
        prevent_initial_call=True
    )
    def export_test(n_clicks_list, tests):
        """Exporte un test en JSON"""
        if not any(n_clicks_list):
            return no_update
        
        # Trouver quel bouton a été cliqué
        clicked_idx = None
        for idx, n in enumerate(n_clicks_list):
            if n:
                clicked_idx = idx
                break
        
        if clicked_idx is None or not tests or clicked_idx >= len(tests):
            return no_update
        
        test = tests[clicked_idx]
        test_id = test.get("id")
        
        # Créer l'export JSON
        export_json = json.dumps(test, ensure_ascii=False, indent=2)
        
        return dbc.Alert([
            html.P(f"📥 Export JSON du test '{test_id}':", className="mb-2"),
            html.Pre(export_json, style={
                "background": "#111", 
                "color": "#0f0", 
                "padding": "10px", 
                "borderRadius": "4px",
                "fontSize": "12px"
            })
        ], color="dark", dismissable=True)
    
    # ===== Modals de documentation =====
    
    @app.callback(
        Output("metric-help-modal", "is_open"),
        Input("open-metric-help", "n_clicks"),
        Input("close-metric-help", "n_clicks"),
        State("metric-help-modal", "is_open"),
        prevent_initial_call=True
    )
    def toggle_metric_help_modal(open_clicks, close_clicks, is_open):
        """Ouvre/ferme le modal d'aide pour les métriques"""
        return not is_open
    
    @app.callback(
        Output("test-help-modal", "is_open"),
        Input("open-test-help", "n_clicks"),
        Input("close-test-help", "n_clicks"),
        State("test-help-modal", "is_open"),
        prevent_initial_call=True
    )
    def toggle_test_help_modal(open_clicks, close_clicks, is_open):
        """Ouvre/ferme le modal d'aide pour les tests"""
        return not is_open

    # ===== Publier et Run DQ depuis le Builder =====
    
    @app.callback(
        Output("publish-status", "children"),
        Input("publish", "n_clicks"),
        State("store_datasets", "data"),
        State("store_metrics", "data"),
        State("store_tests", "data"),
        State("store_scripts", "data"),
        State("url", "search"),
        State("run-context-store", "data"),
        prevent_initial_call=True
    )
    def publish_dq_config(n_clicks, datasets, metrics, tests, scripts, search, run_context):
        """Publie la configuration DQ dans un fichier YAML"""
        if not n_clicks:
            raise PreventUpdate
        
        try:
            # Générer la configuration
            q = parse_query(search or "")
            cfg = cfg_template()
            
            # Context avec quarter
            quarter_value = (run_context or {}).get("quarter") if run_context else None
            cfg["context"] = {
                "stream": q.get("stream"),
                "project": q.get("project"),
                "zone": q.get("zone"),
                "quarter": quarter_value
            }
            
            cfg["databases"] = datasets or []
            
            # Convertir metrics en dictionnaire
            metrics_dict = {}
            for m in (metrics or []):
                metric_id = m.get("id")
                if metric_id:
                    metric_copy = {k: v for k, v in m.items() if k != "id"}
                    if "params" in metric_copy:
                        metric_copy["params"] = {k: v for k, v in metric_copy["params"].items() 
                                                if k not in ["dataset", "column", "where", "expr"]}
                    metrics_dict[metric_id] = metric_copy
            
            # Convertir tests en dictionnaire
            tests_dict = {}
            for t in (tests or []):
                test_id = t.get("id")
                if test_id:
                    test_copy = {k: v for k, v in t.items() if k != "id"}
                    if "specific" in test_copy:
                        test_copy["specific"] = {k: v for k, v in test_copy["specific"].items() 
                                               if k not in ["lower_enabled", "upper_enabled"]}
                    tests_dict[test_id] = test_copy
            
            cfg["metrics"] = metrics_dict
            cfg["tests"] = tests_dict
            cfg["scripts"] = scripts or []
            
            # Créer un nom de fichier basé sur le contexte
            stream = q.get("stream") or "unknown"
            project = q.get("project") or "unknown"
            zone = q.get("zone") or "unknown"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"dq_{stream}_{project}_{zone}_{timestamp}.yaml"
            
            # Sauvegarder dans dq/definitions/
            output_dir = os.path.join(os.getcwd(), "dq", "definitions")
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, filename)
            
            with open(output_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(cfg, f, sort_keys=False, allow_unicode=True)
            
            return dbc.Alert([
                html.Div([
                    html.Strong("✅ Configuration publiée avec succès !"),
                    html.Br(),
                    html.Small(f"Fichier: {filename}"),
                    html.Br(),
                    html.Small(f"Chemin: {output_path}")
                ])
            ], color="success", className="mt-3")
            
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            return dbc.Alert([
                html.Div(f"❌ Erreur lors de la publication: {e}"),
                html.Pre(tb, style={"whiteSpace": "pre-wrap", "fontSize": "10px"})
            ], color="danger", className="mt-3")
    
    @app.callback(
        Output("dq-run-results", "children"),
        Output("download-dq-results", "data"),
        Input("run-dq", "n_clicks"),
        State("store_datasets", "data"),
        State("store_metrics", "data"),
        State("store_tests", "data"),
        State("store_scripts", "data"),
        State("url", "search"),
        State("run-context-store", "data"),
        prevent_initial_call=True
    )
    def run_dq_from_builder(n_clicks, datasets, metrics, tests, scripts, search, run_context):
        """Execute la configuration DQ sur les données et génère un fichier Excel"""
        if not n_clicks:
            raise PreventUpdate
        
        try:
            from src.core.executor import execute
            from src.core.parser import build_execution_plan
            from src.core.models_inventory import Inventory
            from src.core.models_dq import DQDefinition
            from src.core.simple_excel_export import export_run_result_to_excel
            from pathlib import Path
            import pandas as pd
            import yaml
            import tempfile
            import os
            
            # Charger l'inventaire
            inv_path = Path("config/inventory.yaml")
            inv_data = yaml.safe_load(inv_path.read_text(encoding="utf-8"))
            inv = Inventory(**inv_data)
            
            # Générer la configuration
            q = parse_query(search or "")
            cfg = cfg_template()
            
            quarter_value = (run_context or {}).get("quarter") if run_context else None
            cfg["context"] = {
                "stream": q.get("stream"),
                "project": q.get("project"),
                "zone": q.get("zone"),
                "quarter": quarter_value
            }
            
            cfg["databases"] = datasets or []
            
            # Convertir metrics
            metrics_dict = {}
            for m in (metrics or []):
                metric_id = m.get("id")
                if metric_id:
                    metric_copy = {k: v for k, v in m.items() if k != "id"}
                    metrics_dict[metric_id] = metric_copy
            
            # Convertir tests
            tests_dict = {}
            for t in (tests or []):
                test_id = t.get("id")
                if test_id:
                    test_copy = {k: v for k, v in t.items() if k != "id"}
                    if "specific" in test_copy:
                        test_copy["specific"] = {k: v for k, v in test_copy["specific"].items() 
                                               if k not in ["lower_enabled", "upper_enabled"]}
                    tests_dict[test_id] = test_copy
            
            cfg["metrics"] = metrics_dict
            cfg["tests"] = tests_dict
            cfg["scripts"] = scripts or []
            
            # Créer un objet DQDefinition
            dq = DQDefinition(**cfg)
            
            # Construire le plan et exécuter (même système que le runner DQ normal)
            plan = build_execution_plan(inv, dq, overrides={})
            
            # Utiliser LocalReader qui sait résoudre les alias via plan.alias_map
            from src.core.connectors import LocalReader
            run_result = execute(plan, loader=LocalReader(plan.alias_map), investigate=False)
            
            # Générer un fichier Excel temporaire
            stream = q.get("stream", "unknown")
            project = q.get("project", "unknown")
            zone = q.get("zone", "unknown")
            dq_id = f"{stream}_{project}_{zone}"
            
            # Créer un fichier temporaire pour l'export
            temp_dir = tempfile.gettempdir()
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"dq_results_{dq_id}_{timestamp}.xlsx"
            temp_path = os.path.join(temp_dir, filename)
            
            # Exporter vers Excel (même fonction que le Runner)
            export_run_result_to_excel(
                run_result=run_result,
                output_path=temp_path,
                dq_id=dq_id,
                quarter=quarter_value,
                project=project
            )
            
            # Lire le fichier pour le téléchargement
            with open(temp_path, 'rb') as f:
                excel_content = f.read()
            
            # Nettoyer le fichier temporaire
            try:
                os.remove(temp_path)
            except:
                pass
            
            # Préparer le résumé pour l'affichage
            total_tests = len(run_result.tests)
            passed_tests = sum(1 for t in run_result.tests.values() if t.passed)
            failed_tests = total_tests - passed_tests
            
            status_color = "success" if failed_tests == 0 else "danger"
            status_icon = "check-circle-fill" if failed_tests == 0 else "x-circle-fill"
            
            display = dbc.Card([
                dbc.CardHeader([
                    html.I(className=f"bi bi-{status_icon} me-2"),
                    "Résultats de l'exécution DQ"
                ], className=f"bg-{status_color} text-white"),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.H6("Métriques"),
                            html.H3(len(run_result.metrics), className="text-primary")
                        ], md=3),
                        dbc.Col([
                            html.H6("Tests Total"),
                            html.H3(total_tests, className="text-info")
                        ], md=3),
                        dbc.Col([
                            html.H6("Tests Réussis"),
                            html.H3(passed_tests, className="text-success")
                        ], md=3),
                        dbc.Col([
                            html.H6("Tests Échoués"),
                            html.H3(failed_tests, className="text-danger")
                        ], md=3)
                    ]),
                    html.Hr(),
                    dbc.Alert([
                        html.I(className="bi bi-download me-2"),
                        f"Le fichier Excel '{filename}' a été généré et va être téléchargé automatiquement."
                    ], color="info", className="mb-0")
                ])
            ], className="mt-3")
            
            return display, dcc.send_bytes(excel_content, filename)
            
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            return dbc.Alert([
                html.Div(f"❌ Erreur lors de l'exécution: {e}"),
                html.Pre(tb, style={"whiteSpace": "pre-wrap", "fontSize": "10px"})
            ], color="danger", className="mt-3"), no_update

    # ===== Callbacks pour les Scripts =====
    
    @app.callback(
        Output("script-picker", "options"),
        Input("url", "search"),
        prevent_initial_call=False
    )
    def update_script_options(search):
        """Met à jour les scripts disponibles selon le contexte"""
        from dq.scripts.script_loader import get_script_options
        
        q = parse_query(search or "")
        stream = q.get("stream")
        project = q.get("project")
        zone = q.get("zone")
        
        options = get_script_options(stream=stream, project=project, zone=zone)
        
        return options
    
    @app.callback(
        Output("store_scripts", "data"),
        Output("save-scripts-status", "children"),
        Input("save-scripts", "n_clicks"),
        State("script-picker", "value"),
        State("url", "search"),
        prevent_initial_call=True
    )
    def save_scripts(n_clicks, selected_scripts, search):
        """Enregistre les scripts sélectionnés"""
        from dq.scripts.script_loader import get_script_by_id
        
        if not n_clicks:
            raise PreventUpdate
        
        q = parse_query(search or "")
        stream = q.get("stream")
        project = q.get("project")
        zone = q.get("zone")
        
        scripts_data = []
        
        if selected_scripts:
            for script_id in selected_scripts:
                metadata = get_script_by_id(script_id, stream, project, zone)
                
                if metadata:
                    scripts_data.append({
                        "id": metadata.id,
                        "label": metadata.label,
                        "path": metadata.path,
                        "enabled": True,
                        "execute_on": metadata.execute_on,
                        "params": metadata.params
                    })
        
        status = f"✅ {len(scripts_data)} script(s) enregistré(s)" if scripts_data else "Aucun script sélectionné"
        
        return scripts_data, status
    
    @app.callback(
        Output("selected-scripts-display", "children"),
        Input("store_scripts", "data")
    )
    def display_selected_scripts(scripts_data):
        """Affiche les scripts sélectionnés"""
        if not scripts_data:
            return html.Div("Aucun script sélectionné", className="text-muted")
        
        cards = []
        for script in scripts_data:
            cards.append(
                dbc.Card([
                    dbc.CardHeader([
                        html.Strong(script.get("label", script.get("id"))),
                        dbc.Badge(
                            script.get("execute_on", "post_dq"),
                            color="info" if script.get("execute_on") == "post_dq" else "warning",
                            className="ms-2"
                        )
                    ]),
                    dbc.CardBody([
                        html.Small(f"ID: {script.get('id')}", className="d-block text-muted"),
                        html.Small(f"Path: {script.get('path')}", className="d-block text-muted"),
                        html.Small(f"Params: {json.dumps(script.get('params', {}))}", className="d-block text-muted mt-1")
                    ])
                ], className="mb-2")
            )
        
        return html.Div(cards)

    # ===== Télécharger le résumé DQ =====
    
    @app.callback(
        Output("download-summary", "data"),
        Input("download-summary-btn", "n_clicks"),
        State("store_datasets", "data"),
        State("store_metrics", "data"),
        State("store_tests", "data"),
        State("store_scripts", "data"),
        State("url", "search"),
        State("run-context-store", "data"),
        prevent_initial_call=True
    )
    def download_dq_summary(n_clicks, datasets, metrics, tests, scripts, search, run_context):
        """Télécharge un résumé visuel de la configuration DQ au format Markdown"""
        if not n_clicks:
            raise PreventUpdate
        
        try:
            # Générer la configuration
            q = parse_query(search or "")
            cfg = cfg_template()
            
            # Context avec quarter
            quarter_value = (run_context or {}).get("quarter") if run_context else None
            cfg["context"] = {
                "stream": q.get("stream"),
                "project": q.get("project"),
                "zone": q.get("zone"),
                "quarter": quarter_value
            }
            
            cfg["datasets"] = datasets or []
            cfg["metrics"] = metrics or []
            cfg["tests"] = tests or []
            cfg["scripts"] = scripts or []
            
            # Créer le résumé Markdown
            lines = []
            lines.append("# 📊 Résumé de la Configuration Data Quality\n")
            lines.append(f"**Date de génération:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            lines.append("---\n")
            
            # Context
            lines.append("## 🎯 Contexte\n")
            ctx = cfg.get("context", {})
            lines.append(f"- **Stream:** {ctx.get('stream') or 'N/A'}")
            lines.append(f"- **Project:** {ctx.get('project') or 'N/A'}")
            lines.append(f"- **Zone:** {ctx.get('zone') or 'N/A'}")
            lines.append(f"- **Quarter:** {ctx.get('quarter') or 'N/A'}\n")
            
            # Datasets
            lines.append("## 📁 Datasets\n")
            if datasets:
                for i, ds in enumerate(datasets, 1):
                    lines.append(f"### {i}. {ds.get('alias', 'Sans alias')}")
                    lines.append(f"- **Dataset:** `{ds.get('dataset', 'N/A')}`")
                    if ds.get('filters'):
                        lines.append(f"- **Filtres:** {', '.join([f.get('id', 'N/A') for f in ds['filters']])}")
                    lines.append("")
            else:
                lines.append("*Aucun dataset configuré*\n")
            
            # Metrics
            lines.append("## 📈 Métriques\n")
            if metrics:
                for i, m in enumerate(metrics, 1):
                    lines.append(f"### {i}. {m.get('id', 'N/A')} ({m.get('type', 'N/A')})")
                    lines.append(f"- **Type:** {m.get('type', 'N/A')}")
                    if m.get('column'):
                        lines.append(f"- **Colonne:** `{m['column']}`")
                    if m.get('dataset'):
                        lines.append(f"- **Dataset:** {m['dataset']}")
                    # Afficher autres paramètres
                    skip_keys = {'id', 'type', 'column', 'dataset'}
                    other_params = {k: v for k, v in m.items() if k not in skip_keys}
                    if other_params:
                        lines.append(f"- **Paramètres:** {json.dumps(other_params, ensure_ascii=False)}")
                    lines.append("")
            else:
                lines.append("*Aucune métrique configurée*\n")
            
            # Tests
            lines.append("## ✅ Tests\n")
            if tests:
                for i, t in enumerate(tests, 1):
                    lines.append(f"### {i}. {t.get('id', 'N/A')} ({t.get('type', 'N/A')})")
                    lines.append(f"- **Type:** {t.get('type', 'N/A')}")
                    if t.get('metric'):
                        lines.append(f"- **Métrique:** {t['metric']}")
                    # Afficher autres paramètres
                    skip_keys = {'id', 'type', 'metric'}
                    other_params = {k: v for k, v in t.items() if k not in skip_keys}
                    if other_params:
                        lines.append(f"- **Paramètres:** {json.dumps(other_params, ensure_ascii=False)}")
                    lines.append("")
            else:
                lines.append("*Aucun test configuré*\n")
            
            # Scripts
            lines.append("## 🔧 Scripts\n")
            if scripts:
                for i, s in enumerate(scripts, 1):
                    lines.append(f"### {i}. {s.get('label', s.get('id', 'N/A'))}")
                    lines.append(f"- **ID:** {s.get('id', 'N/A')}")
                    lines.append(f"- **Exécution:** {s.get('execute_on', 'post_dq')}")
                    lines.append(f"- **Path:** `{s.get('path', 'N/A')}`")
                    if s.get('params'):
                        lines.append(f"- **Paramètres:** {json.dumps(s['params'], ensure_ascii=False)}")
                    lines.append("")
            else:
                lines.append("*Aucun script configuré*\n")
            
            # Statistiques
            lines.append("---")
            lines.append("## 📊 Statistiques\n")
            lines.append(f"- **Datasets:** {len(datasets or [])}")
            lines.append(f"- **Métriques:** {len(metrics or [])}")
            lines.append(f"- **Tests:** {len(tests or [])}")
            lines.append(f"- **Scripts:** {len(scripts or [])}")
            
            # Générer le nom de fichier
            stream = ctx.get('stream', 'unknown')
            project = ctx.get('project', 'unknown')
            zone = ctx.get('zone', 'unknown')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"dq_summary_{stream}_{project}_{zone}_{timestamp}.md"
            
            content = "\n".join(lines)
            
            return dict(content=content, filename=filename)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise PreventUpdate
