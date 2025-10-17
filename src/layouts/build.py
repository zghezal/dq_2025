# Page Build (wizard de création DQ avec onglets)

from dash import html, dcc
from src.metrics_registry import get_metric_options
import dash_bootstrap_components as dbc


def build_page():
    """Page de construction de configuration DQ (4 onglets)"""
    return dbc.Container([
        html.Div(id="ctx-banner"),
        html.H3("🔧 Configuration DQ Builder", className="mb-3"),
        
        dcc.Store(id="store_datasets", storage_type="session"),
        dcc.Store(id="store_metrics", storage_type="session"),
        dcc.Store(id="store_tests", storage_type="session"),
        dcc.Store(id="store_edit_metric", storage_type="session"),
        dcc.Store(id="inventory-datasets-store", storage_type="session"),

        dbc.Tabs([
            # Onglet 1: Datasets
            dbc.Tab(label="📁 Datasets", tab_id="tab-datasets", children=[
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Datasets & Aliases", className="mb-3"),
                        html.Label("Datasets (depuis ./datasets/*.csv)"),
                        dcc.Dropdown(
                            id="ds-picker",
                            options=[],
                            multi=True,
                            placeholder="Sélectionne des datasets",
                            persistence=True,
                            persistence_type="session"
                        ),
                        html.Div(id="alias-mapper", className="mt-3"),
                        dbc.Button("✅ Enregistrer les datasets", id="save-datasets", color="primary", className="mt-3"),
                        html.Div(id="save-datasets-status", className="text-success mt-2")
                    ])
                ], className="mt-3")
            ]),

            # Onglet 2: Métriques
            dbc.Tab(label="📊 Métriques", tab_id="tab-metrics", children=[
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Configuration des Métriques", className="mb-3"),
                        dbc.Tabs([
                            # Sous-onglet: Créer
                            dbc.Tab(label="➕ Créer", tab_id="tab-metric-create", children=[
                                html.Div(className="mt-3", children=[
                                    html.Div([
                                        html.Label("Type de métrique", className="d-inline me-2"),
                                        dbc.Button("❓", id="open-metric-help", color="info", size="sm", className="mb-1")
                                    ]),
                                    dcc.Dropdown(
                                        id="metric-type",
                                        options=get_metric_options(),
                                        placeholder="Choisir le type",
                                        clearable=False,
                                        persistence=True,
                                        persistence_type="session"
                                    ),
                                    html.Div(id="metric-params", className="mt-3"),
                                    dbc.Button("🔍 Forcer l'aperçu", id="force-metric-preview", color="secondary", className="mt-3 me-2"),
                                    dbc.Button("✅ Ajouter la métrique", id="add-metric", color="primary", className="mt-3"),
                                    html.Div(id="add-metric-status", className="text-success mt-2"),
                                ])
                            ]),
                            # Sous-onglet: Visualiser (Tableau)
                            dbc.Tab(label="📋 Visualiser", tab_id="tab-metric-viz", children=[
                                html.Div(className="mt-3", children=[
                                    html.Div(id="metrics-table-container")
                                ])
                            ]),
                            # Sous-onglet: Liste (format ancien pour compatibilité)
                            dbc.Tab(label="📝 Liste", tab_id="tab-metric-list", children=[
                                html.Div(id="metrics-list", className="mt-3")
                            ]),
                        ], id="metric-tabs", active_tab="tab-metric-create")
                    ])
                ], className="mt-3")
            ]),

            # Onglet 3: Tests
            dbc.Tab(label="✅ Tests", tab_id="tab-tests", children=[
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Configuration des Tests", className="mb-3"),
                        dbc.Tabs([
                            # Sous-onglet: Créer
                            dbc.Tab(label="➕ Créer", tab_id="tab-test-create", children=[
                                html.Div(className="mt-3", children=[
                                    html.Div([
                                        html.Label("Type de test", className="d-inline me-2"),
                                        dbc.Button("❓", id="open-test-help", color="info", size="sm", className="mb-1")
                                    ]),
                                    dcc.Dropdown(
                                        id="test-type",
                                        options=[
                                            {"label": "range", "value": "range"}
                                        ],
                                        placeholder="Choisir le type",
                                        clearable=False,
                                        persistence=True,
                                        persistence_type="session"
                                    ),
                                    html.Div(id="test-params", className="mt-3"),
                                    dbc.Button("✅ Ajouter le test", id="add-test", color="primary", className="mt-3"),
                                    html.Div(id="add-test-status", className="text-success mt-2"),
                                ])
                            ]),
                            # Sous-onglet: Visualiser (Tableau)
                            dbc.Tab(label="📋 Visualiser", tab_id="tab-test-viz", children=[
                                html.Div(className="mt-3", children=[
                                    html.Div(id="tests-table-container")
                                ])
                            ]),
                            # Sous-onglet: Liste (format ancien pour compatibilité)
                            dbc.Tab(label="📝 Liste", tab_id="tab-test-list", children=[
                                html.Div(id="tests-list", className="mt-3")
                            ]),
                        ], id="test-tabs", active_tab="tab-test-create")
                    ])
                ], className="mt-3")
            ]),

            # Onglet 4: Publication
            dbc.Tab(label="🚀 Publication", tab_id="tab-publication", children=[
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Prévisualisation & Publication", className="mb-3"),
                        dbc.Row([
                            dbc.Col([
                                html.Label("Managed Folder ID"),
                                dcc.Input(id="folder-id", type="text", value="dq_params", className="form-control")
                            ], md=4),
                            dbc.Col([
                                html.Label("Nom de la configuration"),
                                dcc.Input(id="cfg-name", type="text", value="default", className="form-control")
                            ], md=4),
                            dbc.Col([
                                html.Label("Format"),
                                dcc.RadioItems(
                                    id="fmt",
                                    options=[
                                        {"label": "JSON", "value": "json"},
                                        {"label": "YAML", "value": "yaml"}
                                    ],
                                    value="yaml",
                                    inline=True
                                )
                            ], md=4)
                        ]),
                        html.Hr(className="my-3"),
                        html.H6("Aperçu de la configuration", className="mb-2"),
                        html.Pre(
                            id="cfg-preview",
                            className="mt-3",
                            style={"background": "#111", "color": "#eee", "padding": "1rem", "whiteSpace": "pre-wrap", "borderRadius": "4px"}
                        ),
                        dbc.Button("✅ Publier", id="publish", color="success", className="mt-3"),
                        dbc.Button("▶️ Run DQ", id="run-dq", color="primary", className="mt-3 ms-2"),
                        html.Div(id="dq-run-results", className="mt-3"),
                        html.Div(id="publish-status", className="text-success mt-2")
                    ])
                ], className="mt-3")
            ]),

        ], id="build-main-tabs", active_tab="tab-datasets"),
        
        dbc.Toast(
            id="toast",
            header="Info",
            is_open=False,
            dismissable=True,
            icon="info",
            style={"position": "fixed", "top": 20, "right": 20, "zIndex": 2000}
        ),
    # Hidden placeholders so pattern-matching callback ids exist for validation
    # Note: include an extra `_placeholder` key so these do NOT match callbacks that
    # expect exactly {'role':'metric-preview'} or {'role':'metric-column','form':'metric'}
    # (placeholders for validation moved to app.validation_layout to avoid duplicate DOM objects)
        
        # Modal de documentation pour les métriques
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("📊 Documentation des Métriques")),
            dbc.ModalBody([
                html.H6("Type de métrique disponible :", className="mb-3"),
                
                html.Div([
                    html.H6("📏 Range", className="text-primary"),
                    html.P("Métrique de plage de valeurs pour une ou plusieurs colonnes."),
                    html.Ul([
                        html.Li("Paramètres : dataset (alias), colonnes (une ou plusieurs)"),
                        html.Li("Supporte la multi-sélection de colonnes"),
                        html.Li("Optionnel : where (clause de filtrage)"),
                    ]),
                ], className="mb-3"),
            ]),
            dbc.ModalFooter(
                dbc.Button("Fermer", id="close-metric-help", className="ms-auto")
            ),
        ], id="metric-help-modal", size="lg", is_open=False),
        
        # Modal de documentation pour les tests
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("✅ Documentation des Tests")),
            dbc.ModalBody([
                html.H6("Type de test disponible :", className="mb-3"),
                
                html.Div([
                    html.H6("📏 Range", className="text-primary"),
                    html.P("Vérifie que les valeurs sont dans une plage définie (min, max)."),
                    html.Ul([
                        html.Li("Peut se baser sur : une colonne de database OU une métrique"),
                        html.Li("Paramètres : min (valeur minimale), max (valeur maximale)"),
                        html.Li("Optionnel : seuil pour tolérance (op et value)"),
                        html.Li("💡 Choisissez 'Database' pour tester une colonne directe ou 'Métrique' pour tester une métrique calculée"),
                    ]),
                ], className="mb-3"),
            ]),
            dbc.ModalFooter(
                dbc.Button("Fermer", id="close-test-help", className="ms-auto")
            ),
        ], id="test-help-modal", size="lg", is_open=False),
        
    ], fluid=True)

# Placeholder global pour les callbacks qui ciblent {"role": "metric-preview"}
metric_preview_placeholder = html.Div(id={"role": "metric-preview"})

# Insérer metric_preview_placeholder dans la liste des children du layout,
# par exemple juste après la dropdown des métriques ou dans la colonne de preview.
layout_children = [
    # ... autres composants ...
    metric_preview_placeholder,
    # ... autres composants ...
]
