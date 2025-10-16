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
        if clean_path in ("/", "", None):
            return home_page()
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
        if clean_path == "/drop-dq":
            return drop_dq_page()
        if clean_path == "/configs":
            return configs_page()
        return dbc.Container([
            dbc.Alert("🛠️ Bientôt disponible. Revenez à la Construction pour l'instant.", color="info")
        ], fluid=True)

    # Stepper pages: Stream -> Project -> DQ Point
    @app.callback(
        Output("page-content", "children"),
        Input("url", "pathname"),
        prevent_initial_call=True
    )
    def display_step_pages(pathname):
        clean_path = (pathname or "").split('?')[0]
        if clean_path == "/select-stream":
            return select_stream_page()
        if clean_path == "/select-project":
            return select_project_page()
        if clean_path == "/select-dq-point":
            return select_dq_point_page()
        return no_update

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
        Output("url", "pathname"),
        Output("url", "search"),
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
        Output("url", "pathname"),
        Output("url", "search"),
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
