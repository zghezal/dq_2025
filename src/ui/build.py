# src/ui/build.py
from __future__ import annotations

import dash
from dash import html, dcc
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc

from src.ui.components.filter_selector import register_filter_selector

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Store global pour piloter le contexte (peut être mis à jour ailleurs dans l'app)
context_store = dcc.Store(id="dqf-context", data={"stream": "", "project": "", "zone": ""})

filter_selector = register_filter_selector(
    app,
    prefix="dqf",
    context_store_id="dqf-context"  # le composant se mettra à jour si ce store change
)

app.layout = dbc.Container([
    context_store,
    html.H2("Ma webapp DQ"),
    dbc.Row([dbc.Col(filter_selector, width=12)]),
    html.Hr(),
    html.Div(id="debug"),
], fluid=True)

@app.callback(
    Output("debug", "children"),
    Input("dqf-filter", "value"),
    State("dqf-stream", "value"),
    State("dqf-project", "value"),
    State("dqf-zone", "value"),
)
def _debug(flt, stream, project, zone):
    return f"selected: stream={stream}, project={project}, zone={zone}, filter={flt}"

if __name__ == "__main__":
    app.run_server(debug=True)
