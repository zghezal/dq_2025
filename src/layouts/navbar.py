# Composant Navbar

from dash import html
import dash_bootstrap_components as dbc


def navbar():
    """Barre de navigation principale"""
    return dbc.Navbar(
        dbc.Container([
            html.A(dbc.NavbarBrand("DQ App", className="ms-2"), href="/", className="navbar-brand"),
            dbc.Nav([
                dbc.NavItem(dbc.NavLink("Home", href="/", active="exact")),
                dbc.NavItem(dbc.NavLink("DQ Management", href="/dq", active="exact")),
                dbc.NavItem(dbc.NavLink("Configurations", href="/configs", active="exact"))
            ], className="ms-auto", navbar=True),
            html.Div(id="crumb", className="ms-4 small text-muted")
        ]),
        color="light", dark=False, className="mb-4"
    )


def stepper(active_idx=0):
    """Affiche un stepper pour les étapes du wizard Build"""
    steps = ["1. Datasets", "2. Métriques", "3. Tests", "4. Publication"]
    items = []
    for i, label in enumerate(steps):
        color = "primary" if i == active_idx else "secondary"
        items.append(dbc.Badge(label, color=color, className="me-2 p-2"))
    return html.Div(items, className="mb-3")
