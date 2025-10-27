from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc
from src.config import get_streams_with_labels


def select_stream_page():
    streams = get_streams_with_labels()
    options = [{"label": data["label"], "value": stream_id} for stream_id, data in streams.items()]
    return dbc.Container([
        html.H2("Étape 1 — Choisir le Stream"),
        html.P("Sélectionnez le stream de données que vous souhaitez gérer."),
        dcc.Dropdown(id="select-stream-dropdown", options=options, placeholder="Choisir un stream"),
        
        html.Div(id="stream-overview-container", className="mt-4"),
        
        dbc.Button("Suivant", id="select-stream-next", color="primary", className="mt-3"),
        html.Div(id="select-stream-status", className="mt-2")
    ], fluid=True)
