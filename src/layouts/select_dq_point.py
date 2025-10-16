from dash import html, dcc
import dash_bootstrap_components as dbc


def select_dq_point_page():
    return dbc.Container([
        html.H2("Étape 3 — Choisir le DQ Point"),
        html.P("Sélectionnez le point DQ (ex: Extraction, Transformation, Chargement)."),
        dcc.Dropdown(id="select-dq-point-dropdown", options=[{"label":"Extraction","value":"Extraction"},{"label":"Transformation","value":"Transformation"},{"label":"Chargement","value":"Chargement"}], placeholder="Choisir un DQ Point"),
        dbc.Button("Aller au Builder", id="select-dq-next", color="primary", className="mt-3"),
        html.Div(id="select-dq-status", className="mt-2")
    ], fluid=True)
