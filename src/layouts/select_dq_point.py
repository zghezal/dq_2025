from dash import html, dcc
import dash_bootstrap_components as dbc


def select_dq_point_page():
    return dbc.Container([
        html.H2("Étape 3 — Choisir le DQ Point"),
        html.P("Sélectionnez le point DQ (ex: Extraction, Transformation, Chargement)."),
        dcc.Dropdown(id="select-dq-point-dropdown", options=[{"label":"Extraction","value":"Extraction"},{"label":"Transformation","value":"Transformation"},{"label":"Chargement","value":"Chargement"}], placeholder="Choisir un DQ Point"),
            dbc.Button("Aller au Builder", id="select-dq-next", color="primary", className="mt-3"),
            html.Div(id="select-dq-status", className="mt-2"),

            # Store qui contient la base de datasets sélectionnée depuis l'inventory
            dcc.Store(id="inventory-datasets-store", storage_type="memory"),

            # Affichage de la liste des datasets associés au dq point sélectionné
            html.Div([
                html.H5("Datasets associés"),
                dcc.Checklist(id="datasets-checklist", options=[], value=[], inputStyle={"margin-right": "8px"}),
                html.Div(id="datasets-help", className="small text-muted mt-1", children="Sélectionnez les datasets qui seront utilisés pour les étapes suivantes")
            ], id="datasets-container", className="mt-3")
    ], fluid=True)
