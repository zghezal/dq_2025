from dash import html
import dash_bootstrap_components as dbc


def drop_landing_page():
    return dbc.Container([
        html.H2("Drop & DQ — Accueil"),
        html.P("Interface provider : déposer un dataset et déclencher des contrôles DQ."),
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardHeader("📥 Déposer un dataset"),
                dbc.CardBody([
                    html.P("Uploader un fichier CSV et fournir un alias."),
                    dbc.Button("Aller à Drop", href="/drop-dq", color="warning")
                ])
            ]), md=6),
            dbc.Col(dbc.Card([
                dbc.CardHeader("⚙️ Exécuter DQ"),
                dbc.CardBody([
                    html.P("Sélectionner une configuration DQ et lancer un run."),
                    dbc.Button("Aller à Runner", href="/dq-runner", color="info")
                ])
            ]), md=6),
        ], className="g-3 mt-3"),
        html.Hr(),
        dbc.Button("Retour à l'accueil", href="/", color="secondary")
    ], fluid=True)
