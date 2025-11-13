# Page dashboard DQ Editor (accès complet)

from dash import html
import dash_bootstrap_components as dbc


def dq_management_dashboard_page():
    """Page dashboard DQ Editor avec accès complet à toutes les fonctionnalités"""
    return dbc.Container([
        # En-tête principal avec description
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H1([
                        html.I(className="bi bi-gear-fill me-3"),
                        "DQ Editor Dashboard"
                    ], className="mb-3 text-primary"),
                    html.P(
                        "Plateforme de gestion complète de la qualité des données. "
                        "Créez, configurez et exécutez vos règles de contrôle qualité.",
                        className="lead text-muted mb-4"
                    ),
                    html.Hr()
                ])
            ], width=12)
        ], className="mb-4"),
        
        # Section principale: Outils principaux
        dbc.Row([
            dbc.Col(html.H4([
                html.I(className="bi bi-tools me-2"),
                "Outils Principaux"
            ], className="mb-3"), width=12)
        ]),
        
        dbc.Row([
            # DQ Inventory
            dbc.Col(dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="bi bi-folder2-open text-secondary", 
                               style={"fontSize": "3rem"}),
                    ], className="text-center mb-3"),
                    html.H5("DQ Inventory", className="card-title text-center mb-3"),
                    html.P(
                        "Explorez l'inventaire complet des configurations DQ existantes. "
                        "Consultez, recherchez et gérez vos règles de qualité.",
                        className="card-text text-muted small",
                        style={"minHeight": "60px"}
                    ),
                    html.Div([
                        dbc.Button([
                            html.I(className="bi bi-box-arrow-in-right me-2"),
                            "Accéder à l'inventaire"
                        ], href="/dq-inventory", color="secondary", size="lg", 
                        className="w-100")
                    ])
                ])
            ], className="shadow-sm hover-shadow h-100", 
               style={"transition": "all 0.3s ease"}), md=4),
            
            # Builder
            dbc.Col(dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="bi bi-hammer text-primary", 
                               style={"fontSize": "3rem"}),
                    ], className="text-center mb-3"),
                    html.H5("Builder", className="card-title text-center mb-3"),
                    html.P(
                        "Créez et configurez de nouvelles règles de qualité des données. "
                        "Définissez métriques, tests et seuils personnalisés.",
                        className="card-text text-muted small",
                        style={"minHeight": "60px"}
                    ),
                    html.Div([
                        dbc.Button([
                            html.I(className="bi bi-plus-circle me-2"),
                            "Créer une règle DQ"
                        ], href="/select-quarter", color="primary", size="lg", 
                        className="w-100")
                    ])
                ])
            ], className="shadow-sm hover-shadow h-100",
               style={"transition": "all 0.3s ease"}), md=4),
            
            # Runner
            dbc.Col(dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="bi bi-play-circle text-info", 
                               style={"fontSize": "3rem"}),
                    ], className="text-center mb-3"),
                    html.H5("Runner", className="card-title text-center mb-3"),
                    html.P(
                        "Exécutez les contrôles qualité et générez des rapports détaillés. "
                        "Visualisez les résultats et exportez en Excel.",
                        className="card-text text-muted small",
                        style={"minHeight": "60px"}
                    ),
                    html.Div([
                        dbc.Button([
                            html.I(className="bi bi-lightning-charge me-2"),
                            "Exécuter les contrôles"
                        ], href="/dq-runner", color="info", size="lg", 
                        className="w-100")
                    ])
                ])
            ], className="shadow-sm hover-shadow h-100",
               style={"transition": "all 0.3s ease"}), md=4)
        ], className="g-4 mb-5"),
        
        # Section secondaire: Fonctionnalités additionnelles
        dbc.Row([
            dbc.Col(html.H4([
                html.I(className="bi bi-grid-3x3-gap me-2"),
                "Fonctionnalités Additionnelles"
            ], className="mb-3 mt-4"), width=12)
        ]),
        
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.Div([
                            html.I(className="bi bi-cloud-upload text-warning me-3", 
                                   style={"fontSize": "2.5rem"}),
                            html.Div([
                                html.H5("Drop & DQ", className="mb-2"),
                                html.P(
                                    "Déposez vos datasets et associez-les à des règles de qualité. "
                                    "Interface partagée avec les data providers.",
                                    className="text-muted small mb-0"
                                )
                            ])
                        ], className="d-flex align-items-center mb-3"),
                        dbc.Button([
                            html.I(className="bi bi-upload me-2"),
                            "Accéder au dépôt"
                        ], href="/drop-dq", color="warning", outline=True, size="lg", className="me-2"),
                        dbc.Button([
                            html.I(className="bi bi-broadcast me-2"),
                            "Admin Canaux"
                        ], href="/channel-admin", color="primary", outline=True, size="lg")
                    ])
                ])
            ], className="shadow-sm hover-shadow",
               style={"transition": "all 0.3s ease"}), md=8),
            
            dbc.Col(dbc.Card([
                dbc.CardBody([
                    html.H6([
                        html.I(className="bi bi-info-circle me-2"),
                        "Ressources"
                    ], className="mb-3"),
                    html.Ul([
                        html.Li([
                            html.A("Documentation", href="#", className="text-decoration-none"),
                            html.Br(),
                            html.Small("Guide d'utilisation complet", className="text-muted")
                        ], className="mb-2"),
                        html.Li([
                            html.A("Support", href="#", className="text-decoration-none"),
                            html.Br(),
                            html.Small("Aide et assistance technique", className="text-muted")
                        ], className="mb-2"),
                        html.Li([
                            html.A("API Reference", href="#", className="text-decoration-none"),
                            html.Br(),
                            html.Small("Documentation API", className="text-muted")
                        ])
                    ], className="list-unstyled mb-0")
                ])
            ], className="shadow-sm h-100", 
               style={"backgroundColor": "#f8f9fa"}), md=4)
        ], className="g-4"),
        
        # Footer avec statistiques
        dbc.Row([
            dbc.Col(html.Hr(className="my-4"), width=12)
        ]),
        
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.Small([
                        html.I(className="bi bi-shield-check text-success me-2"),
                        "Plateforme certifiée pour la gestion de la qualité des données"
                    ], className="text-muted")
                ], className="text-center")
            ], width=12)
        ])
        
    ], fluid=True, className="py-4",
       style={"maxWidth": "1400px"})
