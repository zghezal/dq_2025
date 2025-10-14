# src/layouts/configs.py — Page de visualisation des configurations

from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc

def configs_page():
    """Page pour visualiser les configurations DQ stockées"""
    return dbc.Container([
        html.H2("📊 Configurations DQ", className="my-4"),
        
        dbc.Card([
            dbc.CardBody([
                html.H5("Configurations enregistrées", className="card-title"),
                html.P("Visualisation synthétique des métriques et tests configurés", className="text-muted"),
                
                dbc.Row([
                    dbc.Col([
                        dbc.Button(
                            "🔄 Rafraîchir",
                            id="refresh-configs",
                            color="primary",
                            className="mb-3"
                        )
                    ], width="auto"),
                    dbc.Col([
                        dcc.Dropdown(
                            id="config-file-selector",
                            placeholder="Sélectionner une configuration...",
                            className="mb-3"
                        )
                    ], width=8)
                ], className="align-items-center"),
                
                html.Div(id="config-info-banner", className="mb-3"),
                
                dbc.Tabs([
                    dbc.Tab(label="📊 Métriques", tab_id="tab-metrics"),
                    dbc.Tab(label="✅ Tests", tab_id="tab-tests")
                ], id="config-tabs", active_tab="tab-metrics"),
                
                html.Div(id="config-table-container", className="mt-3")
            ])
        ], className="mb-4"),
        
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle(id="detail-modal-title")),
            dbc.ModalBody(id="detail-modal-body"),
            dbc.ModalFooter(
                dbc.Button("Fermer", id="close-detail-modal", className="ms-auto", n_clicks=0)
            )
        ], id="detail-modal", size="lg", is_open=False),
        
        dcc.Store(id="store_config_data", data=None)
    ], fluid=True)
