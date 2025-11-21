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
                "Help - STDA Portal"
            ])),
            dbc.ModalBody([
                dbc.Accordion([
                    dbc.AccordionItem([
                        html.P("The STDA Portal is a data quality (DQ) management and execution system for your datasets."),
                        html.P("It allows you to:"),
                        html.Ul([
                            html.Li("Create DQ configurations with the Builder"),
                            html.Li("Execute quality checks on your datasets"),
                            html.Li("Manage data deposit channels"),
                            html.Li("Visualize results in dashboards")
                        ])
                    ], title="📖 What is STDA Portal?"),
                    
                    dbc.AccordionItem([
                        html.P("The inventory is the central catalog of all your datasets."),
                        html.P("Structure:"),
                        html.Ul([
                            html.Li(html.Strong("Stream:")),
                            html.Span(" Highest organizational level (e.g., A, B, C)", className="ms-2"),
                            html.Li(html.Strong("Project:")),
                            html.Span(" Business project or domain (e.g., P1, P2)", className="ms-2"),
                            html.Li(html.Strong("Zone:")),
                            html.Span(" Processing zone (raw, cleaned, aggregated)", className="ms-2"),
                            html.Li(html.Strong("Dataset:")),
                            html.Span(" Data file with a unique alias", className="ms-2")
                        ]),
                        html.P("The inventory is located at ", className="mt-3"),
                        html.Code("config/inventory.yaml", className="text-primary")
                    ], title="📦 Data Inventory"),
                    
                    dbc.AccordionItem([
                        html.P("The DQ Builder is the tool for creating quality control configurations."),
                        html.H6("Steps:"),
                        html.Ol([
                            html.Li([html.Strong("Datasets:"), " Select the data to check"]),
                            html.Li([html.Strong("Metrics:"), " Define calculations (null rates, averages, etc.)"]),
                            html.Li([html.Strong("Tests:"), " Create validations (thresholds, comparisons, etc.)"]),
                            html.Li([html.Strong("Scripts:"), " Add custom checks (optional)"]),
                            html.Li([html.Strong("Publication:"), " Save and execute your DQ"])
                        ]),
                        html.P("Access: Main menu → DQ Editor → Builder", className="mt-3 text-muted")
                    ], title="🔨 DQ Builder"),
                    
                    dbc.AccordionItem([
                        html.P("Drop channels allow users to submit files for validation."),
                        html.H6("How it works:"),
                        html.Ol([
                            html.Li("A channel is created with an associated DQ configuration"),
                            html.Li("Users deposit their files through the interface"),
                            html.Li("The system automatically runs DQ checks"),
                            html.Li("A comprehensive report is generated (Excel + investigations)")
                        ]),
                        html.P("Use cases:", className="mt-3"),
                        html.Ul([
                            html.Li("Monthly file validation"),
                            html.Li("Quality control before integration"),
                            html.Li("Automated audit of external data")
                        ]),
                        html.H6("Channel types:", className="mt-3"),
                        html.Ul([
                            html.Li([
                                html.Strong("Inbound (to STDA) ⬇:"),
                                " External teams deposit their data into STDA. Example: Finance submits monthly sales."
                            ]),
                            html.Li([
                                html.Strong("Outbound (from STDA) ⬆:"),
                                " STDA sends data to teams. Example: Automatic export to BI."
                            ])
                        ]),
                        html.P("Access: Main menu → Check & Drop", className="mt-3 text-muted")
                    ], title="📥 Drop Channels"),
                    
                    dbc.AccordionItem([
                        html.P("The DQ Runner allows manual execution of existing DQ configurations."),
                        html.H6("Difference with Builder:"),
                        html.Ul([
                            html.Li([html.Strong("Builder:"), " Create and configure DQs"]),
                            html.Li([html.Strong("Runner:"), " Execute already configured DQs"])
                        ]),
                        html.H6("Execution options:", className="mt-3"),
                        html.Ul([
                            html.Li([html.Strong("Investigation:"), " Generates samples of problematic data"]),
                            html.Li([html.Strong("Verbose:"), " Displays more details in logs"])
                        ]),
                        html.H6("Export:", className="mt-3"),
                        html.P("Results are exported in a ZIP file containing:"),
                        html.Ul([
                            html.Li("Excel file with metrics and tests"),
                            html.Li("Investigation report (text)"),
                            html.Li("Problematic data samples (CSV)")
                        ]),
                        html.P("Access: Main menu → DQ Editor → Runner", className="mt-3 text-muted")
                    ], title="▶️ DQ Runner"),
                    
                    dbc.AccordionItem([
                        html.H6("Metrics"),
                        html.P("Metrics calculate values on your data:"),
                        html.Ul([
                            html.Li("Missing value rates"),
                            html.Li("Averages, sums, counts"),
                            html.Li("Custom aggregations")
                        ]),
                        html.H6("Tests", className="mt-3"),
                        html.P("Tests validate that metrics meet criteria:"),
                        html.Ul([
                            html.Li("Min/max thresholds"),
                            html.Li("Cross-dataset comparisons"),
                            html.Li("Outlier detection")
                        ]),
                        html.H6("Scripts", className="mt-3"),
                        html.P("Scripts allow 100% custom Python checks."),
                        html.P("Full documentation: ", className="mt-3"),
                        html.Code("docs/SCRIPTS_DQ_GUIDE.md", className="text-primary")
                    ], title="🔧 Metrics, Tests and Scripts")
                ], start_collapsed=True)
            ]),
            dbc.ModalFooter(
                dbc.Button("Close", id="help-modal-close", color="secondary")
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
