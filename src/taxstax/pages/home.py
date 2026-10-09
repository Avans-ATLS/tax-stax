"""
Upload / landing page: abundance, samplesheet, and color-legend uploads.
Download combined files in long or wide format. Wide format for easy Excel viz.
Plot customization lives on the TaxStax page (pages/taxstax.py).
"""

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dcc, html

from components import UPLOAD_STYLE, section_label
from data import load_abundance, parse_tsv

# new
from io import StringIO
import pandas as pd

dash.register_page(__name__, path="/", name="Upload", title="TaxStax - Upload")


def _status_row(status_id: str, clear_id: str) -> html.Div:
    return html.Div(style={"display": "flex", "alignItems": "center", "gap": "4px"}, children=[
        html.Div(id=status_id,
                 style={"fontSize": "0.75rem", "color": "#3a7d44", "marginTop": "4px", "flex": "1"}),
        dbc.Button("✕", id=clear_id, size="sm", color="light",
                   style={"padding": "0 6px", "fontSize": "0.7rem"}),
    ])


layout = dbc.Container(
    fluid=True,
    style={"padding": "24px", "maxWidth": "520px", "margin": "0 auto"},
    children=[
        html.Img(src=dash.get_asset_url("logo_text.png"),
                 style={"height": "120px", "display": "block", "margin": "0 auto 16px auto"}),
        html.H5("Upload your data", style={"color": "#1a3a52", "marginBottom": "16px"}),

        section_label("Abundance TSV(s)"),
        dcc.Upload(
            id="upload-abundance",
            children=html.Div(["Abundance TSV(s)", html.Br(), html.Small("one or multiple GermGenie/emu files")]),
            style=UPLOAD_STYLE, multiple=True,
        ),
        _status_row("upload-abundance-status", "btn-clear-abundance"),

        section_label("Samplesheet TSV"),
        dcc.Upload(
            id="upload-samplesheet",
            children=html.Div(["Samplesheet TSV", html.Br(), html.Small("optional, create groups and sample order")]),
            style=UPLOAD_STYLE, multiple=False,
        ),
        _status_row("upload-samplesheet-status", "btn-clear-samplesheet"),

        section_label("Color legend TSV"),
        dcc.Upload(
            id="upload-legend",
            children=html.Div(["color legend TSV", html.Br(), html.Small("optional, export from TaxStax plot page")]),
            style=UPLOAD_STYLE, multiple=False,
        ),
        # new
        _status_row("upload-legend-status", "btn-clear-legend"),
        dbc.Button("Download combined abundances", id="btn-download-combined", size="sm",
           color="secondary", outline=True, style={"display": "none", "marginTop": "4px"}),
        dcc.Download(id="download-combined"),
        
        # new2
        dbc.Button("Download wide format (for Excel)", id="btn-download-wide", size="sm",
           color="secondary", outline=True, style={"display": "none", "marginTop": "4px", "marginLeft": "4px"}),
        dcc.Download(id="download-wide"),

        html.Div(style={"display": "flex", "alignItems": "center", "justifyContent": "space-between", "marginTop": "20px"}, children=[
            html.Div([
                dbc.NavLink("Go to TaxStax plot →", href="/taxstax/taxstax", style={"fontSize": "0.9rem"}),
                dbc.NavLink("Go to TaxStax alpha →", href="/taxstax/alpha-diversity", style={"fontSize": "0.9rem"}),
                dbc.NavLink("Go to TaxStax beta →", href="/taxstax/beta-diversity", style={"fontSize": "0.9rem"}),
            ]),
            html.Img(src=dash.get_asset_url("logo.png"), style={"height": "90px"}),
        ]),
    ],
)


# Abundance upload, store
@callback(
    Output("store-abundance", "data"),
    Output("upload-abundance-status", "children"),
    Input("upload-abundance", "contents"),
    State("upload-abundance", "filename"),
    prevent_initial_call=True,
)
def store_abundance(contents_list, filenames):
    if not contents_list:
        return None, ""
    try:
        df = load_abundance(contents_list)
        return df.to_json(orient="split"), f"{len(filenames)} file(s), {len(df)} rows"
    except Exception as e:
        return None, f"✗ {e}"


# Samplesheet upload, store
@callback(
    Output("store-samplesheet", "data"),
    Output("upload-samplesheet-status", "children"),
    Input("upload-samplesheet", "contents"),
    State("upload-samplesheet", "filename"),
    prevent_initial_call=True,
)
def store_samplesheet(contents, filename):
    if not contents:
        return None, ""
    try:
        df = parse_tsv(contents)
        return df.to_json(orient="split"), f"{filename}"
    except Exception as e:
        return None, f"✗ {e}"


# Legend upload, store
@callback(
    Output("store-legend", "data"),
    Output("upload-legend-status", "children"),
    Input("upload-legend", "contents"),
    State("upload-legend", "filename"),
    prevent_initial_call=True,
)
def store_legend_upload(contents, filename):
    if not contents:
        return None, ""
    try:
        df = parse_tsv(contents)
        return df.to_json(orient="split"), f"{filename}"
    except Exception as e:
        return None, f"✗ {e}"


# Clear buttons, reset stores + upload widgets
@callback(
    Output("store-abundance", "data", allow_duplicate=True),
    Output("upload-abundance-status", "children", allow_duplicate=True),
    Output("upload-abundance", "contents"),
    Output("upload-abundance", "filename"),
    Input("btn-clear-abundance", "n_clicks"),
    prevent_initial_call=True,
)
def clear_abundance(n):
    if not n:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update
    return None, "", None, None


@callback(
    Output("store-samplesheet", "data", allow_duplicate=True),
    Output("upload-samplesheet-status", "children", allow_duplicate=True),
    Output("upload-samplesheet", "contents"),
    Output("upload-samplesheet", "filename"),
    Input("btn-clear-samplesheet", "n_clicks"),
    prevent_initial_call=True,
)
def clear_samplesheet(n):
    if not n:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update
    return None, "", None, None


@callback(
    Output("store-legend", "data", allow_duplicate=True),
    Output("upload-legend-status", "children", allow_duplicate=True),
    Output("upload-legend", "contents"),
    Output("upload-legend", "filename"),
    Input("btn-clear-legend", "n_clicks"),
    prevent_initial_call=True,
)
def clear_legend(n):
    if not n:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update
    return None, "", None, None

#new 
# Show the button only when multiple abundance files are loaded
@callback(
    Output("btn-download-combined", "style"),
    Input("store-abundance", "data"),
    State("upload-abundance", "filename"),
)
def toggle_combined_button(data, filenames):
    visible = bool(data) and isinstance(filenames, list) and len(filenames) > 1
    return {"display": "inline-block" if visible else "none", "marginTop": "4px"}

@callback(
    Output("download-combined", "data"),
    Input("btn-download-combined", "n_clicks"),
    State("store-abundance", "data"),
    prevent_initial_call=True,
)
def download_combined(n, data):
    if not n or not data:
        return dash.no_update
    df = pd.read_json(StringIO(data), orient="split")
    cols = [c for c in ("sample", "species", "abundance") if c in df.columns]
    return dcc.send_data_frame(df[cols].to_csv, "combined_abundances.tsv", sep="\t", index=False)

# new 2
# Show the wide-format button whenever abundance data is loaded
@callback(
    Output("btn-download-wide", "style"),
    Input("store-abundance", "data"),
)
def toggle_wide_button(data):
    return {"display": "inline-block" if data else "none", "marginTop": "4px", "marginLeft": "4px"}


@callback(
    Output("download-wide", "data"),
    Input("btn-download-wide", "n_clicks"),
    State("store-abundance", "data"),
    prevent_initial_call=True,
)
def download_wide(n, data):
    if not n or not data:
        return dash.no_update
    df = pd.read_json(StringIO(data), orient="split")
    wide = (df.pivot_table(index="species", columns="sample", values="abundance", aggfunc="sum")
              .fillna(0)
              .reset_index())
    wide.columns.name = None
    return dcc.send_data_frame(wide.to_csv, "abundances_wide.tsv", sep="\t", index=False)
