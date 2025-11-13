"""
Callbacks pour la page DQ Inventory
"""

from dash import Input, Output, State, callback, html, no_update
import dash_bootstrap_components as dbc
from src.utils_dq.dq_scanner import DQDefinition


def register_dq_inventory_callbacks(app):
    """Enregistre les callbacks de la page DQ Inventory"""
    
    @app.callback(
        Output("dq-inventory-content", "children"),
        Input("dq-inventory-quarter-filter", "value"),
        Input("dq-inventory-search", "value"),
        State("dq-inventory-data", "data")
    )
    def filter_dq_inventory(quarter_filter, search_text, data):
        """Filtre l'inventaire DQ selon le quarter et le texte de recherche"""
        if not data:
            return no_update
        
        # Reconstituer les objets DQDefinition depuis les dictionnaires
        from pathlib import Path
        definitions = []
        for d_dict in data.get('definitions', []):
            # Créer un objet DQDefinition à partir du dictionnaire
            class SimpleDQ:
                def __init__(self, d):
                    self.id = d['id']
                    self.label = d['label']
                    self.version = d['version']
                    self.file_name = d['file_name']
                    self.file_path = Path(d['file_path'])
                    self.stream = d['context']['stream']
                    self.project = d['context']['project']
                    self.zone = d['context']['zone']
                    self.dq_point = d['context']['dq_point']
                    self.quarter = d['context'].get('quarter', 'N/A')
                    self.datasets = d['datasets']
                    self.metrics_count = d['metrics_count']
                    self.tests_count = d['tests_count']
                    self.file_size = d['file_size']
                    from datetime import datetime
                    self.modified_date = datetime.fromisoformat(d['modified_date']) if d['modified_date'] else None
            
            definitions.append(SimpleDQ(d_dict))
        
        # Filtrer par quarter
        if quarter_filter and quarter_filter != "all":
            definitions = [d for d in definitions if d.quarter == quarter_filter]
        
        # Filtrer par texte de recherche
        if search_text:
            search_lower = search_text.lower()
            definitions = [
                d for d in definitions
                if search_lower in d.id.lower() 
                or search_lower in d.label.lower()
                or search_lower in d.stream.lower()
                or search_lower in d.project.lower()
            ]
        
        # Recalculer les stats pour les définitions filtrées
        from src.utils_dq.dq_scanner import DQScanner
        scanner = DQScanner()
        stats = scanner.get_summary_stats(definitions)
        
        # Régénérer le contenu
        return _generate_inventory_content(definitions, stats)


def _generate_inventory_content(definitions, stats):
    """Génère le contenu de l'inventaire avec les définitions filtrées"""
    from src.layouts.dq_inventory import _create_summary_table, _create_dq_card
    
    return html.Div([
        # Tableau summary
        html.Div([
            html.H5([
                html.I(className="bi bi-table me-2"),
                "Vue d'ensemble"
            ], className="mb-3"),
            _create_summary_table(definitions)
        ], className="mb-4"),
        
        # Liste des définitions DQ
        html.Div([
            html.H5([
                html.I(className="bi bi-list-ul me-2"),
                f"Définitions disponibles ({len(definitions)})"
            ], className="mb-3"),
            
            html.Div([
                _create_dq_card(dq) for dq in definitions
            ] if definitions else [
                dbc.Alert([
                    html.I(className="bi bi-info-circle me-2"),
                    "Aucune définition DQ ne correspond aux critères de filtrage"
                ], color="info")
            ])
        ])
    ])
