# Page dashboard Check&Drop (accès limité aux fonctionnalités de dépôt)

from dash import html
import dash_bootstrap_components as dbc


def check_drop_dashboard_page():
    """Page dashboard Check&Drop avec uniquement les fonctionnalités de dépôt"""
    return dbc.Container([
        dbc.Row([
            dbc.Col(html.H2([
                html.I(className="bi bi-cloud-upload me-3"),
                "Check&Drop - Dépôt et Contrôle DQ"
            ], className="mb-4"), width=12)
        ]),
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardHeader([
                    html.I(className="bi bi-upload me-2"),
                    "Canaux de Dépôt"
                ], className="bg-primary text-white"),
                dbc.CardBody([
                    html.P("Déposez vos données via les canaux configurés. Le système effectue automatiquement les contrôles qualité."),
                    html.Ul([
                        html.Li("Sélection du canal approprié"),
                        html.Li("Fourniture des fichiers requis"),
                        html.Li("Validation et contrôles automatiques"),
                        html.Li("Rapport par email immédiat")
                    ]),
                    dbc.Button([
                        html.I(className="bi bi-cloud-upload me-2"),
                        "Déposer mes Données"
                    ], href="/channel-drop", color="primary", size="lg", className="mt-3")
                ])
            ], className="shadow-sm hover-shadow"), md=6),
            
            dbc.Col(dbc.Card([
                dbc.CardHeader([
                    html.I(className="bi bi-file-earmark-text me-2"),
                    "Drop & DQ Manuel"
                ], className="bg-warning text-dark"),
                dbc.CardBody([
                    html.P("Mode avancé : déposez et lancez des contrôles DQ manuellement."),
                    html.Ul([
                        html.Li("Dépôt de fichiers manuel"),
                        html.Li("Sélection des contrôles"),
                        html.Li("Configuration personnalisée"),
                        html.Li("Rapports détaillés")
                    ]),
                    dbc.Button([
                        html.I(className="bi bi-gear me-2"),
                        "Mode Manuel"
                    ], href="/drop-dq", color="warning", outline=True, size="lg", className="mt-3")
                ])
            ], className="shadow-sm"), md=6)
        ], className="g-4")
    ], fluid=True, className="py-4")
