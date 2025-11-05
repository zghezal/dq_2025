from dash import html
import dash_bootstrap_components as dbc


def dq_inventory_page():
    return dbc.Container([
        html.H2("DQ Inventory"),
        html.P("Page placeholder — inventaire des configurations DQ et points de contrôle."),
    dbc.Button("Aller au Builder", href="/select-quarter", color="primary", className="me-2"),
        dbc.Button("Retour à l'accueil", href="/", color="secondary")
    ], fluid=True)
