"""
Callbacks pour l'interface de dépôt de fichiers (équipes externes).
Gère la sélection de canal, le mapping de fichiers et la soumission.
"""

import dash
from dash import Input, Output, State, callback, html, dcc, no_update, ALL, MATCH
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import uuid
from datetime import datetime

from src.core.models_channels import ChannelSubmission, FileMapping, SubmissionStatus
from src.core.channel_manager import get_channel_manager
from src.core.submission_processor import SubmissionProcessor
from src.auth.auth_demo import get_demo_users_list, get_user_permissions


@callback(
    Output('drop-channel-dropdown', 'options'),
    Input('interval-refresh-drop', 'n_intervals')
)
def load_channel_options(n_intervals):
    """Charge les canaux actifs dans le dropdown."""
    manager = get_channel_manager()
    
    # Afficher tous les canaux actifs
    channels = manager.list_channels(active_only=True)
    
    options = []
    for ch in channels:
        direction_label = "→ STDA" if ch.direction == "incoming" else "← STDA"
        label = f"{ch.name} ({ch.team_name}) {direction_label}"
        options.append({'label': label, 'value': ch.channel_id})
    
    return options


@callback(
    Output('channel-info-display', 'children'),
    Output('file-mapping-container', 'children'),
    Output('file-mapping-card', 'style'),
    Output('contact-card', 'style'),
    Output('summary-card', 'style'),
    Input('drop-channel-dropdown', 'value')
)
def display_channel_info(channel_id):
    """Affiche les informations du canal sélectionné."""
    if not channel_id:
        return "", "", {"display": "none"}, {"display": "none"}, {"display": "none"}
    
    manager = get_channel_manager()
    channel = manager.get_channel(channel_id)
    
    if not channel:
        return html.Div("Canal non trouvé", className="alert alert-danger"), "", {"display": "none"}, {"display": "none"}, {"display": "none"}
    
    # Direction badge
    direction_text = "vers STDA" if channel.direction == "incoming" else "depuis STDA"
    direction_icon = "bi-arrow-down-circle" if channel.direction == "incoming" else "bi-arrow-up-circle"
    direction_color = "success" if channel.direction == "incoming" else "primary"
    
    direction_badge = html.Span([
        html.I(className=f"bi {direction_icon} me-1"),
        direction_text
    ], className=f"badge bg-{direction_color} me-2")
    
    # Info du canal
    info = html.Div([
        html.H5([
            html.I(className="bi bi-info-circle me-2"),
            "Informations du Canal"
        ], className="mb-3"),
        html.Dl([
            html.Dt("Nom du canal:"),
            html.Dd([channel.name, " ", direction_badge]),
            html.Dt("Équipe:"),
            html.Dd(channel.team_name),
            html.Dt("Description:"),
            html.Dd(channel.description or "Aucune description")
        ], className="row"),
        html.Hr(),
        html.P([
            html.Strong(f"{len(channel.file_specifications)} fichier(s) attendu(s)"),
            " - Veuillez fournir les liens vers vos fichiers ci-dessous."
        ], className="text-muted")
    ], className="alert alert-info")
    
    # File mapping inputs
    file_inputs = []
    for i, spec in enumerate(channel.file_specifications):
        file_inputs.append(_render_file_input_row(spec, i))
    
    return info, html.Div(file_inputs), {"display": "block"}, {"display": "block"}, {"display": "block"}


def _render_file_input_row(spec, index):
    """Rend une ligne d'input pour un fichier."""
    required_badge = html.Span(
        "Requis" if spec.required else "Optionnel",
        className=f"badge bg-{'danger' if spec.required else 'secondary'} me-2"
    )
    
    format_badge = html.Span(
        spec.format.value.upper(),
        className="badge bg-info"
    )
    
    return html.Div([
        dcc.Store(id={'type': 'uploaded-file-store', 'file_id': spec.file_id}),
        html.Div([
            html.Label([
                html.Strong(spec.name),
                " ",
                required_badge,
                format_badge
            ], className="form-label"),
            html.Small(
                f"ID: {spec.file_id}",
                className="text-muted d-block mb-2"
            ),
            html.Div([
                dcc.Input(
                    id={'type': 'file-path-input', 'file_id': spec.file_id},
                    placeholder=f"Chemin ou URL vers {spec.name} (.{spec.format.value})",
                    className="form-control mb-2"
                ),
                dcc.Upload(
                    id={'type': 'file-upload', 'file_id': spec.file_id},
                    children=html.Button('📂 Parcourir...', className="btn btn-outline-primary btn-sm mt-2"),
                    multiple=False
                )
            ]),
            html.Div(
                id={'type': 'file-validation-msg', 'file_id': spec.file_id},
                className="small"
            )
        ], className="mb-3")
    ], className="border-bottom pb-3")


@callback(
    Output('submission-summary', 'children'),
    Output('btn-submit-drop', 'disabled'),
    Input('drop-channel-dropdown', 'value'),
    Input('submitter-name-input', 'value'),
    Input('submitter-email-input', 'value'),
    Input({'type': 'file-path-input', 'file_id': dash.dependencies.ALL}, 'value'),
    State('drop-channel-dropdown', 'options'),
)
def update_summary(channel_id, submitter_name, submitter_email, file_paths, channel_options):
    """Met à jour le résumé de la soumission."""
    if not channel_id:
        return html.Div("Veuillez sélectionner un canal", className="text-muted"), True
    
    manager = get_channel_manager()
    channel = manager.get_channel(channel_id)
    
    if not channel:
        return html.Div("Canal non trouvé", className="alert alert-danger"), True
    
    # Compter fichiers fournis
    provided_count = sum(1 for path in file_paths if path)
    required_count = sum(1 for spec in channel.file_specifications if spec.required)
    
    summary_items = [
        html.H5("Résumé de la soumission", className="mb-3"),
        html.Dl([
            html.Dt("Canal:"),
            html.Dd(channel.name),
            html.Dt("Soumis par:"),
            html.Dd(submitter_name or "Non renseigné"),
            html.Dt("Email:"),
            html.Dd(submitter_email or "Non renseigné"),
            html.Dt("Fichiers fournis:"),
            html.Dd(f"{provided_count}/{len(channel.file_specifications)}")
        ], className="row")
    ]
    
    # Vérification
    can_submit = True
    if provided_count < required_count:
        summary_items.append(
            html.Div([
                html.I(className="bi bi-exclamation-triangle me-2"),
                f"Attention: {required_count} fichier(s) requis, {provided_count} fourni(s)"
            ], className="alert alert-warning")
        )
        can_submit = False
    else:
        summary_items.append(
            html.Div([
                html.I(className="bi bi-check-circle me-2"),
                "Tous les fichiers requis sont fournis"
            ], className="alert alert-success")
        )
    
    # Vérifier email
    if not submitter_email:
        can_submit = False
    
    return html.Div(summary_items), not can_submit


@callback(
    Output('success-modal', 'is_open'),
    Output('tracking-number-display', 'children'),
    Output('drop-channel-dropdown', 'value'),
    Output('submitter-name-input', 'value'),
    Output('submitter-email-input', 'value'),
    Output({'type': 'file-path-input', 'file_id': dash.dependencies.ALL}, 'value'),
    Output('toast-container-drop', 'children'),
    Output('download-report-container', 'children'),
    Input('btn-submit-drop', 'n_clicks'),
    State('drop-channel-dropdown', 'value'),
    State('submitter-name-input', 'value'),
    State('submitter-email-input', 'value'),
    State({'type': 'file-path-input', 'file_id': dash.dependencies.ALL}, 'value'),
    State({'type': 'file-path-input', 'file_id': dash.dependencies.ALL}, 'id'),
    prevent_initial_call=True
)
def submit_drop(n_clicks, channel_id, submitter_name, submitter_email, file_paths, file_ids):
    """Traite la soumission de fichiers."""
    if not n_clicks:
        raise PreventUpdate
    
    # Validation
    if not channel_id:
        toast = html.Div([
            html.Strong("Erreur: "),
            "Veuillez sélectionner un canal"
        ], className="toast show bg-danger text-white")
        return False, "", no_update, no_update, no_update, no_update, toast, ""
    
    if not submitter_email:
        toast = html.Div([
            html.Strong("Erreur: "),
            "Veuillez fournir votre email"
        ], className="toast show bg-danger text-white")
        return False, "", no_update, no_update, no_update, no_update, toast, ""
    
    manager = get_channel_manager()
    channel = manager.get_channel(channel_id)
    
    if not channel:
        toast = html.Div([
            html.Strong("Erreur: "),
            "Canal non trouvé"
        ], className="toast show bg-danger text-white")
        return False, "", no_update, no_update, no_update, no_update, toast, ""
    
    # Construire file mappings
    file_mappings = []
    for i, file_id_dict in enumerate(file_ids):
        file_id = file_id_dict['file_id']
        path = file_paths[i] if i < len(file_paths) else None
        
        if path:
            # Trouver le spec correspondant
            spec = next((s for s in channel.file_specifications if s.file_id == file_id), None)
            if spec:
                mapping = FileMapping(
                    file_spec_id=file_id,
                    provided_path=path,
                    provided_name=path.split('/')[-1]  # Extraire nom de fichier
                )
                file_mappings.append(mapping)
    
    # Vérifier fichiers requis
    required_specs = [s for s in channel.file_specifications if s.required]
    provided_file_ids = [m.file_spec_id for m in file_mappings]
    missing_required = [s.name for s in required_specs if s.file_id not in provided_file_ids]
    
    if missing_required:
        toast = html.Div([
            html.Strong("Erreur: "),
            f"Fichiers requis manquants: {', '.join(missing_required)}"
        ], className="toast show bg-danger text-white")
        return False, "", no_update, no_update, no_update, no_update, toast, ""
    
    # Créer submission
    submission_id = f"sub_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    
    # Combiner nom et email pour submitted_by
    submitter_info = f"{submitter_name} <{submitter_email}>" if submitter_name else submitter_email
    
    submission = ChannelSubmission(
        submission_id=submission_id,
        channel_id=channel_id,
        submitted_by=submitter_info,
        file_mappings=file_mappings,
        status=SubmissionStatus.PENDING
    )
    
    # Sauvegarder
    manager.create_submission(submission)
    
    # Lancer traitement en arrière-plan (ici synchrone pour démo)
    processor = SubmissionProcessor(manager)
    try:
        processed = processor.process_submission(submission)
        
        # Déterminer si rejeté ou accepté
        is_rejected = processed.status == SubmissionStatus.REJECTED
        is_success = processed.status == SubmissionStatus.DQ_SUCCESS
        
        # Badge de statut
        if is_rejected:
            status_badge = html.Span(
                "REJETÉ",
                className="badge bg-danger"
            )
            status_color = "danger"
            status_icon = "bi-x-circle-fill"
        elif is_success:
            status_badge = html.Span(
                "ACCEPTÉ",
                className="badge bg-success"
            )
            status_color = "success"
            status_icon = "bi-check-circle-fill"
        else:
            status_badge = html.Span(
                processed.status.value.upper(),
                className="badge bg-warning"
            )
            status_color = "warning"
            status_icon = "bi-exclamation-triangle-fill"
        
        # Message principal selon le statut
        if is_rejected:
            main_message = html.Div([
                html.H4([
                    html.I(className=f"bi {status_icon} text-{status_color} me-2"),
                    "Dépôt Rejeté"
                ], className=f"text-{status_color} mb-3"),
                html.P([
                    "Votre soumission a été ",
                    html.Strong("rejetée", className="text-danger"),
                    " suite aux contrôles qualité."
                ]),
                html.P([
                    html.Strong(f"{processed.dq_failed} test(s) ont échoué", className="text-danger"),
                    f" sur {processed.dq_total}."
                ]),
                html.P([
                    "Un email de notification a été envoyé à ",
                    html.Strong(submitter_email),
                    " avec les détails des anomalies détectées."
                ])
            ])
        else:
            main_message = html.Div([
                html.H4([
                    html.I(className=f"bi {status_icon} text-{status_color} me-2"),
                    "Dépôt Accepté"
                ], className=f"text-{status_color} mb-3"),
                html.P("Votre soumission a été acceptée et validée avec succès."),
                html.P([
                    html.Strong(f"{processed.dq_passed} test(s) ont réussi", className="text-success"),
                    f" sur {processed.dq_total}."
                ]),
                html.P([
                    "Un email de confirmation a été envoyé à ",
                    html.Strong(submitter_email),
                    "."
                ])
            ])
        
        # Modal de résultat
        tracking_display = html.Div([
            main_message,
            html.Hr(),
            html.Div([
                html.Small("Numéro de suivi: "),
                html.Code(submission_id, className="text-muted")
            ]),
            html.Div([
                html.Small("Statut: "),
                status_badge
            ], className="mt-2")
        ])
        
        # Réinitialiser les champs
        empty_paths = [""] * len(file_paths)
        
        # Toast selon le statut
        if is_rejected:
            toast = html.Div([
                html.Strong("Rejeté: "),
                "Le dépôt a été rejeté suite aux contrôles qualité"
            ], className="toast show bg-danger text-white")
        elif is_success:
            toast = html.Div([
                html.Strong("Accepté: "),
                "Le dépôt a été validé avec succès"
            ], className="toast show bg-success text-white")
        else:
            toast = html.Div([
                html.Strong("Traité: "),
                "La soumission a été traitée"
            ], className="toast show bg-warning text-white")
        
        # Boutons d'action (pour download-report-container)
        action_buttons = html.Div()
        if processed.dq_report_path:
            print(f"\n[DEBUG Boutons] Création des boutons pour submission: {submission_id}")
            print(f"[DEBUG Boutons] is_rejected = {is_rejected}")
            print(f"[DEBUG Boutons] dq_report_path = {processed.dq_report_path}")
            
            buttons_list = [
                html.A(
                    dbc.Button(
                        [html.I(className="bi bi-download me-2"), "Télécharger le rapport"],
                        color="danger" if is_rejected else "info",
                        className="me-2"
                    ),
                    href=f"/download-report/{submission_id}"
                )
            ]
            print(f"[DEBUG Boutons] Lien téléchargement créé: /download-report/{submission_id}")
            
            # Ajouter bouton "Forcer le dépôt" si rejeté
            if is_rejected:
                buttons_list.append(
                    dbc.Button(
                        [html.I(className="bi bi-shield-exclamation me-2"), "Forcer le dépôt"],
                        id={'type': 'force-deposit-btn', 'submission_id': submission_id},
                        color="warning",
                        outline=True
                    )
                )
                print(f"[DEBUG Boutons] Bouton forcer créé avec ID: {{'type': 'force-deposit-btn', 'submission_id': '{submission_id}'}}")
            
            print(f"[DEBUG Boutons] Nombre total de boutons: {len(buttons_list)}")
            
            # Pas de dcc.Download ici - on utilise le composant global
            action_buttons = html.Div(buttons_list, className="d-flex justify-content-center gap-2")
        
        return True, tracking_display, None, "", "", empty_paths, toast, action_buttons
        
    except Exception as e:
        toast = html.Div([
            html.Strong("Erreur: "),
            f"Échec du traitement: {str(e)}"
        ], className="toast show bg-danger text-white")
        return False, "", no_update, no_update, no_update, no_update, toast, ""


@callback(
    Output({'type': 'file-validation-msg', 'file_id': dash.dependencies.MATCH}, 'children'),
    Input({'type': 'file-path-input', 'file_id': dash.dependencies.MATCH}, 'value')
)
def validate_file_path(file_path):
    """Valide le chemin d'un fichier."""
    if not file_path:
        return ""
    
    # Validation basique
    import os
    
    # Vérifier si c'est un chemin local
    if os.path.exists(file_path):
        return html.Div([
            html.I(className="bi bi-check-circle text-success me-1"),
            "Fichier trouvé localement"
        ])
    
    # Vérifier si c'est une URL
    if file_path.startswith(('http://', 'https://')):
        return html.Div([
            html.I(className="bi bi-globe text-info me-1"),
            "URL distante"
        ])
    
    # Sinon, avertissement
    return html.Div([
        html.I(className="bi bi-exclamation-triangle text-warning me-1"),
        "Fichier non trouvé (sera validé lors de la soumission)"
    ])

@callback(
    Output('success-modal', 'is_open', allow_duplicate=True),
    Input('btn-close-success-modal', 'n_clicks'),
    prevent_initial_call=True
)
def close_success_modal(n_clicks):
    """Ferme le modal de succès."""
    print(f"\n[DEBUG Fermer] Callback déclenché! n_clicks={n_clicks}")
    if n_clicks:
        print(f"[DEBUG Fermer] Fermeture du modal, retour False")
        try:
            print(f"[DEBUG Fermer] ✅ Retournant: False")
            return False
        except Exception as e:
            print(f"[DEBUG Fermer] ❌ ERREUR: {e}")
            import traceback
            traceback.print_exc()
            raise PreventUpdate
    print(f"[DEBUG Fermer] n_clicks={n_clicks}, PreventUpdate")
    raise PreventUpdate


@callback(
    Output({'type': 'uploaded-file-store', 'file_id': dash.dependencies.MATCH}, 'data'),
    Input({'type': 'file-upload', 'file_id': dash.dependencies.MATCH}, 'filename'),
    Input({'type': 'file-upload', 'file_id': dash.dependencies.MATCH}, 'contents'),
    prevent_initial_call=True
)
def store_uploaded_file(filename, contents):
    """Sauvegarde le fichier uploadé dans data/ et stocke le chemin."""
    if not filename or not contents:
        raise PreventUpdate
    
    import os
    import base64
    from pathlib import Path
    
    upload_dir = Path("data")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        name, ext = os.path.splitext(filename)
        file_path = upload_dir / f"{name}_{timestamp}{ext}"
        with open(file_path, 'wb') as f:
            f.write(decoded)
        return str(file_path.absolute())
    except Exception as e:
        print(f"Erreur upload: {e}")
        raise PreventUpdate

@callback(
    Output({'type': 'file-path-input', 'file_id': dash.dependencies.MATCH}, 'value', allow_duplicate=True),
    Input({'type': 'uploaded-file-store', 'file_id': dash.dependencies.MATCH}, 'data'),
    prevent_initial_call=True
)
def update_input_from_store(file_path):
    """Met à jour le champ de saisie avec le chemin du fichier uploadé."""
    if file_path:
        return file_path
    raise PreventUpdate


# NOTE: Le téléchargement se fait maintenant via un endpoint Flask direct
# Voir app.py @app.server.route('/download-report/<submission_id>')
# Les boutons sont maintenant des liens <a href="/download-report/...">


@callback(
    [Output('success-modal', 'is_open', allow_duplicate=True),
     Output('toast-container-drop', 'children', allow_duplicate=True)],
    Input({'type': 'force-deposit-btn', 'submission_id': ALL}, 'n_clicks'),
    prevent_initial_call=True
)
def force_deposit(n_clicks_list):
    """Force l'acceptation d'un dépôt rejeté."""
    print(f"\n{'='*60}")
    print(f"[DEBUG Force] Callback déclenché!")
    print(f"[DEBUG Force] n_clicks_list = {n_clicks_list}")
    
    # Utiliser ctx pour identifier le bouton cliqué
    from dash import ctx
    print(f"[DEBUG Force] ctx.triggered = {ctx.triggered}")
    print(f"[DEBUG Force] ctx.triggered_id = {ctx.triggered_id}")
    
    if not ctx.triggered_id:
        print(f"[DEBUG Force] Pas de triggered_id, PreventUpdate")
        raise PreventUpdate
    
    # Vérifier que c'est un vrai clic (pas None)
    if ctx.triggered[0].get('value') is None:
        print(f"[DEBUG Force] Valeur None (bouton créé dynamiquement), PreventUpdate")
        raise PreventUpdate
    
    submission_id = ctx.triggered_id['submission_id']
    print(f"[Force] Demande de forçage pour: {submission_id}")
    
    # Récupérer la soumission et changer son statut
    manager = get_channel_manager()
    submission = manager.get_submission(submission_id)
    
    if not submission:
        print(f"[Force] Soumission {submission_id} introuvable")
        raise PreventUpdate
    
    # Forcer le statut à DQ_SUCCESS
    from src.core.models_channels import SubmissionStatus
    submission.status = SubmissionStatus.DQ_SUCCESS
    manager.update_submission(submission)
    
    print(f"[Force] Dépôt {submission_id} forcé à l'acceptation")
    print(f"[Force] Nouveau statut: {submission.status}")
    
    # Fermer le modal et afficher toast de confirmation
    toast_content = html.Div([
        html.Div([
            html.I(className="bi bi-shield-check me-2"),
            html.Strong("Forcé: "),
            "Le dépôt a été accepté malgré les échecs DQ"
        ], className="toast show bg-warning text-dark")
    ])
    
    print(f"[DEBUG Force] Retour: modal=False (fermé), toast créé")
    print(f"[DEBUG Force] Type toast: {type(toast_content)}")
    
    try:
        result = (False, toast_content)
        print(f"[DEBUG Force] ✅ Retournant: {result}")
        return result
    except Exception as e:
        print(f"[DEBUG Force] ❌ ERREUR lors du retour: {e}")
        import traceback
        traceback.print_exc()
        raise PreventUpdate

