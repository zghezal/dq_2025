from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc
from src.config import STREAMS


def select_project_page():
    return dbc.Container([
        html.H2("Étape 3 — Choisir le Project"),
        html.P("Le projet sera filtré en fonction du Stream choisi."),
        dcc.Dropdown(id="select-project-dropdown", options=[], placeholder="Choisir un project"),
        
        html.Div(id="project-overview-container", className="mt-4"),
        
        dbc.Button("Suivant", id="select-project-next", color="primary", className="mt-3"),
        html.Div(id="select-project-status", className="mt-2")
    ], fluid=True)
