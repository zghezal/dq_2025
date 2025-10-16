from dash import html
import dash_bootstrap_components as dbc


def dq_runner_page():
    return dbc.Container([
        html.H2("DQ Runner"),
        html.P("Page placeholder — exécution et visualisation des runs DQ."),
        dbc.Button("Aller au Builder", href="/build", color="primary", className="me-2"),
        dbc.Button("Retour à l'accueil", href="/", color="secondary")
    ], fluid=True)
