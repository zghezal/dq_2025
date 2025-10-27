# app.py — Point d'entrée principal de l'application DQ Builder

from dash import Dash, html, dcc
import dash_bootstrap_components as dbc

# Layouts
from src.layouts.navbar import navbar
from src.layouts.home import home_page
from src.layouts.dashboard import dashboard_page
from src.layouts.check_drop_dashboard import check_drop_dashboard_page
from src.layouts.dq_management_dashboard import dq_management_dashboard_page
from src.layouts.dq import dq_page
from src.layouts.build import build_page
from src.layouts.configs import configs_page
from src.layouts.dq_inventory import dq_inventory_page
from src.layouts.dq_runner import dq_runner_page
from src.layouts.drop_dq import drop_dq_page
from src.layouts.select_stream import select_stream_page
from src.layouts.select_project import select_project_page
from src.layouts.select_dq_point import select_dq_point_page

# Callbacks
from src.callbacks.navigation import register_navigation_callbacks
from src.callbacks.dq import register_dq_callbacks
from src.callbacks.build import register_build_callbacks
from src.callbacks.configs import register_configs_callbacks
# Spark context global (instantiated at app startup so Dataiku webapp finds a ready Spark session)
try:
    from src.context.spark_context import SparkDQContext
    # Create a minimal catalog for now; when launched from Dataiku the inventory mapping
    # can be injected into the context or callbacks can attach datasets to this catalog.
    spark_ctx = SparkDQContext(catalog={})
except Exception:
    spark_ctx = None

# Initialisation de l'application Dash
external_stylesheets = [dbc.themes.BOOTSTRAP]
app = Dash(__name__, external_stylesheets=external_stylesheets, suppress_callback_exceptions=True)

# Attach the Spark context to the underlying Flask server so callbacks can reuse it
if spark_ctx is not None:
    app.server.spark_context = spark_ctx

# Layout principal
app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    navbar(),
    html.Div(id="page-content", children=home_page())
])

# Layout de validation pour les callbacks multi-pages
app.validation_layout = html.Div([
    dcc.Location(id="url", refresh=False),
    navbar(),
    html.Div(id="page-content"),
    
    # Stores globaux partagés entre toutes les pages (déclarés ici pour éviter les duplications)
    dcc.Store(id="inventory-datasets-store", storage_type="session"),
    
    home_page(),
    dashboard_page(),
    check_drop_dashboard_page(),
    dq_management_dashboard_page(),
    dq_page(),
        build_page(),
        dq_inventory_page(),
        dq_runner_page(),
        drop_dq_page(),
        select_stream_page(),
        select_project_page(),
        select_dq_point_page(),
        # Placeholders for pattern-matching callback IDs used in build callbacks
        html.Div(id={"role": "metric-preview"}, style={"display": "none"}),
        dcc.Dropdown(id={"role": "metric-column", "form": "metric"}, options=[], style={"display": "none"}),
    configs_page()
])

# Enregistrement des callbacks
register_navigation_callbacks(app)
register_dq_callbacks(app)
register_build_callbacks(app)
register_configs_callbacks(app)

if __name__ == "__main__":
    app.run(debug=True)
