"""
Page d'administration des canaux de dépôt

Permet aux administrateurs de:
- Créer/éditer/supprimer des canaux
- Définir les fichiers attendus
- Associer les configurations DQ
- Configurer les notifications email
"""

from dash import html, dcc
import dash_bootstrap_components as dbc


def channel_admin_page():
    """Page d'administration des canaux"""
    
    return dbc.Container([
        # Intervalle de rafraîchissement
        dcc.Interval(id='interval-refresh-channels', interval=30000, n_intervals=0),
        
        # Toast container
        html.Div(id="toast-container", style={
            "position": "fixed",
            "top": "20px",
            "right": "20px",
            "zIndex": 9999,
            "minWidth": "300px"
        }),
        
        # En-tête
        dbc.Row([
            dbc.Col([
                html.H2([
                    html.I(className="bi bi-broadcast me-3"),
                    "Administration des Canaux de Dépôt"
                ], className="mb-3"),
                html.P(
                    "Créez et configurez des canaux pour recevoir les données des équipes externes. "
                    "Définissez les fichiers attendus, associez les contrôles qualité et paramétrez les notifications.",
                    className="text-muted mb-4"
                ),
                html.Hr()
            ], width=12)
        ]),
        
        # Barre d'actions
        dbc.Row([
            dbc.Col([
                dbc.Button([
                    html.I(className="bi bi-plus-circle me-2"),
                    "Nouveau Canal"
                ], id="btn-new-channel", color="primary", size="lg"),
                dbc.Button([
                    html.I(className="bi bi-arrow-clockwise me-2"),
                    "Actualiser"
                ], id="btn-refresh-channels", color="secondary", size="lg", 
                className="ms-2")
            ], className="mb-4")
        ]),
        
        # Liste des canaux
        dbc.Row([
            dbc.Col([
                html.Div(id="channels-list-container")
            ], width=12)
        ]),
        
        # Modal pour créer/éditer un canal
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle(id="channel-modal-title")),
            dbc.ModalBody([
                # Store pour l'édition
                dcc.Store(id="channel-edit-store"),
                
                # Formulaire
                html.Div([
                    # Informations générales
                    html.H5("Informations Générales", className="mb-3"),
                    
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Identifiant du canal *"),
                            dbc.Input(
                                id="channel-id-input",
                                placeholder="ex: team_finance_monthly",
                                type="text",
                                className="mb-3"
                            )
                        ], md=6),
                        dbc.Col([
                            dbc.Label("Nom du canal *"),
                            dbc.Input(
                                id="channel-name-input",
                                placeholder="ex: Dépôt Finance Mensuel",
                                type="text",
                                className="mb-3"
                            )
                        ], md=6)
                    ]),
                    
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Équipe *"),
                            dbc.Input(
                                id="channel-team-input",
                                placeholder="ex: Finance",
                                type="text",
                                className="mb-3"
                            )
                        ], md=6),
                        dbc.Col([
                            dbc.Label("Direction *"),
                            dcc.Dropdown(
                                id="channel-direction-dropdown",
                                options=[
                                    {"label": "⬇ Entrant (vers STDA)", "value": "incoming"},
                                    {"label": "⬆ Sortant (depuis STDA)", "value": "outgoing"}
                                ],
                                value="incoming",
                                placeholder="Sélectionnez la direction...",
                                clearable=False,
                                className="mb-3"
                            )
                        ], md=6)
                    ]),
                    
                    # Contexte Inventory (stream/project/zone)
                    html.H6("Contexte Inventory", className="mt-3 mb-2"),
                    html.P("Définissez le contexte inventory pour charger les DQ appropriés.", 
                          className="text-muted small"),
                    
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Stream (optionnel)"),
                            dcc.Dropdown(
                                id="channel-stream-dropdown",
                                placeholder="Sélectionnez un stream...",
                                clearable=True,
                                className="mb-3"
                            )
                        ], md=4),
                        dbc.Col([
                            dbc.Label("Project *"),
                            dcc.Dropdown(
                                id="channel-project-dropdown",
                                placeholder="Sélectionnez un projet...",
                                clearable=False,
                                className="mb-3"
                            )
                        ], md=4),
                        dbc.Col([
                            dbc.Label("Zone *"),
                            dcc.Dropdown(
                                id="channel-zone-dropdown",
                                placeholder="Sélectionnez une zone...",
                                clearable=False,
                                className="mb-3"
                            )
                        ], md=4)
                    ]),
                    
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Statut"),
                            dbc.Checklist(
                                id="channel-active-check",
                                options=[{"label": " Canal actif", "value": "active"}],
                                value=["active"],
                                className="mb-3"
                            )
                        ], md=6)
                    ]),
                    
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Description"),
                            dbc.Textarea(
                                id="channel-description-input",
                                placeholder="Description du canal...",
                                className="mb-3",
                                style={"minHeight": "80px"}
                            )
                        ])
                    ]),
                    
                    html.Hr(className="my-4"),
                    
                    # Fichiers attendus
                    html.H5("Fichiers Attendus", className="mb-3"),
                    html.P("Définissez les fichiers que l'équipe doit fournir.", 
                          className="text-muted small"),
                    
                    html.Div(id="file-specs-container", className="mb-3"),
                    
                    dbc.Button([
                        html.I(className="bi bi-plus me-2"),
                        "Ajouter un fichier"
                    ], id="btn-add-file-spec", color="secondary", outline=True, 
                    size="sm", className="mb-4"),
                    
                    html.Hr(className="my-4"),
                    
                    # Permissions d'accès
                    html.H5("Permissions d'Accès", className="mb-3"),
                    html.P("Contrôlez qui peut voir et utiliser ce canal.", 
                          className="text-muted small"),
                    
                    dbc.Row([
                        dbc.Col([
                            dbc.Checklist(
                                id="channel-public-check",
                                options=[{"label": " Canal public (accessible à tous)", "value": "public"}],
                                value=["public"],
                                className="mb-3"
                            )
                        ])
                    ]),
                    
                    html.Div([
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Utilisateurs autorisés (emails séparés par des virgules)"),
                                dbc.Textarea(
                                    id="channel-allowed-users-input",
                                    placeholder="user1@example.com, user2@example.com",
                                    className="mb-3",
                                    style={"minHeight": "80px"}
                                ),
                                html.Small("Ces utilisateurs pourront voir et utiliser le canal même s'il n'est pas public.", 
                                          className="text-muted")
                            ], md=6),
                            dbc.Col([
                                dbc.Label("Groupes autorisés (séparés par des virgules)"),
                                dbc.Textarea(
                                    id="channel-allowed-groups-input",
                                    placeholder="Finance, Marketing, RH",
                                    className="mb-3",
                                    style={"minHeight": "80px"}
                                ),
                                html.Small("Les membres de ces groupes pourront voir et utiliser le canal.", 
                                          className="text-muted")
                            ], md=6)
                        ])
                    ], id="permissions-detail-container"),
                    
                    html.Hr(className="my-4"),
                    
                    # Configurations DQ
                    html.H5("Configurations DQ", className="mb-3"),
                    html.P("Sélectionnez les contrôles qualité à exécuter.", 
                          className="text-muted small"),
                    
                    dcc.Dropdown(
                        id="channel-dq-configs-dropdown",
                        multi=True,
                        placeholder="Sélectionnez les configs DQ...",
                        className="mb-4"
                    ),
                    
                    html.Hr(className="my-4"),
                    
                    # Configuration email
                    html.H5("Notifications Email", className="mb-3"),
                    
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Emails de l'équipe (séparés par des virgules)"),
                            dbc.Textarea(
                                id="channel-team-emails-input",
                                placeholder="email1@example.com, email2@example.com",
                                className="mb-3",
                                style={"minHeight": "60px"}
                            )
                        ], md=6),
                        dbc.Col([
                            dbc.Label("Emails des admins (notifications succès)"),
                            dbc.Textarea(
                                id="channel-admin-emails-input",
                                placeholder="admin1@example.com, admin2@example.com",
                                className="mb-3",
                                style={"minHeight": "60px"}
                            )
                        ], md=6)
                    ]),
                    
                    dbc.Accordion([
                        dbc.AccordionItem([
                            dbc.Label("Sujet (succès)"),
                            dbc.Input(
                                id="channel-success-subject-input",
                                placeholder="✅ Dépôt de données validé - {channel_name}",
                                className="mb-3"
                            ),
                            dbc.Label("Corps du message (succès)"),
                            dbc.Textarea(
                                id="channel-success-body-input",
                                placeholder="Template du message...",
                                style={"minHeight": "150px"},
                                className="mb-3"
                            ),
                            html.Small("Variables disponibles: {channel_name}, {submission_date}, "
                                     "{file_count}, {dq_total}, {dq_passed}", 
                                     className="text-muted")
                        ], title="Templates Email Succès"),
                        
                        dbc.AccordionItem([
                            dbc.Label("Sujet (échec)"),
                            dbc.Input(
                                id="channel-failure-subject-input",
                                placeholder="⚠️ Dépôt de données - Anomalies détectées",
                                className="mb-3"
                            ),
                            dbc.Label("Corps du message (échec)"),
                            dbc.Textarea(
                                id="channel-failure-body-input",
                                placeholder="Template du message...",
                                style={"minHeight": "150px"},
                                className="mb-3"
                            ),
                            html.Small("Variables disponibles: {channel_name}, {submission_date}, "
                                     "{file_count}, {dq_total}, {dq_passed}, {dq_failed}", 
                                     className="text-muted")
                        ], title="Templates Email Échec")
                    ], start_collapsed=True, className="mb-4")
                ])
            ]),
            dbc.ModalFooter([
                dbc.Button("Annuler", id="btn-cancel-channel", color="secondary"),
                dbc.Button("Enregistrer", id="btn-save-channel", color="primary")
            ])
        ], id="channel-modal", size="xl", scrollable=True),
        
        # Modal pour ajouter un fichier
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Ajouter un fichier attendu")),
            dbc.ModalBody([
                dcc.Store(id="file-spec-index-store"),
                
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Identifiant *"),
                        dbc.Input(
                            id="file-spec-id-input",
                            placeholder="ex: sales_data",
                            className="mb-3"
                        )
                    ], md=6),
                    dbc.Col([
                        dbc.Label("Nom *"),
                        dbc.Input(
                            id="file-spec-name-input",
                            placeholder="ex: Données de ventes",
                            className="mb-3"
                        )
                    ], md=6)
                ]),
                
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Format *"),
                        dcc.Dropdown(
                            id="file-spec-format-dropdown",
                            options=[
                                {"label": "CSV", "value": "csv"},
                                {"label": "Excel (.xlsx)", "value": "xlsx"},
                                {"label": "Parquet", "value": "parquet"},
                                {"label": "JSON", "value": "json"}
                            ],
                            value="csv",
                            className="mb-3"
                        )
                    ], md=6),
                    dbc.Col([
                        dbc.Label("Obligatoire"),
                        dbc.Checklist(
                            id="file-spec-required-check",
                            options=[{"label": " Fichier requis", "value": "required"}],
                            value=["required"],
                            className="mb-3"
                        )
                    ], md=6)
                ]),
                
                dbc.Label("Description"),
                dbc.Textarea(
                    id="file-spec-description-input",
                    placeholder="Description du fichier...",
                    className="mb-3",
                    style={"minHeight": "60px"}
                ),
                
                dbc.Label("Colonnes attendues (optionnel, séparées par des virgules)"),
                dbc.Input(
                    id="file-spec-columns-input",
                    placeholder="date, amount, product_id",
                    className="mb-3"
                )
            ]),
            dbc.ModalFooter([
                dbc.Button("Annuler", id="btn-cancel-file-spec", color="secondary"),
                dbc.Button("Ajouter", id="btn-add-file-spec-confirm", color="primary")
            ])
        ], id="file-spec-modal", size="lg"),
        
        # Store pour les file specs
        dcc.Store(id="file-specs-store", data=[]),
        
        # Alert pour les messages
        html.Div(id="channel-alert-container", className="mt-3")
        
    ], fluid=True, className="py-4")


def _render_channel_card(channel_data: dict) -> dbc.Card:
    """Rend une carte pour un canal"""
    
    stats = channel_data.get('stats', {})
    
    return dbc.Card([
        dbc.CardHeader([
            dbc.Row([
                dbc.Col([
                    html.H5([
                        html.I(className="bi bi-broadcast-pin me-2"),
                        channel_data['name']
                    ], className="mb-0")
                ], width=8),
                dbc.Col([
                    dbc.Badge(
                        "Actif" if channel_data.get('active', True) else "Inactif",
                        color="success" if channel_data.get('active', True) else "secondary",
                        className="me-2"
                    ),
                    dbc.Button([
                        html.I(className="bi bi-pencil")
                    ], id={"type": "btn-edit-channel", "id": channel_data['channel_id']},
                    color="primary", size="sm", className="me-1"),
                    dbc.Button([
                        html.I(className="bi bi-trash")
                    ], id={"type": "btn-delete-channel", "id": channel_data['channel_id']},
                    color="danger", size="sm")
                ], width=4, className="text-end")
            ])
        ]),
        dbc.CardBody([
            html.Div([
                html.Strong("Équipe: "), channel_data.get('team_name', 'N/A')
            ], className="mb-2"),
            html.Div([
                html.Strong("Description: "), channel_data.get('description', 'Aucune description')
            ], className="mb-3"),
            
            html.Hr(),
            
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.Small("Fichiers attendus", className="text-muted d-block"),
                        html.H6(str(len(channel_data.get('file_specifications', []))))
                    ])
                ], md=3),
                dbc.Col([
                    html.Div([
                        html.Small("Configs DQ", className="text-muted d-block"),
                        html.H6(str(len(channel_data.get('dq_configs', []))))
                    ])
                ], md=3),
                dbc.Col([
                    html.Div([
                        html.Small("Soumissions totales", className="text-muted d-block"),
                        html.H6(str(stats.get('total_submissions', 0)))
                    ])
                ], md=3),
                dbc.Col([
                    html.Div([
                        html.Small("Taux de succès", className="text-muted d-block"),
                        html.H6(f"{stats.get('success_rate', 0):.1f}%")
                    ])
                ], md=3)
            ])
        ])
    ], className="mb-3 shadow-sm")
