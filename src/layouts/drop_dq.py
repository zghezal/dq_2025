from dash import html
import dash_bootstrap_components as dbc


def drop_dq_page():
    return dbc.Container([
        html.H2("Drop & DQ"),
        html.P("Page placeholder — interface provider pour déposer des datasets et lancer des contrôles DQ."),
        dbc.Button("Retour à l'accueil", href="/", color="secondary")
    ], fluid=True)
