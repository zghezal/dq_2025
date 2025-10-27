from dash import html
import dash_bootstrap_components as dbc


def dq_landing_page():
    return dbc.Container([
        html.H2("DQ Editor — Accueil"),
        html.P("Choisissez une action pour les DQ developers. Chaque action ouvre une page dédiée."),
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardHeader("📊 DQ Inventory"),
                dbc.CardBody([
                    html.P("Parcourir l'inventaire des configurations et points DQ."),
                    dbc.Button("Ouvrir Inventory", href="/dq-inventory", color="secondary")
                ])
            ]), md=4),
            dbc.Col(dbc.Card([
                dbc.CardHeader("🔧 Builder"),
                dbc.CardBody([
                    html.P("Créer et configurer des métriques / tests (wizard)."),
                    dbc.Button("Ouvrir Builder", href="/select-stream", color="primary")
                ])
            ]), md=4),
            dbc.Col(dbc.Card([
                dbc.CardHeader("▶️ Runner"),
                dbc.CardBody([
                    html.P("Exécuter une configuration DQ et voir les résultats."),
                    dbc.Button("Ouvrir Runner", href="/dq-runner", color="info")
                ])
            ]), md=4),
        ], className="g-3 mt-3"),
        html.Hr(),
        dbc.Button("Retour à l'accueil", href="/", color="secondary")
    ], fluid=True)
