# Page DQ Editor

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
        dbc.Card([dbc.CardHeader("DQ Editor"), dbc.CardBody([
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
        ])]),
        
        # Modal pour renommer
        dbc.Modal([
            dbc.ModalHeader("Renommer la configuration"),
            dbc.ModalBody([
                html.Label("Nouveau nom du fichier"),
                dcc.Input(id="rename-input", type="text", className="form-control", placeholder="nouveau_nom.json"),
                html.Div(id="rename-feedback", className="mt-2")
            ]),
            dbc.ModalFooter([
                dbc.Button("Annuler", id="rename-cancel", color="secondary", size="sm"),
                dbc.Button("Renommer", id="rename-confirm", color="primary", size="sm")
            ])
        ], id="rename-modal", is_open=False),
        
        # Modal pour confirmer suppression
        dbc.Modal([
            dbc.ModalHeader("Confirmer la suppression"),
            dbc.ModalBody(id="delete-confirm-text"),
            dbc.ModalFooter([
                dbc.Button("Annuler", id="delete-cancel", color="secondary", size="sm"),
                dbc.Button("Supprimer", id="delete-confirm", color="danger", size="sm")
            ])
        ], id="delete-modal", is_open=False),
        
        # Stores pour garder le fichier en cours d'action
        dcc.Store(id="current-file-action"),
    ], fluid=True)
