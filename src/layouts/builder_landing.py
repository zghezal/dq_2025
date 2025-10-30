from dash import html
import dash_bootstrap_components as dbc
from dash import dcc

from pathlib import Path
import yaml
from src.config import DEBUG_UI

DEFINITIONS_DIR = Path(__file__).resolve().parents[2] / "dq" / "definitions"


def list_dq_templates():
    templates = []
    if not DEFINITIONS_DIR.exists():
        return templates
    for p in sorted(DEFINITIONS_DIR.glob("*.yaml")):
        try:
            with open(p, "r", encoding="utf-8") as f:
                obj = yaml.safe_load(f) or {}
                name = obj.get("name") or p.stem
        except Exception:
            name = p.stem
        templates.append({"id": p.stem, "name": name, "path": str(p.relative_to(DEFINITIONS_DIR.parent))})
    return templates


def builder_landing_page():
    """Page intermédiaire avant d'entrer dans le builder.

    Affiche : stream/project/zone context et liste des DQ (templates) applicables
    au contexte sélectionné. Ne montre plus la liste brute des datasets.

    L'utilisateur peut choisir :
        - Créer un DQ from scratch (mode scratch)
        - Créer un DQ from existing template (mode template)
    """
    templates = list_dq_templates()

    main_children = [
        html.H2("Étape intermédiaire — Préparer la construction DQ"),
        html.P("Vérifiez le contexte et choisissez comment démarrer votre DQ."),

        # Hidden placeholders (so callbacks that update datasets-list / datasets-status
        # won't fail when this page is active)
        html.Div(id="datasets-status", style={"display": "none"}),
        html.Div(id="datasets-list", style={"display": "none"}),
        dcc.Dropdown(id="select-zone-dropdown", options=[], style={"display": "none"}),

        # Contexte : carte pleine largeur pour une visibilité claire
        dbc.Row([
            dbc.Col(
                dbc.Card([
                    dbc.CardHeader(html.H5("Contexte sélectionné")),
                    dbc.CardBody(html.Div("Chargement du contexte...", id='builder-landing-context', className="text-muted"), style={"minHeight": "56px"})
                ], className="mb-3 p-2"),
                md=12
            )
        ], className="mb-3"),

        # Actions + DQ disponibles: left = actions, right = templates applicable au contexte
        dbc.Row([
            dbc.Col([
                html.H5("Actions"),
                html.Div("Choisissez 'Initialiser un DQ' pour commencer la construction.", className="text-muted"),
                dbc.Row([
                    dbc.Col(dbc.Button("Initialiser un DQ", id="btn-create-scratch", color="primary", size="lg", className="w-100"), md=12),
                ], className="mt-3")
            ], md=6),

            dbc.Col([
                html.H5("DQ disponibles"),
                html.Div("Liste des templates applicables au contexte sélectionné:", className="text-muted mb-2 small"),
                # Cet élément est rempli par le callback `render_builder_landing_dqs`
                html.Div(id="builder-landing-dqs", children=html.Div("Chargement...", className="text-muted"))
            ], md=6)
        ], className="mb-4 g-3"),
    ]

    # Debug panel (affiché uniquement si DEBUG_UI=True)
    if DEBUG_UI:
        debug_card = dbc.Card([
            dbc.CardHeader(html.H5("🔍 Debug — Inventory stores (DEBUG_MODE)")),
            dbc.CardBody([
                html.Div("Inventory datasets store:", className="fw-bold mb-1"),
                html.Pre(id="debug-inventory-json", style={"whiteSpace": "pre-wrap", "wordBreak": "break-word", "maxHeight": "200px", "overflow": "auto"}),
                html.Hr(),
                html.Div("Inventory DQs store:", className="fw-bold mb-1"),
                html.Pre(id="debug-dqs-json", style={"whiteSpace": "pre-wrap", "wordBreak": "break-word", "maxHeight": "200px", "overflow": "auto"}),
            ])
        ], className="mt-3")
        main_children.append(debug_card)

    return dbc.Container(main_children, fluid=True)
