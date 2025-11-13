from dash import html, dcc
import dash_bootstrap_components as dbc
from src.utils_dq.dq_scanner import get_dq_scanner


def dq_runner_page():
    """Page d'exécution des définitions DQ"""
    
    # Scanner les définitions DQ disponibles
    scanner = get_dq_scanner()
    definitions = scanner.scan_all()
    stats = scanner.get_summary_stats(definitions)
    
    # Options pour le dropdown
    dq_options = [{"label": f"{dq.id} - {dq.label}", "value": dq.id} for dq in definitions]
    
    return dbc.Container([
        # Store pour conserver les résultats d'exécution
        dcc.Store(id="dq-runner-results-store", data=None),
        
        # Store pour déclencher l'export
        dcc.Store(id="dq-runner-export-trigger", data=0),
        
        # Download component pour l'export
        dcc.Download(id="dq-runner-download"),
        
        # Modal pour afficher les détails des tests
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Détails du test")),
            dbc.ModalBody(id="test-detail-modal-body"),
            dbc.ModalFooter(
                dbc.Button("Fermer", id="test-detail-modal-close", className="ms-auto")
            )
        ], id="test-detail-modal", size="lg", is_open=False),
        
        # Header
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.I(className="bi bi-play-circle-fill", style={"fontSize": "2.5rem", "color": "#198754"}),
                ], className="text-center mb-3"),
                html.H2("DQ Runner", className="text-center mb-2"),
                html.P("Exécution et visualisation des contrôles qualité", 
                       className="text-center text-muted mb-4"),
            ], width=12)
        ], className="mt-4"),
        
        # Sélection de la DQ à exécuter
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="bi bi-gear-fill me-2"),
                        html.Strong("Configuration de l'exécution")
                    ], className="bg-light"),
                    dbc.CardBody([
                        # Sélection DQ
                        dbc.Row([
                            dbc.Col([
                                html.Label([
                                    html.I(className="bi bi-file-earmark-check me-2"),
                                    "Définition DQ à exécuter"
                                ], className="fw-bold mb-2"),
                                dbc.Select(
                                    id="dq-runner-select",
                                    options=dq_options,
                                    placeholder="Sélectionner une définition DQ...",
                                    value=dq_options[0]["value"] if dq_options else None
                                )
                            ], md=8),
                            dbc.Col([
                                html.Label("Options", className="fw-bold mb-2"),
                                dbc.Checklist(
                                    id="dq-runner-options",
                                    options=[
                                        {"label": " Investigation auto", "value": "investigate"},
                                        {"label": " Mode verbose", "value": "verbose"}
                                    ],
                                    value=["investigate"],
                                    inline=True
                                )
                            ], md=4)
                        ], className="mb-3"),
                        
                        # Informations sur la DQ sélectionnée
                        html.Div(id="dq-runner-info", className="mb-3"),
                        
                        # Bouton d'exécution
                        dbc.Row([
                            dbc.Col([
                                dbc.Button([
                                    html.I(className="bi bi-play-fill me-2"),
                                    "Exécuter la DQ"
                                ], id="dq-runner-execute-btn", color="success", size="lg", className="w-100")
                            ], md=6),
                            dbc.Col([
                                dbc.Button([
                                    html.I(className="bi bi-arrow-clockwise me-2"),
                                    "Réinitialiser"
                                ], id="dq-runner-reset-btn", color="secondary", size="lg", outline=True, className="w-100")
                            ], md=6)
                        ])
                    ])
                ], className="shadow-sm mb-4")
            ], width=12)
        ]),
        
        # Bouton Export (visible dès le début pour test)
        dbc.Row([
            dbc.Col([
                dbc.Button([
                    html.I(className="bi bi-download me-2"),
                    "Exporter les résultats"
                ], id="dq-runner-export-btn", color="primary", size="sm", className="mb-3")
            ])
        ]),
        
        # Zone de résultats
        dbc.Row([
            dbc.Col([
                html.Div(id="dq-runner-results")
            ], width=12)
        ]),
        
        # Store pour les données
        dcc.Store(id="dq-runner-data"),
        dcc.Interval(id="dq-runner-interval", interval=1000, disabled=True),
        
        # Navigation
        dbc.Row([
            dbc.Col([
                html.Hr(className="my-4"),
                dbc.ButtonGroup([
                    dbc.Button([
                        html.I(className="bi bi-journal-text me-2"),
                        "Inventaire DQ"
                    ], href="/dq-inventory", color="primary", outline=True),
                    dbc.Button([
                        html.I(className="bi bi-house me-2"),
                        "Accueil"
                    ], href="/", color="secondary", outline=True)
                ])
            ], width=12)
        ])
    ], fluid=True, className="mb-5")
