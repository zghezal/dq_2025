# src/callbacks/configs.py — Callbacks pour la visualisation des configurations

from dash import Input, Output, State, html, dash_table, no_update
import dash_bootstrap_components as dbc
import json
import yaml
import os
from pathlib import Path

def register_configs_callbacks(app):
    """Enregistre tous les callbacks pour la page de visualisation des configurations"""
    
    @app.callback(
        Output("config-file-selector", "options"),
        Output("config-file-selector", "value"),
        Input("refresh-configs", "n_clicks"),
        Input("url", "pathname"),
        prevent_initial_call=False
    )
    def load_config_files(n_clicks, pathname):
        """Charge la liste des fichiers de configuration disponibles"""
        if pathname != "/configs":
            return [], None
            
        config_dir = Path("managed_folders/dq_params")
        if not config_dir.exists():
            return [], None
        
        files = []
        for file in sorted(config_dir.glob("dq_config_*.*"), reverse=True):
            if file.suffix in [".yaml", ".yml", ".json"]:
                files.append({
                    "label": f"{file.stem} ({file.suffix})",
                    "value": str(file)
                })
        
        default_value = files[0]["value"] if files else None
        return files, default_value
    
    @app.callback(
        Output("store_config_data", "data"),
        Output("config-info-banner", "children"),
        Input("config-file-selector", "value"),
        prevent_initial_call=True
    )
    def load_config_data(config_file):
        """Charge et parse le fichier de configuration sélectionné"""
        if not config_file or not os.path.exists(config_file):
            return None, dbc.Alert("Aucune configuration sélectionnée", color="warning")
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                if config_file.endswith('.json'):
                    data = json.load(f)
                else:
                    data = yaml.safe_load(f)
            
            context = data.get("context", {})
            stream = context.get("stream", "N/A")
            project = context.get("project", "N/A")
            
            banner = dbc.Alert([
                html.Strong(f"Stream: {stream} | Projet: {project}"),
                html.Br(),
                html.Small(f"Fichier: {Path(config_file).name}")
            ], color="info", className="mb-0")
            
            return data, banner
        
        except Exception as e:
            return None, dbc.Alert(f"Erreur de lecture: {e}", color="danger")
    
    @app.callback(
        Output("config-table-container", "children"),
        Input("config-tabs", "active_tab"),
        Input("store_config_data", "data"),
        prevent_initial_call=True
    )
    def display_config_table(active_tab, config_data):
        """Affiche le tableau des métriques ou tests selon l'onglet actif"""
        if not config_data:
            return dbc.Alert("Aucune donnée à afficher", color="warning")
        
        if active_tab == "tab-metrics":
            items = config_data.get("metrics", [])
            columns = [
                {"name": "ID", "id": "id"},
                {"name": "Type", "id": "type"},
                {"name": "Table", "id": "database"},
                {"name": "Colonne", "id": "column"},
                {"name": "Actions", "id": "actions"}
            ]
            
            data = []
            for item in items:
                row = {
                    "id": item.get("id", "N/A"),
                    "type": item.get("type", "N/A"),
                    "database": item.get("database", "N/A"),
                    "column": item.get("column", "-"),
                    "actions": "👁️ Détails"
                }
                data.append(row)
        
        else:  # tab-tests
            items = config_data.get("tests", [])
            columns = [
                {"name": "ID", "id": "id"},
                {"name": "Type", "id": "type"},
                {"name": "Métrique", "id": "metric"},
                {"name": "Description", "id": "description"},
                {"name": "Actions", "id": "actions"}
            ]
            
            data = []
            for item in items:
                row = {
                    "id": item.get("id", "N/A"),
                    "type": item.get("type", "N/A"),
                    "metric": item.get("metric", "N/A"),
                    "description": item.get("description", "-"),
                    "actions": "👁️ Détails"
                }
                data.append(row)
        
        if not data:
            return dbc.Alert("Aucun élément configuré dans cette section", color="info")
        
        table = dash_table.DataTable(
            id="config-table",
            columns=columns,
            data=data,
            style_table={'overflowX': 'auto'},
            style_cell={
                'textAlign': 'left',
                'padding': '10px',
                'fontSize': '14px'
            },
            style_header={
                'backgroundColor': 'rgb(230, 230, 230)',
                'fontWeight': 'bold'
            },
            style_data_conditional=[
                {
                    'if': {'row_index': 'odd'},
                    'backgroundColor': 'rgb(248, 248, 248)'
                },
                {
                    'if': {'column_id': 'actions'},
                    'cursor': 'pointer',
                    'color': '#0d6efd',
                    'textDecoration': 'underline'
                }
            ],
            row_selectable=False,
            page_size=20
        )
        
        return table
    
    @app.callback(
        Output("detail-modal", "is_open"),
        Output("detail-modal-title", "children"),
        Output("detail-modal-body", "children"),
        Input("config-table", "active_cell"),
        Input("close-detail-modal", "n_clicks"),
        State("config-table", "data"),
        State("store_config_data", "data"),
        State("config-tabs", "active_tab"),
        State("detail-modal", "is_open"),
        prevent_initial_call=True
    )
    def show_detail_modal(active_cell, close_clicks, table_data, config_data, active_tab, is_open):
        """Affiche les détails complets d'un élément dans un modal"""
        from dash import callback_context
        
        if callback_context.triggered_id == "close-detail-modal":
            return False, "", ""
        
        if not active_cell or active_cell.get("column_id") != "actions":
            return no_update, no_update, no_update
        
        row_index = active_cell["row"]
        row_data = table_data[row_index]
        item_id = row_data["id"]
        
        if active_tab == "tab-metrics":
            items = config_data.get("metrics", [])
        else:
            items = config_data.get("tests", [])
        
        item = next((i for i in items if i.get("id") == item_id), None)
        
        if not item:
            return True, "Erreur", "Élément non trouvé"
        
        title = f"Détails: {item_id}"
        
        body = html.Div([
            html.Pre(
                json.dumps(item, ensure_ascii=False, indent=2),
                style={
                    "background": "#f8f9fa",
                    "padding": "1rem",
                    "borderRadius": "4px",
                    "fontSize": "13px"
                }
            )
        ])
        
        return True, title, body
