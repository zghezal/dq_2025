"""
Page de dépôt pour les équipes externes

Permet aux équipes externes de:
- Sélectionner leur canal
- Voir les fichiers attendus
- Fournir les liens vers leurs fichiers
- Soumettre le dépôt
"""

from dash import html, dcc
import dash_bootstrap_components as dbc


def channel_drop_page():
    """Page de dépôt pour équipes externes"""
    
    return dbc.Container([
        # En-tête
        dbc.Row([
            dbc.Col([
                html.H2([
                    html.I(className="bi bi-cloud-upload me-3"),
                    "Dépôt de Données"
                ], className="mb-3"),
                html.P(
                    "Bienvenue! Sélectionnez votre canal de dépôt et fournissez vos fichiers. "
                    "Un contrôle qualité sera automatiquement effectué et vous recevrez un rapport par email.",
                    className="text-muted mb-4"
                ),
                html.Hr()
            ], width=12)
        ]),
        
        # Sélecteur d'utilisateur (DEMO uniquement)
        dbc.Row([
            dbc.Col([
                dbc.Alert([
                    html.Div([
                        html.I(className="bi bi-person-circle me-2"),
                        html.Strong("Mode Démonstration - Sélectionnez votre profil utilisateur")
                    ], className="mb-2"),
                    dcc.Dropdown(
                        id="demo-user-selector",
                        placeholder="Choisissez un utilisateur pour voir les canaux autorisés...",
                        className="mb-2"
                    ),
                    html.Small([
                        html.I(className="bi bi-info-circle me-1"),
                        "En production, l'utilisateur serait authentifié automatiquement (SSO, LDAP, etc.)"
                    ], className="text-muted")
                ], color="info", className="mb-4")
            ], width=12)
        ]),
        
        # Stores
        dcc.Store(id="selected-channel-store"),
        dcc.Store(id="file-mappings-store", data=[]),
        dcc.Interval(id='interval-refresh-drop', interval=30000, n_intervals=0),  # Rafraîchir toutes les 30 secondes
        
        # Toast container
        html.Div(id="toast-container-drop", style={
            "position": "fixed",
            "top": "20px",
            "right": "20px",
            "zIndex": 9999,
            "minWidth": "300px"
        }),
        
        # Étape 1: Sélection du canal
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H5([
                            html.I(className="bi bi-1-circle me-2"),
                            "Sélectionnez votre canal"
                        ], className="mb-0")
                    ]),
                    dbc.CardBody([
                        dbc.Label("Canal de dépôt"),
                        dcc.Dropdown(
                            id="drop-channel-dropdown",
                            placeholder="Choisissez votre canal...",
                            className="mb-3"
                        ),
                        html.Div(id="channel-info-display")
                    ])
                ], className="mb-4")
            ], width=12)
        ]),
        
        # Étape 2: Mapping des fichiers
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H5([
                            html.I(className="bi bi-2-circle me-2"),
                            "Fournissez vos fichiers"
                        ], className="mb-0")
                    ]),
                    dbc.CardBody([
                        html.Div(id="file-mapping-container")
                    ])
                ], className="mb-4", id="file-mapping-card", style={"display": "none"})
            ], width=12)
        ]),
        
        # Étape 3: Informations contact
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H5([
                            html.I(className="bi bi-3-circle me-2"),
                            "Informations de contact"
                        ], className="mb-0")
                    ]),
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Votre nom *"),
                                dbc.Input(
                                    id="submitter-name-input",
                                    placeholder="ex: Jean Dupont",
                                    type="text",
                                    className="mb-3"
                                )
                            ], md=6),
                            dbc.Col([
                                dbc.Label("Votre email *"),
                                dbc.Input(
                                    id="submitter-email-input",
                                    placeholder="ex: jean.dupont@example.com",
                                    type="email",
                                    className="mb-3"
                                )
                            ], md=6)
                        ])
                    ])
                ], className="mb-4", id="contact-card", style={"display": "none"})
            ], width=12)
        ]),
        
        # Récapitulatif et soumission
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H5([
                            html.I(className="bi bi-check-circle me-2"),
                            "Récapitulatif"
                        ], className="mb-0")
                    ]),
                    dbc.CardBody([
                        html.Div(id="submission-summary"),
                        
                        html.Hr(className="my-4"),
                        
                        dbc.Alert([
                            html.I(className="bi bi-info-circle me-2"),
                            "En soumettant ces fichiers, vous acceptez qu'ils soient traités et "
                            "qu'un contrôle qualité soit effectué. Vous recevrez un rapport par email."
                        ], color="info", className="mb-3"),
                        
                        dbc.Button([
                            html.I(className="bi bi-send me-2"),
                            "Soumettre le dépôt"
                        ], id="btn-submit-drop", color="primary", size="lg", 
                        className="w-100", disabled=True)
                    ])
                ], className="mb-4", id="summary-card", style={"display": "none"})
            ], width=12)
        ]),
        
        # Confirmation
        dbc.Row([
            dbc.Col([
                html.Div(id="submission-result-container")
            ])
        ]),
        
        # Modal de confirmation
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Dépôt soumis avec succès")),
            dbc.ModalBody([
                html.Div([
                    html.I(className="bi bi-check-circle-fill text-success", 
                          style={"fontSize": "4rem"}),
                ], className="text-center mb-4"),
                html.H5("Votre dépôt a été enregistré", className="text-center mb-3"),
                html.P([
                    "Votre dépôt est en cours de traitement. Vous recevrez un rapport "
                    "de contrôle qualité par email d'ici quelques minutes."
                ], className="text-center text-muted mb-3"),
                html.Div(id="submission-id-display", className="text-center"),
                html.P([
                    html.Strong("Numéro de suivi: "),
                    html.Span(id="tracking-number-display", className="text-primary")
                ], className="text-center")
            ]),
            dbc.ModalFooter([
                dbc.Button("Fermer", id="btn-close-success-modal", color="primary")
            ])
        ], id="success-modal", centered=True),
        
        # Alert pour les erreurs
        html.Div(id="drop-alert-container", className="mt-3")
        
    ], fluid=True, className="py-4", style={"maxWidth": "1200px"})


def _render_file_input_row(file_spec: dict, index: int) -> dbc.Card:
    """Rend une ligne de saisie pour un fichier"""
    
    required_badge = dbc.Badge("Requis", color="danger") if file_spec.get('required', True) else dbc.Badge("Optionnel", color="secondary")
    
    format_badge = dbc.Badge(file_spec.get('format', 'csv').upper(), color="info")
    
    return dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.H6([
                            html.I(className="bi bi-file-earmark me-2"),
                            file_spec.get('name', 'Fichier'),
                            html.Span(" "),
                            required_badge,
                            html.Span(" "),
                            format_badge
                        ], className="mb-2"),
                        html.P(file_spec.get('description', ''), 
                              className="text-muted small mb-0")
                    ])
                ], md=4),
                dbc.Col([
                    dbc.Label("Lien vers le fichier *", className="small"),
                    dbc.Input(
                        id={"type": "file-path-input", "index": index},
                        placeholder="https://... ou /chemin/vers/fichier.csv",
                        type="text",
                        className="mb-2"
                    ),
                    html.Small(
                        f"Colonnes attendues: {', '.join(file_spec.get('expected_columns', []))}" 
                        if file_spec.get('expected_columns') else "",
                        className="text-muted"
                    )
                ], md=6),
                dbc.Col([
                    dbc.Button([
                        html.I(className="bi bi-check-circle")
                    ], id={"type": "btn-validate-file", "index": index},
                    color="success", outline=True, className="mt-4")
                ], md=2, className="text-end")
            ])
        ])
    ], className="mb-2")
