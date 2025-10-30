# Page Build (wizard de création DQ avec onglets)

from dash import html, dcc
from src.metrics_registry import get_metric_options, get_metric_meta
from src.plugins.discovery import discover_all_plugins
import dash_bootstrap_components as dbc
from src.config import DEBUG_UI


def build_page():
    """Page de construction de configuration DQ (4 onglets)"""
    return dbc.Container([
        html.Div(id="ctx-banner"),
        html.H3("🔧 Configuration DQ Builder", className="mb-3"),
        
        dcc.Store(id="store_datasets", storage_type="session"),
        dcc.Store(id="store_metrics", storage_type="session"),
        dcc.Store(id="store_tests", storage_type="session"),
        dcc.Store(id="store_edit_metric", storage_type="session"),
        # Note: inventory-datasets-store est déclaré dans app.py pour éviter les duplications

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
                                            {"label": info.plugin_class.label, "value": pid}
                                            for pid, info in discover_all_plugins(verbose=False).items()
                                            if info.category == "tests"
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
                html.H6("Métriques disponibles", className="mb-3"),
                # Générer dynamiquement la liste des métriques découvertes
                html.Div([
                    html.Div([
                        html.H6(info.plugin_class.label or pid, className="text-primary"),
                        html.P(get_metric_meta(pid).get("description") or (info.plugin_class.__doc__ or "").strip().splitlines()[0] if info.plugin_class.__doc__ else ""),
                        html.Ul([
                            html.Li(f"ID: {pid}"),
                        ] + [html.Li(f"Param: {p.get('name')} ({p.get('type')})") for p in get_metric_meta(pid).get('params', [])])
                    ], className="mb-3") for pid, info in discover_all_plugins(verbose=False).items() if info.category == 'metrics'
                ])
                # Hidden placeholders so pattern-matching callback ids exist for validation
            ]),
            dbc.ModalFooter(
                dbc.Button("Fermer", id="close-metric-help", className="ms-auto")
            ),
            
        ], id="metric-help-modal", size="lg", is_open=False),
        
        # Modal de documentation pour les tests
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("✅ Documentation des Tests")),
            dbc.ModalBody([
                html.H6("Tests disponibles", className="mb-3"),
                # Générer dynamiquement la liste des plugins de tests
                html.Div([
                    html.Div([
                        html.H6(info.plugin_class.label or pid, className="text-primary"),
                        html.P((info.plugin_class.__doc__ or "").strip().splitlines()[0] if info.plugin_class.__doc__ else ""),
                        html.Ul([
                            html.Li(f"ID: {pid}"),
                        ] + [html.Li(f"Param: {k}") for k in (info.plugin_class.ParamsModel.model_fields.keys() if hasattr(info.plugin_class.ParamsModel, 'model_fields') else list(info.plugin_class.ParamsModel.model_json_schema().get('properties', {}).keys()))])
                    ], className="mb-3") for pid, info in discover_all_plugins(verbose=False).items() if info.category == 'tests'
                ])
            ]),
            dbc.ModalFooter(
                dbc.Button("Fermer", id="close-test-help", className="ms-auto")
            ),
        ], id="test-help-modal", size="lg", is_open=False),

        # Debug panel (affiché uniquement si DEBUG_UI=True)
        html.Div(
            id="build-debug-panel",
            children=[
                html.H5("Debug (DEBUG_UI active)"),
                html.Div("ds-picker options:"),
                html.Pre(id="debug-ds-picker-options", style={"whiteSpace": "pre-wrap", "wordBreak": "break-word"}),
                html.Div("store_datasets:"),
                html.Pre(id="debug-store-datasets", style={"whiteSpace": "pre-wrap", "wordBreak": "break-word"}),
            ],
            style={"display": "block" if DEBUG_UI else "none", "marginTop": "1rem"}
        ),

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
