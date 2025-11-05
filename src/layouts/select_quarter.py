from datetime import datetime
from dash import html, dcc
import dash_bootstrap_components as dbc


def _generate_quarter_options(window: int = 2):
    """Generate a list of quarter options centered around the current year.

    window controls how many years before/after the current year are included.
    """
    now = datetime.utcnow()
    current_year = now.year
    years = range(current_year - window, current_year + window + 1)
    options = []
    for year in years:
        for quarter in range(1, 5):
            label = f"{year}Q{quarter}"
            options.append({"label": label, "value": label})
    # Reverse so the most recent quarters appear first
    return list(reversed(options))


def select_quarter_page():
    options = _generate_quarter_options(window=2)
    return dbc.Container([
        html.H2("Étape 1 — Choisir le quarter"),
        html.P("Sélectionne le quarter concerné par la configuration DQ."),
        dcc.Dropdown(
            id="quarter-dropdown",
            options=options,
            placeholder="Sélectionner un quarter (ex: 2025Q1)",
            clearable=True,
        ),
        dbc.Button("Suivant", id="quarter-next", color="primary", className="mt-3"),
        html.Div(id="quarter-status", className="mt-2 text-danger"),
    ], fluid=True)
