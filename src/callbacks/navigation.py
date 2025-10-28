# Callbacks de navigation

import urllib.parse as urlparse
from dash import Input, Output, State, no_update
import dash_bootstrap_components as dbc
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
from dash import Input, Output, State


def register_navigation_callbacks(app):
    """Enregistre les callbacks de navigation et breadcrumbs"""
    
    @app.callback(
        Output("crumb", "children"),
        Input("url", "pathname")
    )
    def update_crumb(pathname):
        """Met à jour le breadcrumb selon la page"""
        parts = []
        if pathname == "/":
            parts.append("Home")
        elif pathname == "/dashboard":
            parts.append("Dashboard")
        elif pathname == "/check-drop-dashboard":
            parts.append("Check&Drop Dashboard")
        elif pathname == "/dq-editor-dashboard":
            parts.append("DQ Editor Dashboard")
        elif pathname == "/dq":
            parts.append("DQ Editor")
        elif pathname == "/dq-inventory":
            parts.append("DQ Inventory")
        elif pathname == "/dq-runner":
            parts.append("DQ Runner")
        elif pathname == "/drop-dq":
            parts.append("Drop&DQ")
        elif pathname == "/build":
            parts.append("Build")
        elif pathname == "/configs":
            parts.append("Configurations")
        return " / ".join(parts) if parts else ""

    @app.callback(
        Output("page-content", "children"),
        Input("url", "pathname")
    )
    def display_page(pathname):
        """Affiche la page correspondant au pathname"""
        # URL-decode and strip query parameters if they're encoded in the pathname
        decoded_path = urlparse.unquote(pathname) if pathname else pathname
        clean_path = decoded_path.split('?')[0] if decoded_path else decoded_path
        
        # Main pages
        if clean_path in ("/", "", None):
            return home_page()
        if clean_path == "/dashboard":
            return dashboard_page()
        if clean_path == "/check-drop-dashboard":
            return check_drop_dashboard_page()
        if clean_path == "/dq-editor-dashboard":
            return dq_management_dashboard_page()
        if clean_path == "/build":
            return build_page()
        if clean_path == "/dq":
            return dq_landing_page()
        if clean_path == "/drop-dq":
            return drop_landing_page()
        if clean_path == "/dq-inventory":
            return dq_inventory_page()
        if clean_path == "/dq-runner":
            return dq_runner_page()
        if clean_path == "/configs":
            return configs_page()
        
        # Stepper pages: Stream -> Project -> DQ Point
        if clean_path == "/select-stream":
            return select_stream_page()
        if clean_path == "/select-project":
            return select_project_page()
        if clean_path == "/select-dq-point":
            return select_dq_point_page()
        
        return dbc.Container([
            dbc.Alert("🛠️ Bientôt disponible. Revenez à la Construction pour l'instant.", color="info")
        ], fluid=True)

    @app.callback(
        Output("url", "pathname"),
        Output("url", "search"),
        Input("select-stream-next", "n_clicks"),
        State("select-stream-dropdown", "value"),
        prevent_initial_call=True
    )
    def stream_next(n, stream_value):
        if not n or not stream_value:
            return "/select-stream", ""
        # pass stream as query param and go to project selection
        return "/select-project", f"?stream={stream_value}"

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
        if not n or not project_value:
            return "/select-project", search or ""
        # keep stream param and add project
        q = urlparse.parse_qs((search or "").lstrip("?"))
        stream = q.get("stream", [None])[0]
        params = f"?stream={stream}&project={project_value}"
        return "/select-dq-point", params

    # === Inventory integration: Peupler le dropdown des zones ===
    from src.inventory import get_zones, get_datasets_for_zone

    @app.callback(
        Output("select-zone-dropdown", "options"),
        Input("url", "search"),
        State("url", "pathname"),
        prevent_initial_call=False
    )
    def populate_zone_dropdown(search, pathname):
        """Remplit le dropdown des zones basé sur stream/project de l'URL."""
        print(f"[DEBUG] populate_zone_dropdown CALLED: pathname='{pathname}', search='{search}'")
        
        # Clean pathname to handle both encoded and clean paths
        clean_pathname = urlparse.unquote(pathname) if pathname else pathname
        # Extract path without query params
        if clean_pathname and '?' in clean_pathname:
            path_part = clean_pathname.split('?')[0]
            # If search is empty, extract from pathname
            if not search and '?' in clean_pathname:
                search = '?' + clean_pathname.split('?')[1]
        else:
            path_part = clean_pathname
        
        if path_part != "/select-dq-point":
            print(f"[DEBUG] pathname mismatch, returning empty. Expected '/select-dq-point', got '{path_part}'")
            return []
        
        stream_id = None
        project_id = None
        if search:
            q = urlparse.parse_qs(search.lstrip('?'))
            stream_id = q.get('stream', [None])[0]
            project_id = q.get('project', [None])[0]
        
        print(f"[DEBUG] populate_zone_dropdown: stream={stream_id}, project={project_id}")
        
        zones = get_zones(stream_id=stream_id, project_id=project_id)
        options = [{"label": f"{z['label']} ({z['datasets_count']} datasets)", "value": z['id']} for z in zones]
        
        print(f"[DEBUG] Found {len(options)} zones with options: {options}")
        return options

    @app.callback(
        Output("url", "pathname", allow_duplicate=True),
        Output("url", "search", allow_duplicate=True),
        Input("select-dq-next", "n_clicks"),
        State("select-zone-dropdown", "value"),
        State("url", "search"),
        prevent_initial_call=True
    )
    def zone_next(n, zone_value, search):
        """Navigation: Zone → Builder avec paramètre 'zone' au lieu de 'dq_point'."""
        if not n or not zone_value:
            return "/select-dq-point", search or ""
        q = urlparse.parse_qs((search or "").lstrip("?"))
        stream = q.get("stream", [None])[0]
        project = q.get("project", [None])[0]
        params = f"?stream={stream}&project={project}&zone={zone_value}"
        return "/build", params

    @app.callback(
        Output("datasets-list", "children"),
        Output("datasets-status", "children"),
        Output("inventory-datasets-store", "data"),
        Input("select-zone-dropdown", "value"),
        Input("url", "search"),
        prevent_initial_call='initial_duplicate'
    )
    def populate_datasets_for_zone(zone_id, search):
        """Affiche un aperçu des datasets de la zone et stocke les données pour le Builder.

        Utilise `config/inventory.yaml` via `src.inventory.get_datasets_for_zone`.
        Si le contexte stream/project est fourni dans l'URL, on restreint au scope.
        
        IMPORTANT: Enregistre automatiquement les datasets dans le catalog Spark
        pour permettre l'accès dynamique aux schémas et données.
        """
        from dash import html, no_update
        from flask import current_app
        from src.spark_inventory_adapter import register_inventory_datasets_in_spark
        
        print(f"[DEBUG] populate_datasets_for_zone called: zone={zone_id}, search={search}")
        
        if not zone_id:
            print("[DEBUG] No zone, returning no_update for store to preserve existing data")
            return html.Em("Sélectionnez une zone"), "Sélectionnez une zone pour voir les datasets disponibles", no_update

        stream_id = None
        project_id = None
        if search:
            q = urlparse.parse_qs(search.lstrip('?'))
            stream_id = q.get('stream', [None])[0]
            project_id = q.get('project', [None])[0]
        
        print(f"[DEBUG] Extracted params: stream={stream_id}, project={project_id}")

        datasets = get_datasets_for_zone(zone_id, stream_id=stream_id, project_id=project_id) or []
        
        print(f"[DEBUG] Found {len(datasets)} datasets: {[d.get('alias') for d in datasets]}")
        
        # 🔥 NOUVEAU: Enregistrer les datasets dans le catalog Spark
        spark_ctx = getattr(current_app, 'spark_context', None)
        if spark_ctx and datasets:
            try:
                register_inventory_datasets_in_spark(spark_ctx, datasets)
                print(f"[DEBUG] ✅ {len(datasets)} datasets enregistrés dans Spark catalog")
            except Exception as e:
                print(f"[DEBUG] ⚠️ Erreur lors de l'enregistrement Spark: {e}")

        store_payload = {"zone": zone_id, "datasets": datasets}

        if len(datasets) == 0:
            from dash import html
            status_msg = f"Zone '{zone_id}' sélectionnée"
            list_html = html.Em("Aucun dataset trouvé")
        else:
            from dash import html
            status_msg = f"✅ {len(datasets)} dataset(s) disponible(s)"
            # Afficher la liste des datasets avec leurs alias — chaque item est cliquable
            dataset_items = []
            for i, d in enumerate(datasets):
                alias = d.get('alias', 'N/A')
                name = d.get('name', 'N/A')
                # Ligne avec label et bouton de prévisualisation
                dataset_items.append(
                    html.Li([
                        html.Span(f"{alias} ({name})", className="me-3 small"),
                        dbc.Button("Prévisualiser", id={"type": "dataset-preview", "index": i}, color="primary", size="sm")
                    ], className="mb-2")
                )
            list_html = html.Ul(dataset_items, className="mb-0 list-unstyled")
        
        print(f"[DEBUG] Returning list for {len(datasets)} datasets")
        return list_html, status_msg, store_payload

    # === CALLBACK: clic sur un dataset pour afficher la prévisualisation ===
    from dash import ALL, callback_context

    @app.callback(
        Output("modal-body-content", "children"),
        Output("dataset-preview-modal", "is_open", allow_duplicate=True),
        Output("dataset-preview-title", "children"),
        Input({"type": "dataset-preview", "index": ALL}, "n_clicks"),
        State("inventory-datasets-store", "data"),
        prevent_initial_call=True,
    )
    def show_dataset_preview(n_clicks_list, store_payload):
        """Affiche schema + un échantillon du dataset cliqué via SparkDQContext."""
        from dash import html, dash_table
        import json
        from flask import current_app
        from dash import no_update

        ctx = callback_context
        if not ctx.triggered:
            return no_update

        # Récupérer l'index cliqué depuis le prop_id déclenché
        prop = ctx.triggered[0]["prop_id"]  # ex: '{"type":"dataset-preview","index":0}.n_clicks'
        try:
            triggered_id = json.loads(prop.split('.n_clicks')[0])
        except Exception:
            try:
                triggered_id = json.loads(prop.split('.')[0])
            except Exception:
                return html.Div("Impossible d'identifier l'élément cliqué", className="text-danger")

        idx = triggered_id.get("index")
        if store_payload is None or "datasets" not in store_payload:
            return html.Div("Aucun dataset en mémoire.", className="text-muted")

        datasets = store_payload.get("datasets", [])
        if idx is None or idx >= len(datasets):
            return html.Div("Sélection invalide.", className="text-danger")

        chosen = datasets[idx]
        alias = chosen.get("alias")

        spark_ctx = getattr(current_app, 'spark_context', None)
        if not spark_ctx:
            return html.Div("Spark context non initialisé", className="text-danger")

        try:
            # Récupérer colonnes (schéma) sans scan coûteux
            cols = spark_ctx.peek_schema(alias)

            # Charger un petit échantillon
            df = spark_ctx.load(alias, cache=False)
            sample_pdf = df.limit(10).toPandas()

            # Créer une vue temporaire unique pour cette prévisualisation
            import time
            temp_name = f"tmp_preview_{alias}_{int(time.time())}"
            try:
                df.createOrReplaceTempView(temp_name)
                temp_info = html.Div(f"Vue temporaire créée: '{temp_name}' (session temporaire)", className="text-muted small mb-2")
            except Exception:
                temp_info = html.Div("Impossible de créer la vue temporaire.", className="text-muted small mb-2 text-warning")

            # Construire la carte de preview
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

    # Callback pour fermer le modal
    @app.callback(
        Output("dataset-preview-modal", "is_open", allow_duplicate=True),
        Input("close-dataset-preview", "n_clicks"),
        State("dataset-preview-modal", "is_open"),
        prevent_initial_call=True,
    )
    def close_preview(n, is_open):
        # ferme le modal lorsque l'utilisateur clique sur le bouton Fermer
        if not n:
            return is_open
        return False
    
    # === CALLBACKS POUR LES TABLEAUX DE VISUALISATION ===
    
    @app.callback(
        Output("stream-overview-container", "children"),
        Input("select-stream-dropdown", "value"),
        State("url", "pathname"),
        prevent_initial_call=False
    )
    def display_stream_overview(stream_id, pathname):
        """Affiche le tableau récapitulatif pour le stream sélectionné"""
        from dash import dash_table, html
        from src.inventory import get_stream_overview
        
        if pathname != "/select-stream" or not stream_id:
            return None
        
        data = get_stream_overview(stream_id)
        if not data:
            return html.Div("Aucune donnée disponible pour ce stream.", className="text-muted")
        
        return html.Div([
            html.H5(f"📊 Vue d'ensemble — {stream_id}", className="mb-3"),
            dash_table.DataTable(
                data=data,
                columns=[{"name": col, "id": col} for col in data[0].keys()],
                style_table={'overflowX': 'auto'},
                style_cell={
                    'textAlign': 'left',
                    'padding': '10px',
                    'whiteSpace': 'normal',
                    'height': 'auto',
                },
                style_header={
                    'backgroundColor': 'rgb(230, 230, 230)',
                    'fontWeight': 'bold'
                },
                style_data_conditional=[
                    {'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}
                ]
            )
        ])
    
    @app.callback(
        Output("project-overview-container", "children"),
        Input("select-project-dropdown", "value"),
        Input("url", "search"),
        State("url", "pathname"),
        prevent_initial_call=False
    )
    def display_project_overview(project_id, search, pathname):
        """Affiche le tableau récapitulatif pour le projet sélectionné"""
        from dash import dash_table, html
        from src.inventory import get_project_overview
        import urllib.parse as urlparse
        
        if pathname != "/select-project" or not project_id or not search:
            return None
        
        # Extraire le stream depuis l'URL
        query = urlparse.parse_qs(search.lstrip('?'))
        stream_id = query.get('stream', [None])[0]
        
        if not stream_id:
            return None
        
        data = get_project_overview(stream_id, project_id)
        if not data:
            return html.Div("Aucune donnée disponible pour ce projet.", className="text-muted")
        
        return html.Div([
            html.H5(f"📊 Vue d'ensemble — {stream_id} / {project_id}", className="mb-3"),
            dash_table.DataTable(
                data=data,
                columns=[{"name": col, "id": col} for col in data[0].keys()],
                style_table={'overflowX': 'auto'},
                style_cell={
                    'textAlign': 'left',
                    'padding': '10px',
                    'whiteSpace': 'normal',
                    'height': 'auto',
                },
                style_header={
                    'backgroundColor': 'rgb(230, 230, 230)',
                    'fontWeight': 'bold'
                },
                style_data_conditional=[
                    {'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}
                ]
            )
        ])
    
    @app.callback(
        Output("zone-overview-container", "children"),
        Input("select-zone-dropdown", "value"),
        Input("url", "search"),
        State("url", "pathname"),
        prevent_initial_call=False
    )
    def display_zone_overview(zone_id, search, pathname):
        """Affiche le tableau récapitulatif pour la zone sélectionnée"""
        from dash import dash_table, html
        from src.inventory import get_zone_overview
        import urllib.parse as urlparse
        
        if pathname != "/select-dq-point" or not zone_id or not search:
            return None
        
        # Extraire stream et project depuis l'URL
        query = urlparse.parse_qs(search.lstrip('?'))
        stream_id = query.get('stream', [None])[0]
        project_id = query.get('project', [None])[0]
        
        if not stream_id or not project_id:
            return None
        
        data = get_zone_overview(stream_id, project_id, zone_id)
        if not data:
            return html.Div("Aucune donnée disponible pour cette zone.", className="text-muted")
        
        return html.Div([
            html.H5(f"📊 Vue d'ensemble — {stream_id} / {project_id} / {zone_id}", className="mb-3"),
            dash_table.DataTable(
                data=data,
                columns=[{"name": col, "id": col} for col in data[0].keys()],
                style_table={'overflowX': 'auto'},
                style_cell={
                    'textAlign': 'left',
                    'padding': '10px',
                    'whiteSpace': 'normal',
                    'height': 'auto',
                },
                style_header={
                    'backgroundColor': 'rgb(230, 230, 230)',
                    'fontWeight': 'bold'
                },
                style_data_conditional=[
                    {'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}
                ]
            )
        ])
