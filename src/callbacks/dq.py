# Callbacks de la page DQ Management

from dash import html, Input, Output
import dash_bootstrap_components as dbc
from src.config import STREAMS
from src.utils import list_dq_files


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
        """Met à jour la liste des configurations DQ"""
        if not stream or not project or not dq_point:
            return dbc.Alert("Sélectionne Stream, Projet et DQ Point.", color="light")
        files = list_dq_files("dq_params")
        if not files:
            return dbc.Alert("Aucune configuration DQ publiée.", color="light")
        items = []
        for fn in files:
            items.append(dbc.ListGroupItem([
                html.Div(fn, className="fw-bold"),
                dbc.ButtonGroup([
                    dbc.Button("Modifier", color="primary", size="sm"),
                    dbc.Button("Dupliquer", color="secondary", size="sm"),
                    dbc.Button("Supprimer", color="danger", size="sm"),
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
