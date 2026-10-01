"""
TaxStax - multi-page entrypoint.
Pages live in pages/ and are auto-discovered by Dash (use_pages=True).
Stores/downloads declared here are shared across every page.
"""

import dash
import dash_bootstrap_components as dbc
from dash import dcc, html

app = dash.Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[dbc.themes.FLATLY],
    title="TaxStax - ATLS",
    requests_pathname_prefix="/taxstax/",
    routes_pathname_prefix="/taxstax/",
)

server = app.server

navbar = dbc.Row(
    dbc.Col(
        html.Div([
            html.Div([
                html.Img(src=app.get_asset_url("logo.png"),
                         style={"height": "32px", "marginRight": "10px"}),
                html.Span("TaxStax", style={
                    "fontWeight": "700", "fontSize": "1.15rem",
                    "color": "#1a3a52", "letterSpacing": "-0.02em",
                }),
                html.Span(" - Custom relative abundance, alpha and beta diversity plotter", style={
                    "fontSize": "0.85rem", "color": "#7a95aa", "marginLeft": "8px",
                }),
            ], style={"display": "flex", "alignItems": "center"}),
            html.Div([
                dbc.NavLink(page["name"], href=page["relative_path"], active="exact",
                            style={"fontSize": "0.85rem", "padding": "4px 10px"})
                for page in sorted(
                    dash.page_registry.values(),
                    key=lambda page: {
                        "TaxStax": 0,
                        "Alpha diversity": 1,
                        "Beta diversity": 2,
                        "Upload": 3,
                    }.get(page["name"], 99),
                )
            ], style={"display": "flex"}),
        ], style={
            "padding": "12px 24px",
            "backgroundColor": "#ffffff",
            "borderBottom": "1px solid #dce6ef",
            "display": "flex",
            "justifyContent": "space-between",
            "alignItems": "center",
        })
    ),
    style={"margin": "0"},
)

app.layout = html.Div([
    # shared stores (survive navigation between pages)
    dcc.Store(id="store-abundance"),
    dcc.Store(id="store-samplesheet"),
    dcc.Store(id="store-legend"),       # raw uploaded legend
    dcc.Store(id="store-color-map"),    # computed color map (legend + palette fallback)
    dcc.Store(id="store-groups"),
    dcc.Store(id="store-all-samples"),
    dcc.Store(id="store-sample-order"),

    # shared downloads
    dcc.Download(id="download-html"),
    dcc.Download(id="download-settings"),
    dcc.Download(id="download-legend-tsv"),

    navbar,
    dash.page_container,
])


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=8050)
