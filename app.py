# app.py — Point d'entrée principal de l'application DQ Builder

from dash import Dash, html, dcc
import dash_bootstrap_components as dbc

# Layouts
from src.layouts.navbar import navbar
from src.layouts.home import home_page
from src.layouts.dq import dq_page
from src.layouts.build import build_page
from src.layouts.configs import configs_page

# Callbacks
from src.callbacks.navigation import register_navigation_callbacks
from src.callbacks.dq import register_dq_callbacks
from src.callbacks.build import register_build_callbacks
from src.callbacks.configs import register_configs_callbacks

# Initialisation de l'application Dash
external_stylesheets = [dbc.themes.BOOTSTRAP]
app = Dash(__name__, external_stylesheets=external_stylesheets, suppress_callback_exceptions=True)

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
    home_page(),
    dq_page(),
    build_page(),
    configs_page()
])

# Enregistrement des callbacks
register_navigation_callbacks(app)
register_dq_callbacks(app)
register_build_callbacks(app)
register_configs_callbacks(app)

if __name__ == "__main__":
    app.run(debug=True)
