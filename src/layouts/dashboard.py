# Page dashboard après connexion

from dash import html
import dash_bootstrap_components as dbc


def dashboard_page():
    """Page dashboard avec les options DQ Management et Drop&DQ"""
    return dbc.Container([
        dbc.Row([
            dbc.Col(html.H2("Portal STDA - Dashboard", className="mb-3"), width=12)
        ]),
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardHeader("DQ Management"),
                dbc.CardBody([
                    html.P("Accès pour les DQ developers : Inventory, Builder, Runner."),
                    dbc.Button("DQ Inventory", href="/dq-inventory", color="secondary", className="me-2"),
                    dbc.Button("Builder", href="/build", color="primary", className="me-2"),
                    dbc.Button("Runner", href="/dq-runner", color="info")
                ])
            ]), md=6),
            dbc.Col(dbc.Card([
                dbc.CardHeader("Drop&DQ"),
                dbc.CardBody([
                    html.P("Accès pour les providers : déposer des datasets et lancer des contrôles DQ."),
                    dbc.Button("Drop & DQ", href="/drop-dq", color="warning")
                ])
            ]), md=6)
        ], className="g-3"),
        dbc.Row([
            dbc.Col(html.P("Choisissez un parcours pour continuer."), width=12)
        ])
    ], fluid=True)
