# Page Build (wizard de création DQ)

from dash import html, dcc
import dash_bootstrap_components as dbc
from src.layouts.navbar import stepper


def build_page():
    """Page de construction de configuration DQ (wizard 4 étapes)"""
    return dbc.Container([
        html.Div(id="ctx-banner"),
        stepper(0),
        dcc.Store(id="store_datasets", storage_type="memory"),
        dcc.Store(id="store_metrics", storage_type="memory"),
        dcc.Store(id="store_tests", storage_type="memory"),

        # Étape 1: Datasets
        dbc.Card([dbc.CardHeader("Étape 1 — Datasets & Aliases"), dbc.CardBody([
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
            dbc.Button("Enregistrer les datasets", id="save-datasets", color="primary", className="mt-2"),
            html.Div(id="save-datasets-status", className="text-success mt-2")
        ])], className="mb-3 shadow-sm"),

        # Étape 2: Métriques
        stepper(1),
        dbc.Card([dbc.CardHeader("Étape 2 — Métriques"), dbc.CardBody([
            dbc.Tabs([
                dbc.Tab(label="➕ Créer une métrique", tab_id="tab-metric-create", children=[
                    html.Div(className="mt-3", children=[
                        html.Label("Type de métrique"),
                        dcc.Dropdown(
                            id="metric-type",
                            options=[
                                {"label": "row_count", "value": "row_count"},
                                {"label": "sum", "value": "sum"},
                                {"label": "mean", "value": "mean"},
                                {"label": "distinct_count", "value": "distinct_count"},
                                {"label": "ratio (metricA / metricB)", "value": "ratio"}
                            ],
                            placeholder="Choisir le type",
                            clearable=False,
                            persistence=True,
                            persistence_type="session"
                        ),
                        html.Div(id="metric-params", className="mt-3"),
                        dbc.Button("Forcer l'aperçu", id="force-metric-preview", color="secondary", className="mt-2 me-2"),
                        dbc.Button("Ajouter la métrique", id="add-metric", color="primary", className="mt-2"),
                        html.Div(id="add-metric-status", className="text-success mt-2"),
                    ])
                ]),
                dbc.Tab(label="📋 Métriques définies", tab_id="tab-metric-list", children=[
                    html.Div(id="metrics-list", className="mt-3")
                ]),
            ], id="metric-tabs", active_tab="tab-metric-create")
        ])], className="mb-3 shadow-sm"),

        # Étape 3: Tests
        stepper(2),
        dbc.Card([dbc.CardHeader("Étape 3 — Tests"), dbc.CardBody([
            dbc.Tabs([
                dbc.Tab(label="➕ Créer un test", tab_id="tab-test-create", children=[
                    html.Div(className="mt-3", children=[
                        html.Label("Type de test"),
                        dcc.Dropdown(
                            id="test-type",
                            options=[
                                {"label": "null_rate", "value": "null_rate"},
                                {"label": "uniqueness", "value": "uniqueness"},
                                {"label": "range", "value": "range"},
                                {"label": "regex", "value": "regex"},
                                {"label": "foreign_key", "value": "foreign_key"}
                            ],
                            placeholder="Choisir le type",
                            clearable=False,
                            persistence=True,
                            persistence_type="session"
                        ),
                        html.Div(id="test-params", className="mt-3"),
                        dbc.Button("Ajouter le test", id="add-test", color="primary", className="mt-2"),
                        html.Div(id="add-test-status", className="text-success mt-2"),
                    ])
                ]),
                dbc.Tab(label="📋 Tests définis", tab_id="tab-test-list", children=[
                    html.Div(id="tests-list", className="mt-3")
                ]),
            ], id="test-tabs", active_tab="tab-test-create")
        ])], className="mb-3 shadow-sm"),

        # Étape 4: Publication
        stepper(3),
        dbc.Card([dbc.CardHeader("Étape 4 — Prévisualisation & Publication"), dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Label("Managed Folder ID"),
                    dcc.Input(id="folder-id", type="text", value="dq_params")
                ], md=4),
                dbc.Col([
                    html.Label("Nom de la configuration"),
                    dcc.Input(id="cfg-name", type="text", value="default")
                ], md=4),
                dbc.Col([
                    html.Label("Format"),
                    dcc.RadioItems(
                        id="fmt",
                        options=[
                            {"label": "JSON", "value": "json"},
                            {"label": "YAML", "value": "yaml"}
                        ],
                        value="json",
                        inline=True
                    )
                ], md=4)
            ]),
            html.Pre(
                id="cfg-preview",
                className="mt-3",
                style={"background": "#111", "color": "#eee", "padding": "1rem", "whiteSpace": "pre-wrap"}
            ),
            dbc.Button("✅ Publier", id="publish", color="success"),
            html.Div(id="publish-status", className="text-success mt-2")
        ])], className="mb-5 shadow-sm"),
        
        dbc.Toast(
            id="toast",
            header="Info",
            is_open=False,
            dismissable=True,
            icon="info",
            style={"position": "fixed", "top": 20, "right": 20, "zIndex": 2000}
        )
    ], fluid=True)
