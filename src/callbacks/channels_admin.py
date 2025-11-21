"""
Callbacks pour l'interface d'administration des canaux.
Gère la création, édition, suppression et affichage des canaux de dépôt.
"""

import dash
from dash import Input, Output, State, callback, html, dcc, no_update, ALL
from dash.exceptions import PreventUpdate
import json
from datetime import datetime
from pathlib import Path
import yaml

from src.core.models_channels import (
    DropChannel, FileSpecification, EmailConfig, FileFormat
)
from src.core.channel_manager import get_channel_manager
from src.config import _load_inventory


# Variables globales pour l'état de l'interface
current_channel_id = None
file_specs_list = []


# ========== CALLBACKS POUR INVENTORY CONTEXT ==========

@callback(
    Output('channel-stream-dropdown', 'options'),
    Input('channel-modal', 'is_open'),
    prevent_initial_call=False
)
def populate_streams(is_open):
    """Peuple le dropdown des streams depuis l'inventory."""
    inv = _load_inventory()
    streams = inv.get("streams", [])
    options = [{"label": stream.get("label", stream["id"]), "value": stream["id"]} 
               for stream in streams]
    return options


@callback(
    Output('channel-project-dropdown', 'options'),
    Input('channel-stream-dropdown', 'value'),
    Input('channel-modal', 'is_open'),
    prevent_initial_call=False
)
def populate_projects(stream_id, is_open):
    """Peuple le dropdown des projets en fonction du stream sélectionné."""
    inv = _load_inventory()
    streams = inv.get("streams", [])
    projects = []
    
    if stream_id:
        # Filtrer par stream
        for stream in streams:
            if stream["id"] == stream_id:
                projects = stream.get("projects", [])
                break
    else:
        # Tous les projets de tous les streams
        for stream in streams:
            projects.extend(stream.get("projects", []))
    
    # Dédupliquer par ID
    unique_projects = {}
    for proj in projects:
        if proj["id"] not in unique_projects:
            unique_projects[proj["id"]] = proj
    
    options = [{"label": f"{proj['id']}", "value": proj["id"]} 
               for proj in unique_projects.values()]
    return options


@callback(
    Output('channel-zone-dropdown', 'options'),
    Input('channel-stream-dropdown', 'value'),
    Input('channel-project-dropdown', 'value'),
    Input('channel-modal', 'is_open'),
    prevent_initial_call=False
)
def populate_zones(stream_id, project_id, is_open):
    """Peuple le dropdown des zones en fonction du stream et projet sélectionnés."""
    inv = _load_inventory()
    streams = inv.get("streams", [])
    zones = []
    
    if not project_id:
        # Si pas de projet, retourner toutes les zones
        for stream in streams:
            for project in stream.get("projects", []):
                zones.extend(project.get("zones", []))
    else:
        # Parcourir l'inventory pour trouver les zones
        for stream in streams:
            if stream_id and stream["id"] != stream_id:
                continue
            
            for project in stream.get("projects", []):
                if project["id"] == project_id:
                    zones.extend(project.get("zones", []))
    
    # Dédupliquer par ID
    unique_zones = {}
    for zone in zones:
        if zone["id"] not in unique_zones:
            unique_zones[zone["id"]] = zone
    
    options = [{"label": zone["id"], "value": zone["id"]} 
               for zone in unique_zones.values()]
    return options


@callback(
    Output('channel-dq-configs-dropdown', 'options'),
    Input('channel-stream-dropdown', 'value'),
    Input('channel-project-dropdown', 'value'),
    Input('channel-zone-dropdown', 'value')
)
def load_available_dq_configs(stream_id, project_id, zone_id):
    """Charge les DQ disponibles en fonction du contexte stream/project/zone."""
    print(f"[DEBUG load_available_dq_configs] Contexte: stream={stream_id}, project={project_id}, zone={zone_id}")
    
    dq_dir = Path("dq/definitions")
    if not dq_dir.exists():
        print(f"[DEBUG] Répertoire DQ n'existe pas: {dq_dir}")
        return []
    
    options = []
    
    for dq_file in dq_dir.glob("*.yaml"):
        try:
            with open(dq_file, 'r', encoding='utf-8') as f:
                dq_config = yaml.safe_load(f)
            
            # Vérifier le contexte
            context = dq_config.get('context', {})
            dq_stream = context.get('stream')
            dq_project = context.get('project')
            dq_zone = context.get('zone')
            
            print(f"[DEBUG] Fichier {dq_file.name}: stream={dq_stream}, project={dq_project}, zone={dq_zone}")
            
            # Filtrer selon le contexte sélectionné
            match = True
            if stream_id and dq_stream and dq_stream != stream_id:
                match = False
                print(f"  ❌ Stream mismatch: {dq_stream} != {stream_id}")
            if project_id and dq_project and dq_project != project_id:
                match = False
                print(f"  ❌ Project mismatch: {dq_project} != {project_id}")
            if zone_id and dq_zone and dq_zone != zone_id:
                match = False
                print(f"  ❌ Zone mismatch: {dq_zone} != {zone_id}")
            
            if match:
                dq_id = dq_config.get('id', dq_file.stem)
                dq_desc = dq_config.get('description', '')
                label = f"{dq_id}"
                if dq_desc:
                    label += f" - {dq_desc[:50]}"
                
                print(f"  ✅ Match! Ajout de {label}")
                options.append({
                    "label": label,
                    "value": str(dq_file)  # Déjà un chemin relatif
                })
        except Exception as e:
            print(f"[DEBUG] Erreur lors de la lecture de {dq_file.name}: {e}")
            # Ignorer les fichiers invalides et continuer avec le suivant
    
    print(f"[DEBUG] Total DQ trouvés: {len(options)}")
    return options


@callback(
    Output('channels-list-container', 'children'),
    Input('btn-refresh-channels', 'n_clicks'),
    Input('interval-refresh-channels', 'n_intervals')
)
def refresh_channels_list(n_clicks, n_intervals):
    """Rafraîchit la liste des canaux."""
    manager = get_channel_manager()
    channels = manager.list_channels()
    
    if not channels:
        return html.Div([
            html.I(className="bi bi-inbox", style={'fontSize': '4rem', 'color': '#6c757d'}),
            html.P("Aucun canal configuré", className="text-muted mt-3")
        ], className="text-center py-5")
    
    cards = []
    for channel in channels:
        stats = manager.get_channel_statistics(channel.channel_id)
        card = _render_channel_card(channel, stats)
        cards.append(card)
    
    return html.Div(cards, className="row")


def _render_channel_card(channel: DropChannel, stats: dict):
    """Rend une carte pour un canal."""
    status_badge = html.Span(
        "Actif" if channel.active else "Inactif",
        className=f"badge bg-{'success' if channel.active else 'secondary'} me-2"
    )
    
    # Badge de permission
    if channel.is_public:
        permission_badge = html.Span(
            [html.I(className="bi bi-globe me-1"), "Public"],
            className="badge bg-info me-2"
        )
    else:
        permission_badge = html.Span(
            [html.I(className="bi bi-lock me-1"), "Privé"],
            className="badge bg-warning text-dark me-2"
        )
    
    # Badge de direction
    direction_text = "vers STDA" if channel.direction == "incoming" else "depuis STDA"
    direction_icon = "bi-arrow-down-circle" if channel.direction == "incoming" else "bi-arrow-up-circle"
    direction_color = "success" if channel.direction == "incoming" else "primary"
    direction_badge = html.Span(
        [html.I(className=f"bi {direction_icon} me-1"), direction_text],
        className=f"badge bg-{direction_color} me-2"
    )
    
    success_rate = stats.get('success_rate', 0)
    rate_color = 'success' if success_rate >= 80 else 'warning' if success_rate >= 50 else 'danger'
    
    return html.Div([
        html.Div([
            html.Div([
                html.Div([
                    html.H5([
                        html.I(className="bi bi-cloud-upload me-2"),
                        channel.name
                    ], className="card-title"),
                    html.Div([
                        status_badge,
                        permission_badge,
                        direction_badge
                    ])
                ], className="d-flex justify-content-between align-items-center mb-3"),
                
                html.P([
                    html.Strong("Équipe: "),
                    channel.team_name
                ], className="mb-2"),
                
                # Contexte inventory
                html.Div([
                    html.Small([
                        html.I(className="bi bi-folder2-open me-1"),
                        html.Strong("Contexte: "),
                        f"{channel.stream or '(all)'} / {channel.project} / {channel.zone}"
                    ], className="text-info")
                ], className="mb-2") if channel.project and channel.zone else None,
                
                html.P(channel.description or "Aucune description", 
                       className="text-muted small mb-3"),
                
                # Afficher les permissions si canal privé
                html.Div([
                    html.Small([
                        html.I(className="bi bi-people me-1"),
                        f"{len(channel.allowed_users)} utilisateur(s) autorisé(s)"
                    ], className="text-muted d-block") if channel.allowed_users else None,
                    html.Small([
                        html.I(className="bi bi-diagram-3 me-1"),
                        f"Groupes: {', '.join(channel.allowed_groups)}"
                    ], className="text-muted d-block") if channel.allowed_groups else None
                ], className="mb-2") if not channel.is_public else None,
                
                html.Hr(),
                
                # Statistiques
                html.Div([
                    html.Div([
                        html.Div([
                            html.I(className="bi bi-file-earmark text-primary me-1"),
                            html.Span(f"{len(channel.file_specifications)} fichier(s)")
                        ], className="mb-1"),
                        html.Div([
                            html.I(className="bi bi-shield-check text-success me-1"),
                            html.Span(f"{len(channel.dq_configs)} config(s) DQ")
                        ], className="mb-1")
                    ], className="col-6"),
                    html.Div([
                        html.Div([
                            html.I(className="bi bi-inbox text-info me-1"),
                            html.Span(f"{stats.get('total_submissions', 0)} soumission(s)")
                        ], className="mb-1"),
                        html.Div([
                            html.I(className=f"bi bi-graph-up text-{rate_color} me-1"),
                            html.Span(f"{success_rate:.0f}% succès")
                        ])
                    ], className="col-6")
                ], className="row small"),
                
                html.Hr(),
                
                # Actions
                html.Div([
                    html.Button([
                        html.I(className="bi bi-pencil me-1"),
                        "Éditer"
                    ], id={'type': 'btn-edit-channel', 'index': channel.channel_id},
                       className="btn btn-sm btn-outline-primary me-2"),
                    html.Button([
                        html.I(className="bi bi-trash me-1"),
                        "Supprimer"
                    ], id={'type': 'btn-delete-channel', 'index': channel.channel_id},
                       className="btn btn-sm btn-outline-danger")
                ], className="d-flex justify-content-end")
            ], className="card-body")
        ], className="card h-100 shadow-sm hover-shadow")
    ], className="col-md-6 col-lg-4 mb-3")


@callback(
    Output('channel-modal', 'is_open'),
    Output('channel-modal-title', 'children'),
    Output('channel-id-input', 'value'),
    Output('channel-id-input', 'disabled'),
    Output('channel-name-input', 'value'),
    Output('channel-team-input', 'value'),
    Output('channel-direction-dropdown', 'value'),
    Output('channel-stream-dropdown', 'value'),
    Output('channel-project-dropdown', 'value'),
    Output('channel-zone-dropdown', 'value'),
    Output('channel-description-input', 'value'),
    Output('channel-active-check', 'value'),
    Output('file-specs-container', 'children'),
    Output('channel-dq-configs-dropdown', 'value'),
    Output('channel-public-check', 'value'),
    Output('channel-allowed-users-input', 'value'),
    Output('channel-allowed-groups-input', 'value'),
    Output('channel-team-emails-input', 'value'),
    Output('channel-admin-emails-input', 'value'),
    Output('channel-success-subject-input', 'value'),
    Output('channel-success-body-input', 'value'),
    Output('channel-failure-subject-input', 'value'),
    Output('channel-failure-body-input', 'value'),
    Input('btn-new-channel', 'n_clicks'),
    Input({'type': 'btn-edit-channel', 'index': dash.dependencies.ALL}, 'n_clicks'),
    Input('btn-save-channel', 'n_clicks'),
    Input('btn-cancel-channel', 'n_clicks'),
    State('channel-id-input', 'value'),
    prevent_initial_call=True
)
def manage_channel_modal(new_clicks, edit_clicks, save_clicks, cancel_clicks, current_id):
    """Gère l'ouverture et la fermeture du modal de canal."""
    from dash import ctx
    
    if not ctx.triggered:
        raise PreventUpdate
    
    trigger_id = ctx.triggered[0]['prop_id']
    
    # Fermer le modal (annuler ou sauvegarder)
    if 'btn-cancel-channel' in trigger_id or 'btn-save-channel' in trigger_id:
        return (False,) + tuple([no_update] * 22)
    
    # Nouveau canal
    if 'btn-new-channel' in trigger_id:
        return (
            True,  # is_open
            "Nouveau Canal",
            "",  # channel_id (vide, éditable)
            False,  # channel_id disabled
            "",  # name
            "",  # team
            "incoming",  # direction (default)
            None,  # stream (optionnel)
            "",  # project
            "",  # zone
            "",  # description
            ["active"],  # active (checked)
            [],  # file specs (vide)
            [],  # dq configs
            ["public"],  # is_public (checked by default)
            "",  # allowed_users
            "",  # allowed_groups
            "",  # team emails
            "",  # admin emails
            "✅ Dépôt de données validé - {channel_name}",  # success subject
            "Votre dépôt sur le canal \"{channel_name}\" a été traité avec succès.\n\nRésumé:\n- Date: {submission_date}\n- Fichiers: {file_count}\n- Contrôles: {dq_passed}/{dq_total} réussis",  # success body
            "⚠️ Dépôt de données - Anomalies détectées - {channel_name}",  # failure subject
            "Votre dépôt sur le canal \"{channel_name}\" a été traité mais des anomalies ont été détectées.\n\nRésumé:\n- Date: {submission_date}\n- Fichiers: {file_count}\n- Contrôles: {dq_passed}/{dq_total} réussis\n- Anomalies: {dq_failed} contrôle(s) en échec"  # failure body
        )
    
    # Éditer canal existant
    if 'btn-edit-channel' in trigger_id:
        trigger_dict = json.loads(trigger_id.split('.')[0])
        channel_id = trigger_dict['index']
        
        manager = get_channel_manager()
        channel = manager.get_channel(channel_id)
        
        if not channel:
            return [no_update] * 23
        
        # Rendre les file specs
        file_specs_elements = []
        for idx, spec in enumerate(channel.file_specifications):
            file_specs_elements.append(_render_file_spec_row(spec, idx))
        
        return (
            True,  # is_open
            f"Éditer Canal: {channel.name}",
            channel.channel_id,
            True,  # channel_id disabled (non éditable)
            channel.name,
            channel.team_name,
            channel.direction,
            channel.stream,  # stream
            channel.project,  # project
            channel.zone,  # zone
            channel.description or "",
            ["active"] if channel.active else [],
            file_specs_elements,
            channel.dq_configs,
            ["public"] if channel.is_public else [],
            ", ".join(channel.allowed_users),
            ", ".join(channel.allowed_groups),
            ", ".join(channel.email_config.recipient_team_emails),
            ", ".join(channel.email_config.admin_emails),
            channel.email_config.success_subject,
            channel.email_config.success_body_template,
            channel.email_config.failure_subject,
            channel.email_config.failure_body_template
        )
    
    raise PreventUpdate


@callback(
    Output('file-specs-container', 'children', allow_duplicate=True),
    Input('btn-add-file-spec', 'n_clicks'),
    State('file-specs-container', 'children'),
    prevent_initial_call=True
)
def add_file_spec_row(n_clicks, current_children):
    """Ajoute une nouvelle ligne de spécification de fichier."""
    if not n_clicks:
        raise PreventUpdate
    
    new_spec = FileSpecification(
        file_id="",
        name="",
        format=FileFormat.CSV,
        required=True
    )
    
    new_index = len(current_children) if current_children else 0
    new_row = _render_file_spec_row(new_spec, new_index)
    
    if current_children:
        return current_children + [new_row]
    return [new_row]


def _render_file_spec_row(spec: FileSpecification, index: int):
    """Rend une ligne de spécification de fichier."""
    return html.Div([
        html.Div([
            html.Div([
                dcc.Input(
                    id={'type': 'file-spec-id', 'index': index},
                    value=spec.file_id,
                    placeholder="ex: sales_data",
                    className="form-control form-control-sm"
                )
            ], className="col-md-3"),
            html.Div([
                dcc.Input(
                    id={'type': 'file-spec-name', 'index': index},
                    value=spec.name,
                    placeholder="ex: Données de Ventes",
                    className="form-control form-control-sm"
                )
            ], className="col-md-3"),
            html.Div([
                dcc.Dropdown(
                    id={'type': 'file-spec-format', 'index': index},
                    options=[
                        {'label': 'CSV', 'value': 'csv'},
                        {'label': 'Excel', 'value': 'excel'},
                        {'label': 'Parquet', 'value': 'parquet'},
                        {'label': 'JSON', 'value': 'json'}
                    ],
                    value=spec.format.value,
                    className="form-select-sm",
                    clearable=False
                )
            ], className="col-md-2"),
            html.Div([
                dcc.Checklist(
                    id={'type': 'file-spec-required', 'index': index},
                    options=[{'label': ' Requis', 'value': 'required'}],
                    value=['required'] if spec.required else [],
                    className="form-check"
                )
            ], className="col-md-2 d-flex align-items-center"),
            html.Div([
                html.Button(
                    html.I(className="bi bi-trash"),
                    id={'type': 'btn-remove-file-spec', 'index': index},
                    className="btn btn-sm btn-outline-danger"
                )
            ], className="col-md-2 d-flex align-items-center")
        ], className="row g-2 mb-2")
    ])


@callback(
    Output('file-specs-container', 'children', allow_duplicate=True),
    Input({'type': 'btn-remove-file-spec', 'index': dash.dependencies.ALL}, 'n_clicks'),
    State('file-specs-container', 'children'),
    prevent_initial_call=True
)
def remove_file_spec_row(n_clicks_list, current_children):
    """Supprime une ligne de spécification de fichier."""
    from dash import ctx
    
    if not ctx.triggered or not any(n_clicks_list):
        raise PreventUpdate
    
    # Trouver l'index cliqué
    trigger_id = ctx.triggered[0]['prop_id']
    trigger_dict = json.loads(trigger_id.split('.')[0])
    clicked_index = trigger_dict['index']
    
    # Supprimer la ligne correspondante
    if current_children and clicked_index < len(current_children):
        current_children.pop(clicked_index)
        
        # Réindexer
        for idx, child in enumerate(current_children):
            # Mettre à jour les IDs (simplifié)
            pass
    
    return current_children


@callback(
    Output('toast-container', 'children'),
    Output('channels-list-container', 'children', allow_duplicate=True),
    Output('channel-modal', 'is_open', allow_duplicate=True),
    Input('btn-save-channel', 'n_clicks'),
    State('channel-id-input', 'value'),
    State('channel-name-input', 'value'),
    State('channel-team-input', 'value'),
    State('channel-direction-dropdown', 'value'),
    State('channel-stream-dropdown', 'value'),
    State('channel-project-dropdown', 'value'),
    State('channel-zone-dropdown', 'value'),
    State('channel-description-input', 'value'),
    State('channel-active-check', 'value'),
    State({'type': 'file-spec-id', 'index': dash.dependencies.ALL}, 'value'),
    State({'type': 'file-spec-name', 'index': dash.dependencies.ALL}, 'value'),
    State({'type': 'file-spec-format', 'index': dash.dependencies.ALL}, 'value'),
    State({'type': 'file-spec-required', 'index': dash.dependencies.ALL}, 'value'),
    State('channel-dq-configs-dropdown', 'value'),
    State('channel-public-check', 'value'),
    State('channel-allowed-users-input', 'value'),
    State('channel-allowed-groups-input', 'value'),
    State('channel-team-emails-input', 'value'),
    State('channel-admin-emails-input', 'value'),
    State('channel-success-subject-input', 'value'),
    State('channel-success-body-input', 'value'),
    State('channel-failure-subject-input', 'value'),
    State('channel-failure-body-input', 'value'),
    prevent_initial_call=True
)
def save_channel(n_clicks, channel_id, name, team, direction, stream_id, project_id, zone_id, description, active_check,
                 file_ids, file_names, file_formats, file_required_list,
                 dq_configs, public_check, allowed_users_str, allowed_groups_str,
                 team_emails, admin_emails,
                 success_subject, success_body, failure_subject, failure_body):
    """Sauvegarde un canal (création ou modification)."""
    if not n_clicks:
        raise PreventUpdate
    
    print(f"[DEBUG save_channel] Sauvegarde du canal {channel_id}")
    print(f"  - stream: {stream_id}, project: {project_id}, zone: {zone_id}")
    print(f"  - active_check: {active_check}")
    print(f"  - dq_configs: {dq_configs}")
    
    # Validation
    if not channel_id or not name or not team or not project_id or not zone_id:
        toast = html.Div([
            html.Div([
                html.Strong("Erreur"),
                " Veuillez remplir tous les champs obligatoires (ID, nom, équipe, projet, zone)."
            ], className="toast-body")
        ], className="toast show bg-danger text-white")
        return toast, no_update, no_update
    
    # Validation du contexte (project et zone mandatory)
    if not project_id or not zone_id:
        toast = html.Div([
            html.Div([
                html.Strong("Erreur"),
                " Le projet et la zone sont obligatoires."
            ], className="toast-body")
        ], className="toast show bg-danger text-white")
        return toast, no_update
    
    # Construire file specifications
    file_specs = []
    for i in range(len(file_ids)):
        if file_ids[i]:  # Ignorer les lignes vides
            spec = FileSpecification(
                file_id=file_ids[i],
                name=file_names[i],
                format=FileFormat(file_formats[i]),
                required='required' in (file_required_list[i] if i < len(file_required_list) else [])
            )
            file_specs.append(spec)
    
    # Parser emails
    team_emails_list = [e.strip() for e in team_emails.split(',') if e.strip()]
    admin_emails_list = [e.strip() for e in admin_emails.split(',') if e.strip()]
    
    # Parser permissions
    is_public = 'public' in (public_check or [])
    allowed_users_list = [e.strip() for e in (allowed_users_str or "").split(',') if e.strip()]
    allowed_groups_list = [g.strip() for g in (allowed_groups_str or "").split(',') if g.strip()]
    
    # Construire email config
    email_config = EmailConfig(
        recipient_team_emails=team_emails_list,
        admin_emails=admin_emails_list,
        success_subject=success_subject,
        success_body_template=success_body,
        failure_subject=failure_subject,
        failure_body_template=failure_body
    )
    
    # Construire canal
    channel = DropChannel(
        channel_id=channel_id,
        name=name,
        team_name=team,
        direction=direction or "incoming",
        stream=stream_id,
        project=project_id or "",
        zone=zone_id or "",
        description=description,
        active='active' in (active_check or []),
        file_specifications=file_specs,
        dq_configs=dq_configs or [],
        email_config=email_config,
        is_public=is_public,
        allowed_users=allowed_users_list,
        allowed_groups=allowed_groups_list
    )
    
    # Sauvegarder
    manager = get_channel_manager()
    
    # Vérifier si c'est une création ou modification
    existing = manager.get_channel(channel_id)
    
    if existing:
        manager.update_channel(channel)
        message = f"Canal '{name}' modifié avec succès."
    else:
        manager.create_channel(channel)
        message = f"Canal '{name}' créé avec succès."
    
    # Toast de succès
    toast = html.Div([
        html.Div([
            html.Strong("Succès"),
            f" {message}"
        ], className="toast-body")
    ], className="toast show bg-success text-white")
    
    # Rafraîchir la liste
    channels = manager.list_channels()
    cards = []
    for ch in channels:
        stats = manager.get_channel_statistics(ch.channel_id)
        cards.append(_render_channel_card(ch, stats))
    
    return toast, html.Div(cards, className="row"), False  # False pour fermer la modale


@callback(
    Output('toast-container', 'children', allow_duplicate=True),
    Output('channels-list-container', 'children', allow_duplicate=True),
    Input({'type': 'btn-delete-channel', 'index': dash.dependencies.ALL}, 'n_clicks'),
    prevent_initial_call=True
)
def delete_channel(n_clicks_list):
    """Supprime un canal."""
    from dash import ctx
    
    if not ctx.triggered or not any(n_clicks_list):
        raise PreventUpdate
    
    trigger_id = ctx.triggered[0]['prop_id']
    trigger_dict = json.loads(trigger_id.split('.')[0])
    channel_id = trigger_dict['index']
    
    manager = get_channel_manager()
    channel = manager.get_channel(channel_id)
    
    if not channel:
        raise PreventUpdate
    
    manager.delete_channel(channel_id)
    
    # Toast
    toast = html.Div([
        html.Div([
            html.Strong("Supprimé"),
            f" Canal '{channel.name}' supprimé."
        ], className="toast-body")
    ], className="toast show bg-info text-white")
    
    # Rafraîchir
    channels = manager.list_channels()
    cards = []
    for ch in channels:
        stats = manager.get_channel_statistics(ch.channel_id)
        cards.append(_render_channel_card(ch, stats))
    
    return toast, html.Div(cards, className="row")
