# Page DQ Management

from dash import html, dcc
import dash_bootstrap_components as dbc
from src.config import STREAMS

# DQ points catalogue
DQ_POINTS = [
    "Extraction",
    "Transformation",
    "Chargement"
]


def dq_page():
    """Page de gestion des configurations DQ"""
    return dbc.Container([
        dbc.Card([dbc.CardHeader("DQ Management"), dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Label("Stream"),
                    dcc.Dropdown(
                        id="dq-stream",
                        options=[{"label": s, "value": s} for s in STREAMS.keys()],
                        placeholder="Select stream",
                        clearable=False
                    )
                ], md=4),
                dbc.Col([
                    html.Label("Project"),
                    dcc.Dropdown(
                        id="dq-project",
                        options=[],
                        placeholder="Select project",
                        disabled=True,
                        clearable=False
                    )
                ], md=4),
                dbc.Col([
                    html.Label("DQ Point"),
                    dcc.Dropdown(
                        id="dq-point",
                        options=[{"label": p, "value": p} for p in DQ_POINTS],
                        placeholder="Select DQ point",
                        clearable=False
                    )
                ], md=4),
            ]),
            html.Div(id="dq-list", className="mt-3"),
            html.A(
                id="dq-create",
                className="btn btn-success mt-2 me-2",
                children="Créer de scratch"
            ),
            dbc.Button("Actualiser", id="dq-refresh", color="secondary", className="mt-2"),
        ])])
    ], fluid=True)
