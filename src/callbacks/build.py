# Callbacks de la page Build (wizard de création DQ)

import json
import urllib.parse as urlparse
from datetime import datetime
from dash import html, dcc, Input, Output, State, ALL, no_update
import dash_bootstrap_components as dbc
import yaml

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
    first
)


def register_build_callbacks(app):
    """Enregistre tous les callbacks de la page Build"""
    
    # ===== Contexte et Datasets =====
    
    @app.callback(
        Output("ctx-banner", "children"),
        Input("url", "href")
    )
    def update_ctx_banner(href):
        """Affiche le contexte (Stream/Project) extrait de l'URL"""
        decoded_href = urlparse.unquote(href) if href else ""
        q = {}
        if decoded_href and '?' in decoded_href:
            query_string = '?' + decoded_href.split('?', 1)[1]
            q = parse_query(query_string)
        if not q.get("stream") or not q.get("project"):
            return dbc.Alert(
                "Contexte non défini (utilise l'accueil pour choisir un Stream et un Projet).",
                color="warning",
                className="mb-3"
            )
        return dbc.Alert(
            f"Contexte: Stream = {q['stream']} • Projet = {q['project']}",
            color="info",
            className="mb-3"
        )

    @app.callback(
        Output("ds-picker", "options"), 
        Input("url", "href")
    )
    def update_dataset_options(href):
        """Met à jour les datasets disponibles selon le contexte"""
        decoded_href = urlparse.unquote(href) if href else ""
        q = {}
        if decoded_href and '?' in decoded_href:
            query_string = '?' + decoded_href.split('?', 1)[1]
            q = parse_query(query_string)
        
        stream = q.get("stream")
        projet = q.get("project") 
        dq_point = q.get("dq_point")
        
        datasets = list_project_datasets(stream, projet, dq_point)
        return [{"label": ds, "value": ds} for ds in datasets]

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
        """Affiche le formulaire de création de métrique selon le type"""
        if not metric_type:
            return dbc.Alert("Choisis un type de métrique.", color="light")
        ds_aliases = [d["alias"] for d in (ds_data or [])]
        if not ds_aliases:
            return dbc.Alert(
                "Enregistre d'abord des datasets (Étape 1), puis reviens ici.",
                color="warning"
            )

        common_top = dbc.Row([
            dbc.Col([
                html.Label("ID de la métrique"),
                dcc.Input(
                    id={"role": "metric-id"},
                    type="text",
                    value="",
                    style={"width": "100%"},
                    persistence=True,
                    persistence_type="session"
                )
            ], md=6),
            dbc.Col([
                html.Label("Base (alias)"),
                dcc.Dropdown(
                    id={"role": "metric-db"},
                    options=[{"label": a, "value": a} for a in ds_aliases],
                    clearable=False,
                    persistence=True,
                    persistence_type="session"
                )
            ], md=6),
        ])

        column_visible = metric_type in ("sum", "mean", "distinct_count")
        column_ctrl = dbc.Row([dbc.Col([
            html.Label("Colonne", style={"display": "block" if column_visible else "none"}),
            dcc.Dropdown(
                id={"role": "metric-column"},
                options=[],
                placeholder="Choisir une colonne",
                clearable=False,
                persistence=True,
                persistence_type="session",
                style={"display": "block" if column_visible else "none"}
            )
        ], md=6)])

        extras = html.Div()
        if metric_type == "row_count":
            extras = dbc.Row([dbc.Col([
                html.Label("Filtre WHERE (optionnel)"),
                dcc.Input(
                    id={"role": "metric-where"},
                    type="text",
                    value="",
                    style={"width": "100%"},
                    persistence=True,
                    persistence_type="session",
                    autoComplete="off"
                )
            ], md=12)])
        elif metric_type in ("sum", "mean"):
            extras = dbc.Row([dbc.Col([
                html.Label("Filtre WHERE (optionnel)"),
                dcc.Input(
                    id={"role": "metric-where"},
                    type="text",
                    value="",
                    style={"width": "100%"},
                    persistence=True,
                    persistence_type="session",
                    autoComplete="off"
                )
            ], md=12)])
        elif metric_type == "ratio":
            extras = dbc.Row([dbc.Col([
                html.Label("Expr (metricA / metricB) — IDs de métriques déjà définies"),
                dcc.Input(
                    id={"role": "metric-expr"},
                    type="text",
                    value="",
                    style={"width": "100%"},
                    persistence=True,
                    persistence_type="session",
                    autoComplete="off"
                )
            ], md=12)])

        helper = html.Div(id="metric-helper", className="text-muted small mt-2")
        preview = html.Div([
            html.H6("Prévisualisation"),
            html.Pre(
                id={"role": "metric-preview"},
                style={"background": "#222", "color": "#eee", "padding": "0.75rem"}
            )
        ])
        return html.Div([common_top, html.Br(), column_ctrl, helper, html.Br(), extras, html.Hr(), preview])

    @app.callback(
        Output({"role": "metric-column"}, "options"),
        Output("toast", "is_open", allow_duplicate=True),
        Output("toast", "children", allow_duplicate=True),
        Input({"role": "metric-db"}, "value", ALL),
        State("store_datasets", "data"),
        prevent_initial_call=True
    )
    def fill_metric_columns(db_values, ds_data):
        """Remplit les options de colonnes pour une métrique selon la base sélectionnée"""
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
        Output("metric-helper", "children"),
        Input({"role": "metric-column"}, "options")
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
        Input("force-metric-preview", "n_clicks"),
        Input("metric-type", "value"),
        Input({"role": "metric-id"}, "value", ALL),
        Input({"role": "metric-db"}, "value", ALL),
        Input({"role": "metric-column"}, "value", ALL),
        Input({"role": "metric-where"}, "value", ALL),
        Input({"role": "metric-expr"}, "value", ALL),
        prevent_initial_call=True
    )
    def preview_metric(force, mtype, mid_list, mdb_list, mcol_list, mwhere_list, mexpr_list):
        """Génère la prévisualisation JSON de la métrique"""
        if not mtype:
            return ""
        
        mid = first(mid_list)
        mdb = first(mdb_list)
        mcol = first(mcol_list)
        mwhere = first(mwhere_list)
        mexpr = first(mexpr_list)

        obj = {"id": (mid or safe_id(f"m_{mtype}_{mdb or ''}_{mcol or ''}")), "type": mtype}
        if mtype in ("row_count", "sum", "mean"):
            obj.update({"database": mdb or ""})
            if mtype in ("sum", "mean"):
                obj["column"] = mcol or ""
            if mwhere:
                obj["where"] = mwhere
        elif mtype == "distinct_count":
            obj.update({"database": mdb or "", "column": mcol or ""})
        elif mtype == "ratio":
            obj.update({"expr": (mexpr or "")})
        return json.dumps(obj, ensure_ascii=False, indent=2)

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
        State({"role": "metric-column"}, "value", ALL),
        State({"role": "metric-where"}, "value", ALL),
        State({"role": "metric-expr"}, "value", ALL),
    )
    def add_metric(n, preview_list, metrics, mtype, mid_list, mdb_list, mcol_list, mwhere_list, mexpr_list):
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
            mid = first(mid_list)
            mdb = first(mdb_list)
            mcol = first(mcol_list)
            mwhere = first(mwhere_list)
            mexpr = first(mexpr_list)
            if not mtype:
                return "Prévisualisation vide/invalide.", metrics, no_update, no_update
            m = {"id": (mid or safe_id(f"m_{mtype}_{mdb or ''}_{mcol or ''}")), "type": mtype}
            if mtype in ("row_count", "sum", "mean"):
                m.update({"database": mdb or ""})
                if mtype in ("sum", "mean"):
                    m["column"] = mcol or ""
                if mwhere:
                    m["where"] = mwhere
            elif mtype == "distinct_count":
                m.update({"database": mdb or "", "column": mcol or ""})
            elif mtype == "ratio":
                m.update({"expr": (mexpr or "")})
        metrics = (metrics or [])
        existing = {x.get("id") for x in metrics}
        base_id = m.get("id") or "m"
        uid, k = base_id, 2
        while uid in existing:
            uid = f"{base_id}_{k}"
            k += 1
        m["id"] = uid
        metrics.append(m)
        items = [
            html.Pre(
                json.dumps(x, ensure_ascii=False, indent=2),
                className="p-2 mb-2",
                style={"background": "#111", "color": "#eee"}
            ) for x in metrics
        ]
        return f"Métrique ajoutée: {uid}", metrics, html.Div(items), "tab-metric-list"

    # ===== Tests =====
    
    @app.callback(
        Output("test-params", "children"),
        Input("test-type", "value"),
        State("store_datasets", "data"),
        State("store_metrics", "data")
    )
    def render_test_form(test_type, ds_data, metrics):
        """Affiche le formulaire de création de test selon le type"""
        if not test_type:
            return dbc.Alert("Choisis un type de test.", color="light")
        ds_aliases = [d["alias"] for d in (ds_data or [])]
        if not ds_aliases:
            return dbc.Alert("Enregistre d'abord des datasets.", color="warning")

        common = dbc.Row([
            dbc.Col([
                html.Label("ID du test"),
                dcc.Input(
                    id={"role": "test-id"},
                    type="text",
                    value="",
                    style={"width": "100%"},
                    persistence=True,
                    persistence_type="session",
                    autoComplete="off"
                )
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

        if test_type in ("null_rate", "uniqueness", "range", "regex"):
            db_ctrl = dbc.Row([dbc.Col([
                html.Label("Base (alias)"),
                dcc.Dropdown(
                    id={"role": "test-db"},
                    options=[{"label": a, "value": a} for a in ds_aliases],
                    clearable=False,
                    persistence=True,
                    persistence_type="session"
                )
            ], md=6)])
            col_ctrl = dbc.Row([dbc.Col([
                html.Label("Colonne"),
                dcc.Dropdown(
                    id={"role": "test-col"},
                    options=[],
                    placeholder="Choisir une colonne",
                    clearable=False,
                    persistence=True,
                    persistence_type="session"
                )
            ], md=6)])
            extra = html.Div()
            if test_type == "range":
                extra = dbc.Row([
                    dbc.Col([
                        html.Label("Min"),
                        dcc.Input(
                            id={"role": "test-min"},
                            type="text",
                            value="0",
                            persistence=True,
                            persistence_type="session",
                            autoComplete="off"
                        )
                    ], md=3),
                    dbc.Col([
                        html.Label("Max"),
                        dcc.Input(
                            id={"role": "test-max"},
                            type="text",
                            value="100",
                            persistence=True,
                            persistence_type="session",
                            autoComplete="off"
                        )
                    ], md=3),
                ])
            if test_type == "regex":
                extra = dbc.Row([dbc.Col([
                    html.Label("Pattern (regex)"),
                    dcc.Input(
                        id={"role": "test-pattern"},
                        type="text",
                        value=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
                        style={"width": "100%"},
                        persistence=True,
                        persistence_type="session",
                        autoComplete="off"
                    )
                ], md=12)])
            thresh = dbc.Row([
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
                ], md=3),
                dbc.Col([
                    html.Label("Valeur"),
                    dcc.Input(
                        id={"role": "test-thr"},
                        type="text",
                        value="0.005",
                        persistence=True,
                        persistence_type="session",
                        autoComplete="off"
                    )
                ], md=3),
            ])
            preview = html.Div([
                html.H6("Prévisualisation du test"),
                html.Pre(
                    id={"role": "test-preview"},
                    style={"background": "#222", "color": "#eee", "padding": "0.75rem"}
                )
            ])
            return html.Div([common, html.Br(), db_ctrl, col_ctrl, html.Br(), extra, html.Br(), thresh, html.Hr(), preview])

        if test_type == "foreign_key":
            metric_ids = [m.get("id") for m in (metrics or []) if m.get("id")]
            ref_options = (
                [{"label": f"📊 {mid}", "value": f"metric:{mid}"} for mid in metric_ids] +
                [{"label": f"🗄️ {a}", "value": f"db:{a}"} for a in ds_aliases]
            )
            
            db1 = dbc.Row([dbc.Col([
                html.Label("Base (alias)"),
                dcc.Dropdown(
                    id={"role": "test-db"},
                    options=[{"label": a, "value": a} for a in ds_aliases],
                    clearable=False,
                    persistence=True,
                    persistence_type="session"
                )
            ], md=6)])
            col1 = dbc.Row([dbc.Col([
                html.Label("Colonne"),
                dcc.Dropdown(
                    id={"role": "test-col"},
                    options=[],
                    placeholder="Choisir une colonne",
                    clearable=False,
                    persistence=True,
                    persistence_type="session"
                )
            ], md=6)])
            db2 = dbc.Row([dbc.Col([
                html.Label("Ref Base (alias) ou Métrique"),
                html.Div("Sélectionne une base de données 🗄️ ou une métrique 📊", className="text-muted small mb-1"),
                dcc.Dropdown(
                    id={"role": "test-ref-db"},
                    options=ref_options,
                    placeholder="Base ou métrique...",
                    clearable=False,
                    persistence=True,
                    persistence_type="session"
                )
            ], md=6)])
            col2 = dbc.Row([dbc.Col([
                html.Label("Ref Colonne"),
                html.Div(id="fk-ref-col-helper", className="text-muted small mb-1"),
                dcc.Dropdown(
                    id={"role": "test-ref-col"},
                    options=[],
                    placeholder="Choisir une colonne",
                    clearable=False,
                    persistence=True,
                    persistence_type="session"
                )
            ], md=6)])
            preview = html.Div([
                html.H6("Prévisualisation du test"),
                html.Pre(
                    id={"role": "test-preview"},
                    style={"background": "#222", "color": "#eee", "padding": "0.75rem"}
                )
            ])
            return html.Div([common, html.Br(), db1, col1, db2, col2, html.Hr(), preview])

        return dbc.Alert("Type non géré pour l'instant.", color="warning")

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
        Input("test-type", "value"),
        Input({"role": "test-id"}, "value", ALL),
        Input({"role": "test-sev"}, "value", ALL),
        Input({"role": "test-sof"}, "value", ALL),
        Input({"role": "test-db"}, "value", ALL),
        Input({"role": "test-col"}, "value", ALL),
        Input({"role": "test-op"}, "value", ALL),
        Input({"role": "test-thr"}, "value", ALL),
        Input({"role": "test-min"}, "value", ALL),
        Input({"role": "test-max"}, "value", ALL),
        Input({"role": "test-pattern"}, "value", ALL),
        Input({"role": "test-ref-db"}, "value", ALL),
        Input({"role": "test-ref-col"}, "value", ALL),
        prevent_initial_call=True
    )
    def preview_test(ttype, tid_list, sev_list, sof_list, db_list, col_list, op_list, thr_list, vmin_list, vmax_list, pat_list, refdb_list, refcol_list):
        """Génère la prévisualisation JSON du test"""
        if not ttype:
            return ""
        
        def first_with_default(val, default=None):
            if val is None:
                return default
            if isinstance(val, list):
                return val[0] if val else default
            return val
        
        tid, sev, sof = first_with_default(tid_list), first_with_default(sev_list, "medium"), first_with_default(sof_list, [])
        db, col = first_with_default(db_list), first_with_default(col_list)
        op, thr = first_with_default(op_list), first_with_default(thr_list)
        vmin, vmax = first_with_default(vmin_list), first_with_default(vmax_list)
        pat = first_with_default(pat_list)
        refdb, refcol = first_with_default(refdb_list), first_with_default(refcol_list)

        obj = {
            "id": tid or safe_id(f"t_{ttype}_{db or ''}_{col or ''}"),
            "type": ttype,
            "severity": (sev or "medium"),
            "sample_on_fail": ("yes" in (sof or []))
        }
        if ttype in ("null_rate", "uniqueness", "range", "regex"):
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
        return json.dumps(obj, ensure_ascii=False, indent=2)

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
        State({"role": "test-op"}, "value", ALL),
        State({"role": "test-thr"}, "value", ALL),
        State({"role": "test-min"}, "value", ALL),
        State({"role": "test-max"}, "value", ALL),
        State({"role": "test-pattern"}, "value", ALL),
        State({"role": "test-ref-db"}, "value", ALL),
        State({"role": "test-ref-col"}, "value", ALL),
    )
    def add_test(n, preview_list, tests, ttype, tid_list, sev_list, sof_list, db_list, col_list, op_list, thr_list, vmin_list, vmax_list, pat_list, refdb_list, refcol_list):
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
            tid, sev, sof = first_with_default(tid_list), first_with_default(sev_list, "medium"), first_with_default(sof_list, [])
            db, col = first_with_default(db_list), first_with_default(col_list)
            op, thr = first_with_default(op_list), first_with_default(thr_list)
            vmin, vmax = first_with_default(vmin_list), first_with_default(vmax_list)
            pat = first_with_default(pat_list)
            refdb, refcol = first_with_default(refdb_list), first_with_default(refcol_list)
            t = {
                "id": tid or safe_id(f"t_{ttype}_{db or ''}_{col or ''}"),
                "type": ttype,
                "severity": (sev or "medium"),
                "sample_on_fail": ("yes" in (sof or []))
            }
            if ttype in ("null_rate", "uniqueness", "range", "regex"):
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
        existing = {x.get("id") for x in tests}
        base_id = t.get("id") or "t"
        uid, k = base_id, 2
        while uid in existing:
            uid = f"{base_id}_{k}"
            k += 1
        t["id"] = uid
        tests.append(t)
        items = [
            html.Pre(
                json.dumps(x, ensure_ascii=False, indent=2),
                className="p-2 mb-2",
                style={"background": "#111", "color": "#eee"}
            ) for x in tests
        ]
        return f"Test ajouté: {uid}", tests, html.Div(items), "tab-test-list"

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
        cfg["metrics"] = metrics or []
        cfg["tests"] = tests or []
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
