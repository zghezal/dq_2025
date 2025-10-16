# Page d'accueil

from dash import html
import dash_bootstrap_components as dbc


def home_page():
    """Page d'accueil Portal STDA avec bouton de connexion"""
    return dbc.Container([
        dbc.Row([
            dbc.Col(
                html.Div([
                    html.H1("Portal STDA", className="text-center mb-4 mt-5"),
                    html.P("Bienvenue sur le portail Data Quality", className="text-center text-muted mb-5"),
                    html.Div([
                        dbc.Button("Log In", href="/dashboard", color="primary", size="lg", className="px-5")
                    ], className="text-center")
                ]),
                width={"size": 6, "offset": 3}
            )
        ], className="mt-5")
    ], fluid=True)
