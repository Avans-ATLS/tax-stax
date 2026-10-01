"""
Beta diversity page: ordination scatter plot (PCoA / PCA) of samples,
colored by group, with sidebars for ordination + appearance settings.

Reads the shared stores (store-abundance, store-samplesheet) populated on the
Upload page. Ordination is always computed from the RAW abundance data (not
the Top-N / min-% filtered view used on the TaxStax barplot page), since
collapsing rare taxa into "Other" would distort sample dissimilarities.

store-beta-data and download-beta-html are page-local (defined in this
page's own layout) since nothing else needs them — no app.py changes required.
"""

import base64
import json

import dash
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import Input, Output, State, callback, dcc, html

from components import RIGHT_SIDEBAR_STYLE, SIDEBAR_STYLE, UPLOAD_STYLE, section_label
from data import (
    ORDINATION_METHODS,
    PALETTES,
    apply_samplesheet,
    compute_beta_ordination,
    df_from_store,
)

dash.register_page(__name__, path="/beta-diversity", name="Beta diversity",
                    title="TaxStax - Beta diversity")


layout = dbc.Container(
    fluid=True,
    style={"padding": "0"},
    children=[
        # page-local state
        dcc.Store(id="store-beta-data"),
        dcc.Download(id="download-beta-html"),
        dcc.Download(id="download-beta-settings"),

        dbc.Row(
            style={"margin": "0"},
            children=[

                # LEFT SIDEBAR data & grouping
                dbc.Col(width=2, style=SIDEBAR_STYLE, children=[

                    section_label("Ordination method"),
                    dcc.Dropdown(
                        id="dropdown-beta-method",
                        options=[{"label": v, "value": k} for k, v in ORDINATION_METHODS.items()],
                        value="pcoa", clearable=False,
                        style={"fontSize": "0.85rem"},
                    ),

                    section_label("Groups shown"),
                    dcc.Checklist(
                        id="beta-groups-included",
                        options=[], value=[],
                        style={"fontSize": "0.82rem"},
                        labelStyle={"display": "block", "marginBottom": "3px"},
                    ),

                    section_label("Sample labels"),
                    dbc.Checklist(
                        id="checklist-beta-show-labels",
                        options=[{"label": " Show sample names", "value": "show"}],
                        value=[], style={"fontSize": "0.82rem"},
                        switch=True,
                    ),

                    section_label("Point size"),
                    dcc.Slider(id="slider-beta-point-size", min=3, max=18, step=1, value=9,
                               marks={3: "3", 10: "10", 18: "18"}, tooltip={"placement": "bottom"}),

                    section_label("Export plot"),
                    dbc.Button("HTML", id="btn-export-beta-html", size="sm", color="secondary",
                               outline=True, style={"width": "100%"}),

                    section_label("Settings"),
                    dbc.Button("Save settings", id="btn-save-beta-settings", size="sm", color="secondary",
                               outline=True, style={"width": "100%", "marginBottom": "6px"}),
                    dcc.Upload(
                        id="upload-beta-settings",
                        children=html.Div(["Load settings", html.Br(), html.Small(".json file")]),
                        style={**UPLOAD_STYLE, "marginTop": "2px"}, multiple=False,
                    ),
                    html.Div(style={"display": "flex", "alignItems": "center", "gap": "4px"}, children=[
                        html.Div(id="upload-beta-settings-status",
                                 style={"fontSize": "0.75rem", "color": "#3a7d44", "marginTop": "4px", "flex": "1"}),
                        dbc.Button("✕", id="btn-clear-beta-settings", size="sm", color="light",
                                   style={"padding": "0 6px", "fontSize": "0.7rem"}),
                    ]),
                ]),

                # MAIN PLOT
                dbc.Col(width=8, style={
                    "padding": "20px 24px", "backgroundColor": "#ffffff",
                    "height": "100vh", "overflowY": "auto",
                }, children=[
                    html.H5("Beta diversity", style={"color": "#1a3a52", "marginBottom": "4px"}),
                    html.Div(id="beta-plot-warning",
                             style={"color": "#c0392b", "fontSize": "0.85rem", "marginBottom": "8px"}),
                    dcc.Graph(
                        id="beta-diversity-plot",
                        style={"height": "580px"},
                        config={
                            "toImageButtonOptions": {"format": "png", "filename": "beta_diversity_export", "scale": 3},
                            "displayModeBar": True,
                            "modeBarButtonsToRemove": ["select2d", "lasso2d"],
                            "responsive": False,
                        },
                    ),
                ]),

                # RIGHT SIDEBAR appearance
                dbc.Col(width=2, style=RIGHT_SIDEBAR_STYLE, children=[

                    section_label("Colour palette"),
                    dcc.Dropdown(
                        id="dropdown-beta-palette",
                        options=[{"label": k, "value": k} for k in PALETTES],
                        value="Plotly (default)", clearable=False,
                        style={"fontSize": "0.82rem"},
                    ),

                    section_label("Font size"),
                    dcc.Slider(id="slider-beta-fontsize", min=8, max=20, step=1, value=12,
                               marks={8: "8", 14: "14", 20: "20"}, tooltip={"placement": "bottom"}),

                    section_label("Figure width (px)"),
                    dbc.Input(id="input-beta-fig-width", type="number", value=900, min=400, max=3000, step=50,
                              style={"fontSize": "0.83rem"}),

                    section_label("Figure height (px)"),
                    dbc.Input(id="input-beta-fig-height", type="number", value=600, min=300, max=2000, step=50,
                              style={"fontSize": "0.83rem"}),

                    section_label("X-axis title"),
                    dbc.Input(id="input-beta-xtitle", type="text", value="",
                              placeholder="defaults to axis + % variance", debounce=True,
                              style={"fontSize": "0.83rem"}),

                    section_label("Y-axis title"),
                    dbc.Input(id="input-beta-ytitle", type="text", value="",
                              placeholder="defaults to axis + % variance", debounce=True,
                              style={"fontSize": "0.83rem"}),

                    section_label("Plot title"),
                    dbc.Input(id="input-beta-title", type="text", value="",
                              placeholder="optional title", debounce=True,
                              style={"fontSize": "0.83rem"}),
                ]),
            ],
        ),
    ],
)


# Callbacks

# 1. Populate the group checklist from the shared abundance/samplesheet stores
@callback(
    Output("beta-groups-included", "options"),
    Output("beta-groups-included", "value"),
    Input("store-abundance", "data"),
    Input("store-samplesheet", "data"),
)
def update_beta_group_options(abundance_json, ss_json):
    if not abundance_json:
        return [], []
    df = df_from_store(abundance_json)
    ss = df_from_store(ss_json)
    _, _, groups, _ = apply_samplesheet(df, ss)

    named_groups = [g for g in groups if g != "All"]
    display_groups = named_groups if named_groups else ["All"]
    options = [{"label": g, "value": g} for g in display_groups]
    return options, display_groups


# 2. Compute ordination coordinates + which group(s) each sample belongs to
@callback(
    Output("store-beta-data", "data"),
    Input("store-abundance", "data"),
    Input("store-samplesheet", "data"),
    Input("dropdown-beta-method", "value"),
)
def update_beta_data(abundance_json, ss_json, method):
    if not abundance_json:
        return None
    try:
        df = df_from_store(abundance_json)
        ss = df_from_store(ss_json)
        df, _, groups, _ = apply_samplesheet(df, ss)

        if df["sample"].nunique() < 2:
            return None

        ordination_df, variance_explained, axis_prefix = compute_beta_ordination(
            df, method=method or "pcoa", n_axes=2
        )

        named_groups = [g for g in groups if g != "All"]
        sample_to_groups: dict[str, list[str]] = {}
        if named_groups:
            for g in named_groups:
                for s in groups[g]:
                    sample_to_groups.setdefault(s, []).append(g)
        else:
            for s in groups["All"]:
                sample_to_groups[s] = ["All"]

        records = [
            {
                "sample": row["sample"],
                "axis1": row["axis1"],
                "axis2": row["axis2"],
                "groups": sample_to_groups.get(row["sample"], ["All"]),
            }
            for _, row in ordination_df.iterrows()
        ]
        return json.dumps({
            "records": records,
            "variance_explained": variance_explained,
            "axis_prefix": axis_prefix,
        })
    except Exception:
        return None


# 3. Render the ordination scatter plot
@callback(
    Output("beta-diversity-plot", "figure"),
    Output("beta-plot-warning", "children"),
    Input("store-beta-data", "data"),
    Input("beta-groups-included", "value"),
    Input("checklist-beta-show-labels", "value"),
    Input("slider-beta-point-size", "value"),
    Input("dropdown-beta-palette", "value"),
    Input("slider-beta-fontsize", "value"),
    Input("input-beta-fig-width", "value"),
    Input("input-beta-fig-height", "value"),
    Input("input-beta-xtitle", "value"),
    Input("input-beta-ytitle", "value"),
    Input("input-beta-title", "value"),
)
def render_beta_plot(
    data_json, included_groups, show_labels_val, point_size, palette_name,
    font_size, fig_width, fig_height, x_title, y_title, plot_title,
):
    fig_w = int(fig_width or 900)
    fig_h = int(fig_height or 600)
    font_size = int(font_size or 12)
    point_size = int(point_size or 9)

    def empty(msg="Upload an abundance TSV on the Upload page to get started.", error=False):
        f = go.Figure()
        f.update_layout(
            template="simple_white", autosize=False, width=fig_w, height=fig_h,
            annotations=[{"text": msg, "xref": "paper", "yref": "paper",
                          "x": 0.5, "y": 0.5, "showarrow": False,
                          "font": {"size": 13, "color": "#c0392b" if error else "#9ab0c8"}}],
        )
        return f

    if not data_json:
        return empty(), ""
    if not included_groups:
        return empty("No groups selected."), ""

    try:
        payload = json.loads(data_json)
        records = payload["records"]
        variance_explained = payload["variance_explained"]
        axis_prefix = payload["axis_prefix"]

        palette = PALETTES.get(palette_name, PALETTES["Plotly (default)"])
        show_labels = bool(show_labels_val) and "show" in show_labels_val

        var1 = variance_explained[0] if len(variance_explained) > 0 else 0.0
        var2 = variance_explained[1] if len(variance_explained) > 1 else 0.0
        default_xtitle = f"{axis_prefix}1 ({var1:.1f}%)"
        default_ytitle = f"{axis_prefix}2 ({var2:.1f}%)"

        fig = go.Figure()
        for i, g in enumerate(included_groups):
            color = palette[i % len(palette)]
            group_records = [r for r in records if g in r["groups"]]
            if not group_records:
                continue
            xs = [r["axis1"] for r in group_records]
            ys = [r["axis2"] for r in group_records]
            samples = [r["sample"] for r in group_records]

            fig.add_trace(go.Scatter(
                x=xs, y=ys, mode="markers+text" if show_labels else "markers",
                name=g,
                text=samples,
                textposition="top center",
                textfont=dict(size=max(font_size - 3, 1)),
                marker=dict(size=point_size, color=color, line=dict(width=1, color="#ffffff")),
                hovertemplate=f"<b>%{{text}}</b><br>{axis_prefix}1: %{{x:.3f}}<br>{axis_prefix}2: %{{y:.3f}}<extra></extra>",
            ))

        fig.update_layout(
            template="simple_white",
            autosize=False, width=fig_w, height=fig_h,
            title=dict(text=plot_title, font=dict(size=font_size + 2)) if plot_title else None,
            xaxis=dict(title=dict(text=x_title or default_xtitle, font=dict(size=font_size)),
                       tickfont=dict(size=max(font_size - 1, 1)), zeroline=True),
            yaxis=dict(title=dict(text=y_title or default_ytitle, font=dict(size=font_size)),
                       tickfont=dict(size=max(font_size - 1, 1)), zeroline=True),
            font=dict(size=font_size),
            margin=dict(l=60, r=20, t=40, b=60),
            hovermode="closest",
        )

        return fig, ""

    except Exception as e:
        return empty(f"Error: {e}", error=True), ""


# 4. HTML export
@callback(
    Output("download-beta-html", "data"),
    Input("btn-export-beta-html", "n_clicks"),
    State("beta-diversity-plot", "figure"),
    prevent_initial_call=True,
)
def export_beta_html(n, figure):
    if not n or not figure:
        return dash.no_update
    html_str = go.Figure(figure).to_html(full_html=True, include_plotlyjs="cdn")
    return dict(content=html_str, filename="beta_diversity_export.html", type="text/html")


# Save beta-diversity controls to JSON
@callback(
    Output("download-beta-settings", "data"),
    Input("btn-save-beta-settings", "n_clicks"),
    State("dropdown-beta-method", "value"),
    State("beta-groups-included", "value"),
    State("checklist-beta-show-labels", "value"),
    State("slider-beta-point-size", "value"),
    State("dropdown-beta-palette", "value"),
    State("slider-beta-fontsize", "value"),
    State("input-beta-fig-width", "value"),
    State("input-beta-fig-height", "value"),
    State("input-beta-xtitle", "value"),
    State("input-beta-ytitle", "value"),
    State("input-beta-title", "value"),
    prevent_initial_call=True,
)
def save_beta_settings(n, method, groups, show_labels, point_size, palette,
                      font_size, fig_width, fig_height, x_title, y_title, plot_title):
    if not n:
        return dash.no_update
    settings = {
        "method": method,
        "groups": groups,
        "show_labels": show_labels,
        "point_size": point_size,
        "palette": palette,
        "font_size": font_size,
        "fig_width": fig_width,
        "fig_height": fig_height,
        "x_title": x_title,
        "y_title": y_title,
        "plot_title": plot_title,
    }
    return dict(content=json.dumps(settings, indent=2),
                filename="beta_diversity_settings.json", type="application/json")


# Load beta-diversity settings from JSON
@callback(
    Output("dropdown-beta-method", "value", allow_duplicate=True),
    Output("beta-groups-included", "value", allow_duplicate=True),
    Output("checklist-beta-show-labels", "value", allow_duplicate=True),
    Output("slider-beta-point-size", "value", allow_duplicate=True),
    Output("dropdown-beta-palette", "value", allow_duplicate=True),
    Output("slider-beta-fontsize", "value", allow_duplicate=True),
    Output("input-beta-fig-width", "value", allow_duplicate=True),
    Output("input-beta-fig-height", "value", allow_duplicate=True),
    Output("input-beta-xtitle", "value", allow_duplicate=True),
    Output("input-beta-ytitle", "value", allow_duplicate=True),
    Output("input-beta-title", "value", allow_duplicate=True),
    Output("upload-beta-settings-status", "children"),
    Input("upload-beta-settings", "contents"),
    State("upload-beta-settings", "filename"),
    State("beta-groups-included", "options"),
    prevent_initial_call=True,
)
def load_beta_settings(contents, filename, group_options):
    if not contents:
        return (dash.no_update,) * 11 + ("",)
    try:
        _header, encoded = contents.split(",", 1)
        settings = json.loads(base64.b64decode(encoded).decode("utf-8"))
        available_groups = {option["value"] for option in (group_options or [])}
        selected_groups = [
            group for group in settings.get("groups", list(available_groups))
            if group in available_groups
        ]
        return (
            settings.get("method", "pcoa"),
            selected_groups,
            settings.get("show_labels", []),
            settings.get("point_size", 9),
            settings.get("palette", "Plotly (default)"),
            settings.get("font_size", 12),
            settings.get("fig_width", 900),
            settings.get("fig_height", 600),
            settings.get("x_title", ""),
            settings.get("y_title", ""),
            settings.get("plot_title", ""),
            str(filename or "Loaded settings"),
        )
    except (ValueError, KeyError, TypeError) as error:
        return (dash.no_update,) * 11 + (f"Could not load settings: {error}",)


# Clear beta-diversity settings and restore defaults
@callback(
    Output("upload-beta-settings-status", "children", allow_duplicate=True),
    Output("upload-beta-settings", "contents"),
    Output("upload-beta-settings", "filename"),
    Output("dropdown-beta-method", "value", allow_duplicate=True),
    Output("beta-groups-included", "value", allow_duplicate=True),
    Output("checklist-beta-show-labels", "value", allow_duplicate=True),
    Output("slider-beta-point-size", "value", allow_duplicate=True),
    Output("dropdown-beta-palette", "value", allow_duplicate=True),
    Output("slider-beta-fontsize", "value", allow_duplicate=True),
    Output("input-beta-fig-width", "value", allow_duplicate=True),
    Output("input-beta-fig-height", "value", allow_duplicate=True),
    Output("input-beta-xtitle", "value", allow_duplicate=True),
    Output("input-beta-ytitle", "value", allow_duplicate=True),
    Output("input-beta-title", "value", allow_duplicate=True),
    Input("btn-clear-beta-settings", "n_clicks"),
    State("beta-groups-included", "options"),
    prevent_initial_call=True,
)
def clear_beta_settings(n, group_options):
    if not n:
        return (dash.no_update,) * 14
    all_groups = [option["value"] for option in (group_options or [])]
    return (
        "", None, None,
        "pcoa", all_groups, [], 9, "Plotly (default)", 12,
        900, 600, "", "", "",
    )
