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
        elif pathname == "/dq-management-dashboard":
            parts.append("DQ Management Dashboard")
        elif pathname == "/dq":
            parts.append("DQ Management")
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
        if clean_path == "/dq-management-dashboard":
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
        stream = q.get("stream", [None])[0]
        if not stream:
            return []
        from src.config import STREAMS
        projects = STREAMS.get(stream, [])
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

    @app.callback(
        Output("url", "pathname", allow_duplicate=True),
        Output("url", "search", allow_duplicate=True),
        Input("select-dq-next", "n_clicks"),
        State("select-dq-point-dropdown", "value"),
        State("url", "search"),
        prevent_initial_call=True
    )
    def dq_point_next(n, dq_value, search):
        if not n or not dq_value:
            return "/select-dq-point", search or ""
        q = urlparse.parse_qs((search or "").lstrip("?"))
        stream = q.get("stream", [None])[0]
        project = q.get("project", [None])[0]
        params = f"?stream={stream}&project={project}&dq_point={dq_value}"
        return "/build", params

    # === Inventory integration: peupler la liste des datasets lors de la sélection du DQ point ===
    from src.inventory import get_datasets_for_dq_point

    @app.callback(
        Output("datasets-checklist", "options"),
        Output("inventory-datasets-store", "data"),
        Output("store_datasets", "data"),
        Input("select-dq-point-dropdown", "value"),
        State("url", "search"),
        prevent_initial_call=True
    )
    def populate_datasets_for_dq_point(dq_point, search):
        """Remplit la checklist et le store avec les datasets correspondant au DQ point sélectionné.

        Utilise `config/inventory.yaml` via `src.utils.inventory.get_datasets_for_dq_point`.
        Si le contexte stream/project est fourni dans l'URL, on restreint au scope.
        """
        if not dq_point:
            return [], {}

        stream = None
        project = None
        if search:
            q = urlparse.parse_qs(search.lstrip('?'))
            stream = q.get('stream', [None])[0]
            project = q.get('project', [None])[0]

        datasets = get_datasets_for_dq_point(dq_point, stream=stream, project=project) or []

        options = [{"label": f"{d.get('alias') or d.get('name')}", "value": f"{d.get('alias') or d.get('name')}"} for d in datasets]
        store_payload = {"dq_point": dq_point, "datasets": datasets}

        # Also prepare a shape compatible with store_datasets used par la page Build
        store_datasets_payload = []
        for d in datasets:
            name = d.get('name') or d.get('alias')
            alias = d.get('alias') or (name and name.split('.')[0].lower())
            store_datasets_payload.append({"alias": alias, "dataset": name})

        return options, store_payload, store_datasets_payload
