# Callbacks de la page Build (wizard de création DQ)

import json
import urllib.parse as urlparse
from datetime import datetime
from dash import html, dcc, Input, Output, State, ALL, no_update
import dash_bootstrap_components as dbc
import yaml
import re

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
    validate_cfg
)
from src.metrics_registry import get_metric_options, get_metric_meta
from src.dq_runner import run_dq_config
import pandas as pd


def register_build_callbacks(app):
    """Enregistre tous les callbacks de la page Build"""
    
    # ===== Contexte et Datasets =====
    
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
        dq_point_text = f" • Point DQ = {q['dq_point']}" if q.get("dq_point") else ""
        return dbc.Alert(
            f"Contexte: Stream = {q['stream']} • Projet = {q['project']}{dq_point_text}",
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
        State("store_datasets", "data"),
        prevent_initial_call='initial_duplicate'
    )
    def update_dataset_options(search, current_data):
        """Met à jour les datasets disponibles selon le contexte et auto-charge le store"""
        q = parse_query(search) if search else {}
        
        stream = q.get("stream")
        projet = q.get("project") 
        dq_point = q.get("dq_point")
        
        datasets = list_project_datasets(stream, projet, dq_point)
        options = [{"label": ds, "value": ds} for ds in datasets]
        
        # Auto-charger les datasets dans le store s'il est vide et qu'on a un contexte
        if not current_data and stream and projet and dq_point and datasets:
            auto_data = [{"alias": ds.lower(), "dataset": ds} for ds in datasets]
            return options, auto_data
        
        return options, current_data or no_update

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
                dbc.Col(html.Div(ds), md=6),
                dbc.Col(dcc.Input(
                    id={"role": "alias-input", "ds": ds},
                    type="text",
                    value=ds.lower(),
                    style={"width": "100%"},
                    persistence=True,
                    persistence_type="session",
                    autoComplete="off"
                ), md=6)
            ], className="py-1 border-bottom"))
        return dbc.Container(rows, fluid=True)

    @app.callback(
        Output("save-datasets-status", "children"),
        Output("store_datasets", "data"),
        Input("save-datasets", "n_clicks"),
        State("ds-picker", "value"),
        State({"role": "alias-input", "ds": ALL}, "value"),
        State({"role": "alias-input", "ds": ALL}, "id")
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

    # ===== Métriques =====
    
    @app.callback(
        Output("metric-params", "children"),
        Input("metric-type", "value"),
        State("store_datasets", "data")
    )
    def render_metric_form(metric_type, ds_data):
        """Affiche le formulaire de création de métrique selon le type avec groupes visuels"""
        if not metric_type:
            return dbc.Alert("Choisis un type de métrique.", color="light")
        ds_aliases = [d["alias"] for d in (ds_data or [])]
        if not ds_aliases:
            return dbc.Alert(
                "Enregistre d'abord des datasets (Étape 1), puis reviens ici.",
                color="warning"
            )

    # Groupe 1: Identification
        id_card = dbc.Card([
            dbc.CardHeader("📝 Identification"),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label("ID de la métrique"),
                        dcc.Input(
                            id={"role": "metric-id"},
                            type="number",
                            value=None,
                            placeholder="Entrez un numéro (ex: 1 pour M-001) ou laissez vide",
                            style={"width": "100%"},
                            persistence=True,
                            persistence_type="session",
                            min=1
                        ),
                        html.Small("Saisis seulement le numéro. Préfixe 'M-' sera ajouté automatiquement.", className="text-muted")
                    ], md=12)
                ])
            ])
        ], className="mb-3")

        # Groupe 2: Sélection Dataset & Filtre
        meta = get_metric_meta(metric_type)
        db_visible = meta.get("requires_database", True)

        dataset_card = dbc.Card([
            dbc.CardHeader("📊 Sélection Dataset & Filtre"),
            dbc.CardBody([
                html.Small("Sélectionnez parmi les datasets configurés à l'étape 1 (Datasets)", className="text-muted d-block mb-2"),
                dbc.Row([
                    dbc.Col([
                        html.Label("Dataset (alias)"),
                        dcc.Dropdown(
                            id={"role": "metric-db"},
                            options=[{"label": a, "value": a} for a in ds_aliases],
                            value=ds_aliases[0] if ds_aliases else None,
                            clearable=False,
                            persistence=True,
                            persistence_type="session",
                            style={"display": "block" if db_visible else "none"}
                        )
                    ], md=6),
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
                ])
            ])
        ], className="mb-3")

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
                
            # text param
            if p_type == "text":
                p_name = p.get("name")
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
        
        return html.Div([id_card, dataset_card, options_card, preview])

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
        State({"role": "metric-param", "name": ALL}, "value"),
        State("store_metrics", "data"),
        prevent_initial_call=True
    )
    def preview_metric(force, mtype, mid_list, mdb_list, mcol_list, mwhere_list, mexpr_list, mparam_values, metrics):
        """Génère la prévisualisation JSON de la métrique"""
        if not mtype:
            return "", False, ""
        mid = first(mid_list)
        mdb = first(mdb_list)
        # Handle multi-column selection: mcol_list[0] is the value from dropdown (can be a list if multi=True)
        mcol_raw = first(mcol_list)
        mcol = mcol_raw if mcol_raw else None
        mwhere = first(mwhere_list)
        mexpr = first(mexpr_list)
        # metric params values come as a list corresponding to declared params order
        mparams = (mparam_values or [])

        # mid is now expected to be a number or None. If provided, format as M-###.
        display_id = None
        try:
            if isinstance(mid, (int, float)) or (isinstance(mid, str) and mid.isdigit()):
                num = int(mid)
                display_id = f"M-{num:03d}"
        except Exception:
            display_id = None
        obj = {"id": (display_id or "(auto)"), "type": mtype}
        meta = get_metric_meta(mtype) or {}
        params = meta.get("params", [])
        # Populate known params
        if "database" in params or meta.get("requires_database"):
            obj["database"] = mdb or ""
        if "column" in params or meta.get("requires_column"):
            # Handle both single column (string) and multi-column (list)
            if isinstance(mcol, list):
                obj["column"] = mcol if mcol else []
            else:
                obj["column"] = mcol or ""
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
        # If a concrete display_id was provided, check whether it already exists
        if display_id:
            existing_ids = {x.get("id") for x in (metrics or []) if x.get("id")}
            if display_id in existing_ids:
                msg = f"Le numéro {display_id} est déjà utilisé. Un ID unique sera attribué automatiquement si nécessaire."
                return json.dumps(obj, ensure_ascii=False, indent=2), True, msg
        return json.dumps(obj, ensure_ascii=False, indent=2), False, ""

    @app.callback(
        Output("add-metric-status", "children"),
        Output("store_metrics", "data"),
        Output("metrics-list", "children"),
        Output("metric-tabs", "active_tab"),
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
    )
    def add_metric(n, preview_list, metrics, mtype, mid_list, mdb_list, mcol_list, mwhere_list, mexpr_list, mparam_values):
        """Ajoute une métrique au store et met à jour la liste"""
        if not n:
            return "", metrics, "", no_update
        
        preview_text = first(preview_list)
        m = None
        if preview_text:
            try:
                m = json.loads(preview_text)
            except Exception:
                m = None
        if m is None:
            mid_raw = first(mid_list)
            mdb = first(mdb_list)
            # Handle multi-column selection: mcol_list[0] is the value from dropdown (can be a list if multi=True)
            mcol_raw = first(mcol_list)
            mcol = mcol_raw if mcol_raw else None
            mwhere = first(mwhere_list)
            mexpr = first(mexpr_list)
            if not mtype:
                return "Prévisualisation vide/invalide.", metrics, no_update, no_update
            # Normalize ID: accept numeric (e.g. '1' -> M-001) or M-<num>; otherwise leave blank to auto-generate
            m = {"id": None, "type": mtype}
            # mid_raw should be numeric or None. Accept numeric strings as well.
            if mid_raw is not None and mid_raw != "":
                try:
                    mnum = int(mid_raw)
                    m["id"] = f"M-{mnum:03d}"
                except Exception:
                    # ignore and let auto-generate
                    m["id"] = None
            meta = get_metric_meta(mtype) or {}
            params = meta.get("params", [])
            # Generic population based on params
            if "database" in params or meta.get("requires_database"):
                m["database"] = mdb or ""
            if "column" in params or meta.get("requires_column"):
                # Handle both single column (string) and multi-column (list)
                if isinstance(mcol, list):
                    m["column"] = mcol if mcol else []
                else:
                    m["column"] = mcol or ""
            if "where" in params and mwhere:
                m["where"] = mwhere
            if "expr" in params:
                m["expr"] = mexpr or ""
            # Metric-param values: metric-param name list corresponds to mparam_values order
            # Extract common params by name if provided
            try:
                # mparam_values is a list of values corresponding to each metric-param input present
                # We need to map declared params names to provided values - assume order matches meta.params
                declared = [p.get('name') if isinstance(p, dict) else p for p in params]
                for name, val in zip(declared, (mparam_values or [])):
                    if name is None:
                        continue
                    # columns param may be single or list
                    if name == 'columns':
                        m['columns'] = val or []
                    elif name == 'dataset_filter' or name == 'dataset':
                        # store the selected alias
                        m['database_filter'] = val or ''
                    else:
                        m[name] = val
            except Exception:
                pass
            # Extract metric-param values (dataset_filter, columns, etc.)
            try:
                # Grab all metric-param inputs present in the DOM
                from dash import callback_context
                ctx = callback_context
                # state values for metric-param are not directly accessible here; instead get them from function args by adding States
            except Exception:
                pass
        
        metrics = (metrics or [])
        existing_ids = {x.get("id") for x in metrics}
        
        # Générer un ID unique au format M-XXX si nécessaire
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
        
        metrics.append(m)
        items = [
            html.Pre(
                json.dumps(x, ensure_ascii=False, indent=2),
                className="p-2 mb-2",
                style={"background": "#111", "color": "#eee"}
            ) for x in metrics
        ]
        return f"Métrique ajoutée: {m['id']}", metrics, html.Div(items), "tab-metric-viz"

    # ===== Tests =====
    
    @app.callback(
        Output("test-params", "children"),
        Input("test-type", "value"),
        State("store_datasets", "data"),
        State("store_metrics", "data")
    )
    def render_test_form(test_type, ds_data, metrics):
        """Affiche le formulaire de création de test selon le type avec groupes visuels"""
        if not test_type:
            return dbc.Alert("Choisis un type de test.", color="light")
        ds_aliases = [d["alias"] for d in (ds_data or [])]
        if not ds_aliases:
            return dbc.Alert("Enregistre d'abord des datasets.", color="warning")

        # Groupe 1: Identification
        id_card = dbc.Card([
            dbc.CardHeader("📝 Identification"),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label("ID du test"),
                        dcc.Input(
                            id={"role": "test-id"},
                            type="number",
                            value=None,
                            placeholder="Entrez un numéro (ex: 1 pour T-001) ou laissez vide",
                            style={"width": "100%"},
                            persistence=True,
                            persistence_type="session",
                            min=1,
                            autoComplete="off"
                        ),
                        html.Small("Saisis seulement le numéro. Préfixe 'T-' sera ajouté automatiquement.", className="text-muted")
                    ], md=6),
                    dbc.Col([
                        html.Label("Sévérité"),
                        dcc.Dropdown(
                            id={"role": "test-sev"},
                            options=[{"label": x, "value": x} for x in ["low", "medium", "high"]],
                            value="medium",
                            clearable=False,
                            persistence=True,
                            persistence_type="session"
                        )
                    ], md=3),
                    dbc.Col([
                        html.Label("Échantillon si échec"),
                        dcc.Checklist(
                            id={"role": "test-sof"},
                            options=[{"label": " Oui", "value": "yes"}],
                            value=["yes"],
                            persistence=True,
                            persistence_type="session"
                        )
                    ], md=3),
                ])
            ])
        ], className="mb-3")

        if test_type in ("null_rate", "uniqueness", "range", "regex"):
            metric_ids = [m.get("id") for m in (metrics or []) if m.get("id")]
            
            # Groupe 2: Choix du type de source
            source_choice_card = dbc.Card([
                dbc.CardHeader("🎯 Source des données"),
                dbc.CardBody([
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
                ])
            ], className="mb-3")
            
            # Application selon le choix (sera géré par callback)
            target_card = source_choice_card
            
            # Groupe 3: Paramètres spécifiques
            params_content = []
            if test_type == "range":
                params_content = [
                    dbc.Row([
                        dbc.Col([
                            html.Label("Valeur Min"),
                            dcc.Input(
                                id={"role": "test-min"},
                                type="text",
                                value="0",
                                placeholder="Ex: 0",
                                persistence=True,
                                persistence_type="session",
                                autoComplete="off"
                            )
                        ], md=6),
                        dbc.Col([
                            html.Label("Valeur Max"),
                            dcc.Input(
                                id={"role": "test-max"},
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
            
            params_card = dbc.Card([
                dbc.CardHeader("⚙️ Paramètres du test"),
                dbc.CardBody(params_content if params_content else [html.P("Aucun paramètre spécifique pour ce type", className="text-muted")])
            ], className="mb-3") if params_content else html.Div()
            
            # Groupe 4: Seuils et tolérance
            threshold_card = dbc.Card([
                dbc.CardHeader("📊 Seuils et tolérance"),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Label("Opérateur"),
                            dcc.Dropdown(
                                id={"role": "test-op"},
                                options=[{"label": x, "value": x} for x in ["<=", "<", ">=", ">", "=", "!="]],
                                value="<=",
                                clearable=False,
                                persistence=True,
                                persistence_type="session"
                            )
                        ], md=6),
                        dbc.Col([
                            html.Label("Valeur seuil"),
                            dcc.Input(
                                id={"role": "test-thr"},
                                type="text",
                                value="0.005",
                                placeholder="Ex: 0.01 (1%)",
                                persistence=True,
                                persistence_type="session",
                                autoComplete="off"
                            ),
                            html.Small("Ex: 0.005 = 0.5%", className="text-muted")
                        ], md=6),
                    ])
                ])
            ], className="mb-3")
            
            # Prévisualisation
            preview = dbc.Card([
                dbc.CardHeader("👁️ Prévisualisation"),
                dbc.CardBody([
                    html.Pre(
                        id={"role": "test-preview"},
                        style={"background": "#222", "color": "#eee", "padding": "0.75rem"}
                    )
                ])
            ])
            
            return html.Div([id_card, target_card, params_card, threshold_card, preview])

        if test_type == "foreign_key":
            metric_ids = [m.get("id") for m in (metrics or []) if m.get("id")]
            ref_options = (
                [{"label": f"📊 {mid}", "value": f"metric:{mid}"} for mid in metric_ids] +
                [{"label": f"🗄️ {a}", "value": f"db:{a}"} for a in ds_aliases]
            )
            
            # Groupe 2: Colonne source
            source_card = dbc.Card([
                dbc.CardHeader("🎯 Colonne source"),
                dbc.CardBody([
                    dbc.Row([
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
                            html.Label("Colonne"),
                            dcc.Dropdown(
                                id={"role": "test-col"},
                                options=[],
                                placeholder="Choisir une colonne",
                                clearable=False,
                                persistence=True,
                                persistence_type="session"
                            )
                        ], md=6)
                    ])
                ])
            ], className="mb-3")
            
            # Groupe 3: Référence
            ref_card = dbc.Card([
                dbc.CardHeader("🔗 Référence (Foreign Key)"),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Label("Référence (Base ou Métrique)"),
                            html.Div("Sélectionne une base de données 🗄️ ou une métrique 📊", className="text-muted small mb-1"),
                            dcc.Dropdown(
                                id={"role": "test-ref-db"},
                                options=ref_options,
                                placeholder="Base ou métrique...",
                                clearable=False,
                                persistence=True,
                                persistence_type="session"
                            )
                        ], md=6),
                        dbc.Col([
                            html.Label("Colonne de référence"),
                            html.Div(id="fk-ref-col-helper", className="text-muted small mb-1"),
                            dcc.Dropdown(
                                id={"role": "test-ref-col"},
                                options=[],
                                placeholder="Choisir une colonne",
                                clearable=False,
                                persistence=True,
                                persistence_type="session"
                            )
                        ], md=6)
                    ])
                ])
            ], className="mb-3")
            
            # Prévisualisation
            preview = dbc.Card([
                dbc.CardHeader("👁️ Prévisualisation"),
                dbc.CardBody([
                    html.Pre(
                        id={"role": "test-preview"},
                        style={"background": "#222", "color": "#eee", "padding": "0.75rem"}
                    )
                ])
            ])
            
            return html.Div([id_card, source_card, ref_card, preview])

        return dbc.Alert("Type non géré pour l'instant.", color="warning")

    @app.callback(
        Output({"role": "test-source-inputs"}, "children"),
        Input({"role": "test-source-type"}, "value", ALL),
        State("store_datasets", "data"),
        State("store_metrics", "data")
    )
    def update_test_source_inputs(source_type_list, ds_data, metrics):
        """Affiche les champs appropriés selon le choix database/metric"""
        source_type = first(source_type_list) or "database"
        ds_aliases = [d["alias"] for d in (ds_data or [])]
        metric_ids = [m.get("id") for m in (metrics or []) if m.get("id")]
        
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
                    html.Label("Colonne"),
                    dcc.Dropdown(
                        id={"role": "test-col"},
                        options=[],
                        placeholder="Choisir une colonne",
                        clearable=False,
                        persistence=True,
                        persistence_type="session"
                    )
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
        Output({"role": "test-ref-col"}, "options"),
        Output({"role": "test-ref-col"}, "disabled"),
        Output("fk-ref-col-helper", "children"),
        Input({"role": "test-ref-db"}, "value", ALL),
        State("store_datasets", "data"),
        prevent_initial_call=True
    )
    def fill_test_ref_columns(ref_values, ds_data):
        """Remplit les options de colonnes de référence pour un test foreign_key"""
        ref_value = first(ref_values)
        if not ref_value:
            return [], True, ""
        
        if ref_value.startswith("metric:"):
            return [], True, "Les métriques n'ont pas de colonnes (valeur unique)"
        
        if ref_value.startswith("db:"):
            db_alias = ref_value[3:]
            if not ds_data:
                return [], True, ""
            ds_name = next((d["dataset"] for d in ds_data if d["alias"] == db_alias), None)
            if not ds_name:
                return [], True, f"Dataset introuvable pour l'alias « {db_alias} »"
            cols = get_columns_for_dataset(ds_name)
            if not cols:
                return [], True, f"Aucune colonne pour « {ds_name} »"
            opts = [{"label": c, "value": c} for c in cols]
            return opts, False, f"{len(opts)} colonne(s) disponibles"
        
        return [], True, ""

    @app.callback(
        Output({"role": "test-preview"}, "children"),
        Output("toast", "is_open", allow_duplicate=True),
        Output("toast", "children", allow_duplicate=True),
        Input("test-type", "value"),
        Input({"role": "test-id"}, "value", ALL),
        Input({"role": "test-sev"}, "value", ALL),
        Input({"role": "test-sof"}, "value", ALL),
        Input({"role": "test-db"}, "value", ALL),
        Input({"role": "test-col"}, "value", ALL),
        Input({"role": "test-metric"}, "value", ALL),
        Input({"role": "test-op"}, "value", ALL),
        Input({"role": "test-thr"}, "value", ALL),
        Input({"role": "test-min"}, "value", ALL),
        Input({"role": "test-max"}, "value", ALL),
        Input({"role": "test-pattern"}, "value", ALL),
        Input({"role": "test-ref-db"}, "value", ALL),
        Input({"role": "test-ref-col"}, "value", ALL),
        State("store_tests", "data"),
        prevent_initial_call=True
    )
    def preview_test(ttype, tid_list, sev_list, sof_list, db_list, col_list, metric_list, op_list, thr_list, vmin_list, vmax_list, pat_list, refdb_list, refcol_list, tests):
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
        # tid_raw is expected to be numeric or None. Format as T-### if present.
        tid = None
        try:
            if isinstance(tid_raw, (int, float)) or (isinstance(tid_raw, str) and str(tid_raw).isdigit()):
                tid = f"T-{int(tid_raw):03d}"
        except Exception:
            tid = None
        db, col = first_with_default(db_list), first_with_default(col_list)
        metric = first_with_default(metric_list)
        op, thr = first_with_default(op_list), first_with_default(thr_list)
        vmin, vmax = first_with_default(vmin_list), first_with_default(vmax_list)
        pat = first_with_default(pat_list)
        refdb, refcol = first_with_default(refdb_list), first_with_default(refcol_list)

        obj = {
            "id": tid or "(auto)",
            "type": ttype,
            "severity": (sev or "medium"),
            "sample_on_fail": ("yes" in (sof or []))
        }
        if ttype in ("null_rate", "uniqueness", "range", "regex"):
            # Si une métrique est sélectionnée, utiliser la métrique
            if metric:
                obj.update({"metric": metric})
            else:
                obj.update({"database": db or "", "column": col or ""})
            
            if ttype == "range":
                obj.update({"min": vmin, "max": vmax})
            if ttype == "regex":
                obj.update({"pattern": pat})
            if op and thr is not None:
                obj["threshold"] = {"op": op, "value": thr}
        elif ttype == "foreign_key":
            obj.update({"database": db or "", "column": col or ""})
            if refdb and refdb.startswith("metric:"):
                obj["ref"] = {"metric": refdb[7:]}
            elif refdb and refdb.startswith("db:"):
                obj["ref"] = {"database": refdb[3:], "column": refcol or ""}
            else:
                obj["ref"] = {"database": refdb or "", "column": refcol or ""}
        # If tid provided, check whether it's already used
        if tid:
            existing_ids = {x.get("id") for x in (tests or []) if x.get("id")}
            if tid in existing_ids:
                msg = f"Le numéro {tid} est déjà utilisé. Un ID unique sera attribué automatiquement si nécessaire."
                return json.dumps(obj, ensure_ascii=False, indent=2), True, msg
        return json.dumps(obj, ensure_ascii=False, indent=2), False, ""

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
        State({"role": "test-db"}, "value", ALL),
        State({"role": "test-col"}, "value", ALL),
        State({"role": "test-metric"}, "value", ALL),
        State({"role": "test-op"}, "value", ALL),
        State({"role": "test-thr"}, "value", ALL),
        State({"role": "test-min"}, "value", ALL),
        State({"role": "test-max"}, "value", ALL),
        State({"role": "test-pattern"}, "value", ALL),
        State({"role": "test-ref-db"}, "value", ALL),
        State({"role": "test-ref-col"}, "value", ALL),
    )
    def add_test(n, preview_list, tests, ttype, tid_list, sev_list, sof_list, db_list, col_list, metric_list, op_list, thr_list, vmin_list, vmax_list, pat_list, refdb_list, refcol_list):
        """Ajoute un test au store et met à jour la liste"""
        if not n:
            return "", tests, "", no_update
        
        def first_with_default(val, default=None):
            if val is None:
                return default
            if isinstance(val, list):
                return val[0] if val else default
            return val
        
        preview_text = first_with_default(preview_list)
        t = None
        if preview_text:
            try:
                t = json.loads(preview_text)
            except Exception:
                t = None
        if t is None:
            if not ttype:
                return "Prévisualisation vide/invalide.", tests, no_update, no_update
            tid_raw, sev, sof = first_with_default(tid_list), first_with_default(sev_list, "medium"), first_with_default(sof_list, [])
            db, col = first_with_default(db_list), first_with_default(col_list)
            metric = first_with_default(metric_list)
            op, thr = first_with_default(op_list), first_with_default(thr_list)
            vmin, vmax = first_with_default(vmin_list), first_with_default(vmax_list)
            pat = first_with_default(pat_list)
            refdb, refcol = first_with_default(refdb_list), first_with_default(refcol_list)
            # Normalize tid input: accept numeric or T-<num>
            t = {"id": None, "type": ttype, "severity": (sev or "medium"), "sample_on_fail": ("yes" in (sof or []))}
            # Accept numeric tid_raw (int or numeric string). Otherwise leave None to auto-generate.
            if tid_raw is not None and tid_raw != "":
                try:
                    tnum = int(tid_raw)
                    t["id"] = f"T-{tnum:03d}"
                except Exception:
                    t["id"] = None
            if ttype in ("null_rate", "uniqueness", "range", "regex"):
                # Si une métrique est sélectionnée, utiliser la métrique
                if metric:
                    t.update({"metric": metric})
                else:
                    t.update({"database": db or "", "column": col or ""})
                
                if ttype == "range":
                    t.update({"min": vmin, "max": vmax})
                if ttype == "regex":
                    t.update({"pattern": pat})
                if op and thr is not None:
                    t["threshold"] = {"op": op, "value": thr}
            elif ttype == "foreign_key":
                t.update({"database": db or "", "column": col or ""})
                if refdb and refdb.startswith("metric:"):
                    t["ref"] = {"metric": refdb[7:]}
                elif refdb and refdb.startswith("db:"):
                    t["ref"] = {"database": refdb[3:], "column": refcol or ""}
                else:
                    t["ref"] = {"database": refdb or "", "column": refcol or ""}
        
        tests = (tests or [])
        existing_ids = {x.get("id") for x in tests}
        
        # Générer un ID unique au format T-XXX
        if not t.get("id") or t.get("id") in existing_ids:
            existing_numbers = []
            for test in tests:
                test_id = str(test.get("id", ""))
                m_match = re.match(r"^T-(\d+)$", test_id)
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

            t["id"] = f"T-{next_num:03d}"
        
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
        Input("fmt", "value"),
        State("url", "search")
    )
    def render_cfg_preview(datasets, metrics, tests, fmt, search):
        """Génère la prévisualisation de la configuration finale"""
        q = parse_query(search or "")
        cfg = cfg_template()
        cfg["context"] = {"stream": q.get("stream"), "project": q.get("project")}
        cfg["databases"] = datasets or []
        cfg["metrics"] = sanitize_metrics(metrics or [])
        cfg["tests"] = sanitize_tests(tests or [])
        cfg["orchestration"]["order"] = [
            *(m.get("id") for m in (metrics or []) if m.get("id")),
            *(t.get("id") for t in (tests or []) if t.get("id"))
        ]
        try:
            if fmt == "yaml":
                return yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True)
            else:
                return json.dumps(cfg, ensure_ascii=False, indent=2)
        except Exception as e:
            return f"Erreur de sérialisation: {e}"

    @app.callback(
        Output("publish-status", "children"),
        Input("publish", "n_clicks"),
        State("cfg-preview", "children"),
        State("fmt", "value"),
        State("folder-id", "value"),
        State("cfg-name", "value")
    )
    def publish_cfg(n, preview_text, fmt, folder_id, cfg_name):
        """Publie la configuration dans un Managed Folder Dataiku"""
        if not n:
            return ""
        if not preview_text:
            return "Aperçu vide : rien à publier."
        # Validate the configuration before publishing
        try:
            cfg_obj = yaml.safe_load(preview_text) if fmt == 'yaml' else json.loads(preview_text)
        except Exception:
            return "Aperçu invalide: impossible de parser le contenu"
        issues = validate_cfg(cfg_obj)
        if issues:
            # Return a formatted list of issues
            return dbc.Alert([html.P("Validation échouée : vérifier la configuration."), html.Ul([html.Li(i) for i in issues])], color="danger", dismissable=True)
        try:
            folder = dataiku.Folder(folder_id or "dq_params")
        except Exception as e:
            return f"Erreur: folder '{folder_id}' introuvable ({e})"
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        fname = f"dq_config_{cfg_name or 'default'}_{ts}." + ("yaml" if fmt == 'yaml' else "json")
        try:
            folder.upload_data(fname, preview_text.encode("utf-8"))
            return f"Publié : {fname} → Folder '{folder_id or 'dq_params'}'"
        except Exception as e:
            return f"Erreur de publication : {e}"

    # ===== Tableaux de visualisation =====
    
    @app.callback(
        Output("metrics-table-container", "children"),
        Input("store_metrics", "data")
    )
    def display_metrics_table(metrics):
        """Affiche le tableau de visualisation des métriques avec actions"""
        if not metrics:
            return dbc.Alert("Aucune métrique définie. Utilisez l'onglet 'Créer' pour en ajouter.", color="info")
        
        # Créer les lignes du tableau avec boutons d'action
        table_rows = []
        
        # En-tête
        header = html.Tr([
            html.Th("ID"),
            html.Th("Type"),
            html.Th("Base"),
            html.Th("Colonne"),
            html.Th("Where"),
            html.Th("Expression"),
            html.Th("Actions", style={"width": "200px"})
        ])
        
        # Lignes de données
        for idx, m in enumerate(metrics):
            metric_id = m.get("id", "N/A")
            has_print = m.get("type") in ("row_count", "sum", "mean", "distinct_count")
            
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
                    "🗑️", 
                    id={"type": "delete-metric", "index": idx},
                    color="danger",
                    size="sm",
                    className="me-1",
                    title="Supprimer"
                ),
                dbc.Button(
                    "🖨️", 
                    id={"type": "print-metric", "index": idx},
                    color="info",
                    size="sm",
                    title="Print",
                    style={"display": "inline-block" if has_print else "none"}
                ) if has_print else None
            ])
            
            row = html.Tr([
                html.Td(metric_id),
                html.Td(m.get("type", "N/A")),
                html.Td(m.get("database", "-")),
                html.Td(m.get("column", "-")),
                html.Td(m.get("where", "-")),
                html.Td(m.get("expr", "-")),
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
            html.H6(f"📊 {len(metrics)} métrique(s) configurée(s)", className="mb-3"),
            table,
            html.Div(id="metric-action-status", className="mt-2")
        ])
    
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
            html.Th("Base"),
            html.Th("Colonne"),
            html.Th("Sévérité"),
            html.Th("Seuil"),
            html.Th("Échantillon"),
            html.Th("Actions", style={"width": "200px"})
        ])
        
        # Lignes de données
        for idx, t in enumerate(tests):
            test_id = t.get("id", "N/A")
            
            # Extraire le seuil si présent (peut être un dict ou un nombre)
            threshold = t.get("threshold")
            if isinstance(threshold, dict):
                threshold_str = f"{threshold.get('op', '')} {threshold.get('value', '')}"
            elif threshold is not None:
                threshold_str = str(threshold)
            else:
                threshold_str = "-"
            
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
            
            row = html.Tr([
                html.Td(test_id),
                html.Td(t.get("type", "N/A")),
                html.Td(t.get("database", "-")),
                html.Td(t.get("column", "-")),
                html.Td(t.get("severity", "-")),
                html.Td(threshold_str),
                html.Td("Oui" if t.get("sample_on_fail") else "Non"),
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
        
        # Supprimer les tests qui référencent cette métrique
        new_tests = tests or []
        deleted_tests = []
        if metric_id and tests:
            filtered_tests = []
            for t in tests:
                # Vérifier si le test référence cette métrique
                if t.get("type") == "foreign_key":
                    ref = t.get("ref", {})
                    if ref.get("metric") == metric_id:
                        deleted_tests.append(t.get("id"))
                        continue
                filtered_tests.append(t)
            new_tests = filtered_tests
        
        # Message de statut
        status_msg = f"✅ Métrique '{metric_id}' supprimée."
        if deleted_tests:
            status_msg += f" {len(deleted_tests)} test(s) associé(s) supprimé(s): {', '.join(deleted_tests)}"
        
        return new_metrics, new_tests, dbc.Alert(status_msg, color="success", dismissable=True, duration=4000)
    
    @app.callback(
        [Output("metric-type", "value", allow_duplicate=True),
         Output("metric-tabs", "active_tab", allow_duplicate=True),
         Output("metric-action-status", "children", allow_duplicate=True)],
        Input({"type": "edit-metric", "index": ALL}, "n_clicks"),
        State("store_metrics", "data"),
        prevent_initial_call=True
    )
    def edit_metric(n_clicks_list, metrics):
        """Charge la métrique pour modification"""
        if not any(n_clicks_list):
            return no_update, no_update, no_update
        
        # Trouver quel bouton a été cliqué
        clicked_idx = None
        for idx, n in enumerate(n_clicks_list):
            if n:
                clicked_idx = idx
                break
        
        if clicked_idx is None or not metrics or clicked_idx >= len(metrics):
            return no_update, no_update, no_update
        
        # Récupérer la métrique à modifier
        metric = metrics[clicked_idx]
        
        # Créer un message détaillé avec toutes les valeurs
        values_text = html.Div([
            html.P(f"✏️ Pour modifier la métrique '{metric.get('id')}', utilisez les valeurs suivantes :", className="mb-2"),
            html.Ul([
                html.Li(f"Type: {metric.get('type', 'N/A')}"),
                html.Li(f"ID: {metric.get('id', 'N/A')}"),
                html.Li(f"Database: {metric.get('database', 'N/A')}") if metric.get('database') else None,
                html.Li(f"Colonne: {metric.get('column', 'N/A')}") if metric.get('column') else None,
                html.Li(f"Where: {metric.get('where', 'N/A')}") if metric.get('where') else None,
                html.Li(f"Expression: {metric.get('expr', 'N/A')}") if metric.get('expr') else None,
            ]),
            html.P("📝 Saisissez ces valeurs dans le formulaire, puis cliquez sur 'Ajouter' pour mettre à jour.", className="mt-2 text-primary")
        ])
        
        return (
            metric.get("type", ""),  # Pré-sélectionner le type
            "tab-metric-create",  # Basculer vers l'onglet de création
            dbc.Alert(values_text, color="info", dismissable=True)
        )
    
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
        
        values_list = [
            html.Li(f"Type: {test.get('type', 'N/A')}"),
            html.Li(f"ID: {test.get('id', 'N/A')}"),
            html.Li(f"Sévérité: {test.get('severity', 'medium')}"),
            html.Li(f"Échantillon si échec: {'Oui' if test.get('sample_on_fail') else 'Non'}"),
        ]
        
        if test.get('database'):
            values_list.append(html.Li(f"Database: {test.get('database')}"))
        if test.get('column'):
            values_list.append(html.Li(f"Colonne: {test.get('column')}"))
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

    # ===== Run DQ (simple runner invocation) =====

    @app.callback(
        Output("dq-run-results", "children"),
        Input("run-dq", "n_clicks"),
        State("store_datasets", "data"),
        State("store_metrics", "data"),
        State("store_tests", "data"),
        prevent_initial_call=True
    )
    def run_dq(n, datasets, metrics, tests):
        """Exécute le runner DQ sur un DataFrame d'exemple et affiche les résultats."""
        if not n:
            return no_update

        # Build config
        cfg = {"metrics": sanitize_metrics(metrics or []), "tests": sanitize_tests(tests or [])}

        # Try to load a representative DataFrame
        df = pd.DataFrame()
        # If datasets are provided, try the first one
        try:
            if datasets:
                first_ds = datasets[0].get("dataset") if isinstance(datasets[0], dict) else None
                if first_ds:
                    try:
                        ds = dataiku.Dataset(first_ds)
                        df = ds.get_dataframe(limit=1000)
                    except Exception:
                        # fallback to CSV in ./datasets/{name}.csv
                        import os
                        csv_path = f"./datasets/{first_ds}.csv"
                        if os.path.exists(csv_path):
                            df = pd.read_csv(csv_path)
        except Exception:
            df = pd.DataFrame()

        # If still empty, create a minimal DF based on metric/test columns to allow missing_rate to run
        if df.empty:
            # Gather column candidates from metrics/tests
            cols = set()
            for m in (metrics or []):
                if isinstance(m, dict) and m.get("column"):
                    cols.add(m.get("column"))
            for t in (tests or []):
                if isinstance(t, dict) and t.get("column"):
                    cols.add(t.get("column"))
            if not cols:
                # create a default column
                df = pd.DataFrame({"col1": [1, None, 3, None, 5]})
            else:
                d = {}
                for c in cols:
                    d[c] = [1, None, 3, None, 5]
                df = pd.DataFrame(d)

        # Run the runner
        try:
            results = run_dq_config(df, cfg)
            pretty = json.dumps(results, ensure_ascii=False, indent=2)
            return dbc.Card([
                dbc.CardHeader("Résultats Run DQ"),
                dbc.CardBody(html.Pre(pretty, style={"background": "#111", "color": "#0f0", "padding": "0.75rem"}))
            ])
        except Exception as e:
            return dbc.Alert(f"Erreur lors du Run DQ: {e}", color="danger")
