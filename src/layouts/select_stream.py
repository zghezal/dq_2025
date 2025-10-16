from dash import html, dcc
import dash_bootstrap_components as dbc
from src.config import STREAMS


def select_stream_page():
    options = [{"label": s, "value": s} for s in STREAMS.keys()]
    return dbc.Container([
        html.H2("Étape 1 — Choisir le Stream"),
        html.P("Sélectionnez le stream de données que vous souhaitez gérer."),
        dcc.Dropdown(id="select-stream-dropdown", options=options, placeholder="Choisir un stream"),
        dbc.Button("Suivant", id="select-stream-next", color="primary", className="mt-3"),
        html.Div(id="select-stream-status", className="mt-2")
    ], fluid=True)
