# Page dashboard DQ Editor (accès complet)

from dash import html
import dash_bootstrap_components as dbc


def dq_management_dashboard_page():
    """Page dashboard DQ Editor avec accès complet à toutes les fonctionnalités"""
    return dbc.Container([
        dbc.Row([
            dbc.Col(html.H2("DQ Editor - Accès Complet", className="mb-4"), width=12)
        ]),
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardHeader("DQ Inventory", className="bg-secondary text-white"),
                dbc.CardBody([
                    html.P("Consultez l'inventaire complet des configurations DQ existantes."),
                    dbc.Button("DQ Inventory", href="/dq-inventory", color="secondary", className="me-2")
                ])
            ], className="shadow"), md=4),
            dbc.Col(dbc.Card([
                dbc.CardHeader("Builder", className="bg-primary text-white"),
                dbc.CardBody([
                    html.P("Créez et configurez de nouvelles règles de qualité des données."),
                    dbc.Button("Builder", href="/select-stream", color="primary", className="me-2")
                ])
            ], className="shadow"), md=4),
            dbc.Col(dbc.Card([
                dbc.CardHeader("Runner", className="bg-info text-white"),
                dbc.CardBody([
                    html.P("Exécutez les contrôles DQ et générez des rapports."),
                    dbc.Button("Runner", href="/dq-runner", color="info")
                ])
            ], className="shadow"), md=4)
        ], className="g-3 mb-3"),
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardHeader("Drop & DQ", className="bg-warning text-dark"),
                dbc.CardBody([
                    html.P("Accès au dépôt de datasets (également disponible pour les providers)."),
                    dbc.Button("Drop & DQ", href="/drop-dq", color="warning")
                ])
            ], className="shadow"), md={"size": 6, "offset": 3})
        ], className="g-3")
    ], fluid=True)
