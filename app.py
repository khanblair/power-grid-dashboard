"""
Uganda Power Grid Operations Dashboard
Entry point for the Dash multi-page app. Exposes `server` for Gunicorn.

Run locally:
    python app.py
Run under Gunicorn (production):
    gunicorn app:server -b 0.0.0.0:8050
"""

import dash
from dash import Dash, html, dcc
import dash_bootstrap_components as dbc

app = Dash(
    __name__,
    use_pages=True,
    pages_folder="pages",
    external_stylesheets=[dbc.themes.CYBORG, dbc.icons.FONT_AWESOME],
    title="Uganda Grid Ops",
    update_title=None,
)
server = app.server  # WSGI entry point for Gunicorn

navbar = dbc.Navbar(
    dbc.Container(
        [
            html.Div(
                [
                    html.I(className="fa-solid fa-bolt me-2", style={"color": "#f4a623"}),
                    dbc.NavbarBrand("Uganda Power Grid Operations", className="fw-bold"),
                ],
                className="d-flex align-items-center",
            ),
            dbc.Nav(
                [
                    dbc.NavLink(page["name"], href=page["path"], active="exact")
                    for page in dash.page_registry.values()
                ],
                pills=True,
            ),
        ],
        fluid=True,
        className="d-flex justify-content-between align-items-center",
    ),
    color="dark",
    dark=True,
    className="mb-3 shadow-sm",
)

footer = html.Footer(
    dbc.Container(
        html.Small(
            "Simulated operational data \u2014 plant names and capacities are loosely based on Uganda's "
            "real generation fleet for realism; hourly output, demand, outages, and water levels are "
            "synthetically generated and do not represent actual UEGCL / UEDCL / ERA telemetry.",
            className="text-muted",
        ),
        fluid=True,
    ),
    className="mt-4 py-3 border-top border-secondary",
)

app.layout = html.Div(
    [
        navbar,
        dbc.Container(dash.page_container, fluid=True),
        footer,
    ]
)

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=8050)
