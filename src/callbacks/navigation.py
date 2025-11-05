# Cleaned callbacks de navigation

import urllib.parse as urlparse
from dash import Input, Output, State, ALL, callback_context, no_update
import dash_bootstrap_components as dbc
from dash import html, dash_table
from flask import current_app

from src.layouts.navbar import navbar
from src.layouts.home import home_page
from src.layouts.dq import dq_page
from src.layouts.build import build_page
from src.layouts.configs import configs_page
from src.layouts.dq_inventory import dq_inventory_page
from src.layouts.dq_runner import dq_runner_page
from src.layouts.drop_dq import drop_dq_page
from src.layouts.select_stream import select_stream_page
from src.layouts.select_project import select_project_page
from src.layouts.select_dq_point import select_dq_point_page
from src.layouts.dq_landing import dq_landing_page
from src.layouts.drop_landing import drop_landing_page
from src.layouts.dashboard import dashboard_page
from src.layouts.check_drop_dashboard import check_drop_dashboard_page
from src.layouts.dq_management_dashboard import dq_management_dashboard_page
from src.layouts.builder_landing import builder_landing_page
from src.layouts.select_quarter import select_quarter_page
from src.config import DEBUG_UI


def register_navigation_callbacks(app):
    """Enregistre les callbacks de navigation et auxiliaires.

    Cette version est volontairement compacte et robuste :
    - évite les callbacks imbriqués
    - s'assure que le nombre de Outputs correspond aux retours
    - populate les stores `inventory-datasets-store` et `inventory-dqs-store`
    """

    @app.callback(
        Output("crumb", "children"),
        Input("url", "pathname")
    )
    def update_crumb(pathname):
        if not pathname:
            return []
        parts = [p for p in pathname.split('/') if p]
        return [html.Span(p) for p in parts]

    @app.callback(
        Output("page-content", "children"),
        Input("url", "pathname")
    )
    def display_page(pathname):
        """Router minimal: renvoie le layout correspondant au pathname."""
        clean_path = (pathname or "/").split("?")[0]
        if clean_path in ["/", "", "/home"]:
            return home_page()
        if clean_path == "/dashboard":
            return dashboard_page()
        if clean_path == "/dq-editor-dashboard":
            return dq_management_dashboard_page()
        if clean_path == "/dq":
            return dq_page()
        if clean_path == "/build":
            return build_page()
        if clean_path == "/dq-inventory":
            return dq_inventory_page()
        if clean_path == "/dq-runner":
            return dq_runner_page()
        if clean_path == "/drop-dq":
            return drop_landing_page()
        if clean_path == "/check-drop-dashboard":
            return check_drop_dashboard_page()
        if clean_path == "/configs":
            return configs_page()
        if clean_path == "/select-quarter":
            return select_quarter_page()
        if clean_path == "/select-stream":
            return select_stream_page()
        if clean_path == "/select-project":
            return select_project_page()
        if clean_path == "/select-dq-point":
            return select_dq_point_page()
        if clean_path == "/builder-landing":
            return builder_landing_page()

        # Fallback
        return dbc.Container([
            dbc.Alert("Page introuvable", color="warning")
        ], fluid=True)

    @app.callback(
        Output("url", "pathname", allow_duplicate=True),
        Output("url", "search", allow_duplicate=True),
        Input("home-checkdrop-btn", "n_clicks"),
        Input("home-dqeditor-btn", "n_clicks"),
        prevent_initial_call=True
    )
    def home_access_navigation(n_checkdrop, n_dqeditor):
        """Navigation explicite pour les boutons de la page d'accueil."""
        ctx = callback_context
        if not ctx.triggered:
            return no_update, no_update
        triggered = ctx.triggered[0]["prop_id"].split(".")[0]
        if triggered == "home-checkdrop-btn":
            return "/check-drop-dashboard", ""
        if triggered == "home-dqeditor-btn":
            return "/dq-editor-dashboard", ""
        return no_update, no_update

    # Inventory helpers imports
    from src.inventory import get_zones, get_datasets_for_zone
    from src.spark_inventory_adapter import register_inventory_datasets_in_spark
    from src.utils import list_dq_files, read_dq_file

    @app.callback(
        Output("select-zone-dropdown", "options"),
        Input("url", "search"),
        State("url", "pathname"),
        prevent_initial_call=False
    )
    def populate_zone_dropdown(search, pathname):
        """Remplit le dropdown des zones basé sur stream/project de l'URL."""
        if pathname != "/select-dq-point":
            return []
        stream_id = project_id = None
        if search:
            q = urlparse.parse_qs(search.lstrip('?'))
            stream_id = q.get('stream', [None])[0]
            project_id = q.get('project', [None])[0]
        zones = get_zones(stream_id=stream_id, project_id=project_id)
        try:
            print(f"[DEBUG_UI] populate_zone_dropdown: stream={stream_id} project={project_id} zones_found={len(zones)}")
        except Exception:
            pass
        options = [{"label": f"{z['label']} ({z.get('datasets_count', 0)} datasets)", "value": z['id']} for z in zones]
        return options

    @app.callback(
        Output("url", "pathname", allow_duplicate=True),
        Output("url", "search", allow_duplicate=True),
        Output("inventory-datasets-store", "data", allow_duplicate=True),
        Output("inventory-dqs-store", "data", allow_duplicate=True),
        Output("run-context-store", "data", allow_duplicate=True),
        Input("select-dq-next", "n_clicks"),
        State("select-zone-dropdown", "value"),
        State("url", "search"),
        State("run-context-store", "data"),
        prevent_initial_call=True
    )
    def zone_next(n, zone_value, search, run_ctx):
        """Navigation: Zone → Builder. Prépare stores et redirige."""
        if not n:
            return "/select-dq-point", search or "", no_update, no_update, run_ctx or no_update
        if not zone_value:
            return "/select-dq-point", search or "", no_update, no_update, run_ctx or no_update

        q = urlparse.parse_qs((search or "").lstrip("?"))
        stream = q.get("stream", [None])[0]
        project = q.get("project", [None])[0]
        quarter = q.get("quarter", [None])[0] or (run_ctx or {}).get("quarter")

        if not quarter:
            return "/select-dq-point", search or "", no_update, no_update, run_ctx or no_update
        if not stream or not project:
            return "/select-dq-point", search or "", no_update, no_update, run_ctx or no_update

        params_parts = [f"quarter={quarter}", f"stream={stream}", f"project={project}", f"zone={zone_value}"]
        params = "?" + "&".join(params_parts)

        store_payload = {"zone": zone_value, "datasets": []}
        dqs_payload = {"dqs": []}

        try:
            datasets = get_datasets_for_zone(zone_value, stream_id=stream, project_id=project) or []
            store_payload = {"zone": zone_value, "datasets": datasets}

            spark_ctx = getattr(current_app, 'spark_context', None)
            if spark_ctx and datasets:
                try:
                    register_inventory_datasets_in_spark(spark_ctx, datasets)
                except Exception as e:
                    print(f"[DEBUG] Erreur enregistrement Spark: {e}")

            try:
                dq_files = list_dq_files("dq_params", stream=stream, project=project, dq_point=zone_value)
                dqs = []
                for fn in dq_files:
                    cfg = read_dq_file(fn, "dq_params") or {}
                    label = cfg.get('name') or fn
                    path = f"dq_params/{fn}"
                    dqs.append({"id": fn, "label": label, "path": path, "databases": cfg.get('databases', []), "context": cfg.get('context', {})})

                from pathlib import Path
                import yaml
                defs_dir = Path(__file__).resolve().parents[2] / "dq" / "definitions"
                if defs_dir.exists():
                    for p in sorted(defs_dir.glob("*.yaml")):
                        try:
                            with open(p, 'r', encoding='utf-8') as f:
                                doc = yaml.safe_load(f) or {}
                            ctx = doc.get('context') or {}
                            match = True
                            if stream and ctx.get('stream') and ctx.get('stream') != stream:
                                match = False
                            if project and ctx.get('project') and ctx.get('project') != project:
                                match = False
                            if zone_value and ctx.get('dq_point') and ctx.get('dq_point') != zone_value:
                                match = False
                            if match:
                                fn2 = p.name
                                label2 = doc.get('name') or p.stem
                                path2 = f"dq/definitions/{fn2}"
                                dqs.append({"id": fn2, "label": label2, "path": path2, "databases": doc.get('databases', []), "context": ctx})
                        except Exception as _e:
                            print(f"[DEBUG] erreur lecture définition DQ {p}: {_e}")
                dqs_payload = {"dqs": dqs}
            except Exception as e:
                print(f"[DEBUG] Erreur détection DQ: {e}")

        except Exception as e:
            print(f"[DEBUG] Erreur zone_next: {e}")

        new_ctx = {"quarter": quarter, "stream": stream, "project": project, "zone": zone_value}

        return "/builder-landing", params, store_payload, dqs_payload, new_ctx

    @app.callback(
        Output("datasets-list", "children"),
        Output("datasets-status", "children"),
        Output("inventory-datasets-store", "data", allow_duplicate=True),
        Output("inventory-dqs-store", "data", allow_duplicate=True),
        Input("select-zone-dropdown", "value"),
        State("url", "search"),
        State("url", "pathname"),
        prevent_initial_call=True
    )
    def populate_datasets_for_zone(zone_id, search, pathname):
        """Affiche la liste des datasets pour une zone et met à jour le store d'inventaire.

        Retourne (list_html, status_msg, store_payload, dqs_payload)
        """
        if pathname != "/select-dq-point" or not zone_id:
            return None, None, no_update, no_update

        q = urlparse.parse_qs((search or "").lstrip('?'))
        stream = q.get('stream', [None])[0]
        project = q.get('project', [None])[0]

        store_payload = {"zone": zone_id, "datasets": []}
        dqs_payload = {"dqs": []}

        try:
            datasets = get_datasets_for_zone(zone_id, stream_id=stream, project_id=project) or []
            try:
                print(f"[DEBUG_UI] populate_datasets_for_zone: stream={stream} project={project} zone={zone_id} datasets={len(datasets)}")
            except Exception:
                pass
            store_payload = {"zone": zone_id, "datasets": datasets}

            # register in spark
            spark_ctx = getattr(current_app, 'spark_context', None)
            if spark_ctx and datasets:
                try:
                    register_inventory_datasets_in_spark(spark_ctx, datasets)
                except Exception as e:
                    print(f"[DEBUG] Erreur enregistrement Spark (populate): {e}")

            # build UI list
            if len(datasets) == 0:
                status_msg = f"Zone '{zone_id}' sélectionnée"
                list_html = html.Em("Aucun dataset trouvé")
            else:
                status_msg = f"✅ {len(datasets)} dataset(s) disponible(s)"
                items = []
                for i, d in enumerate(datasets):
                    alias = d.get('alias', 'N/A')
                    name = d.get('name', 'N/A')
                    items.append(
                        html.Li([
                            html.Span(f"{alias} ({name})", className="me-3 small"),
                            dbc.Button("Prévisualiser", id={"type": "dataset-preview", "index": i}, color="primary", size="sm")
                        ], className="mb-2")
                    )
                list_html = html.Ul(items, className="mb-0 list-unstyled")

            # Discover DQs same as zone_next
            try:
                dq_files = list_dq_files("dq_params", stream=stream, project=project, dq_point=zone_id)
                dqs = []
                for fn in dq_files:
                    cfg = read_dq_file(fn, "dq_params") or {}
                    label = cfg.get('name') or fn
                    path = f"dq_params/{fn}"
                    dqs.append({"id": fn, "label": label, "path": path, "databases": cfg.get('databases', []), "context": cfg.get('context', {})})

                from pathlib import Path
                import yaml
                defs_dir = Path(__file__).resolve().parents[2] / "dq" / "definitions"
                if defs_dir.exists():
                    for p in sorted(defs_dir.glob("*.yaml")):
                        try:
                            with open(p, 'r', encoding='utf-8') as f:
                                doc = yaml.safe_load(f) or {}
                            ctx = doc.get('context') or {}
                            match = True
                            if stream and ctx.get('stream') and ctx.get('stream') != stream:
                                match = False
                            if project and ctx.get('project') and ctx.get('project') != project:
                                match = False
                            if zone_id and ctx.get('dq_point') and ctx.get('dq_point') != zone_id:
                                match = False
                            if match:
                                fn2 = p.name
                                label2 = doc.get('name') or p.stem
                                path2 = f"dq/definitions/{fn2}"
                                dqs.append({"id": fn2, "label": label2, "path": path2, "databases": doc.get('databases', []), "context": ctx})
                        except Exception as _e:
                            print(f"[DEBUG] erreur lecture définition DQ {p}: {_e}")
                dqs_payload = {"dqs": dqs}
            except Exception as e:
                print(f"[DEBUG] Erreur détection DQ (populate): {e}")

        except Exception as e:
            print(f"[DEBUG] Erreur populate_datasets_for_zone: {e}")
            return html.Em("Erreur lors de la récupération des datasets."), "Erreur", no_update, no_update

        return list_html, status_msg, store_payload, dqs_payload

    @app.callback(
        Output("builder-landing-dqs", "children"),
        Input("inventory-dqs-store", "data"),
        Input("url", "search"),
        Input("url", "pathname"),
        State("inventory-datasets-store", "data"),
        prevent_initial_call=False
    )
    def render_builder_landing_dqs(dqs_store, search, pathname, inventory_store):
        """Affiche la liste des DQ (templates) applicables pour la page builder-landing.

        Comportement amélioré : si l'URL ne contient pas le query string (arrivée
        directe sur la page), on tente d'extraire stream/project/zone depuis
        `inventory-datasets-store` (si disponible). Cela permet d'afficher les
        templates même lorsque l'utilisateur a été redirigé par le flow interne
        sans query params visibles.
        """
        if pathname != "/builder-landing":
            return None

        stream = project = zone = None
        if search:
            q = urlparse.parse_qs(search.lstrip('?'))
            stream = q.get('stream', [None])[0]
            project = q.get('project', [None])[0]
            zone = q.get('zone', [None])[0]

        # Fallback : essayer d'extraire le contexte depuis le store d'inventaire
        if not any([stream, project, zone]) and inventory_store:
            try:
                zone = zone or inventory_store.get('zone')
                datasets = inventory_store.get('datasets', []) or []
                if datasets:
                    first = datasets[0]
                    stream = stream or first.get('stream')
                    project = project or first.get('project')
            except Exception:
                pass

        if not all([stream, project, zone]):
            return html.Div("Paramètres manquants (stream/project/zone).", className="text-warning")

        # If the store is empty, attempt to discover DQs on the fly from repo/Dataiku
        dqs = []
        if dqs_store and 'dqs' in dqs_store:
            dqs = dqs_store.get('dqs', []) or []
        if not dqs:
            try:
                from src.utils import list_dq_files, read_dq_file
                dq_files = list_dq_files('dq_params', stream=stream, project=project, dq_point=zone)
                for fn in dq_files:
                    cfg = read_dq_file(fn, 'dq_params') or {}
                    label = cfg.get('name') or cfg.get('label') or fn
                    dqs.append({
                        'id': fn,
                        'label': label,
                        'path': fn,
                        'databases': cfg.get('databases', []),
                        'context': cfg.get('context', {})
                    })
            except Exception as _e:
                print(f"[DEBUG] erreur découverte DQ inline: {_e}")
        if not dqs:
            return html.Div("Aucun template DQ applicable à ce contexte.", className="text-muted")

        # Deduplicate templates by filename stem (covers cases where the same
        # template appears as 'dq/definitions/foo.yaml' and 'foo' or similar).
        from pathlib import Path
        seen = set()
        deduped = []
        for dq in dqs:
            raw = dq.get('path') or dq.get('id') or ''
            stem = Path(raw).stem if raw else raw
            if stem in seen:
                continue
            seen.add(stem)
            deduped.append(dq)

        items = []
        for dq in deduped:
            label = dq.get('label') or dq.get('id')
            dq_id = dq.get('id')
            dq_path = dq.get('path')
            dbs = dq.get('databases') or []
            # databases can be list of dicts like {'alias': 'name'} or plain strings
            try:
                db_labels = [d.get('alias') if isinstance(d, dict) else str(d) for d in dbs]
            except Exception:
                db_labels = [str(d) for d in dbs]
            desc = html.Div(', '.join([l for l in db_labels if l]), className='small text-muted') if dbs else html.Div('', className='small')
            edit_btn = dbc.Button("Créer à partir de ce DQ", id={"type": "use-dq", "id": dq_id, "path": dq_path}, color="secondary", size="sm", className="ms-3")
            items.append(html.Li([html.Strong(label), desc, edit_btn]))
        return html.Ul(items)

    @app.callback(
        Output("builder-landing-context", "children"),
        Input("url", "search"),
        State("url", "pathname"),
        State("inventory-datasets-store", "data"),
        prevent_initial_call=False
    )
    def render_builder_context(search, pathname, inventory_store):
        if pathname != "/builder-landing":
            return no_update
        quarter = stream = project = zone = None
        if search:
            q = urlparse.parse_qs(search.lstrip('?'))
            quarter = q.get('quarter', [None])[0]
            stream = q.get('stream', [None])[0]
            project = q.get('project', [None])[0]
            zone = q.get('zone', [None])[0]
        if not any([stream, project, zone]) and inventory_store:
            try:
                zone = zone or inventory_store.get('zone')
                datasets = inventory_store.get('datasets', []) or []
                if datasets:
                    first = datasets[0]
                    stream = stream or first.get('stream')
                    project = project or first.get('project')
            except Exception:
                pass
        if not any([quarter, stream, project, zone]):
            return html.Div("Aucun contexte fourni.", className="text-muted")
        try:
            return html.Div([
                html.Span("Contexte : ", className="me-2 fw-bold"),
                dbc.Badge(f"Quarter: {quarter}", color="dark", className="me-2") if quarter else None,
                dbc.Badge(f"Stream: {stream}", color="primary", className="me-2"),
                dbc.Badge(f"Project: {project}", color="secondary", className="me-2"),
                dbc.Badge(f"Zone: {zone}", color="info")
            ], className="d-flex align-items-center")
        except Exception:
            return html.Div(f"Quarter: {quarter} — Stream: {stream} — Project: {project} — Zone: {zone}")

    @app.callback(
        Output("inventory-datasets-store", "data", allow_duplicate=True),
        Output("inventory-dqs-store", "data", allow_duplicate=True),
        Input("url", "search"),
        Input("url", "pathname"),
        State("inventory-datasets-store", "data"),
        prevent_initial_call=True
    )
    def ensure_inventory_store(search, pathname, inventory_store):
        """Si l'utilisateur arrive directement sur builder-landing (ex: via URL)
        et que le store d'inventaire est vide, remplir automatiquement le
        store depuis l'inventory.yaml via get_datasets_for_zone.

        Cela couvre les cas où la navigation n'a pas transité par
        /select-dq-point (ex: arrivée directe depuis un lien externe).
        """
        if pathname != "/builder-landing":
            return no_update, no_update

        # Si le store contient déjà des datasets, rien à faire
        try:
            if inventory_store and inventory_store.get('datasets'):
                return no_update, no_update
        except Exception:
            pass

        # Extraire stream/project/zone depuis l'URL
        stream = project = zone = None
        if search:
            q = urlparse.parse_qs(search.lstrip('?'))
            stream = q.get('stream', [None])[0]
            project = q.get('project', [None])[0]
            zone = q.get('zone', [None])[0]

        if not all([stream, project, zone]):
            return no_update, no_update

        try:
            datasets = get_datasets_for_zone(zone, stream_id=stream, project_id=project) or []
            store_payload = {"zone": zone, "datasets": datasets}

            # Register in spark if available
            spark_ctx = getattr(current_app, 'spark_context', None)
            if spark_ctx and datasets:
                try:
                    register_inventory_datasets_in_spark(spark_ctx, datasets)
                except Exception as e:
                    print(f"[DEBUG] Erreur enregistrement Spark (ensure_store): {e}")

            # Discover DQs (light) — reuse existing discovery logic pattern
            from src.utils import list_dq_files, read_dq_file
            dqs = []
            try:
                dq_files = list_dq_files('dq_params', stream=stream, project=project, dq_point=zone)
                for fn in dq_files:
                    cfg = read_dq_file(fn, 'dq_params') or {}
                    label = cfg.get('name') or fn
                    path = f'dq_params/{fn}'
                    dqs.append({"id": fn, "label": label, "path": path, "databases": cfg.get('databases', []), "context": cfg.get('context', {})})
            except Exception:
                pass

            # local YAML definitions
            from pathlib import Path
            import yaml
            defs_dir = Path(__file__).resolve().parents[2] / "dq" / "definitions"
            if defs_dir.exists():
                for p in sorted(defs_dir.glob("*.yaml")):
                    try:
                        with open(p, 'r', encoding='utf-8') as f:
                            doc = yaml.safe_load(f) or {}
                        ctx = doc.get('context') or {}
                        match = True
                        if stream and ctx.get('stream') and ctx.get('stream') != stream:
                            match = False
                        if project and ctx.get('project') and ctx.get('project') != project:
                            match = False
                        if zone and ctx.get('dq_point') and ctx.get('dq_point') != zone:
                            match = False
                        if match:
                            fn2 = p.name
                            label2 = doc.get('name') or p.stem
                            path2 = f'dq/definitions/{fn2}'
                            dqs.append({"id": fn2, "label": label2, "path": path2, "databases": doc.get('databases', []), "context": ctx})
                    except Exception:
                        pass

            dqs_payload = {"dqs": dqs}
            return store_payload, dqs_payload
        except Exception as e:
            print(f"[DEBUG] Erreur ensure_inventory_store: {e}")
            return no_update, no_update

    # Debug panel updater (seulement si DEBUG_UI activé)
    if DEBUG_UI:
        @app.callback(
            Output("debug-inventory-json", "children"),
            Output("debug-dqs-json", "children"),
            Input("inventory-datasets-store", "data"),
            Input("inventory-dqs-store", "data"),
            Input("url", "pathname"),
            prevent_initial_call=False
        )
        def render_debug_stores(inv_store, dqs_store, pathname):
            # N'affiche que si on est sur builder-landing
            try:
                if pathname != "/builder-landing":
                    return "", ""
            except Exception:
                pass
            import json
            try:
                inv_text = json.dumps(inv_store, indent=2, ensure_ascii=False) if inv_store else "(empty)"
            except Exception:
                inv_text = str(inv_store)
            try:
                dqs_text = json.dumps(dqs_store, indent=2, ensure_ascii=False) if dqs_store else "(empty)"
            except Exception:
                dqs_text = str(dqs_store)
            return inv_text, dqs_text

    @app.callback(
        Output("url", "pathname", allow_duplicate=True),
        Output("url", "search", allow_duplicate=True),
        Input("btn-create-scratch", "n_clicks"),
        State("url", "search"),
        prevent_initial_call=True
    )
    def builder_start(n_scratch, search):
        from urllib.parse import urlencode
        if not n_scratch:
            return no_update
        q = urlparse.parse_qs((search or '').lstrip('?'))
        q['mode'] = ['scratch']
        flat = {k: v[0] for k, v in q.items() if v}
        new_search = '?' + urlencode(flat)
        return '/build', new_search

    @app.callback(
        Output("url", "pathname", allow_duplicate=True),
        Output("url", "search", allow_duplicate=True),
        Input({"type": "use-dq", "id": ALL, "path": ALL}, "n_clicks"),
        State("url", "search"),
        prevent_initial_call=True,
    )
    def use_dq(n_clicks_list, search):
        ctx = callback_context
        if not ctx.triggered:
            return no_update
        prop = ctx.triggered[0]["prop_id"]
        import json
        try:
            triggered = json.loads(prop.split('.n_clicks')[0])
        except Exception:
            try:
                triggered = json.loads(prop.split('.')[0])
            except Exception:
                return no_update
        dq_id = triggered.get('id')
        dq_path = triggered.get('path')
        q = urlparse.parse_qs((search or '').lstrip('?'))
        q['mode'] = ['template']
        q['template'] = [dq_path or dq_id]
        from urllib.parse import urlencode
        flat = {k: v[0] for k, v in q.items() if v}
        new_search = '?' + urlencode(flat)
        return '/build', new_search

    @app.callback(
        Output("modal-body-content", "children"),
        Output("dataset-preview-modal", "is_open", allow_duplicate=True),
        Output("dataset-preview-title", "children"),
        Input({"type": "dataset-preview", "index": ALL}, "n_clicks"),
        State("inventory-datasets-store", "data"),
        prevent_initial_call=True,
    )
    def show_dataset_preview(n_clicks_list, store_payload):
        ctx = callback_context
        if not ctx.triggered:
            return no_update
        prop = ctx.triggered[0]["prop_id"]
        import json
        try:
            triggered_id = json.loads(prop.split('.n_clicks')[0])
        except Exception:
            try:
                triggered_id = json.loads(prop.split('.')[0])
            except Exception:
                return html.Div("Impossible d'identifier l'élément cliqué", className="text-danger"), True, ""
        idx = triggered_id.get('index')
        if store_payload is None or 'datasets' not in store_payload:
            return html.Div("Aucun dataset en mémoire.", className="text-muted"), True, ""
        datasets = store_payload.get('datasets', [])
        if idx is None or idx >= len(datasets):
            return html.Div("Sélection invalide.", className="text-danger"), True, ""
        chosen = datasets[idx]
        alias = chosen.get('alias')
        spark_ctx = getattr(current_app, 'spark_context', None)
        if not spark_ctx:
            message = html.Div([
                html.P("⚠️ Prévisualisation non disponible", className="text-warning mb-2"),
                html.Small("Le contexte Spark n'est pas initialisé. Cette fonctionnalité nécessite un environnement Spark configuré.", 
                          className="text-muted")
            ])
            return message, True, f"Dataset: {alias}"
        try:
            cols = spark_ctx.peek_schema(alias)
            df = spark_ctx.load(alias, cache=False)
            sample_pdf = df.limit(10).toPandas()
            import time
            temp_name = f"tmp_preview_{alias}_{int(time.time())}"
            try:
                df.createOrReplaceTempView(temp_name)
                temp_info = html.Div(f"Vue temporaire créée: '{temp_name}' (session temporaire)", className="text-muted small mb-2")
            except Exception:
                temp_info = html.Div("Impossible de créer la vue temporaire.", className="text-muted small mb-2 text-warning")
            schema_list = html.Ul([html.Li(c) for c in cols], className="mb-2")
            table = dash_table.DataTable(
                data=sample_pdf.to_dict(orient='records'),
                columns=[{"name": c, "id": c} for c in sample_pdf.columns],
                page_size=5,
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'left'}
            )
            card = html.Div([
                temp_info,
                html.H6("Schéma", className="mt-1"),
                schema_list,
                html.H6("Aperçu", className="mt-2"),
                table
            ])
            title = f"Prévisualisation — {alias}"
            return card, True, title
        except Exception as e:
            err = html.Div(f"Erreur lors de la lecture du dataset: {e}", className="text-danger")
            return err, True, "Erreur"

    @app.callback(
        Output("dataset-preview-modal", "is_open", allow_duplicate=True),
        Input("close-dataset-preview", "n_clicks"),
        State("dataset-preview-modal", "is_open"),
        prevent_initial_call=True,
    )
    def close_preview(n, is_open):
        if not n:
            return is_open
        return False

    @app.callback(
        Output("url", "pathname", allow_duplicate=True),
        Output("url", "search", allow_duplicate=True),
        Output("run-context-store", "data", allow_duplicate=True),
        Output("quarter-status", "children"),
        Input("quarter-next", "n_clicks"),
        State("quarter-dropdown", "value"),
        prevent_initial_call=True
    )
    def quarter_next(n, quarter_value):
        if not n:
            return no_update, no_update, no_update, no_update
        if not quarter_value:
            return "/select-quarter", no_update, no_update, "Sélectionne un quarter avant de continuer."
        ctx_payload = {"quarter": quarter_value, "stream": "", "project": "", "zone": ""}
        return "/select-stream", f"?quarter={quarter_value}", ctx_payload, ""

    # Minimal overview callbacks
    @app.callback(
        Output("stream-overview-container", "children"),
        Input("select-stream-dropdown", "value"),
        State("url", "pathname"),
        prevent_initial_call=False
    )
    def display_stream_overview(stream_id, pathname):
        from src.inventory import get_stream_overview
        if pathname != "/select-stream" or not stream_id:
            return None
        data = get_stream_overview(stream_id)
        if not data:
            return html.Div("Aucune donnée disponible pour ce stream.", className="text-muted")
        return html.Div([
            html.H5(f"📊 Vue d'ensemble — {stream_id}", className="mb-3"),
            dash_table.DataTable(data=data, columns=[{"name": col, "id": col} for col in data[0].keys()], style_table={'overflowX': 'auto'})
        ])

    @app.callback(
        Output("url", "pathname"),
        Output("url", "search"),
        Output("select-stream-status", "children"),
        Input("select-stream-next", "n_clicks"),
        State("select-stream-dropdown", "value"),
        State("url", "search"),
        prevent_initial_call=True
    )
    def stream_next(n, stream_value, search):
        """Handle 'Suivant' on select-stream page: go to /select-project with stream param."""
        if not n:
            return no_update, no_update, no_update
        q = urlparse.parse_qs((search or "").lstrip("?"))
        quarter = q.get("quarter", [None])[0]
        if not quarter:
            return "/select-stream", search or "", "Sélectionne un quarter avant de choisir un stream."
        if not stream_value:
            return "/select-stream", search or "", "Sélectionne un stream avant de continuer."
        q = urlparse.parse_qs((search or "").lstrip("?"))
        params = []
        if quarter:
            params.append(f"quarter={quarter}")
        params.append(f"stream={stream_value}")
        new_search = "?" + "&".join(params) if params else ""
        return "/select-project", new_search, ""

    @app.callback(
        Output("project-overview-container", "children"),
        Input("select-project-dropdown", "value"),
        Input("url", "search"),
        State("url", "pathname"),
        prevent_initial_call=False
    )
    def display_project_overview(project_id, search, pathname):
        from src.inventory import get_project_overview
        import urllib.parse as urlparse_local
        if pathname != "/select-project" or not project_id or not search:
            return None
        query = urlparse_local.parse_qs(search.lstrip('?'))
        stream_id = query.get('stream', [None])[0]
        if not stream_id:
            return None
        data = get_project_overview(stream_id, project_id)
        if not data:
            return html.Div("Aucune donnée disponible pour ce projet.", className="text-muted")
        return html.Div([
            html.H5(f"📊 Vue d'ensemble — {stream_id} / {project_id}", className="mb-3"),
            dash_table.DataTable(data=data, columns=[{"name": col, "id": col} for col in data[0].keys()], style_table={'overflowX': 'auto'})
        ])

    @app.callback(
        Output("select-project-dropdown", "options"),
        Input("url", "search"),
        State("url", "pathname"),
        prevent_initial_call=False
    )
    def update_project_options(search, pathname):
        """Populate project dropdown based on selected stream from URL"""
        if pathname != "/select-project":
            return []
        if not search:
            return []
        q = urlparse.parse_qs(search.lstrip("?"))
        stream_id = q.get("stream", [None])[0]
        if not stream_id:
            return []
        from src.config import STREAMS
        projects = STREAMS.get(stream_id, [])
        try:
            print(f"[DEBUG_UI] update_project_options: stream={stream_id} projects_found={len(projects)}")
        except Exception:
            pass
        return [{"label": p, "value": p} for p in projects]

    @app.callback(
        Output("url", "pathname", allow_duplicate=True),
        Output("url", "search", allow_duplicate=True),
        Input("select-project-next", "n_clicks"),
        State("select-project-dropdown", "value"),
        State("url", "search"),
        prevent_initial_call=True
    )
    def project_next(n, project_value, search):
        """Handle 'Suivant' on select-project page: go to /select-dq-point preserving stream."""
        if not n or not project_value:
            return "/select-project", search or ""
        q = urlparse.parse_qs((search or "").lstrip("?"))
        stream = q.get("stream", [None])[0]
        quarter = q.get("quarter", [None])[0]
        params_parts = []
        if quarter:
            params_parts.append(f"quarter={quarter}")
        if stream:
            params_parts.append(f"stream={stream}")
        params_parts.append(f"project={project_value}")
        params = "?" + "&".join(params_parts)
        return "/select-dq-point", params

    @app.callback(
        Output("zone-overview-container", "children"),
        Input("select-zone-dropdown", "value"),
        Input("url", "search"),
        State("url", "pathname"),
        prevent_initial_call=False
    )
    def display_zone_overview(zone_id, search, pathname):
        from src.inventory import get_zone_overview
        import urllib.parse as urlparse_local
        if pathname != "/select-dq-point" or not zone_id or not search:
            return None
        query = urlparse_local.parse_qs(search.lstrip('?'))
        stream_id = query.get('stream', [None])[0]
        project_id = query.get('project', [None])[0]
        if not stream_id or not project_id:
            return None
        data = get_zone_overview(stream_id, project_id, zone_id)
        if not data:
            return html.Div("Aucune donnée disponible pour cette zone.", className="text-muted")
        return html.Div([
            html.H5(f"📊 Vue d'ensemble — {stream_id} / {project_id} / {zone_id}", className="mb-3"),
            dash_table.DataTable(data=data, columns=[{"name": col, "id": col} for col in data[0].keys()], style_table={'overflowX': 'auto'})
        ])
