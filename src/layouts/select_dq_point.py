from dash import html, dcc
import dash_bootstrap_components as dbc


def select_dq_point_page():
    """Page de sélection de la zone (raw/trusted/sandbox) - anciennement DQ Point."""
    return dbc.Container([
        html.H2("Étape 3 — Choisir la Zone"),
        html.P("Sélectionnez la zone de données (ex: raw, trusted, sandbox)."),
        dcc.Dropdown(
            id="select-zone-dropdown", 
            options=[], 
            placeholder="Choisir une zone"
        ),
        dbc.Button("Aller au Builder", id="select-dq-next", color="primary", className="mt-3"),
        html.Div(id="select-dq-status", className="mt-2"),

        # Stores pour datasets
        dcc.Store(id="inventory-datasets-store", storage_type="memory"),
        dcc.Store(id="store_datasets", storage_type="memory"),

        # Affichage de la liste des datasets associés à la zone sélectionnée
        dbc.Card([
            dbc.CardHeader(html.H5("📦 Datasets associés", className="mb-0")),
            dbc.CardBody([
                html.Div(id="datasets-status", className="mb-2 text-muted", children="Sélectionnez une zone pour voir les datasets disponibles"),
                dcc.Checklist(
                    id="datasets-checklist", 
                    options=[], 
                    value=[], 
                    inputStyle={"margin-right": "8px"},
                    className="mb-2"
                ),
                html.Div(id="datasets-help", className="small text-muted", children="Cochez les datasets que vous souhaitez utiliser")
            ])
        ], id="datasets-container", className="mt-4")
    ], fluid=True)
