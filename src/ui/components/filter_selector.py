# src/ui/components/filter_selector.py
from __future__ import annotations

from typing import Optional
from dash import dcc, html
from dash.dependencies import Input, Output
from dq.filters.filter_loader import list_filters
from src.config.defaults import get_default_stream, get_default_project, get_default_zone

def register_filter_selector(
    app,
    *,
    prefix: str = "dqf",
    default_stream: Optional[str] = None,
    default_project: Optional[str] = None,
    default_zone: Optional[str] = None,
    context_store_id: Optional[str] = None,  # id d'un dcc.Store {'stream','project','zone'}
):
    """
    Bloc UI (Stream/Project/Zone + Filter dropdown) + callbacks.
    - Si context_store_id est fourni, les inputs stream/project/zone sont pilotés par ce store.
    - Sinon, on utilise les defaults (env ou paramètres).
    - Le dropdown est rempli au premier rendu.
    """
    ds = default_stream if default_stream is not None else get_default_stream()
    dp = default_project if default_project is not None else get_default_project()
    dz = default_zone if default_zone is not None else get_default_zone()

    layout = html.Div([
        html.Div([html.Label("Stream"),
                  dcc.Input(id=f"{prefix}-stream", value=ds, type="text", disabled=bool(context_store_id))],
                 style={"marginRight": 8}),
        html.Div([html.Label("Project"),
                  dcc.Input(id=f"{prefix}-project", value=dp, type="text", disabled=bool(context_store_id))],
                 style={"marginRight": 8}),
        html.Div([html.Label("Zone"),
                  dcc.Input(id=f"{prefix}-zone", value=dz, type="text", disabled=bool(context_store_id))],
                 style={"marginRight": 8}),
        html.Div([html.Label("Filtre (banque JSON)"),
                  dcc.Dropdown(id=f"{prefix}-filter", options=[], value=None, placeholder="Choisir un filtre…")],
                 style={"minWidth": 300}),
    ], style={"display": "flex", "gap": "12px", "alignItems": "end"})

    @app.callback(
        Output(f"{prefix}-filter", "options"),
        Output(f"{prefix}-filter", "value"),
        Input(f"{prefix}-stream", "value"),
        Input(f"{prefix}-project", "value"),
        Input(f"{prefix}-zone", "value"),
        prevent_initial_call=False,
    )
    def _refresh_filters(stream, project, zone):
        names = list_filters(stream=stream, project=project, zone=zone)
        options = [{"label": n, "value": n} for n in names]
        value = names[0] if names else None
        return options, value

    if context_store_id:
        @app.callback(
            Output(f"{prefix}-stream", "value"),
            Output(f"{prefix}-project", "value"),
            Output(f"{prefix}-zone", "value"),
            Input(context_store_id, "data"),
            prevent_initial_call=False,
        )
        def _apply_store(data):
            data = data or {}
            return data.get("stream", ds), data.get("project", dp), data.get("zone", dz)

    return layout
