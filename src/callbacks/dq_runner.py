"""
Callbacks pour la page DQ Runner
"""

import dash
from dash import Input, Output, State, callback, html, no_update, dcc
import dash_bootstrap_components as dbc
from pathlib import Path
import yaml
import traceback
from datetime import datetime

# In-memory cache to store the latest run results for server-side export
# Keyed by run_id -> store_data
# Must be at module level so Flask routes can access it
EXPORT_CACHE = {}


def register_dq_runner_callbacks(app):
    """Enregistre les callbacks du DQ Runner"""
    
    @app.callback(
        Output("dq-runner-info", "children"),
        Input("dq-runner-select", "value")
    )
    def show_dq_info(dq_id):
        """Affiche les informations de la DQ sélectionnée"""
        if not dq_id:
            return dbc.Alert("Veuillez sélectionner une définition DQ", color="info")
        
        # Charger la définition
        from src.utils_dq.dq_scanner import get_dq_scanner
        scanner = get_dq_scanner()
        definitions = scanner.scan_all()
        
        dq = next((d for d in definitions if d.id == dq_id), None)
        if not dq:
            return dbc.Alert("Définition DQ introuvable", color="danger")
        
        return dbc.Card([
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Div([
                            html.Strong("Contexte:", className="text-muted"),
                            html.Ul([
                                html.Li([html.Strong("Stream: "), dq.stream]),
                                html.Li([html.Strong("Project: "), dq.project]),
                                html.Li([html.Strong("Zone: "), dq.zone]),
                                html.Li([html.Strong("Quarter: "), dbc.Badge(dq.quarter, color="info")]),
                            ], className="small mb-0")
                        ])
                    ], md=4),
                    dbc.Col([
                        html.Div([
                            html.Strong("Datasets:", className="text-muted"),
                            html.Div([
                                dbc.Badge(ds, color="light", text_color="dark", className="me-1 mb-1")
                                for ds in dq.datasets
                            ])
                        ])
                    ], md=4),
                    dbc.Col([
                        html.Div([
                            html.Strong("Statistiques:", className="text-muted"),
                            html.Div([
                                dbc.Badge([
                                    html.I(className="bi bi-speedometer2 me-1"),
                                    f"{dq.metrics_count} métriques"
                                ], color="success", className="me-2"),
                                dbc.Badge([
                                    html.I(className="bi bi-check-circle me-1"),
                                    f"{dq.tests_count} tests"
                                ], color="warning")
                            ])
                        ])
                    ], md=4)
                ])
            ])
        ], className="border-info", style={"borderLeft": "4px solid #0dcaf0"})
    
    @app.callback(
        Output("dq-runner-select", "value", allow_duplicate=True),
        Output("dq-runner-options", "value", allow_duplicate=True),
        Output("dq-runner-results", "children", allow_duplicate=True),
        Input("dq-runner-reset-btn", "n_clicks"),
        prevent_initial_call=True
    )
    def reset_dq_runner(n_clicks):
        """Réinitialise le DQ Runner"""
        return None, ["investigate"], None
    
    @app.callback(
        Output("dq-runner-results", "children"),
        Output("dq-runner-execute-btn", "disabled"),
        Output("dq-runner-results-store", "data"),
        Input("dq-runner-execute-btn", "n_clicks"),
        State("dq-runner-select", "value"),
        State("dq-runner-options", "value"),
        prevent_initial_call=True
    )
    def execute_dq(n_clicks, dq_id, options):
        """Exécute la définition DQ sélectionnée"""
        if not dq_id:
            return dbc.Alert("Aucune DQ sélectionnée", color="warning"), False, None
        
        investigate = "investigate" in (options or [])
        verbose = "verbose" in (options or [])
        
        # Afficher un spinner pendant l'exécution
        loading = dbc.Card([
            dbc.CardBody([
                html.Div([
                    dbc.Spinner(color="primary", size="lg"),
                    html.H5("Exécution en cours...", className="mt-3"),
                    html.P(f"Traitement de la définition: {dq_id}", className="text-muted")
                ], className="text-center py-5")
            ])
        ], className="shadow-sm")
        
        try:
            # Importer les modules nécessaires
            from src.core.models_inventory import Inventory
            from src.core.models_dq import DQDefinition
            from src.core.parser import build_execution_plan
            from src.core.executor import execute
            from src.core.connectors import LocalReader
            
            # Charger l'inventaire
            inv_path = Path("config/inventory.yaml")
            inv_data = yaml.safe_load(inv_path.read_text(encoding="utf-8"))
            inv = Inventory(**inv_data)
            
            # Trouver le fichier DQ
            dq_files = list(Path("dq/definitions").glob("*.yaml")) + list(Path("dq/definitions").glob("*.yml"))
            dq_file = next((f for f in dq_files if f.stem == dq_id or dq_id in f.read_text()), None)
            
            if not dq_file:
                return dbc.Alert(f"Fichier de définition introuvable pour {dq_id}", color="danger"), False
            
            # Charger la DQ
            dq_data = yaml.safe_load(dq_file.read_text(encoding="utf-8"))
            dq = DQDefinition(**dq_data)
            
            # Construire le plan d'exécution
            plan = build_execution_plan(inv, dq, overrides={})
            
            # Exécuter
            start_time = datetime.now()
            run_result = execute(plan, loader=LocalReader(plan.alias_map), investigate=investigate)
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Stocker les résultats pour l'export
            store_data = {
                "dq_id": dq_id,
                "run_id": run_result.run_id,
                "duration": duration,
                "investigate": investigate,
                "timestamp": start_time.isoformat(),
                "metrics": {k: {"value": v.value, "passed": v.passed, "message": v.message} for k, v in run_result.metrics.items()},
                "tests": {k: {"value": v.value, "passed": v.passed, "message": v.message, "meta": v.meta} for k, v in run_result.tests.items()},
                "investigations": run_result.investigations,
                "investigation_report": run_result.investigation_report
            }
            
            # store on server-side cache for export endpoint
            try:
                EXPORT_CACHE[run_result.run_id] = store_data
                print(f"[DEBUG] Stored run_id={run_result.run_id} in EXPORT_CACHE")
                print(f"[DEBUG] EXPORT_CACHE now contains: {list(EXPORT_CACHE.keys())}")
            except Exception as e:
                print(f"[ERROR] Failed to store in EXPORT_CACHE: {e}")
                # If anything goes wrong saving the cache, continue without blocking the UI
                pass

            # Construire l'affichage des résultats
            return _build_results_display(run_result, dq_id, duration, investigate), False, store_data
        
        except Exception as e:
            error_msg = str(e)
            error_trace = traceback.format_exc() if verbose else ""
            
            return dbc.Alert([
                html.H5([
                    html.I(className="bi bi-x-circle me-2"),
                    "Erreur lors de l'exécution"
                ], className="alert-heading"),
                html.Hr(),
                html.P(error_msg),
                html.Pre(error_trace, className="small") if error_trace else None
            ], color="danger"), False, None

    # Callback pour ouvrir la modal de confirmation d'export
    @app.callback(
        Output("export-confirm-modal", "is_open"),
        Output("export-confirm-modal-body", "children"),
        Input("dq-runner-export-btn", "n_clicks"),
        Input("export-confirm-cancel", "n_clicks"),
        Input("export-confirm-download", "n_clicks"),
        State("dq-runner-results-store", "data"),
        State("export-confirm-modal", "is_open"),
        prevent_initial_call=True
    )
    def toggle_export_modal(export_clicks, cancel_clicks, download_clicks, store_data, is_open):
        """Affiche/cache la modal de confirmation d'export"""
        from dash import callback_context
        
        if not callback_context.triggered:
            return False, no_update
        
        triggered_id = callback_context.triggered[0]["prop_id"].split(".")[0]
        
        # Si on clique sur Annuler ou fermer, on ferme la modal
        if triggered_id in ["export-confirm-cancel"]:
            return False, no_update
        
        # Si on clique sur Télécharger, on ferme la modal (le téléchargement sera géré par un autre callback)
        if triggered_id == "export-confirm-download":
            return False, no_update
        
        # Si on clique sur Exporter, on ouvre la modal avec le contenu
        if triggered_id == "dq-runner-export-btn" and store_data:
            run_id = store_data.get("run_id")
            dq_id = store_data.get("dq_id")
            timestamp = store_data.get("timestamp", "N/A")
            duration = store_data.get("duration", 0)
            investigate = store_data.get("investigate", False)
            
            metrics_count = len(store_data.get("metrics", {}))
            tests = store_data.get("tests", {})
            tests_count = len(tests)
            passed_tests = sum(1 for t in tests.values() if t.get("passed", False))
            failed_tests = tests_count - passed_tests
            
            investigations = store_data.get("investigations", [])
            investigations_count = len(investigations)
            
            # Construire le contenu de la modal
            content = [
                html.P("Le fichier ZIP contiendra les éléments suivants:", className="mb-3"),
                
                dbc.Card([
                    dbc.CardBody([
                        html.H6([html.I(className="bi bi-info-circle me-2"), "Informations générales"], className="mb-3"),
                        html.Ul([
                            html.Li([html.Strong("DQ ID: "), dq_id]),
                            html.Li([html.Strong("Run ID: "), run_id]),
                            html.Li([html.Strong("Timestamp: "), timestamp]),
                            html.Li([html.Strong("Durée: "), f"{duration:.2f}s"]),
                            html.Li([html.Strong("Investigation: "), "Activée" if investigate else "Désactivée"]),
                        ])
                    ])
                ], className="mb-3"),
                
                dbc.Card([
                    dbc.CardBody([
                        html.H6([html.I(className="bi bi-file-earmark-text me-2"), "Fichiers inclus"], className="mb-3"),
                        html.Ul([
                            html.Li([
                                html.Strong("manifest.json"),
                                html.Span(" - Métadonnées de l'exécution", className="text-muted small")
                            ]),
                            html.Li([
                                html.Strong("results.json"),
                                html.Span(f" - {metrics_count} métriques, {tests_count} tests ({passed_tests} réussis, {failed_tests} échoués)", 
                                         className="text-muted small")
                            ]),
                            html.Li([
                                html.Strong("investigation_report.txt"),
                                html.Span(" - Rapport d'investigation", className="text-muted small")
                            ]) if store_data.get("investigation_report") else None,
                            html.Li([
                                html.Strong(f"investigations/ ({investigations_count} fichiers CSV)"),
                                html.Span(" - Échantillons de données problématiques", className="text-muted small")
                            ]) if investigations_count > 0 else None,
                        ])
                    ])
                ], className="mb-3"),
                
                dbc.Alert([
                    html.I(className="bi bi-info-circle-fill me-2"),
                    f"Taille estimée: ~{metrics_count + tests_count + investigations_count} fichiers"
                ], color="info", className="mb-0")
            ]
            
            return True, content
        
        return False, no_update
    
    # Callback principal qui fait l'export
    @app.callback(
        Output("dq-runner-download", "data"),
        Input("export-confirm-download", "n_clicks"),
        State("dq-runner-results-store", "data"),
        prevent_initial_call=True
    )
    def export_dq_results(n_clicks, store_data):
        """Exporte les résultats DQ dans un fichier ZIP"""
        import json
        import zipfile
        import io
        from pathlib import Path
        
        print(f"========== EXPORT CALLBACK TRIGGERED ==========")
        print(f"[DEBUG export_dq_results] n_clicks={n_clicks}")
        print(f"[DEBUG export_dq_results] store_data type: {type(store_data)}")
        print(f"[DEBUG export_dq_results] store_data keys: {store_data.keys() if isinstance(store_data, dict) else 'N/A'}")
        
        # Si pas de clicks ou pas de données, ne rien faire
        if not n_clicks or not store_data:
            print(f"[ERROR export_dq_results] No store_data available")
            return no_update
        
        run_id = store_data.get("run_id")
        print(f"[DEBUG export_dq_results] run_id from store: {run_id}")
        print(f"[DEBUG export_dq_results] EXPORT_CACHE contains: {list(EXPORT_CACHE.keys())}")
        
        export_data = EXPORT_CACHE.get(run_id)
        if not export_data:
            print(f"[ERROR export_dq_results] Run {run_id} not found in EXPORT_CACHE")
            return no_update

        print(f"[DEBUG export_dq_results] Creating ZIP file...")
        # Créer le ZIP
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            manifest = {
                "dq_id": export_data["dq_id"],
                "run_id": export_data["run_id"],
                "timestamp": export_data["timestamp"],
                "duration_seconds": export_data["duration"],
                "investigate_enabled": export_data["investigate"]
            }
            zip_file.writestr("manifest.json", json.dumps(manifest, indent=2))

            results = {
                "metrics": export_data["metrics"],
                "tests": export_data["tests"],
                "summary": {
                    "total_metrics": len(export_data["metrics"]),
                    "total_tests": len(export_data["tests"]),
                    "passed_tests": sum(1 for t in export_data["tests"].values() if t["passed"]),
                    "failed_tests": sum(1 for t in export_data["tests"].values() if not t["passed"])
                }
            }
            zip_file.writestr("results.json", json.dumps(results, indent=2))

            if export_data.get("investigation_report"):
                zip_file.writestr("investigation_report.txt", export_data["investigation_report"])

            if export_data.get("investigations"):
                for inv in export_data["investigations"]:
                    sample_file = inv.get("sample_file")
                    if sample_file:
                        from pathlib import Path as PathLib
                        sample_path = PathLib(sample_file)
                        if sample_path.exists():
                            zip_file.write(sample_path, f"investigations/{sample_path.name}")

        zip_buffer.seek(0)
        filename = f"dq_export_{export_data['dq_id']}_{export_data['run_id']}.zip"
        print(f"[DEBUG export_dq_results] Sending file: {filename}")
        return dcc.send_bytes(zip_buffer.getvalue(), filename)


def _build_results_display(run_result, dq_id, duration, investigate):
    """Construit l'affichage des résultats d'exécution"""
    
    # Compter les succès/échecs
    total_tests = len(run_result.tests)
    passed_tests = sum(1 for t in run_result.tests.values() if t.passed)
    failed_tests = total_tests - passed_tests
    
    # Déterminer le statut global
    all_passed = failed_tests == 0
    status_color = "success" if all_passed else "danger"
    status_icon = "check-circle-fill" if all_passed else "x-circle-fill"
    status_text = "SUCCÈS" if all_passed else "ÉCHEC"
    
    return html.Div([
        # Header des résultats
        dbc.Card([
            dbc.CardHeader([
                html.Div([
                    html.I(className=f"bi bi-{status_icon} me-2", style={"fontSize": "1.5rem", "color": f"var(--bs-{status_color})"}),
                    html.Strong(f"Résultats - {status_text}", style={"fontSize": "1.2rem"})
                ], className="d-flex align-items-center")
            ], className=f"bg-{status_color} text-white"),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Div([
                            html.Small("Run ID", className="text-muted d-block"),
                            html.Strong(run_result.run_id)
                        ])
                    ], md=3),
                    dbc.Col([
                        html.Div([
                            html.Small("Durée", className="text-muted d-block"),
                            html.Strong(f"{duration:.2f}s")
                        ])
                    ], md=2),
                    dbc.Col([
                        html.Div([
                            html.Small("Tests", className="text-muted d-block"),
                            dbc.Badge(f"{passed_tests}/{total_tests} réussis", 
                                     color="success" if all_passed else "warning")
                        ])
                    ], md=3),
                    dbc.Col([
                        html.Div([
                            html.Small("Métriques", className="text-muted d-block"),
                            html.Strong(f"{len(run_result.metrics)} calculées")
                        ])
                    ], md=2)
                ])
            ])
        ], className="shadow-sm mb-4"),
        
        # Résultats des métriques
        dbc.Card([
            dbc.CardHeader([
                html.I(className="bi bi-speedometer2 me-2"),
                html.Strong(f"Métriques ({len(run_result.metrics)})")
            ]),
            dbc.CardBody([
                _build_metrics_table(run_result.metrics)
            ])
        ], className="shadow-sm mb-3"),
        
        # Résultats des tests
        dbc.Card([
            dbc.CardHeader([
                html.I(className="bi bi-check-circle me-2"),
                html.Strong(f"Tests ({total_tests})")
            ]),
            dbc.CardBody([
                _build_tests_table(run_result.tests, investigate)
            ])
        ], className="shadow-sm mb-3"),
        
        # Investigations si présentes
        _build_investigations_section(run_result) if investigate else None
    ])


def _build_metrics_table(metrics):
    """Construit le tableau des métriques"""
    if not metrics:
        return dbc.Alert("Aucune métrique calculée", color="info")
    
    rows = []
    for metric_id, result in metrics.items():
        rows.append(html.Tr([
            html.Td(metric_id, className="font-monospace small"),
            html.Td(
                dbc.Badge(f"{result.value:.4f}" if isinstance(result.value, float) else str(result.value), 
                         color="success"),
                className="text-center"
            ),
            html.Td(result.message or "-", className="small text-muted")
        ]))
    
    return dbc.Table([
        html.Thead(html.Tr([
            html.Th("Métrique"),
            html.Th("Valeur", className="text-center"),
            html.Th("Message")
        ])),
        html.Tbody(rows)
    ], bordered=True, hover=True, responsive=True, size="sm")


def _build_tests_table(tests, investigate):
    """Construit le tableau des tests"""
    if not tests:
        return dbc.Alert("Aucun test exécuté", color="info")
    
    rows = []
    for test_id, result in tests.items():
        status_icon = "check-circle-fill" if result.passed else "x-circle-fill"
        status_color = "success" if result.passed else "danger"
        
        rows.append(html.Tr([
            html.Td([
                html.I(className=f"bi bi-{status_icon} me-2", style={"color": f"var(--bs-{status_color})"}),
                html.Span(test_id, className="font-monospace small")
            ]),
            html.Td(
                dbc.Badge("PASS" if result.passed else "FAIL", color=status_color),
                className="text-center"
            ),
            html.Td(result.message or "-", className="small"),
            html.Td([
                dbc.Button([
                    html.I(className="bi bi-eye me-1"),
                    "Détails"
                ], id={"type": "test-detail-btn", "index": test_id}, 
                   size="sm", color="info", outline=True) if result.meta else None
            ], className="text-end")
        ]))
    
    return dbc.Table([
        html.Thead(html.Tr([
            html.Th("Test"),
            html.Th("Statut", className="text-center"),
            html.Th("Message"),
            html.Th("Actions", className="text-end")
        ])),
        html.Tbody(rows)
    ], bordered=True, hover=True, responsive=True, size="sm")


def _build_investigations_section(run_result):
    """Construit la section des investigations"""
    investigations = getattr(run_result, 'investigations', [])
    
    if not investigations:
        return None
    
    return dbc.Card([
        dbc.CardHeader([
            html.I(className="bi bi-search me-2"),
            html.Strong(f"Investigations ({len(investigations)})")
        ], className="bg-warning text-dark"),
        dbc.CardBody([
            html.P("Échantillons de données problématiques générés pour les tests échoués:", 
                   className="text-muted mb-3"),
            html.Div([
                dbc.Card([
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                html.Strong(inv.get('test_id', 'N/A'), className="text-primary")
                            ], md=4),
                            dbc.Col([
                                html.Small(inv.get('description', ''), className="text-muted")
                            ], md=4),
                            dbc.Col([
                                dbc.Badge(f"{inv.get('total_problematic_rows', 0)} lignes", color="danger", className="me-2"),
                                dbc.Button([
                                    html.I(className="bi bi-download me-1"),
                                    "Télécharger"
                                ], size="sm", color="primary", outline=True, href=f"/{inv.get('sample_file', '')}")
                            ], md=4, className="text-end")
                        ])
                    ])
                ], className="mb-2")
                for inv in investigations
            ])
        ])
    ], className="shadow-sm mb-3")


    @app.callback(
        Output("test-detail-modal", "is_open"),
        Output("test-detail-modal-body", "children"),
        Input({"type": "test-detail-btn", "index": dash.ALL}, "n_clicks"),
        Input("test-detail-modal-close", "n_clicks"),
        State("dq-runner-results-store", "data"),
        State("test-detail-modal", "is_open"),
        prevent_initial_call=True
    )
    def toggle_test_detail_modal(detail_clicks, close_click, store_data, is_open):
        """Affiche/ferme le modal des détails de test"""
        from dash import callback_context
        
        print(f"[DEBUG toggle_test_detail_modal] ===== CALLBACK TRIGGERED =====")
        print(f"[DEBUG toggle_test_detail_modal] detail_clicks={detail_clicks}")
        print(f"[DEBUG toggle_test_detail_modal] close_click={close_click}")
        print(f"[DEBUG toggle_test_detail_modal] store_data is None: {store_data is None}")
        print(f"[DEBUG toggle_test_detail_modal] callback_context.triggered={callback_context.triggered}")
        
        if not callback_context.triggered:
            print(f"[DEBUG toggle_test_detail_modal] No trigger")
            return no_update, no_update
        
        triggered_id = callback_context.triggered[0]["prop_id"]
        print(f"[DEBUG toggle_test_detail_modal] triggered_id={triggered_id}")
        
        # Si on ferme le modal
        if "test-detail-modal-close" in triggered_id:
            return False, no_update
        
        # Si on ouvre le modal pour voir les détails
        if "test-detail-btn" in triggered_id and store_data:
            # Extraire l'index (test_id) du bouton cliqué
            import json as json_lib
            try:
                button_id = json_lib.loads(triggered_id.split(".")[0])
                test_id = button_id["index"]
                
                # Récupérer les détails du test
                test_data = store_data["tests"].get(test_id)
                if not test_data:
                    return True, dbc.Alert("Test non trouvé", color="warning")
                
                # Construire le contenu du modal
                content = [
                    html.H5(f"Test: {test_id}", className="mb-3"),
                    dbc.Row([
                        dbc.Col([
                            html.Strong("Statut:"),
                            html.Br(),
                            dbc.Badge("PASS" if test_data["passed"] else "FAIL", 
                                     color="success" if test_data["passed"] else "danger",
                                     className="mt-1")
                        ], md=3),
                        dbc.Col([
                            html.Strong("Valeur:"),
                            html.Br(),
                            html.Span(str(test_data.get("value", "N/A")))
                        ], md=3),
                        dbc.Col([
                            html.Strong("Message:"),
                            html.Br(),
                            html.Span(test_data.get("message", "-"))
                        ], md=6)
                    ], className="mb-3"),
                    html.Hr()
                ]
                
                # Ajouter les métadonnées si disponibles
                meta = test_data.get("meta")
                if meta and isinstance(meta, dict):
                    content.append(html.H6("Métadonnées:", className="mt-3 mb-2"))
                    
                    # Créer un tableau des métadonnées
                    meta_rows = []
                    for key, value in meta.items():
                        meta_rows.append(html.Tr([
                            html.Td(html.Strong(key), style={"width": "30%"}),
                            html.Td(html.Code(str(value)) if isinstance(value, (int, float, bool)) else str(value))
                        ]))
                    
                    content.append(
                        dbc.Table([
                            html.Tbody(meta_rows)
                        ], bordered=True, size="sm", className="mt-2")
                    )
                
                return True, html.Div(content)
            except Exception as e:
                return True, dbc.Alert(f"Erreur: {str(e)}", color="danger")
        
        return is_open, no_update
