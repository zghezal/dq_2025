# Composant Navbar

from dash import html
import dash_bootstrap_components as dbc


def navbar():
    """Barre de navigation principale"""
    return html.Div([
        dbc.Navbar(
            dbc.Container([
                # Logo et titre STDA
                html.Div([
                    html.A([
                        html.I(className="bi bi-database-fill-gear", style={
                            "fontSize": "2rem", 
                            "color": "#0d6efd",
                            "marginRight": "12px"
                        }),
                        html.Span("STDA", style={
                            "fontSize": "1.5rem",
                            "fontWeight": "bold",
                            "color": "#0d6efd",
                            "marginRight": "8px"
                        }),
                        html.Span("Portal", style={
                            "fontSize": "1.2rem",
                            "color": "#6c757d"
                        })
                    ], href="/", style={
                        "textDecoration": "none",
                        "display": "flex", 
                        "alignItems": "center"
                    })
                ], className="d-flex align-items-center"),
                
                # Navigation et boutons alignés
                dbc.Nav([
                    dbc.NavItem(dbc.NavLink("Home", href="/", active="exact", className="me-3")),
                    dbc.NavItem(
                        dbc.Button(
                            [html.I(className="bi bi-person-circle me-2"), "Profile"],
                            id="profile-button",
                            color="primary",
                            size="sm",
                            className="me-2",
                            outline=True
                        )
                    ),
                    dbc.NavItem(
                        dbc.Button(
                            [html.I(className="bi bi-question-circle me-2"), "Help"],
                            id="help-button",
                            color="info",
                            size="sm",
                            outline=True
                        )
                    )
                ], className="ms-auto d-flex align-items-center", navbar=True),
                html.Div(id="crumb", className="ms-4 small text-muted")
            ], fluid=True, className="d-flex align-items-center"),
            color="light", dark=False, className="mb-4", style={"boxShadow": "0 2px 4px rgba(0,0,0,0.1)"}
        ),
        
        # Modal Profile
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle([
                html.I(className="bi bi-person-circle me-2"),
                "Profil Utilisateur"
            ])),
            dbc.ModalBody([
                dbc.Row([
                    dbc.Col([
                        html.Div([
                            html.I(className="bi bi-person-circle", style={"fontSize": "5rem", "color": "#0d6efd"})
                        ], className="text-center mb-3")
                    ], width=12)
                ]),
                dbc.Row([
                    dbc.Col([
                        html.Div([
                            html.Strong("Nom:"),
                            html.Span(" Développeur STDA", className="ms-2")
                        ], className="mb-2"),
                        html.Div([
                            html.Strong("Email:"),
                            html.Span(" dev@stda.local", className="ms-2")
                        ], className="mb-2"),
                        html.Div([
                            html.Strong("Rôle:"),
                            dbc.Badge("Administrateur", color="success", className="ms-2")
                        ], className="mb-2"),
                        html.Div([
                            html.Strong("Environnement:"),
                            dbc.Badge("DEV", color="warning", className="ms-2")
                        ], className="mb-3"),
                        html.Hr(),
                        html.H6("Permissions", className="mt-3"),
                        html.Ul([
                            html.Li("Création de DQ"),
                            html.Li("Exécution de DQ"),
                            html.Li("Gestion des canaux de dépôt"),
                            html.Li("Administration complète")
                        ], className="small")
                    ])
                ])
            ]),
            dbc.ModalFooter(
                dbc.Button("Fermer", id="profile-modal-close", color="secondary")
            )
        ], id="profile-modal", size="lg", is_open=False),
        
        # Modal Help
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle([
                html.I(className="bi bi-question-circle me-2"),
                "Aide - Portal STDA"
            ])),
            dbc.ModalBody([
                dbc.Accordion([
                    dbc.AccordionItem([
                        html.P("Le Portal STDA est un système de gestion et d'exécution de contrôles qualité (DQ) sur vos données."),
                        html.P("Il vous permet de:"),
                        html.Ul([
                            html.Li("Créer des configurations DQ avec le Builder"),
                            html.Li("Exécuter des contrôles sur vos datasets"),
                            html.Li("Gérer les canaux de dépôt de données"),
                            html.Li("Visualiser les résultats dans des tableaux de bord")
                        ])
                    ], title="📖 Qu'est-ce que le Portal STDA?"),
                    
                    dbc.AccordionItem([
                        html.P("L'inventaire est le catalogue central de tous vos datasets."),
                        html.P("Structure:"),
                        html.Ul([
                            html.Li(html.Strong("Stream:")),
                            html.Span(" Niveau organisationnel le plus haut (ex: A, B, C)", className="ms-2"),
                            html.Li(html.Strong("Project:")),
                            html.Span(" Projet ou domaine métier (ex: P1, P2)", className="ms-2"),
                            html.Li(html.Strong("Zone:")),
                            html.Span(" Zone de traitement (raw, cleaned, aggregated)", className="ms-2"),
                            html.Li(html.Strong("Dataset:")),
                            html.Span(" Fichier de données avec un alias unique", className="ms-2")
                        ]),
                        html.P("L'inventaire se trouve dans ", className="mt-3"),
                        html.Code("config/inventory.yaml", className="text-primary")
                    ], title="📦 Inventaire des Données"),
                    
                    dbc.AccordionItem([
                        html.P("Le DQ Builder est l'outil de création de configurations de contrôle qualité."),
                        html.H6("Étapes:"),
                        html.Ol([
                            html.Li([html.Strong("Datasets:"), " Sélectionnez les données à contrôler"]),
                            html.Li([html.Strong("Métriques:"), " Définissez les calculs (taux de nulls, moyennes, etc.)"]),
                            html.Li([html.Strong("Tests:"), " Créez les validations (seuils, comparaisons, etc.)"]),
                            html.Li([html.Strong("Scripts:"), " Ajoutez des contrôles personnalisés (optionnel)"]),
                            html.Li([html.Strong("Publication:"), " Sauvegardez et exécutez votre DQ"])
                        ]),
                        html.P("Accès: Menu principal → DQ Editor → Builder", className="mt-3 text-muted")
                    ], title="🔨 DQ Builder"),
                    
                    dbc.AccordionItem([
                        html.P("Les canaux de dépôt permettent aux utilisateurs de soumettre des fichiers pour validation."),
                        html.H6("Fonctionnement:"),
                        html.Ol([
                            html.Li("Un canal est créé avec une configuration DQ associée"),
                            html.Li("Les utilisateurs déposent leurs fichiers via l'interface"),
                            html.Li("Le système exécute automatiquement les contrôles DQ"),
                            html.Li("Un rapport complet est généré (Excel + investigations)")
                        ]),
                        html.P("Cas d'usage:", className="mt-3"),
                        html.Ul([
                            html.Li("Validation des fichiers mensuels"),
                            html.Li("Contrôle qualité avant intégration"),
                            html.Li("Audit automatique des données externes")
                        ]),
                        html.H6("Types de canaux:", className="mt-3"),
                        html.Ul([
                            html.Li([
                                html.Strong("Entrant (vers STDA) ⬇:"),
                                " Les équipes externes déposent leurs données dans STDA. Exemple: Finance soumet les ventes mensuelles."
                            ]),
                            html.Li([
                                html.Strong("Sortant (depuis STDA) ⬆:"),
                                " STDA envoie des données aux équipes. Exemple: Export automatique vers le BI."
                            ])
                        ]),
                        html.P("Accès: Menu principal → Check & Drop", className="mt-3 text-muted")
                    ], title="📥 Canaux de Dépôt"),
                    
                    dbc.AccordionItem([
                        html.P("Le DQ Runner permet d'exécuter manuellement des configurations DQ existantes."),
                        html.H6("Différence avec le Builder:"),
                        html.Ul([
                            html.Li([html.Strong("Builder:"), " Créer et configurer des DQ"]),
                            html.Li([html.Strong("Runner:"), " Exécuter des DQ déjà configurées"])
                        ]),
                        html.H6("Options d'exécution:", className="mt-3"),
                        html.Ul([
                            html.Li([html.Strong("Investigation:"), " Génère des échantillons de données problématiques"]),
                            html.Li([html.Strong("Verbose:"), " Affiche plus de détails dans les logs"])
                        ]),
                        html.H6("Export:", className="mt-3"),
                        html.P("Les résultats sont exportés dans un fichier ZIP contenant:"),
                        html.Ul([
                            html.Li("Fichier Excel avec métriques et tests"),
                            html.Li("Rapport d'investigation (texte)"),
                            html.Li("Échantillons de données problématiques (CSV)")
                        ]),
                        html.P("Accès: Menu principal → DQ Editor → Runner", className="mt-3 text-muted")
                    ], title="▶️ DQ Runner"),
                    
                    dbc.AccordionItem([
                        html.H6("Métriques"),
                        html.P("Les métriques calculent des valeurs sur vos données:"),
                        html.Ul([
                            html.Li("Taux de valeurs manquantes"),
                            html.Li("Moyennes, sommes, comptages"),
                            html.Li("Agrégations personnalisées")
                        ]),
                        html.H6("Tests", className="mt-3"),
                        html.P("Les tests valident que les métriques respectent des critères:"),
                        html.Ul([
                            html.Li("Seuils min/max"),
                            html.Li("Comparaisons entre datasets"),
                            html.Li("Détection d'outliers")
                        ]),
                        html.H6("Scripts", className="mt-3"),
                        html.P("Les scripts permettent des contrôles 100% personnalisés en Python."),
                        html.P("Documentation complète: ", className="mt-3"),
                        html.Code("docs/SCRIPTS_DQ_GUIDE.md", className="text-primary")
                    ], title="🔧 Métriques, Tests et Scripts")
                ], start_collapsed=True)
            ]),
            dbc.ModalFooter(
                dbc.Button("Fermer", id="help-modal-close", color="secondary")
            )
        ], id="help-modal", size="xl", is_open=False, scrollable=True)
    ])


def stepper(active_idx=0):
    """Affiche un stepper pour les étapes du wizard Build"""
    steps = ["1. Datasets", "2. Métriques", "3. Tests", "4. Publication"]
    items = []
    for i, label in enumerate(steps):
        color = "primary" if i == active_idx else "secondary"
        items.append(dbc.Badge(label, color=color, className="me-2 p-2"))
    return html.Div(items, className="mb-3")
