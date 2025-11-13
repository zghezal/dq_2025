from dash import html, dcc
import dash_bootstrap_components as dbc
from src.utils_dq.dq_scanner import get_dq_scanner


def dq_inventory_page():
    """Page d'inventaire des définitions DQ disponibles"""
    
    # Scanner toutes les définitions DQ
    scanner = get_dq_scanner()
    definitions = scanner.scan_all()
    stats = scanner.get_summary_stats(definitions)
    
    return dbc.Container([
        # Store pour les données complètes (pour le filtrage)
        dcc.Store(id="dq-inventory-data", data={
            'definitions': [d.to_dict() for d in definitions],
            'stats': stats
        }),
        # Header
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.I(className="bi bi-journal-text", style={"fontSize": "2.5rem", "color": "#0d6efd"}),
                ], className="text-center mb-3"),
                html.H2("DQ Inventory", className="text-center mb-2"),
                html.P("Inventaire des configurations DQ et points de contrôle", 
                       className="text-center text-muted mb-4"),
            ], width=12)
        ], className="mt-4"),
        
        # Statistiques globales
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.I(className="bi bi-file-earmark-check", style={"fontSize": "2rem", "color": "#0d6efd"}),
                        ], className="text-center mb-2"),
                        html.H3(stats['total_definitions'], className="text-center mb-0"),
                        html.P("Définitions DQ", className="text-center text-muted mb-0 small")
                    ])
                ], className="shadow-sm border-0 mb-3")
            ], md=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.I(className="bi bi-speedometer2", style={"fontSize": "2rem", "color": "#198754"}),
                        ], className="text-center mb-2"),
                        html.H3(stats['total_metrics'], className="text-center mb-0"),
                        html.P("Métriques", className="text-center text-muted mb-0 small")
                    ])
                ], className="shadow-sm border-0 mb-3")
            ], md=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.I(className="bi bi-check-circle", style={"fontSize": "2rem", "color": "#ffc107"}),
                        ], className="text-center mb-2"),
                        html.H3(stats['total_tests'], className="text-center mb-0"),
                        html.P("Tests", className="text-center text-muted mb-0 small")
                    ])
                ], className="shadow-sm border-0 mb-3")
            ], md=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.I(className="bi bi-database", style={"fontSize": "2rem", "color": "#dc3545"}),
                        ], className="text-center mb-2"),
                        html.H3(stats['total_datasets'], className="text-center mb-0"),
                        html.P("Datasets", className="text-center text-muted mb-0 small")
                    ])
                ], className="shadow-sm border-0 mb-3")
            ], md=3),
        ], className="mb-4"),
        
        # Container pour le contenu filtrable
        html.Div(id="dq-inventory-content", children=[
            # Tableau summary des DQ
            html.Div([
                html.H5([
                    html.I(className="bi bi-table me-2"),
                    "Vue d'ensemble"
                ], className="mb-3"),
                _create_summary_table(definitions)
            ], className="mb-4"),
        
        # Filtres et actions
        dbc.Row([
            dbc.Col([
                dbc.InputGroup([
                    dbc.InputGroupText(html.I(className="bi bi-search")),
                    dbc.Input(id="dq-inventory-search", placeholder="Rechercher une définition...", type="text")
                ])
            ], md=4),
            dbc.Col([
                dbc.InputGroup([
                    dbc.InputGroupText([
                        html.I(className="bi bi-calendar-event me-1"),
                        "Quarter"
                    ]),
                    dbc.Select(
                        id="dq-inventory-quarter-filter",
                        options=[{"label": "Tous les quarters", "value": "all"}] + 
                                [{"label": q, "value": q} for q in stats.get('quarters', [])],
                        value="all"
                    )
                ])
            ], md=2),
            dbc.Col([
                dbc.Button([
                    html.I(className="bi bi-plus-circle me-2"),
                    "Créer une DQ"
                ], href="/select-quarter", color="primary", className="me-2"),
                dbc.Button([
                    html.I(className="bi bi-arrow-clockwise me-2"),
                    "Actualiser"
                ], id="dq-inventory-refresh", color="secondary", outline=True)
            ], md=6, className="text-end")
        ], className="mb-4"),
        
            # Liste des définitions DQ
            html.Div([
                html.H5([
                    html.I(className="bi bi-list-ul me-2"),
                    f"Définitions disponibles ({len(definitions)})"
                ], className="mb-3"),
                
                # Cards pour chaque définition
                html.Div([
                    _create_dq_card(dq) for dq in definitions
                ] if definitions else [
                    dbc.Alert([
                        html.I(className="bi bi-info-circle me-2"),
                        "Aucune définition DQ trouvée dans le répertoire dq/definitions/"
                    ], color="info")
                ])
            ])
        ]),  # Fin du div dq-inventory-content
        
        # Boutons de navigation
        dbc.Row([
            dbc.Col([
                html.Hr(className="my-4"),
                dbc.Button([
                    html.I(className="bi bi-house me-2"),
                    "Retour à l'accueil"
                ], href="/", color="secondary", className="me-2")
            ], width=12)
        ])
    ], fluid=True, className="mb-5")


def _create_summary_table(definitions):
    """Crée un tableau summary des définitions DQ"""
    if not definitions:
        return dbc.Alert([
            html.I(className="bi bi-info-circle me-2"),
            "Aucune définition DQ disponible"
        ], color="info")
    
    # Créer les données du tableau
    table_data = []
    for dq in definitions:
        table_data.append({
            'ID': dq.id,
            'Label': dq.label,
            'Stream': dq.stream,
            'Project': dq.project,
            'Zone': dq.zone,
            'DQ Point': dq.dq_point,
            'Quarter': dq.quarter,
            'Métriques': dq.metrics_count,
            'Tests': dq.tests_count,
            'Datasets': len(dq.datasets),
            'Version': dq.version
        })
    
    # Créer le tableau avec dash_table
    from dash import dash_table
    
    return dbc.Card([
        dbc.CardBody([
            dash_table.DataTable(
                data=table_data,
                columns=[
                    {'name': 'ID', 'id': 'ID'},
                    {'name': 'Label', 'id': 'Label'},
                    {'name': 'Quarter', 'id': 'Quarter'},
                    {'name': 'Stream', 'id': 'Stream'},
                    {'name': 'Project', 'id': 'Project'},
                    {'name': 'Zone', 'id': 'Zone'},
                    {'name': 'DQ Point', 'id': 'DQ Point'},
                    {'name': 'Métriques', 'id': 'Métriques'},
                    {'name': 'Tests', 'id': 'Tests'},
                    {'name': 'Datasets', 'id': 'Datasets'},
                    {'name': 'Version', 'id': 'Version'}
                ],
                style_table={
                    'overflowX': 'auto',
                },
                style_cell={
                    'textAlign': 'left',
                    'padding': '10px',
                    'fontSize': '14px',
                    'fontFamily': 'sans-serif'
                },
                style_header={
                    'backgroundColor': '#f8f9fa',
                    'fontWeight': 'bold',
                    'borderBottom': '2px solid #dee2e6',
                    'color': '#495057'
                },
                style_data={
                    'borderBottom': '1px solid #dee2e6',
                },
                style_data_conditional=[
                    {
                        'if': {'row_index': 'odd'},
                        'backgroundColor': '#f8f9fa'
                    },
                    {
                        'if': {'column_id': 'Métriques'},
                        'color': '#198754',
                        'fontWeight': 'bold'
                    },
                    {
                        'if': {'column_id': 'Tests'},
                        'color': '#ffc107',
                        'fontWeight': 'bold'
                    }
                ],
                page_size=20,
                sort_action='native',
                filter_action='native',
                page_action='native'
            )
        ], className="p-0")
    ], className="shadow-sm")


def _create_dq_card(dq):
    """Crée une card pour une définition DQ"""
    return dbc.Card([
        dbc.CardHeader([
            dbc.Row([
                dbc.Col([
                    html.H5([
                        html.I(className="bi bi-file-earmark-text me-2"),
                        dq.label
                    ], className="mb-0")
                ], md=8),
                dbc.Col([
                    dbc.Badge(dq.id, color="info", className="me-2"),
                    dbc.Badge(f"v{dq.version}", color="secondary") if dq.version != 'N/A' else None
                ], md=4, className="text-end")
            ])
        ], className="bg-light"),
        dbc.CardBody([
            dbc.Row([
                # Contexte
                dbc.Col([
                    html.Div([
                        html.H6([
                            html.I(className="bi bi-diagram-3 me-2"),
                            "Contexte"
                        ], className="text-muted mb-2"),
                        html.Ul([
                            html.Li([html.Strong("Stream: "), dq.stream]),
                            html.Li([html.Strong("Project: "), dq.project]),
                            html.Li([html.Strong("Zone: "), dq.zone]),
                            html.Li([html.Strong("Point DQ: "), dq.dq_point]),
                            html.Li([
                                html.I(className="bi bi-calendar-event me-1"),
                                html.Strong("Quarter: "),
                                dbc.Badge(dq.quarter, color="info" if dq.quarter != 'N/A' else "secondary")
                            ]) if dq.quarter != 'N/A' else None,
                        ], className="small mb-0")
                    ])
                ], md=4),
                
                # Datasets
                dbc.Col([
                    html.Div([
                        html.H6([
                            html.I(className="bi bi-database me-2"),
                            "Datasets"
                        ], className="text-muted mb-2"),
                        html.Div([
                            dbc.Badge(ds, color="light", text_color="dark", className="me-1 mb-1")
                            for ds in dq.datasets
                        ] if dq.datasets else [
                            html.Span("Aucun dataset", className="text-muted small")
                        ])
                    ])
                ], md=4),
                
                # Statistiques
                dbc.Col([
                    html.Div([
                        html.H6([
                            html.I(className="bi bi-graph-up me-2"),
                            "Statistiques"
                        ], className="text-muted mb-2"),
                        html.Div([
                            dbc.Badge([
                                html.I(className="bi bi-speedometer2 me-1"),
                                f"{dq.metrics_count} métriques"
                            ], color="success", className="me-1 mb-1"),
                            dbc.Badge([
                                html.I(className="bi bi-check-circle me-1"),
                                f"{dq.tests_count} tests"
                            ], color="warning", className="mb-1"),
                        ])
                    ])
                ], md=4)
            ]),
            
            html.Hr(className="my-3"),
            
            # Actions et métadonnées
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.I(className="bi bi-file-earmark me-1 text-muted small"),
                        html.Span(dq.file_name, className="text-muted small me-3"),
                        html.I(className="bi bi-clock me-1 text-muted small"),
                        html.Span(
                            dq.modified_date.strftime("%d/%m/%Y %H:%M") if dq.modified_date else "N/A",
                            className="text-muted small"
                        )
                    ])
                ], md=8),
                dbc.Col([
                    dbc.ButtonGroup([
                        dbc.Button([
                            html.I(className="bi bi-play-circle me-1"),
                            "Exécuter"
                        ], size="sm", color="primary", outline=True),
                        dbc.Button([
                            html.I(className="bi bi-pencil me-1"),
                            "Éditer"
                        ], size="sm", color="secondary", outline=True),
                        dbc.Button([
                            html.I(className="bi bi-eye me-1"),
                            "Détails"
                        ], size="sm", color="info", outline=True)
                    ], size="sm")
                ], md=4, className="text-end")
            ])
        ])
    ], className="shadow-sm mb-3")
