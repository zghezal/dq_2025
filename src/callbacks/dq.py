# Callbacks de la page DQ Management

from dash import html, Input, Output, State, ALL, ctx, no_update
import dash_bootstrap_components as dbc
from datetime import datetime
from src.config import STREAMS
from src.utils import (
    list_dq_files, 
    read_dq_file, 
    delete_dq_file, 
    rename_dq_file, 
    duplicate_dq_file
)


def register_dq_callbacks(app):
    """Enregistre les callbacks de la page DQ Management"""
    
    @app.callback(
        Output("dq-project", "options"),
        Output("dq-project", "disabled"),
        Input("dq-stream", "value")
    )
    def on_stream_change(stream):
        """Met à jour les options de projet selon le stream sélectionné"""
        if not stream:
            return [], True
        projects = STREAMS.get(stream, [])
        opts = [{"label": p, "value": p} for p in projects]
        return opts, False

    @app.callback(
        Output("dq-list", "children"),
        Input("dq-refresh", "n_clicks"),
        Input("dq-stream", "value"),
        Input("dq-project", "value"),
        Input("dq-point", "value")
    )
    def update_dq_list(_n, stream, project, dq_point):
        """Met à jour la liste des configurations DQ filtrées par contexte"""
        if not stream or not project or not dq_point:
            return dbc.Alert("Sélectionne Stream, Projet et DQ Point.", color="light")
        files = list_dq_files("dq_params", stream=stream, project=project, dq_point=dq_point)
        if not files:
            return dbc.Alert(f"Aucune configuration DQ publiée pour {stream} / {project} / {dq_point}.", color="light")
        items = []
        for fn in files:
            items.append(dbc.ListGroupItem([
                html.Div(fn, className="fw-bold"),
                dbc.ButtonGroup([
                    dbc.Button("Modifier", id={"type": "dq-modify", "file": fn}, color="primary", size="sm"),
                    dbc.Button("Dupliquer", id={"type": "dq-duplicate", "file": fn}, color="secondary", size="sm"),
                    dbc.Button("Renommer", id={"type": "dq-rename", "file": fn}, color="info", size="sm"),
                    dbc.Button("Supprimer", id={"type": "dq-delete", "file": fn}, color="danger", size="sm"),
                ], className="mt-2")
            ]))
        hint = html.Div(
            f"Contexte: {stream} / {project} / {dq_point}",
            className="text-muted small mb-2"
        )
        return html.Div([hint, dbc.ListGroup(items)])

    @app.callback(
        Output("dq-create", "href"),
        Input("dq-stream", "value"),
        Input("dq-project", "value"),
        Input("dq-point", "value")
    )
    def update_create_link(stream, project, dq_point):
        """Construit le lien vers la page Build avec les paramètres du contexte"""
        q = []
        if stream:
            q.append(f"stream={stream}")
        if project:
            q.append(f"project={project}")
        if dq_point:
            q.append(f"dq_point={dq_point}")
        query_string = ("?" + "&".join(q)) if q else ""
        return f"/build{query_string}"
    
    # === Action: Modifier ===
    @app.callback(
        Output("url", "pathname", allow_duplicate=True),
        Output("url", "search", allow_duplicate=True),
        Input({"type": "dq-modify", "file": ALL}, "n_clicks"),
        State("dq-stream", "value"),
        State("dq-project", "value"),
        State("dq-point", "value"),
        prevent_initial_call=True
    )
    def modify_config(n_clicks, stream, project, dq_point):
        """Redirige vers Build avec les données du fichier chargées"""
        if not any(n_clicks):
            return no_update, no_update
        
        # Identifier quel bouton a été cliqué
        triggered = ctx.triggered_id
        if not triggered:
            return no_update, no_update
        
        filename = triggered["file"]
        
        # Construire l'URL avec le nom du fichier
        q = []
        if stream:
            q.append(f"stream={stream}")
        if project:
            q.append(f"project={project}")
        if dq_point:
            q.append(f"dq_point={dq_point}")
        q.append(f"load_config={filename}")
        query_string = ("?" + "&".join(q)) if q else ""
        
        return "/build", query_string
    
    # === Action: Dupliquer ===
    @app.callback(
        Output("dq-list", "children", allow_duplicate=True),
        Input({"type": "dq-duplicate", "file": ALL}, "n_clicks"),
        State("dq-stream", "value"),
        State("dq-project", "value"),
        State("dq-point", "value"),
        prevent_initial_call=True
    )
    def duplicate_config(n_clicks, stream, project, dq_point):
        """Duplique une configuration avec un nouveau nom"""
        if not any(n_clicks):
            return no_update
        
        triggered = ctx.triggered_id
        if not triggered:
            return no_update
        
        filename = triggered["file"]
        
        # Générer un nouveau nom avec timestamp
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        base_name = filename.rsplit('.', 1)[0]
        ext = filename.rsplit('.', 1)[1] if '.' in filename else 'json'
        new_filename = f"{base_name}_copie_{timestamp}.{ext}"
        
        # Dupliquer le fichier
        success = duplicate_dq_file(filename, new_filename)
        
        if success:
            # Recharger la liste filtrée par contexte
            files = list_dq_files("dq_params", stream=stream, project=project, dq_point=dq_point)
            if not files:
                return dbc.Alert(f"Aucune configuration DQ publiée pour {stream} / {project} / {dq_point}.", color="light")
            items = []
            for fn in files:
                items.append(dbc.ListGroupItem([
                    html.Div(fn, className="fw-bold"),
                    dbc.ButtonGroup([
                        dbc.Button("Modifier", id={"type": "dq-modify", "file": fn}, color="primary", size="sm"),
                        dbc.Button("Dupliquer", id={"type": "dq-duplicate", "file": fn}, color="secondary", size="sm"),
                        dbc.Button("Renommer", id={"type": "dq-rename", "file": fn}, color="info", size="sm"),
                        dbc.Button("Supprimer", id={"type": "dq-delete", "file": fn}, color="danger", size="sm"),
                    ], className="mt-2")
                ]))
            hint = html.Div(
                [
                    f"Contexte: {stream} / {project} / {dq_point}",
                    html.Br(),
                    dbc.Alert(f"✅ Fichier dupliqué: {new_filename}", color="success", className="mt-2")
                ],
                className="text-muted small mb-2"
            )
            return html.Div([hint, dbc.ListGroup(items)])
        else:
            return dbc.Alert(f"❌ Erreur lors de la duplication de {filename}", color="danger")
    
    # === Action: Renommer - Ouvrir modal ===
    @app.callback(
        Output("rename-modal", "is_open"),
        Output("current-file-action", "data"),
        Output("rename-input", "value"),
        Input({"type": "dq-rename", "file": ALL}, "n_clicks"),
        Input("rename-cancel", "n_clicks"),
        Input("rename-confirm", "n_clicks"),
        State("rename-modal", "is_open"),
        State("current-file-action", "data"),
        prevent_initial_call=True
    )
    def toggle_rename_modal(rename_clicks, cancel_click, confirm_click, is_open, current_file):
        """Gère l'ouverture/fermeture du modal de renommage"""
        triggered = ctx.triggered_id
        
        if not triggered:
            return no_update, no_update, no_update
        
        # Ouverture du modal
        if isinstance(triggered, dict) and triggered.get("type") == "dq-rename":
            if any(rename_clicks):
                filename = triggered["file"]
                return True, filename, filename
        
        # Fermeture du modal
        if triggered in ["rename-cancel", "rename-confirm"]:
            return False, None, ""
        
        return no_update, no_update, no_update
    
    # === Action: Renommer - Confirmer ===
    @app.callback(
        Output("dq-list", "children", allow_duplicate=True),
        Output("rename-feedback", "children"),
        Input("rename-confirm", "n_clicks"),
        State("current-file-action", "data"),
        State("rename-input", "value"),
        State("dq-stream", "value"),
        State("dq-project", "value"),
        State("dq-point", "value"),
        prevent_initial_call=True
    )
    def confirm_rename(n, old_filename, new_filename, stream, project, dq_point):
        """Effectue le renommage du fichier"""
        if not n or not old_filename or not new_filename:
            return no_update, ""
        
        if old_filename == new_filename:
            return no_update, dbc.Alert("Le nom est identique", color="warning", dismissable=True)
        
        # Renommer le fichier
        success = rename_dq_file(old_filename, new_filename)
        
        if success:
            # Recharger la liste filtrée par contexte
            files = list_dq_files("dq_params", stream=stream, project=project, dq_point=dq_point)
            if not files:
                return dbc.Alert(f"Aucune configuration DQ publiée pour {stream} / {project} / {dq_point}.", color="light"), ""
            items = []
            for fn in files:
                items.append(dbc.ListGroupItem([
                    html.Div(fn, className="fw-bold"),
                    dbc.ButtonGroup([
                        dbc.Button("Modifier", id={"type": "dq-modify", "file": fn}, color="primary", size="sm"),
                        dbc.Button("Dupliquer", id={"type": "dq-duplicate", "file": fn}, color="secondary", size="sm"),
                        dbc.Button("Renommer", id={"type": "dq-rename", "file": fn}, color="info", size="sm"),
                        dbc.Button("Supprimer", id={"type": "dq-delete", "file": fn}, color="danger", size="sm"),
                    ], className="mt-2")
                ]))
            hint = html.Div(
                [
                    f"Contexte: {stream} / {project} / {dq_point}",
                    html.Br(),
                    dbc.Alert(f"✅ Fichier renommé: {new_filename}", color="success", className="mt-2")
                ],
                className="text-muted small mb-2"
            )
            return html.Div([hint, dbc.ListGroup(items)]), ""
        else:
            return no_update, dbc.Alert(f"❌ Erreur: fichier déjà existant ou introuvable", color="danger", dismissable=True)
    
    # === Action: Supprimer - Ouvrir modal ===
    @app.callback(
        Output("delete-modal", "is_open"),
        Output("current-file-action", "data", allow_duplicate=True),
        Output("delete-confirm-text", "children"),
        Input({"type": "dq-delete", "file": ALL}, "n_clicks"),
        Input("delete-cancel", "n_clicks"),
        Input("delete-confirm", "n_clicks"),
        State("delete-modal", "is_open"),
        prevent_initial_call=True
    )
    def toggle_delete_modal(delete_clicks, cancel_click, confirm_click, is_open):
        """Gère l'ouverture/fermeture du modal de suppression"""
        triggered = ctx.triggered_id
        
        if not triggered:
            return no_update, no_update, no_update
        
        # Ouverture du modal
        if isinstance(triggered, dict) and triggered.get("type") == "dq-delete":
            if any(delete_clicks):
                filename = triggered["file"]
                return True, filename, f"Êtes-vous sûr de vouloir supprimer '{filename}' ?"
        
        # Fermeture du modal
        if triggered in ["delete-cancel", "delete-confirm"]:
            return False, None, ""
        
        return no_update, no_update, no_update
    
    # === Action: Supprimer - Confirmer ===
    @app.callback(
        Output("dq-list", "children", allow_duplicate=True),
        Input("delete-confirm", "n_clicks"),
        State("current-file-action", "data"),
        State("dq-stream", "value"),
        State("dq-project", "value"),
        State("dq-point", "value"),
        prevent_initial_call=True
    )
    def confirm_delete(n, filename, stream, project, dq_point):
        """Effectue la suppression du fichier"""
        if not n or not filename:
            return no_update
        
        # Supprimer le fichier
        success = delete_dq_file(filename)
        
        if success:
            # Recharger la liste filtrée par contexte
            files = list_dq_files("dq_params", stream=stream, project=project, dq_point=dq_point)
            if not files:
                return dbc.Alert(f"Aucune configuration DQ publiée pour {stream} / {project} / {dq_point}.", color="light")
            items = []
            for fn in files:
                items.append(dbc.ListGroupItem([
                    html.Div(fn, className="fw-bold"),
                    dbc.ButtonGroup([
                        dbc.Button("Modifier", id={"type": "dq-modify", "file": fn}, color="primary", size="sm"),
                        dbc.Button("Dupliquer", id={"type": "dq-duplicate", "file": fn}, color="secondary", size="sm"),
                        dbc.Button("Renommer", id={"type": "dq-rename", "file": fn}, color="info", size="sm"),
                        dbc.Button("Supprimer", id={"type": "dq-delete", "file": fn}, color="danger", size="sm"),
                    ], className="mt-2")
                ]))
            hint = html.Div(
                [
                    f"Contexte: {stream} / {project} / {dq_point}",
                    html.Br(),
                    dbc.Alert(f"✅ Fichier supprimé: {filename}", color="success", className="mt-2")
                ],
                className="text-muted small mb-2"
            )
            return html.Div([hint, dbc.ListGroup(items)])
        else:
            return dbc.Alert(f"❌ Erreur lors de la suppression de {filename}", color="danger")
