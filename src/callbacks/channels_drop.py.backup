"""
Callbacks pour l'interface de dépôt de fichiers (équipes externes).
Gère la sélection de canal, le mapping de fichiers et la soumission.
"""

import dash
from dash import Input, Output, State, callback, html, dcc, no_update, ALL
from dash.exceptions import PreventUpdate
import uuid
from datetime import datetime

from src.core.models_channels import ChannelSubmission, FileMapping, SubmissionStatus
from src.core.channel_manager import get_channel_manager
from src.core.submission_processor import SubmissionProcessor
from src.auth.auth_demo import get_demo_users_list, get_user_permissions


@callback(
    Output('demo-user-selector', 'options'),
    Input('interval-refresh-drop', 'n_intervals')
)
def load_demo_users(n_intervals):
    """Charge la liste des utilisateurs de démo"""
    return get_demo_users_list()


@callback(
    Output('drop-channel-dropdown', 'options'),
    Input('demo-user-selector', 'value'),
    Input('interval-refresh-drop', 'n_intervals')
)
def load_channel_options(selected_user, n_intervals):
    """Charge les canaux actifs dans le dropdown selon l'utilisateur."""
    manager = get_channel_manager()
    
    # Si un utilisateur est sélectionné, filtrer les canaux
    if selected_user:
        user_email, user_groups = get_user_permissions(selected_user)
        channels = manager.list_channels(active_only=True, user_email=user_email, user_groups=user_groups)
    else:
        # Par défaut, afficher tous les canaux publics
        channels = manager.list_channels(active_only=True)
        channels = [c for c in channels if c.is_public]
    
    return [
        {'label': f"{ch.name} ({ch.team_name})", 'value': ch.channel_id}
        for ch in channels
    ]


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
    
    # Info du canal
    info = html.Div([
        html.H5([
            html.I(className="bi bi-info-circle me-2"),
            "Informations du Canal"
        ], className="mb-3"),
        html.Dl([
            html.Dt("Nom du canal:"),
            html.Dd(channel.name),
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
            dcc.Input(
                id={'type': 'file-path-input', 'file_id': spec.file_id},
                placeholder=f"Chemin ou URL vers {spec.name} (.{spec.format.value})",
                className="form-control mb-2"
            ),
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
        return False, "", no_update, no_update, no_update, no_update, toast
    
    if not submitter_email:
        toast = html.Div([
            html.Strong("Erreur: "),
            "Veuillez fournir votre email"
        ], className="toast show bg-danger text-white")
        return False, "", no_update, no_update, no_update, no_update, toast
    
    manager = get_channel_manager()
    channel = manager.get_channel(channel_id)
    
    if not channel:
        toast = html.Div([
            html.Strong("Erreur: "),
            "Canal non trouvé"
        ], className="toast show bg-danger text-white")
        return False, "", no_update, no_update, no_update, no_update, toast
    
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
        return False, "", no_update, no_update, no_update, no_update, toast
    
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
        
        # Modal de succès
        tracking_display = html.Div([
            html.H4(submission_id, className="text-primary mb-3"),
            html.P("Votre soumission a été enregistrée et est en cours de traitement."),
            html.P([
                "Vous recevrez un email à ",
                html.Strong(submitter_email),
                " avec les résultats de l'analyse qualité."
            ]),
            html.Hr(),
            html.Small([
                "Statut actuel: ",
                html.Span(
                    processed.status.value.upper(),
                    className=f"badge bg-{'success' if processed.status == SubmissionStatus.DQ_SUCCESS else 'warning'}"
                )
            ])
        ])
        
        # Réinitialiser les champs
        empty_paths = [""] * len(file_paths)
        
        toast = html.Div([
            html.Strong("Succès: "),
            "Soumission enregistrée et traitée"
        ], className="toast show bg-success text-white")
        
        return True, tracking_display, None, "", "", empty_paths, toast
        
    except Exception as e:
        toast = html.Div([
            html.Strong("Erreur: "),
            f"Échec du traitement: {str(e)}"
        ], className="toast show bg-danger text-white")
        return False, "", no_update, no_update, no_update, no_update, toast


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
    if n_clicks:
        return False
    raise PreventUpdate
