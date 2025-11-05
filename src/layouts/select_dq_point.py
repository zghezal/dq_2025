from dash import html, dcc
import dash_bootstrap_components as dbc


def select_dq_point_page():
    """Page de sélection de la zone (raw/trusted/sandbox) - anciennement DQ Point."""
    return dbc.Container([
        html.H2("Étape 4 — Choisir la Zone"),
        html.P("Sélectionnez la zone de données (ex: raw, trusted, sandbox)."),
        dcc.Dropdown(
            id="select-zone-dropdown", 
            options=[], 
            placeholder="Choisir une zone"
        ),
        
        html.Div(id="zone-overview-container", className="mt-4"),
        
        dbc.Button("Aller au Builder", id="select-dq-next", color="primary", className="mt-3"),
        html.Div(id="select-dq-status", className="mt-2"),

        # Stores pour datasets, metrics, tests (requis par les callbacks globaux)
        # Note: inventory-datasets-store est déclaré dans app.py pour éviter les duplications
        dcc.Store(id="store_datasets", storage_type="session"),
        dcc.Store(id="store_metrics", storage_type="session"),
        dcc.Store(id="store_tests", storage_type="session"),
        
        # Éléments cachés requis par les callbacks globaux de build
        html.Div(id="ds-picker", style={"display": "none"}),
        html.Div(id="metrics-list", style={"display": "none"}),
        html.Div(id="tests-list", style={"display": "none"}),
        html.Div(id="save-datasets-status", style={"display": "none"}),

        # Affichage de la liste des datasets associés à la zone sélectionnée (aperçu uniquement)
        dbc.Card([
            dbc.CardHeader(html.H5("📦 Aperçu des datasets", className="mb-0")),
            dbc.CardBody([
                    html.Div(id="datasets-status", className="text-muted", children="Sélectionnez une zone pour voir les datasets disponibles"),
                    # Colonne gauche: liste des datasets. Colonne droite: prévisualisation du dataset sélectionné
                    dbc.Row([
                        dbc.Col(html.Div(id="datasets-list"), md=6),
                        dbc.Col(html.Div(id="dataset-detail-preview", className="ms-2"), md=6)
                    ], className="mt-2")
                ])
            # Modal pour prévisualisation (rempli dynamiquement)
            ,
            dbc.Modal(
                [
                    dbc.ModalHeader(dbc.ModalTitle(id="dataset-preview-title"), close_button=True),
                    dbc.ModalBody(id="modal-body-content"),
                    dbc.ModalFooter(
                        dbc.Button("Fermer", id="close-dataset-preview", className="ml-auto", color="secondary")
                    )
                ],
                id="dataset-preview-modal",
                size="lg",
                is_open=False,
            )
        ], id="datasets-container", className="mt-4")
    ], fluid=True)
