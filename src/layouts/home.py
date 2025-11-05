# Page d'accueil

from dash import html
import dash_bootstrap_components as dbc


def home_page():
    """Page d'accueil Portal STDA avec deux accès distincts"""
    return dbc.Container([
        dbc.Row([
            dbc.Col(
                html.Div([
                    html.H1("Portal STDA", className="text-center mb-4 mt-5"),
                    html.P("Bienvenue sur le portail Data Quality", className="text-center text-muted mb-5"),
                    html.P("Choisissez votre type d'accès :", className="text-center mb-4"),
                ]),
                width=12
            )
        ], className="mt-5"),
        dbc.Row([
            dbc.Col(
                dbc.Card([
                    dbc.CardBody([
                        html.H4("Check&Drop", className="text-center mb-3"),
                        html.P("Accès pour déposer des datasets et lancer des contrôles DQ", className="text-center text-muted mb-4"),
                        dbc.Button(
                            "Accéder",
                            id="home-checkdrop-btn",
                            color="warning",
                            size="lg",
                            className="w-100"
                        )
                    ])
                ], className="shadow"),
                md={"size": 4, "offset": 2}
            ),
            dbc.Col(
                dbc.Card([
                    dbc.CardBody([
                        html.H4("DQ Editor", className="text-center mb-3"),
                        html.P("Accès complet pour les DQ developers : Inventory, Builder, Runner", className="text-center text-muted mb-4"),
                        dbc.Button(
                            "Accéder",
                            id="home-dqeditor-btn",
                            color="primary",
                            size="lg",
                            className="w-100"
                        )
                    ])
                ], className="shadow"),
                md=4
            )
        ], className="g-4 mb-5")
    ], fluid=True)
