from dash import html, dcc
import dash_bootstrap_components as dbc

def _choices_from_source(source, context, depends_value=None):
    if source == "aliases":
        return [{"label": a, "value": a} for a in getattr(context, "aliases", [])]
    if source == "metrics":
        return [{"label": m, "value": m} for m in getattr(context, "metric_ids", [])]
    if source == "databases_and_metrics":
        databases = [{"label": f"📊 {a}", "value": a} for a in getattr(context, "aliases", [])]
        metrics = [{"label": f"🔢 virtual:{m}", "value": f"virtual:{m}"} for m in getattr(context, "metric_ids", [])]
        return databases + metrics
    if source == "columns" and depends_value:
        cols = context.columns_for(depends_value) if hasattr(context, "columns_for") else []
        return [{"label": c, "value": c} for c in cols]
    if source == "columns_for_database" and depends_value:
        cols = context.columns_for(depends_value) if hasattr(context, "columns_for") else []
        return [{"label": c, "value": c} for c in cols]
    return []

def component_for_field(name, field, meta, context):
    label = html.Label(field.title or name)
    help_ = html.Small((getattr(meta, "help", None) or ""), className="text-muted")

    role_id = {"role": f"arg-{name}"}

    options = []
    if getattr(meta, "choices_source", None) == "enums":
        options = [{"label": v, "value": v} for v in (meta.enum_values or [])]
    elif getattr(meta, "choices_source", None) and getattr(meta, "choices_source") != "none":
        # dynamic, resolved via callbacks by the app; leave options empty here
        pass

    if meta.widget in ("select","multi-select"):
        return dbc.FormGroup([
            label,
            dcc.Dropdown(id=role_id, options=options, multi=(meta.widget=="multi-select"), placeholder=getattr(meta, "placeholder", None)),
            help_,
        ])
    if meta.widget == "checkbox":
        return dbc.FormGroup([dbc.Checkbox(id=role_id, label=field.title or name)] )
    if meta.widget == "number":
        return dbc.FormGroup([label, dcc.Input(id=role_id, type="number", placeholder=getattr(meta,"placeholder",None)), help_])
    if meta.widget == "code":
        return dbc.FormGroup([label, dcc.Textarea(id=role_id, placeholder=getattr(meta,"placeholder",None), style={"fontFamily":"monospace"}), help_])
    return dbc.FormGroup([label, dcc.Input(id=role_id, type="text", placeholder=getattr(meta,"placeholder",None)), help_])

def build_form_from_model(ParamsModel, context, prefix=""):
    groups = {"general": [], "data": [], "specific": []}

    for name, fld in ParamsModel.model_fields.items():
        ann = fld.annotation
        # submodels (e.g., data, specific)
        if hasattr(ann, "model_fields"):
            sub = build_form_from_model(ann, context, prefix=f"{name}.")
            groups["specific"].append(sub)
            continue

        meta = None
        if fld.metadata:
            for m in fld.metadata:
                if hasattr(m, "group"):
                    meta = m
                    break
        if meta is None:
            class Dummy: pass
            meta = Dummy()
            meta.group = "specific"
            meta.widget = "input"
            meta.choices_source = "none"
            meta.placeholder = None
            meta.help = None

        comp = component_for_field(prefix+name, fld, meta, context)
        groups[getattr(meta, "group", "specific")].append(comp)

    def card(title, children):
        return dbc.Card([dbc.CardHeader(title), dbc.CardBody(children)], className="mb-3") if children else html.Div()

    return html.Div([
        card("🧩 Général", groups["general"]),
        card("🗄️ Données", groups["data"]),
        card("⚙️ Spécifique", groups["specific"]),
    ])
