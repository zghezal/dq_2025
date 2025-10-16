# Page dashboard Check&Drop (accès limité aux fonctionnalités de dépôt)

from dash import html
import dash_bootstrap_components as dbc


def check_drop_dashboard_page():
    """Page dashboard Check&Drop avec uniquement les fonctionnalités de dépôt"""
    return dbc.Container([
        dbc.Row([
            dbc.Col(html.H2("Check&Drop - Dépôt et Contrôle DQ", className="mb-4"), width=12)
        ]),
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardHeader("Drop & DQ", className="bg-warning text-dark"),
                dbc.CardBody([
                    html.P("Déposez vos datasets et lancez des contrôles DQ automatiques."),
                    html.Ul([
                        html.Li("Dépôt de fichiers"),
                        html.Li("Validation automatique"),
                        html.Li("Rapports de qualité")
                    ]),
                    dbc.Button("Accéder au Drop & DQ", href="/drop-dq", color="warning", className="mt-3")
                ])
            ], className="shadow"), md={"size": 8, "offset": 2})
        ], className="g-3")
    ], fluid=True)
