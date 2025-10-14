# app.py — v3.6
try:
    import dataiku
except Exception:
    import dataiku_stub as dataiku

import json, re, urllib.parse as urlparse
from datetime import datetime
from dash import Dash, html, dcc, Input, Output, State, ALL, no_update
import dash_bootstrap_components as dbc
import yaml

external_stylesheets = [dbc.themes.BOOTSTRAP]
app = Dash(__name__, external_stylesheets=external_stylesheets, suppress_callback_exceptions=True)

STREAMS = {
    "Résultats globaux des ventes": [
        "Récolte des résultats par sites",
        "Unification des Résultats"
    ],
    "Qualité des données RH": [
        "Contrôles contrats",
        "Gestion des absences"
    ]
}

# Mapping des datasets par contexte (stream, projet, dq_point)
DATASET_MAPPING = {
    ("Résultats globaux des ventes", "Récolte des résultats par sites", "Extraction"): ["ventes_par_site", "produits_vendus"],
    ("Résultats globaux des ventes", "Récolte des résultats par sites", "Transformation"): ["ventes_par_site", "produits_vendus"],
    ("Résultats globaux des ventes", "Récolte des résultats par sites", "Chargement"): ["resultats_consolides"],
    ("Résultats globaux des ventes", "Unification des Résultats", "Extraction"): ["resultats_consolides"],
    ("Résultats globaux des ventes", "Unification des Résultats", "Transformation"): ["resultats_consolides"],
    ("Résultats globaux des ventes", "Unification des Résultats", "Chargement"): ["resultats_consolides"],
    ("Qualité des données RH", "Contrôles contrats", "Extraction"): ["contrats_employes"],
    ("Qualité des données RH", "Contrôles contrats", "Transformation"): ["contrats_employes"],
    ("Qualité des données RH", "Contrôles contrats", "Chargement"): ["contrats_employes"],
    ("Qualité des données RH", "Gestion des absences", "Extraction"): ["absences_employes", "contrats_employes"],
    ("Qualité des données RH", "Gestion des absences", "Transformation"): ["absences_employes"],
    ("Qualité des données RH", "Gestion des absences", "Chargement"): ["absences_employes"],
}

client = dataiku.api_client()
project = client.get_default_project()

def list_project_datasets(stream=None, projet=None, dq_point=None):
    """Liste les datasets filtrés par contexte (stream, projet, dq_point)"""
    try:
        # Si contexte fourni, utiliser le mapping
        if stream and projet and dq_point:
            key = (stream, projet, dq_point)
            mapped_datasets = DATASET_MAPPING.get(key, [])
            if mapped_datasets:
                return mapped_datasets
        
        # Sinon, retourner tous les datasets disponibles
        return [d["name"] for d in project.list_datasets()]
    except Exception:
        return []

def get_columns_for_dataset(ds_name):
    try:
        ds = dataiku.Dataset(ds_name)
        schema = ds.read_schema() or []
        return [c.get("name") for c in schema if c.get("name")]
    except Exception:
        return []

def safe_id(s):
    return re.sub(r"[^a-zA-Z0-9_]+", "_", s).lower()

def cfg_template():
    return {
        "version":"1.0",
        "globals":{"default_severity":"medium","sample_size":10,"fail_fast":False,"timezone":"Europe/Paris"},
        "context":{},
        "databases":[],
        "metrics":[],
        "tests":[],
        "orchestration":{"order":[],"dependencies":[]}
    }

def parse_query(search: str):
    if not search:
        return {}
    q = urlparse.parse_qs(search.lstrip("?"))
    return {k:(v[0] if isinstance(v, list) and v else v) for k,v in q.items()}

def navbar():
    return dbc.Navbar(
        dbc.Container([
            html.A(dbc.NavbarBrand("DQ App", className="ms-2"), href="/", className="navbar-brand"),
            html.Div(id="crumb", className="ms-auto small text-muted")
        ]),
        color="light", dark=False, className="mb-4"
    )

def stepper(active_idx=0):
    steps = ["1. Datasets", "2. Métriques", "3. Tests", "4. Publication"]
    items = []
    for i, label in enumerate(steps):
        color = "primary" if i==active_idx else "secondary"
        items.append(dbc.Badge(label, color=color, className="me-2 p-2"))
    return html.Div(items, className="mb-3")

def home_page():
    return dbc.Container([
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardHeader("Bienvenue"),
                dbc.CardBody([
                    html.P("Gérer la qualité des données"),
                    dbc.Button("DQ Management", href="/dq", color="primary")
                ])
            ]), md=6, lg=5)
        ], className="g-3")
    ], fluid=True)

# DQ points catalogue (placeholder)
DQ_POINTS = [
    "Extraction",
    "Transformation",
    "Chargement"
]

def dq_page():
    return dbc.Container([
        dbc.Card([dbc.CardHeader("DQ Management"), dbc.CardBody([
            dbc.Row([
                dbc.Col([html.Label("Stream"), dcc.Dropdown(id="dq-stream", options=[{"label": s, "value": s} for s in STREAMS.keys()], placeholder="Select stream", clearable=False)], md=4),
                dbc.Col([html.Label("Project"), dcc.Dropdown(id="dq-project", options=[], placeholder="Select project", disabled=True, clearable=False)], md=4),
                dbc.Col([html.Label("DQ Point"), dcc.Dropdown(id="dq-point", options=[{"label":p,"value":p} for p in DQ_POINTS], placeholder="Select DQ point", clearable=False)], md=4),
            ]),
            html.Div(id="dq-list", className="mt-3"),
            html.A(id="dq-create", className="btn btn-success mt-2 me-2", children="Créer de scratch"),
            dbc.Button("Actualiser", id="dq-refresh", color="secondary", className="mt-2"),
        ])])
    ], fluid=True)

def build_page():
    return dbc.Container([
        html.Div(id="ctx-banner"),
        stepper(0),
        dcc.Store(id="store_datasets", storage_type="memory"),
        dcc.Store(id="store_metrics", storage_type="memory"),
        dcc.Store(id="store_tests", storage_type="memory"),

        dbc.Card([dbc.CardHeader("Étape 1 — Datasets & Aliases"), dbc.CardBody([
            html.Label("Datasets (depuis ./datasets/*.csv)"),
            dcc.Dropdown(id="ds-picker",
                         options=[],
                         multi=True, placeholder="Sélectionne des datasets", persistence=True, persistence_type="session"),
            html.Div(id="alias-mapper", className="mt-3"),
            dbc.Button("Enregistrer les datasets", id="save-datasets", color="primary", className="mt-2"),
            html.Div(id="save-datasets-status", className="text-success mt-2")
        ])], className="mb-3 shadow-sm"),

        stepper(1),
        dbc.Card([dbc.CardHeader("Étape 2 — Métriques"), dbc.CardBody([
            dbc.Tabs([
                dbc.Tab(label="➕ Créer une métrique", tab_id="tab-metric-create", children=[
                    html.Div(className="mt-3", children=[
                        html.Label("Type de métrique"),
                        dcc.Dropdown(id="metric-type", options=[
                            {"label":"row_count","value":"row_count"},
                            {"label":"sum","value":"sum"},
                            {"label":"mean","value":"mean"},
                            {"label":"distinct_count","value":"distinct_count"},
                            {"label":"ratio (metricA / metricB)","value":"ratio"}
                        ], placeholder="Choisir le type", clearable=False, persistence=True, persistence_type="session"),
                        html.Div(id="metric-params", className="mt-3"),
                        dbc.Button("Forcer l'aperçu", id="force-metric-preview", color="secondary", className="mt-2 me-2"),
                        dbc.Button("Ajouter la métrique", id="add-metric", color="primary", className="mt-2"),
                        html.Div(id="add-metric-status", className="text-success mt-2"),
                    ])
                ]),
                dbc.Tab(label="📋 Métriques définies", tab_id="tab-metric-list", children=[
                    html.Div(id="metrics-list", className="mt-3")
                ]),
            ], id="metric-tabs", active_tab="tab-metric-create")
        ])], className="mb-3 shadow-sm"),

        stepper(2),
        dbc.Card([dbc.CardHeader("Étape 3 — Tests"), dbc.CardBody([
            dbc.Tabs([
                dbc.Tab(label="➕ Créer un test", tab_id="tab-test-create", children=[
                    html.Div(className="mt-3", children=[
                        html.Label("Type de test"),
                        dcc.Dropdown(id="test-type", options=[
                            {"label":"null_rate","value":"null_rate"},
                            {"label":"uniqueness","value":"uniqueness"},
                            {"label":"range","value":"range"},
                            {"label":"regex","value":"regex"},
                            {"label":"foreign_key","value":"foreign_key"}
                        ], placeholder="Choisir le type", clearable=False, persistence=True, persistence_type="session"),
                        html.Div(id="test-params", className="mt-3"),
                        dbc.Button("Ajouter le test", id="add-test", color="primary", className="mt-2"),
                        html.Div(id="add-test-status", className="text-success mt-2"),
                    ])
                ]),
                dbc.Tab(label="📋 Tests définis", tab_id="tab-test-list", children=[
                    html.Div(id="tests-list", className="mt-3")
                ]),
            ], id="test-tabs", active_tab="tab-test-create")
        ])], className="mb-3 shadow-sm"),

        stepper(3),
        dbc.Card([dbc.CardHeader("Étape 4 — Prévisualisation & Publication"), dbc.CardBody([
            dbc.Row([
                dbc.Col([html.Label("Managed Folder ID"), dcc.Input(id="folder-id", type="text", value="dq_params")], md=4),
                dbc.Col([html.Label("Nom de la configuration"), dcc.Input(id="cfg-name", type="text", value="default")], md=4),
                dbc.Col([html.Label("Format"),
                         dcc.RadioItems(id="fmt", options=[{"label":"JSON","value":"json"},{"label":"YAML","value":"yaml"}],
                                        value="json", inline=True)], md=4)
            ]),
            html.Pre(id="cfg-preview", className="mt-3", style={"background":"#111","color":"#eee","padding":"1rem","whiteSpace":"pre-wrap"}),
            dbc.Button("✅ Publier", id="publish", color="success"),
            html.Div(id="publish-status", className="text-success mt-2")
        ])], className="mb-5 shadow-sm"),
        dbc.Toast(id="toast", header="Info", is_open=False, dismissable=True, icon="info",
                  style={"position":"fixed","top":20,"right":20,"zIndex":2000})
    ], fluid=True)

app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    navbar(),
    html.Div(id="page-content", children=home_page())
])

app.validation_layout = html.Div([
    dcc.Location(id="url", refresh=False),
    navbar(),
    html.Div(id="page-content"),
    home_page(),
    dq_page(),
    build_page()
])

@app.callback(Output("crumb","children"),
              Input("url","pathname"))
def update_crumb(pathname):
    parts = []
    if pathname == "/":
        parts.append("Home")
    elif pathname == "/dq":
        parts.append("DQ Management")
    elif pathname == "/build":
        parts.append("Build")
    return " / ".join(parts) if parts else ""

@app.callback(
    Output("dq-project","options"),
    Output("dq-project","disabled"),
    Input("dq-stream","value")
)
def on_stream_change(stream):
    if not stream:
        return [], True
    projects = STREAMS.get(stream, [])
    opts = [{"label": p, "value": p} for p in projects]
    return opts, False

@app.callback(Output("dq-list","children"),
              Input("dq-refresh","n_clicks"),
              Input("dq-stream","value"),
              Input("dq-project","value"),
              Input("dq-point","value"))
def update_dq_list(_n, stream, project, dq_point):
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
    hint = html.Div(f"Contexte: {stream} / {project} / {dq_point}", className="text-muted small mb-2")
    return html.Div([hint, dbc.ListGroup(items)])

@app.callback(
    Output("dq-create","href"),
    Input("dq-stream","value"),
    Input("dq-project","value"),
    Input("dq-point","value")
)
def update_create_link(stream, project, dq_point):
    # Build the href dynamically based on dropdown selections
    q = []
    if stream: q.append(f"stream={stream}")
    if project: q.append(f"project={project}")
    if dq_point: q.append(f"dq_point={dq_point}")
    query_string = ("?" + "&".join(q)) if q else ""
    return f"/build{query_string}"

@app.callback(Output("page-content","children"), Input("url","pathname"))
def display_page(pathname):
    # URL-decode and strip query parameters if they're encoded in the pathname
    decoded_path = urlparse.unquote(pathname) if pathname else pathname
    clean_path = decoded_path.split('?')[0] if decoded_path else decoded_path
    if clean_path in ("/","",None):
        return home_page()
    if clean_path == "/build":
        return build_page()
    if clean_path == "/dq":
        return dq_page()
    return dbc.Container([dbc.Alert("🛠️ Bientôt disponible. Revenez à la Construction pour l’instant.", color="info")], fluid=True)

@app.callback(Output("ctx-banner","children"), Input("url","href"))
def update_ctx_banner(href):
    # Extract query params from full URL (URL-decode first!)
    decoded_href = urlparse.unquote(href) if href else ""
    q = {}
    if decoded_href and '?' in decoded_href:
        query_string = '?' + decoded_href.split('?', 1)[1]
        q = parse_query(query_string)
    else:
        q = {}
    if not q.get("stream") or not q.get("project"):
        return dbc.Alert("Contexte non défini (utilise l’accueil pour choisir un Stream et un Projet).", color="warning", className="mb-3")
    return dbc.Alert(f"Contexte: Stream = {q['stream']} • Projet = {q['project']}", color="info", className="mb-3")

@app.callback(
    Output("ds-picker","options"), 
    Input("url","href")
)
def update_dataset_options(href):
    """Met à jour les datasets disponibles selon le contexte"""
    # Extract query params from full URL (URL-decode first!)
    decoded_href = urlparse.unquote(href) if href else ""
    q = {}
    if decoded_href and '?' in decoded_href:
        query_string = '?' + decoded_href.split('?', 1)[1]
        q = parse_query(query_string)
    else:
        q = {}
    stream = q.get("stream")
    projet = q.get("project") 
    dq_point = q.get("dq_point")
    
    datasets = list_project_datasets(stream, projet, dq_point)
    return [{"label": ds, "value": ds} for ds in datasets]

@app.callback(Output("manage-banner","children"), Input("manage-url","search"))
def update_manage_banner(search):
    q = parse_query(search or "")
    if not q.get("stream") or not q.get("project") or not q.get("dq_point"):
        return dbc.Alert("Contexte incomplet pour la gestion DQ.", color="warning")
    return dbc.Alert(f"Gestion DQ — Stream={q['stream']} • Projet={q['project']} • Point={q['dq_point']}", color="info")

@app.callback(Output("alias-mapper","children"), Input("ds-picker","value"))
def render_alias_mapper(selected):
    if not selected:
        return html.Div([html.Em("Sélectionne au moins un dataset.")])
    rows = []
    for ds in selected:
        rows.append(dbc.Row([
            dbc.Col(html.Div(ds), md=6),
            dbc.Col(dcc.Input(id={"role":"alias-input","ds":ds}, type="text", value=ds.lower(),
                              style={"width":"100%"}, persistence=True,
                              persistence_type="session", autoComplete="off"), md=6)
        ], className="py-1 border-bottom"))
    return dbc.Container(rows, fluid=True)

@app.callback(
    Output("save-datasets-status","children"),
    Output("store_datasets","data"),
    Input("save-datasets","n_clicks"),
    State("ds-picker","value"),
    State({"role":"alias-input","ds":ALL},"value"),
    State({"role":"alias-input","ds":ALL},"id")
)
def save_datasets(n, selected, alias_values, alias_ids):
    if not n:
        return "", None
    if not selected:
        return "Aucun dataset sélectionné.", None
    alias_map = {}
    if alias_values and alias_ids:
        for v, i in zip(alias_values, alias_ids):
            alias_map[i["ds"]] = v or i["ds"].lower()
    data = [{"alias": alias_map.get(ds, ds.lower()), "dataset": ds} for ds in selected]
    return f"{len(data)} dataset(s) enregistrés.", data

# ---- Metrics ----
@app.callback(Output("metric-params","children"),
              Input("metric-type","value"),
              State("store_datasets","data"))
def render_metric_form(metric_type, ds_data):
    if not metric_type:
        return dbc.Alert("Choisis un type de métrique.", color="light")
    ds_aliases = [d["alias"] for d in (ds_data or [])]
    if not ds_aliases:
        return dbc.Alert("Enregistre d'abord des datasets (Étape 1), puis reviens ici.", color="warning")

    common_top = dbc.Row([
        dbc.Col([html.Label("ID de la métrique"),
                 dcc.Input(id={"role":"metric-id"}, type="text", value="", style={"width":"100%"},
                           persistence=True, persistence_type="session")], md=6),
        dbc.Col([html.Label("Base (alias)"),
                 dcc.Dropdown(id={"role":"metric-db"}, options=[{"label":a,"value":a} for a in ds_aliases],
                              clearable=False, persistence=True, persistence_type="session")], md=6),
    ])

    if metric_type in ("sum","mean","distinct_count"):
        column_ctrl = dbc.Row([dbc.Col([html.Label("Colonne"),
                               dcc.Dropdown(id={"role":"metric-column"}, options=[], placeholder="Choisir une colonne",
                                            clearable=False, persistence=True, persistence_type="session")], md=6)])
    else:
        column_ctrl = html.Div()

    extras = html.Div()
    if metric_type == "row_count":
        extras = dbc.Row([dbc.Col([html.Label("Filtre WHERE (optionnel)"),
                                   dcc.Input(id={"role":"metric-where"}, type="text", value="", style={"width":"100%"},
                                             persistence=True, persistence_type="session",
                                             autoComplete="off")], md=12)])
    elif metric_type in ("sum","mean"):
        extras = dbc.Row([dbc.Col([html.Label("Filtre WHERE (optionnel)"),
                                   dcc.Input(id={"role":"metric-where"}, type="text", value="", style={"width":"100%"},
                                             persistence=True, persistence_type="session",
                                             autoComplete="off")], md=12)])
    elif metric_type == "ratio":
        extras = dbc.Row([dbc.Col([html.Label("Expr (metricA / metricB) — IDs de métriques déjà définies"),
                                   dcc.Input(id={"role":"metric-expr"}, type="text", value="", style={"width":"100%"},
                                             persistence=True, persistence_type="session",
                                             autoComplete="off")], md=12)])

    helper = html.Div(id="metric-helper", className="text-muted small mt-2")
    preview = html.Div([html.H6("Prévisualisation"),
                        html.Pre(id={"role":"metric-preview"}, style={"background":"#222","color":"#eee","padding":"0.75rem"})])
    return html.Div([common_top, html.Br(), column_ctrl, helper, html.Br(), extras, html.Hr(), preview])

@app.callback(
    Output({"role":"metric-column"},"options"),
    Output("toast","is_open", allow_duplicate=True),
    Output("toast","children", allow_duplicate=True),
    Input({"role":"metric-db"},"value", ALL),
    State("store_datasets","data"),
    prevent_initial_call=True)
def fill_metric_columns(db_values, ds_data):
    db_alias = (db_values[0] if db_values else None)
    if not db_alias or not ds_data:
        return [], False, ""
    ds_name = next((d["dataset"] for d in ds_data if d["alias"] == db_alias), None)
    if not ds_name:
        return [], True, f"Aucun dataset associé à l'alias « {db_alias} »."
    cols = get_columns_for_dataset(ds_name)
    if not cols:
        return [], True, f"Aucune colonne lisible pour « {ds_name} ». Vérifie le CSV."
    opts = [{"label":c,"value":c} for c in cols]
    return opts, False, ""

@app.callback(Output("metric-helper","children"),
              Input({"role":"metric-column"},"options"))
def metric_helper(opts):
    if opts is None:
        return ""
    if len(opts)==0:
        return "Aucune colonne détectée. Assure-toi d’avoir cliqué « Enregistrer les datasets » à l’étape 1."
    return f"{len(opts)} colonne(s) disponibles."

@app.callback(Output({"role":"metric-preview"},"children"),
              Input("force-metric-preview","n_clicks"),
              Input("metric-type","value"),
              Input({"role":"metric-id"},"value", ALL),
              Input({"role":"metric-db"},"value", ALL),
              Input({"role":"metric-column"},"value", ALL),
              Input({"role":"metric-where"},"value", ALL),
              Input({"role":"metric-expr"},"value", ALL),
              prevent_initial_call=True)
def preview_metric(force, mtype, mid_list, mdb_list, mcol_list, mwhere_list, mexpr_list):
    if not mtype: return ""
    # Helper function to extract first value (handle both list and non-list)
    def first(val):
        if val is None:
            return None
        if isinstance(val, list):
            return val[0] if val else None
        return val
    
    mid   = first(mid_list)
    mdb   = first(mdb_list)
    mcol  = first(mcol_list)
    mwhere= first(mwhere_list)
    mexpr = first(mexpr_list)

    obj = {"id": (mid or safe_id(f"m_{mtype}_{mdb or ''}_{mcol or ''}")), "type": mtype}
    if mtype in ("row_count","sum","mean"):
        obj.update({"database": mdb or ""})
        if mtype in ("sum","mean"): obj["column"] = mcol or ""
        if mwhere: obj["where"] = mwhere
    elif mtype == "distinct_count":
        obj.update({"database": mdb or "", "column": mcol or ""})
    elif mtype == "ratio":
        obj.update({"expr": (mexpr or "")})
    return json.dumps(obj, ensure_ascii=False, indent=2)

@app.callback(
    Output("add-metric-status","children"),
    Output("store_metrics","data"),
    Output("metrics-list","children"),
    Output("metric-tabs","active_tab"),
    Input("add-metric","n_clicks"),
    State({"role":"metric-preview"},"children", ALL),
    State("store_metrics","data"),
    State("metric-type","value"),
    State({"role":"metric-id"},"value", ALL),
    State({"role":"metric-db"},"value", ALL),
    State({"role":"metric-column"},"value", ALL),
    State({"role":"metric-where"},"value", ALL),
    State({"role":"metric-expr"},"value", ALL),
)
def add_metric(n, preview_list, metrics, mtype, mid_list, mdb_list, mcol_list, mwhere_list, mexpr_list):
    if not n:
        return "", metrics, "", no_update
    
    # Helper function to extract first value (handle both list and non-list)
    def first(val):
        if val is None:
            return None
        if isinstance(val, list):
            return val[0] if val else None
        return val
    
    preview_text = first(preview_list)
    m = None
    if preview_text:
        try:
            m = json.loads(preview_text)
        except Exception:
            m = None
    if m is None:
        mid   = first(mid_list)
        mdb   = first(mdb_list)
        mcol  = first(mcol_list)
        mwhere= first(mwhere_list)
        mexpr = first(mexpr_list)
        if not mtype:
            return "Prévisualisation vide/invalide.", metrics, no_update, no_update
        m = {"id": (mid or safe_id(f"m_{mtype}_{mdb or ''}_{mcol or ''}")), "type": mtype}
        if mtype in ("row_count","sum","mean"):
            m.update({"database": mdb or ""})
            if mtype in ("sum","mean"):
                m["column"] = mcol or ""
            if mwhere:
                m["where"] = mwhere
        elif mtype == "distinct_count":
            m.update({"database": mdb or "", "column": mcol or ""})
        elif mtype == "ratio":
            m.update({"expr": (mexpr or "")})
    metrics = (metrics or [])
    existing = {x.get("id") for x in metrics}
    base_id = m.get("id") or "m"
    uid, k = base_id, 2
    while uid in existing:
        uid = f"{base_id}_{k}"; k += 1
    m["id"] = uid
    metrics.append(m)
    items = [html.Pre(json.dumps(x, ensure_ascii=False, indent=2), className="p-2 mb-2", style={"background":"#111","color":"#eee"}) for x in metrics]
    return f"Métrique ajoutée: {uid}", metrics, html.Div(items), "tab-metric-list"

# ---- Tests ----
@app.callback(Output("test-params","children"),
              Input("test-type","value"),
              State("store_datasets","data"),
              State("store_metrics","data"))
def render_test_form(test_type, ds_data, metrics):
    if not test_type:
        return dbc.Alert("Choisis un type de test.", color="light")
    ds_aliases = [d["alias"] for d in (ds_data or [])]
    if not ds_aliases:
        return dbc.Alert("Enregistre d'abord des datasets.", color="warning")

    common = dbc.Row([
        dbc.Col([html.Label("ID du test"),
                 dcc.Input(id={"role":"test-id"}, type="text", value="", style={"width":"100%"},
                           persistence=True, persistence_type="session",
                           autoComplete="off")], md=6),
        dbc.Col([html.Label("Sévérité"),
                 dcc.Dropdown(id={"role":"test-sev"},
                              options=[{"label":x,"value":x} for x in ["low","medium","high"]],
                              value="medium", clearable=False, persistence=True, persistence_type="session")], md=3),
        dbc.Col([html.Label("Échantillon si échec"),
                 dcc.Checklist(id={"role":"test-sof"}, options=[{"label":" Oui","value":"yes"}], value=["yes"],
                               persistence=True, persistence_type="session")], md=3),
    ])

    if test_type in ("null_rate","uniqueness","range","regex"):
        db_ctrl = dbc.Row([dbc.Col([html.Label("Base (alias)"),
                                    dcc.Dropdown(id={"role":"test-db"},
                                                 options=[{"label":a,"value":a} for a in ds_aliases],
                                                 clearable=False, persistence=True, persistence_type="session")], md=6)])
        col_ctrl = dbc.Row([dbc.Col([html.Label("Colonne"),
                                     dcc.Dropdown(id={"role":"test-col"}, options=[], placeholder="Choisir une colonne",
                                                  clearable=False, persistence=True, persistence_type="session")], md=6)])
        extra = html.Div()
        if test_type == "range":
            extra = dbc.Row([
                dbc.Col([html.Label("Min"), dcc.Input(id={"role":"test-min"}, type="text", value="0",
                                                      persistence=True, persistence_type="session",
                                                      autoComplete="off")], md=3),
                dbc.Col([html.Label("Max"), dcc.Input(id={"role":"test-max"}, type="text", value="100",
                                                      persistence=True, persistence_type="session",
                                                      autoComplete="off")], md=3),
            ])
        if test_type == "regex":
            extra = dbc.Row([dbc.Col([html.Label("Pattern (regex)"),
                                      dcc.Input(id={"role":"test-pattern"}, type="text",
                                                value=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
                                                style={"width":"100%"}, persistence=True, persistence_type="session",
                                                autoComplete="off")], md=12)])
        thresh = dbc.Row([
            dbc.Col([html.Label("Opérateur"),
                     dcc.Dropdown(id={"role":"test-op"},
                                  options=[{"label":x,"value":x} for x in ["<=","<",">=",">","=","!="]],
                                  value="<=", clearable=False, persistence=True, persistence_type="session")], md=3),
            dbc.Col([html.Label("Valeur"),
                     dcc.Input(id={"role":"test-thr"}, type="text", value="0.005",
                               persistence=True, persistence_type="session",
                               autoComplete="off")], md=3),
        ])
        preview = html.Div([html.H6("Prévisualisation du test"),
                            html.Pre(id={"role":"test-preview"}, style={"background":"#222","color":"#eee","padding":"0.75rem"})])
        return html.Div([common, html.Br(), db_ctrl, col_ctrl, html.Br(), extra, html.Br(), thresh, html.Hr(), preview])

    if test_type == "foreign_key":
        db1 = dbc.Row([dbc.Col([html.Label("Base (alias)"),
                                dcc.Dropdown(id={"role":"test-db"}, options=[{"label":a,"value":a} for a in ds_aliases],
                                             clearable=False, persistence=True, persistence_type="session")], md=6)])
        col1 = dbc.Row([dbc.Col([html.Label("Colonne"),
                                 dcc.Dropdown(id={"role":"test-col"}, options=[], placeholder="Choisir une colonne",
                                              clearable=False, persistence=True, persistence_type="session")], md=6)])
        db2 = dbc.Row([dbc.Col([html.Label("Ref Base (alias)"),
                                dcc.Dropdown(id={"role":"test-ref-db"}, options=[{"label":a,"value":a} for a in ds_aliases],
                                             clearable=False, persistence=True, persistence_type="session")], md=6)])
        col2 = dbc.Row([dbc.Col([html.Label("Ref Colonne"),
                                 dcc.Dropdown(id={"role":"test-ref-col"}, options=[], placeholder="Choisir une colonne",
                                              clearable=False, persistence=True, persistence_type="session")], md=6)])
        preview = html.Div([html.H6("Prévisualisation du test"),
                            html.Pre(id={"role":"test-preview"}, style={"background":"#222","color":"#eee","padding":"0.75rem"})])
        return html.Div([common, html.Br(), db1, col1, db2, col2, html.Hr(), preview])

    return dbc.Alert("Type non géré pour l'instant.", color="warning")

@app.callback(
    Output({"role":"test-col"},"options"),
    Output("toast","is_open", allow_duplicate=True),
    Output("toast","children", allow_duplicate=True),
    Input({"role":"test-db"},"value", ALL),
    State("store_datasets","data"),
    prevent_initial_call=True)
def fill_test_columns(db_values, ds_data):
    def first(val):
        if val is None:
            return None
        if isinstance(val, list):
            return val[0] if val else None
        return val
    
    db_alias = first(db_values)
    if not db_alias or not ds_data:
        return [], False, ""
    ds_name = next((d["dataset"] for d in ds_data if d["alias"] == db_alias), None)
    if not ds_name:
        return [], True, f"Aucun dataset associé à l'alias « {db_alias} »."
    cols = get_columns_for_dataset(ds_name)
    if not cols:
        return [], True, f"Aucune colonne lisible pour « {ds_name} ». Vérifie le CSV."
    opts = [{"label":c,"value":c} for c in cols]
    return opts, False, ""

@app.callback(Output({"role":"test-ref-col"},"options"),
              Input({"role":"test-ref-db"},"value", ALL),
              State("store_datasets","data"),
              prevent_initial_call=True)
def fill_test_ref_columns(db_values, ds_data):
    def first(val):
        if val is None:
            return None
        if isinstance(val, list):
            return val[0] if val else None
        return val
    
    db_alias = first(db_values)
    if not db_alias or not ds_data:
        return []
    ds_name = next((d["dataset"] for d in ds_data if d["alias"] == db_alias), None)
    if not ds_name:
        return []
    cols = get_columns_for_dataset(ds_name)
    opts = [{"label":c,"value":c} for c in cols]
    return opts

@app.callback(Output({"role":"test-preview"},"children"),
              Input("test-type","value"),
              Input({"role":"test-id"},"value", ALL),
              Input({"role":"test-sev"},"value", ALL),
              Input({"role":"test-sof"},"value", ALL),
              Input({"role":"test-db"},"value", ALL),
              Input({"role":"test-col"},"value", ALL),
              Input({"role":"test-op"},"value", ALL),
              Input({"role":"test-thr"},"value", ALL),
              Input({"role":"test-min"},"value", ALL),
              Input({"role":"test-max"},"value", ALL),
              Input({"role":"test-pattern"},"value", ALL),
              Input({"role":"test-ref-db"},"value", ALL),
              Input({"role":"test-ref-col"},"value", ALL),
              prevent_initial_call=True)
def preview_test(ttype, tid_list, sev_list, sof_list, db_list, col_list, op_list, thr_list, vmin_list, vmax_list, pat_list, refdb_list, refcol_list):
    if not ttype: return ""
    def first(val, default=None):
        if val is None:
            return default
        if isinstance(val, list):
            return val[0] if val else default
        return val
    tid, sev, sof = first(tid_list), first(sev_list, "medium"), first(sof_list, [])
    db, col = first(db_list), first(col_list)
    op, thr = first(op_list), first(thr_list)
    vmin, vmax = first(vmin_list), first(vmax_list)
    pat = first(pat_list)
    refdb, refcol = first(refdb_list), first(refcol_list)

    obj = {"id": tid or safe_id(f"t_{ttype}_{db or ''}_{col or ''}"),
           "type": ttype, "severity": (sev or "medium"),
           "sample_on_fail": ("yes" in (sof or []))}
    if ttype in ("null_rate","uniqueness","range","regex"):
        obj.update({"database": db or "", "column": col or ""})
        if ttype == "range":
            obj.update({"min": vmin, "max": vmax})
        if ttype == "regex":
            obj.update({"pattern": pat})
        if op and thr is not None:
            obj["threshold"] = {"op": op, "value": thr}
    elif ttype == "foreign_key":
        obj.update({"database": db or "", "column": col or "",
                    "ref": {"database": refdb or "", "column": refcol or ""}})
    return json.dumps(obj, ensure_ascii=False, indent=2)

@app.callback(
    Output("add-test-status","children"),
    Output("store_tests","data"),
    Output("tests-list","children"),
    Output("test-tabs","active_tab"),
    Input("add-test","n_clicks"),
    State({"role":"test-preview"},"children", ALL),
    State("store_tests","data"),
    State("test-type","value"),
    State({"role":"test-id"},"value", ALL),
    State({"role":"test-sev"},"value", ALL),
    State({"role":"test-sof"},"value", ALL),
    State({"role":"test-db"},"value", ALL),
    State({"role":"test-col"},"value", ALL),
    State({"role":"test-op"},"value", ALL),
    State({"role":"test-thr"},"value", ALL),
    State({"role":"test-min"},"value", ALL),
    State({"role":"test-max"},"value", ALL),
    State({"role":"test-pattern"},"value", ALL),
    State({"role":"test-ref-db"},"value", ALL),
    State({"role":"test-ref-col"},"value", ALL),
)
def add_test(n, preview_list, tests, ttype, tid_list, sev_list, sof_list, db_list, col_list, op_list, thr_list, vmin_list, vmax_list, pat_list, refdb_list, refcol_list):
    if not n:
        return "", tests, "", no_update
    
    def first(val, default=None):
        if val is None:
            return default
        if isinstance(val, list):
            return val[0] if val else default
        return val
    
    preview_text = first(preview_list)
    t = None
    if preview_text:
        try:
            t = json.loads(preview_text)
        except Exception:
            t = None
    if t is None:
        if not ttype:
            return "Prévisualisation vide/invalide.", tests, no_update, no_update
        tid, sev, sof = first(tid_list), first(sev_list, "medium"), first(sof_list, [])
        db, col = first(db_list), first(col_list)
        op, thr = first(op_list), first(thr_list)
        vmin, vmax = first(vmin_list), first(vmax_list)
        pat = first(pat_list)
        refdb, refcol = first(refdb_list), first(refcol_list)
        t = {"id": tid or safe_id(f"t_{ttype}_{db or ''}_{col or ''}"),
             "type": ttype, "severity": (sev or "medium"),
             "sample_on_fail": ("yes" in (sof or []))}
        if ttype in ("null_rate","uniqueness","range","regex"):
            t.update({"database": db or "", "column": col or ""})
            if ttype == "range":
                t.update({"min": vmin, "max": vmax})
            if ttype == "regex":
                t.update({"pattern": pat})
            if op and thr is not None:
                t["threshold"] = {"op": op, "value": thr}
        elif ttype == "foreign_key":
            t.update({"database": db or "", "column": col or "",
                      "ref": {"database": refdb or "", "column": refcol or ""}})
    tests = (tests or [])
    existing = {x.get("id") for x in tests}
    base_id = t.get("id") or "t"
    uid, k = base_id, 2
    while uid in existing:
        uid = f"{base_id}_{k}"; k += 1
    t["id"] = uid
    tests.append(t)
    items = [html.Pre(json.dumps(x, ensure_ascii=False, indent=2), className="p-2 mb-2", style={"background":"#111","color":"#eee"}) for x in tests]
    return f"Test ajouté: {uid}", tests, html.Div(items), "tab-test-list"

@app.callback(Output("cfg-preview","children"),
              Input("store_datasets","data"),
              Input("store_metrics","data"),
              Input("store_tests","data"),
              Input("fmt","value"),
              State("url","search"))
def render_cfg_preview(datasets, metrics, tests, fmt, search):
    q = parse_query(search or "")
    cfg = cfg_template()
    cfg["context"] = {"stream": q.get("stream"), "project": q.get("project")}
    cfg["databases"] = datasets or []
    cfg["metrics"] = metrics or []
    cfg["tests"] = tests or []
    cfg["orchestration"]["order"] = [*(m.get("id") for m in (metrics or []) if m.get("id")),
                                     *(t.get("id") for t in (tests or []) if t.get("id"))]
    try:
        if fmt == "yaml":
            return yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True)
        else:
            return json.dumps(cfg, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Erreur de sérialisation: {e}"

def list_dq_files(folder_id="dq_params"):
    try:
        folder = dataiku.Folder(folder_id)
    except Exception:
        return []
    import os
    path = getattr(folder, "path", None)
    if not path or not os.path.isdir(path):
        return []
    return sorted([fn for fn in os.listdir(path) if fn.startswith("dq_config_") and (fn.endswith(".json") or fn.endswith(".yaml"))])

@app.callback(Output("publish-status","children"),
              Input("publish","n_clicks"),
              State("cfg-preview","children"),
              State("fmt","value"),
              State("folder-id","value"),
              State("cfg-name","value"))
def publish_cfg(n, preview_text, fmt, folder_id, cfg_name):
    if not n:
        return ""
    if not preview_text:
        return "Aperçu vide : rien à publier."
    try:
        folder = dataiku.Folder(folder_id or "dq_params")
    except Exception as e:
        return f"Erreur: folder '{folder_id}' introuvable ({e})"
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    fname = f"dq_config_{cfg_name or 'default'}_{ts}." + ("yaml" if fmt=='yaml' else "json")
    try:
        folder.upload_data(fname, preview_text.encode("utf-8"))
        return f"Publié : {fname} → Folder '{folder_id or 'dq_params'}'"
    except Exception as e:
        return f"Erreur de publication : {e}"

if __name__ == "__main__":
    app.run(debug=True)
