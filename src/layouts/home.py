# Page d'accueil

from dash import html
import dash_bootstrap_components as dbc


def home_page():
    """Page d'accueil Portal STDA avec deux accès distincts"""
    return dbc.Container([
        # Header avec titre principal
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.I(className="bi bi-shield-check", style={"fontSize": "4rem", "color": "#0d6efd"}),
                ], className="text-center mb-3 mt-5"),
                html.H1("Portal STDA", className="text-center mb-2", style={"fontWeight": "700", "color": "#212529"}),
                html.H4("Data Quality Management", className="text-center text-muted mb-4", style={"fontWeight": "300"}),
                html.Hr(style={"width": "200px", "margin": "0 auto", "border": "2px solid #0d6efd"}),
            ], width=12)
        ]),
        
        # Message de bienvenue
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H5("Choisissez votre profil d'accès", className="text-center mb-2 mt-5", style={"fontWeight": "500"}),
                    html.P("Deux environnements distincts pour gérer la qualité de vos données", 
                           className="text-center text-muted", style={"fontSize": "1.1rem"}),
                ], className="mb-4")
            ], width=12)
        ]),
        
        # Cards des deux accès
        dbc.Row([
            # Accès Client
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.Div([
                            html.I(className="bi bi-upload", style={"fontSize": "2.5rem", "color": "#ffc107"}),
                        ], className="text-center mb-2"),
                        html.H4("Accès Client", className="text-center mb-0", style={"fontWeight": "600"}),
                    ], className="bg-light border-bottom-0 pt-4 pb-3"),
                    dbc.CardBody([
                        html.Div([
                            html.H5("Check & Drop", className="text-center mb-3", style={"color": "#ffc107", "fontWeight": "600"}),
                            html.Ul([
                                html.Li("Déposer vos fichiers de données", className="mb-2"),
                                html.Li("Lancer des contrôles qualité automatiques", className="mb-2"),
                                html.Li("Consulter les résultats DQ", className="mb-2"),
                                html.Li("Télécharger les rapports", className="mb-2"),
                            ], className="text-start", style={"fontSize": "0.95rem"}),
                        ], className="mb-4"),
                        html.Div([
                            html.I(className="bi bi-person-circle me-2"),
                            html.Span("Pour les utilisateurs métier", className="text-muted", style={"fontSize": "0.9rem"})
                        ], className="text-center mb-3"),
                        dbc.Button([
                            html.I(className="bi bi-box-arrow-in-right me-2"),
                            "Accéder à Check & Drop"
                        ], id="home-checkdrop-btn", color="warning", size="lg", className="w-100", 
                           style={"fontWeight": "600", "padding": "12px"})
                    ], className="pt-3")
                ], className="shadow-lg border-0 h-100", style={"transition": "transform 0.2s"}),
            ], md=5, className="mb-4"),
            
            # Accès STDA Admin
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.Div([
                            html.I(className="bi bi-gear-fill", style={"fontSize": "2.5rem", "color": "#0d6efd"}),
                        ], className="text-center mb-2"),
                        html.H4("Accès STDA Admin", className="text-center mb-0", style={"fontWeight": "600"}),
                    ], className="bg-light border-bottom-0 pt-4 pb-3"),
                    dbc.CardBody([
                        html.Div([
                            html.H5("DQ Editor", className="text-center mb-3", style={"color": "#0d6efd", "fontWeight": "600"}),
                            html.Ul([
                                html.Li("Gérer l'inventaire des datasets", className="mb-2"),
                                html.Li("Construire des définitions DQ", className="mb-2"),
                                html.Li("Configurer les contrôles qualité", className="mb-2"),
                                html.Li("Administrer les canaux de dépôt", className="mb-2"),
                            ], className="text-start", style={"fontSize": "0.95rem"}),
                        ], className="mb-4"),
                        html.Div([
                            html.I(className="bi bi-shield-lock-fill me-2"),
                            html.Span("Pour les administrateurs DQ", className="text-muted", style={"fontSize": "0.9rem"})
                        ], className="text-center mb-3"),
                        dbc.Button([
                            html.I(className="bi bi-tools me-2"),
                            "Accéder au DQ Editor"
                        ], id="home-dqeditor-btn", color="primary", size="lg", className="w-100",
                           style={"fontWeight": "600", "padding": "12px"})
                    ], className="pt-3")
                ], className="shadow-lg border-0 h-100", style={"transition": "transform 0.2s"}),
            ], md=5, className="mb-4"),
        ], justify="center", className="g-4 mb-5"),
        
        # Footer avec info
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.I(className="bi bi-info-circle me-2", style={"color": "#6c757d"}),
                    html.Small("Besoin d'aide ? Contactez l'équipe STDA", className="text-muted")
                ], className="text-center mb-5")
            ], width=12)
        ])
    ], fluid=True, className="bg-light min-vh-100")
