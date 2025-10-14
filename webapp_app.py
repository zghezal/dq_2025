# webapp_app.py — Dataiku DSS Webapp (Dash legacy)
from dataiku import dash
import dataiku, json, re
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output, State
from datetime import datetime

try:
    import yaml
except Exception:
    yaml = None

app = dash.get_app()

client = dataiku.api_client()
project = client.get_default_project()

def list_project_datasets():
    try:
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
        "version": "1.0",
        "globals": {"default_severity":"medium","sample_size":10,"fail_fast":False,"timezone":"Europe/Paris"},
        "databases": [], "metrics": [], "tests": [], "orchestration":{"order": [], "dependencies": []}
    }

def navbar():
    return html.Div([
        dcc.Location(id="url", refresh=False),
        html.Div([
            html.A("Accueil", href="/", style={"marginRight":"1rem"}),
            html.A("Construction", href="/build", style={"marginRight":"1rem"}),
            html.A("Modification", href="/modify", style={"marginRight":"1rem"}),
            html.A("Lancer un DQ report", href="/run", style={"marginRight":"1rem"}),
            html.A("Visualisation DQ report", href="/view"),
        ], style={"marginBottom":"1rem"})
    ])

def home_page():
    card_style = {"border":"1px solid #ddd","padding":"1rem","borderRadius":"8px","width":"22%","minWidth":"220px"}
    return html.Div([
        html.H2("🧭 Accueil — Data Quality App"),
        html.Div([
            html.Div([html.H4("Construction de DQ"), html.P("Créer une nouvelle configuration"), html.A("Ouvrir", href="/build")], style=card_style),
            html.Div([html.H4("Modification de DQ"), html.P("Modifier une configuration existante"), html.A("Ouvrir", href="/modify")], style=card_style),
            html.Div([html.H4("Lancer un DQ report"), html.P("Déclencher une exécution DQ"), html.A("Ouvrir", href="/run")], style=card_style),
            html.Div([html.H4("Visualisation DQ report"), html.P("Explorer un rapport DQ"), html.A("Ouvrir", href="/view")], style=card_style),
        ], style={"display":"flex","justifyContent":"space-between","gap":"1rem","flexWrap":"wrap","marginTop":"1rem"})
    ])

def build_page():
    return html.Div([
        dcc.Store(id="store_datasets", storage_type="memory"),
        dcc.Store(id="store_metrics", storage_type="memory"),
        dcc.Store(id="store_tests", storage_type="memory"),
        html.H3("Étape 1 — Datasets & Aliases"),
        html.Div([
            html.Label("Datasets du projet"),
            dcc.Dropdown(id="ds-picker", options=[{"label": n, "value": n} for n in list_project_datasets()], multi=True, placeholder="Sélectionne des datasets"),
        ], style={"maxWidth":"700px"}),
        html.Br(),
        html.Div(id="alias-mapper"),
        html.Button("Enregistrer les datasets", id="save-datasets", n_clicks=0),
        html.Div(id="save-datasets-status", style={"marginTop":".5rem","color":"#0a6"}),
        html.Hr(),

        html.H3("Étape 2 — Ajouter une métrique"),
        html.Div([
            html.Label("Type de métrique"),
            dcc.Dropdown(id="metric-type", options=[
                {"label":"row_count","value":"row_count"},
                {"label":"sum","value":"sum"},
                {"label":"mean","value":"mean"},
                {"label":"distinct_count","value":"distinct_count"},
                {"label":"ratio (metricA / metricB)","value":"ratio"}
            ], placeholder="Choisir le type"),
        ], style={"maxWidth":"500px"}),
        html.Br(),
        html.Div(id="metric-params"),
        html.Br(),
        html.Div([html.Button("Ajouter la métrique", id="add-metric", n_clicks=0, style={"marginRight":"1rem"}),
                  html.Span(id="add-metric-status", style={"color":"#0a6"})]),
        html.Br(),
        html.H4("Métriques définies"),
        html.Div(id="metrics-list"),
        html.Hr(),

        html.H3("Étape 3 — Ajouter un test"),
        html.Div([
            html.Label("Type de test"),
            dcc.Dropdown(id="test-type", options=[
                {"label":"null_rate","value":"null_rate"},
                {"label":"uniqueness","value":"uniqueness"},
                {"label":"range","value":"range"},
                {"label":"regex","value":"regex"},
                {"label":"foreign_key","value":"foreign_key"}
            ], placeholder="Choisir le type"),
        ], style={"maxWidth":"500px"}),
        html.Br(),
        html.Div(id="test-params"),
        html.Br(),
        html.Div([html.Button("Ajouter le test", id="add-test", n_clicks=0, style={"marginRight":"1rem"}),
                  html.Span(id="add-test-status", style={"color":"#0a6"})]),
        html.Br(),
        html.H4("Tests définis"),
        html.Div(id="tests-list"),
        html.Hr(),

        html.H3("Étape 4 — Prévisualisation & Publication"),
        html.Div([
            html.Div([html.Label("Managed Folder ID"), dcc.Input(id="folder-id", type="text", value="dq_params")], style={"flex":"1","padding":"0 .5rem"}),
            html.Div([html.Label("Nom de la configuration"), dcc.Input(id="cfg-name", type="text", value="default")], style={"flex":"1","padding":"0 .5rem"}),
            html.Div([html.Label("Format"),
                      dcc.RadioItems(id="fmt", options=[{"label":"JSON","value":"json"}]+([{"label":"YAML","value":"yaml"}] if yaml else []),
                                     value="json", labelStyle={"display":"inline-block","marginRight":"1rem"})], style={"flex":"1","padding":"0 .5rem"}),
        ], style={"display":"flex","flexWrap":"wrap","maxWidth":"900px"}),
        html.Br(),
        html.Pre(id="cfg-preview", style={"background":"#111","color":"#eee","padding":"1rem","whiteSpace":"pre-wrap"}),
        html.Button("✅ Publier", id="publish", n_clicks=0),
        html.Div(id="publish-status", style={"marginTop":".5rem","color":"#0a6"})
    ])

app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    navbar(),
    html.Div(id="page-content")
])

@app.callback(Output("page-content","children"), [Input("url","pathname")])
def display_page(pathname):
    if pathname in ("/","",None):
        return home_page()
    if pathname == "/build":
        return build_page()
    title = {"modify":"Modification de DQ","run":"Lancer un DQ report","view":"Visualisation DQ report"}.get(pathname.strip("/"), "Page")
    return html.Div([html.H2(title), html.P("🛠️ Bientôt disponible. ← Accueil"), html.A("← Accueil", href="/")])

# ----- Datasets
@app.callback(Output("alias-mapper","children"), [Input("ds-picker","value")])
def render_alias_mapper(selected):
    if not selected:
        return html.Div([html.Em("Sélectionne au moins un dataset.")])
    rows = []
    for ds in selected:
        rows.append(html.Div([
            html.Div([html.Label(ds)], style={"flex":"2"}),
            html.Div([dcc.Input(id={"type":"alias-input","ds":ds}, type="text", value=ds.lower(), style={"width":"100%"})], style={"flex":"3"}),
        ], style={"display":"flex","gap":"1rem","padding":".25rem 0","borderBottom":"1px dotted #eee"}))
    return html.Div(rows, style={"maxWidth":"700px"})

@app.callback(
    Output("save-datasets-status","children"),
    Output("store_datasets","data"),
    [Input("save-datasets","n_clicks")],
    [State("ds-picker","value"),
     State({"type":"alias-input","ds":dash.dependencies.ALL},"value"),
     State({"type":"alias-input","ds":dash.dependencies.ALL},"id")]
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

# ----- Metrics
@app.callback(Output("metric-params","children"),
              [Input("metric-type","value"),
               Input("store_datasets","data")])
def render_metric_form(metric_type, ds_data):
    if not metric_type:
        return html.Div([html.Em("Choisis un type de métrique.")])
    ds_aliases = [d["alias"] for d in (ds_data or [])]
    if not ds_aliases:
        return html.Div([html.Em("Enregistre d'abord des datasets.")])

    common_top = html.Div([
        html.Div([html.Label("ID de la métrique"), dcc.Input(id="metric-id", type="text", value="")], style={"flex":"2","padding":"0 .5rem"}),
        html.Div([html.Label("Base (alias)"), dcc.Dropdown(id="metric-db", options=[{"label":a,"value":a} for a in ds_aliases])], style={"flex":"2","padding":"0 .5rem"}),
    ], style={"display":"flex","flexWrap":"wrap"})

    if metric_type in ("sum","mean","distinct_count"):
        column_ctrl = html.Div([html.Label("Colonne"), dcc.Dropdown(id="metric-column", options=[], placeholder="Choisir une colonne")])
    else:
        column_ctrl = html.Div([])

    extra = []
    if metric_type == "row_count":
        extra = [html.Label("Filtre WHERE (optionnel)"), dcc.Input(id="metric-where", type="text", value="", style={"width":"100%"})]
    elif metric_type in ("sum","mean"):
        extra = [html.Label("Filtre WHERE (optionnel)"), dcc.Input(id="metric-where", type="text", value="", style={"width":"100%"})]
    elif metric_type == "distinct_count":
        extra = []
    elif metric_type == "ratio":
        extra = [html.Label("Expr (metricA / metricB) — indique les IDs de métriques déjà définies"),
                 dcc.Input(id="metric-expr", type="text", value="", style={"width":"100%"})]

    preview = html.Div([html.H5("Prévisualisation"), html.Pre(id="metric-preview", style={"background":"#222","color":"#eee","padding":"0.75rem"})])
    return html.Div([common_top, column_ctrl, html.Div(extra), preview])

@app.callback(Output("metric-column","options"),
              [Input("metric-db","value"), Input("store_datasets","data")])
def fill_metric_columns(db_alias, ds_data):
    if not db_alias or not ds_data:
        return []
    ds_name = next((d["dataset"] for d in ds_data if d["alias"] == db_alias), None)
    if not ds_name:
        return []
    cols = get_columns_for_dataset(ds_name)
    return [{"label":c,"value":c} for c in cols]

@app.callback(Output("metric-preview","children"),
              [Input("metric-type","value"),
               Input("metric-id","value"),
               Input("metric-db","value"),
               Input("metric-column","value"),
               Input("metric-where","value"),
               Input("metric-expr","value")])
def preview_metric(mtype, mid, mdb, mcol, mwhere, mexpr):
    if not mtype: return ""
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

@app.callback(Output("add-metric-status","children"),
              Output("store_metrics","data"),
              Output("metrics-list","children"),
              [Input("add-metric","n_clicks")],
              [State("metric-preview","children"),
               State("store_metrics","data")])
def add_metric(n, preview_text, metrics):
    if not n:
        return "", metrics, ""
    try:
        m = json.loads(preview_text)
    except Exception:
        return "Prévisualisation vide/invalide.", metrics, ""
    metrics = (metrics or [])
    existing = set([x.get("id") for x in metrics])
    base_id = m.get("id") or "m"
    uid = base_id
    k = 2
    while uid in existing:
        uid = f"{base_id}_{k}"; k += 1
    m["id"] = uid
    metrics.append(m)
    items = [html.Pre(json.dumps(x, ensure_ascii=False, indent=2), style={"background":"#111","color":"#eee","padding":".5rem","marginBottom":".5rem"}) for x in metrics]
    return f"Métrique ajoutée: {uid}", metrics, html.Div(items)

# ----- Tests
@app.callback(Output("test-params","children"),
              [Input("test-type","value"),
               Input("store_datasets","data"),
               Input("store_metrics","data")])
def render_test_form(test_type, ds_data, metrics):
    if not test_type:
        return html.Div([html.Em("Choisis un type de test.")])
    ds_aliases = [d["alias"] for d in (ds_data or [])]
    if not ds_aliases:
        return html.Div([html.Em("Enregistre d'abord des datasets.")])

    common = html.Div([
        html.Div([html.Label("ID du test"), dcc.Input(id="test-id", type="text", value="")], style={"flex":"2","padding":"0 .5rem"}),
        html.Div([html.Label("Sévérité"), dcc.Dropdown(id="test-sev",
                                                       options=[{"label":x,"value":x} for x in ["low","medium","high"]],
                                                       value="medium")], style={"flex":"1","padding":"0 .5rem"}),
        html.Div([html.Label("Échantillon si échec"), dcc.Checklist(id="test-sof",
                                                                    options=[{"label":" Oui","value":"yes"}],
                                                                    value=["yes"])], style={"flex":"1","padding":"0 .5rem"}),
    ], style={"display":"flex","flexWrap":"wrap"})

    if test_type in ("null_rate","uniqueness","range","regex"):
        db_ctrl = html.Div([html.Label("Base (alias)"),
                            dcc.Dropdown(id="test-db", options=[{"label":a,"value":a} for a in ds_aliases])])
        col_ctrl = html.Div([html.Label("Colonne"),
                             dcc.Dropdown(id="test-col", options=[], placeholder="Choisir une colonne")])
        extra = []
        if test_type == "range":
            extra = [
                html.Div([html.Label("Min"), dcc.Input(id="test-min", type="text", value="0")], style={"flex":"1","padding":"0 .5rem"}),
                html.Div([html.Label("Max"), dcc.Input(id="test-max", type="text", value="100")], style={"flex":"1","padding":"0 .5rem"}),
            ]
        if test_type == "regex":
            extra = [html.Label("Pattern (regex)"),
                     dcc.Input(id="test-pattern", type="text", value="^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$")]
        thresh = html.Div([
            html.Div([html.Label("Opérateur"), dcc.Dropdown(id="test-op",
                                                            options=[{"label":x,"value":x} for x in ["<=","<",">=",">","=","!="]],
                                                            value="<=")], style={"flex":"1","padding":"0 .5rem"}),
            html.Div([html.Label("Valeur"), dcc.Input(id="test-thr", type="text", value="0.005")], style={"flex":"1","padding":"0 .5rem"}),
        ], style={"display":"flex","flexWrap":"wrap"})
        preview = html.Div([html.H5("Prévisualisation du test"), html.Pre(id="test-preview", style={"background":"#222","color":"#eee","padding":"0.75rem"})])
        return html.Div([common, db_ctrl, col_ctrl, html.Div(extra), thresh, preview])

    if test_type == "foreign_key":
        db1 = html.Div([html.Label("Base (alias)"),
                        dcc.Dropdown(id="test-db", options=[{"label":a,"value":a} for a in ds_aliases])])
        col1 = html.Div([html.Label("Colonne"),
                         dcc.Dropdown(id="test-col", options=[], placeholder="Choisir une colonne")])
        db2 = html.Div([html.Label("Ref Base (alias)"),
                        dcc.Dropdown(id="test-ref-db", options=[{"label":a,"value":a} for a in ds_aliases])])
        col2 = html.Div([html.Label("Ref Colonne"),
                         dcc.Dropdown(id="test-ref-col", options=[], placeholder="Choisir une colonne")])
        preview = html.Div([html.H5("Prévisualisation du test"), html.Pre(id="test-preview", style={"background":"#222","color":"#eee","padding":"0.75rem"})])
        return html.Div([common, db1, col1, db2, col2, preview])

    return html.Div([html.Em("Type non géré pour l'instant.")])

@app.callback(Output("test-col","options"),
              [Input("test-db","value"), Input("store_datasets","data")])
def fill_test_columns(db_alias, ds_data):
    if not db_alias or not ds_data: return []
    ds_name = next((d["dataset"] for d in ds_data if d["alias"] == db_alias), None)
    if not ds_name: return []
    cols = get_columns_for_dataset(ds_name)
    return [{"label":c,"value":c} for c in cols]

@app.callback(Output("test-ref-col","options"),
              [Input("test-ref-db","value"), Input("store_datasets","data")])
def fill_test_ref_columns(db_alias, ds_data):
    if not db_alias or not ds_data: return []
    ds_name = next((d["dataset"] for d in ds_data if d["alias"] == db_alias), None)
    if not ds_name: return []
    cols = get_columns_for_dataset(ds_name)
    return [{"label":c,"value":c} for c in cols]

@app.callback(Output("test-preview","children"),
              [Input("test-type","value"),
               Input("test-id","value"),
               Input("test-sev","value"),
               Input("test-sof","value"),
               Input("test-db","value"),
               Input("test-col","value"),
               Input("test-op","value"),
               Input("test-thr","value"),
               Input("test-min","value"),
               Input("test-max","value"),
               Input("test-pattern","value"),
               Input("test-ref-db","value"),
               Input("test-ref-col","value")])
def preview_test(ttype, tid, sev, sof, db, col, op, thr, vmin, vmax, pat, refdb, refcol):
    if not ttype: return ""
    obj = {"id": tid or safe_id(f"t_{ttype}_{db or ''}_{col or ''}"), "type": ttype, "severity": (sev or "medium"),
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
        obj.update({"database": db or "", "column": col or "", "ref": {"database": refdb or "", "column": refcol or ""}})
    return json.dumps(obj, ensure_ascii=False, indent=2)

@app.callback(Output("add-test-status","children"),
              Output("store_tests","data"),
              Output("tests-list","children"),
              [Input("add-test","n_clicks")],
              [State("test-preview","children"),
               State("store_tests","data")])
def add_test(n, preview_text, tests):
    if not n:
        return "", tests, ""
    try:
        t = json.loads(preview_text)
    except Exception:
        return "Prévisualisation vide/invalide.", tests, ""
    tests = (tests or [])
    existing = set([x.get("id") for x in tests])
    base_id = t.get("id") or "t"
    uid = base_id
    k = 2
    while uid in existing:
        uid = f"{base_id}_{k}"; k += 1
    t["id"] = uid
    tests.append(t)
    items = [html.Pre(json.dumps(x, ensure_ascii=False, indent=2), style={"background":"#111","color":"#eee","padding":".5rem","marginBottom":".5rem"}) for x in tests]
    return f"Test ajouté: {uid}", tests, html.Div(items)

# ----- Preview & Publish
@app.callback(Output("cfg-preview","children"),
              [Input("store_datasets","data"),
               Input("store_metrics","data"),
               Input("store_tests","data"),
               Input("fmt","value")])
def render_cfg_preview(datasets, metrics, tests, fmt):
    cfg = cfg_template()
    cfg["databases"] = datasets or []
    cfg["metrics"] = metrics or []
    cfg["tests"] = tests or []
    cfg["orchestration"]["order"] = [*(m.get("id") for m in (metrics or [])), *(t.get("id") for t in (tests or []))]
    try:
        if fmt == "yaml" and yaml:
            return yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True)
        else:
            return json.dumps(cfg, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Erreur de sérialisation: {e}"

@app.callback(Output("publish-status","children"),
              [Input("publish","n_clicks")],
              [State("cfg-preview","children"),
               State("fmt","value"),
               State("folder-id","value"),
               State("cfg-name","value")])
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
    fname = f"dq_config_{cfg_name or 'default'}_{ts}." + ("yaml" if (fmt=='yaml' and yaml) else "json")
    try:
        folder.upload_data(fname, preview_text.encode("utf-8"))
        return f"Publié : {fname} → Folder '{folder_id or 'dq_params'}'"
    except Exception as e:
        return f"Erreur de publication : {e}"
