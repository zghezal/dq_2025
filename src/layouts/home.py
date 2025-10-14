# Page d'accueil

from dash import html
import dash_bootstrap_components as dbc


def home_page():
    """Page d'accueil principale"""
    return dbc.Container([
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardHeader("Bienvenue"),
                dbc.CardBody([
                    html.P("Gérer la qualité des données"),
                    dbc.Button("DQ Management", href="/dq", color="primary")
                ])
            ]), md=6, lg=5)
        ], className="g-3")
    ], fluid=True)
