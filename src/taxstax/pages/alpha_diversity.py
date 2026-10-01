"""
Alpha diversity page: customizable box/violin plot of per-sample diversity,
grouped by samplegroup, with each sample shown as a dot.

Reads the shared stores (store-abundance, store-samplesheet) populated on the
Upload page. Diversity is always computed from the RAW abundance data (not the
Top-N / min-% filtered view used on the TaxStax barplot page), since merging
rare taxa into "Other" would distort richness/Shannon/Simpson.

store-alpha-data and download-alpha-html are page-local (defined in this
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
    METRIC_LABELS,
    PALETTES,
    apply_samplesheet,
    compute_alpha_diversity,
    df_from_store,
)


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    """Convert a '#RRGGBB' color to an 'rgba(...)' string with the given alpha."""
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r}, {g}, {b}, {alpha})"

dash.register_page(__name__, path="/alpha-diversity", name="Alpha diversity",
                    title="TaxStax - Alpha diversity")


layout = dbc.Container(
    fluid=True,
    style={"padding": "0"},
    children=[
        # page-local state
        dcc.Store(id="store-alpha-data"),
        dcc.Download(id="download-alpha-html"),
        dcc.Download(id="download-alpha-settings"),

        dbc.Row(
            style={"margin": "0"},
            children=[

                # LEFT SIDEBAR data & grouping
                dbc.Col(width=2, style=SIDEBAR_STYLE, children=[

                    section_label("Diversity metric"),
                    dcc.Dropdown(
                        id="dropdown-alpha-metric",
                        options=[{"label": v, "value": k} for k, v in METRIC_LABELS.items()],
                        value="shannon", clearable=False,
                        style={"fontSize": "0.85rem"},
                    ),

                    section_label("Groups shown"),
                    dcc.Checklist(
                        id="alpha-groups-included",
                        options=[], value=[],
                        style={"fontSize": "0.82rem"},
                        labelStyle={"display": "block", "marginBottom": "3px"},
                    ),

                    section_label("Plot type"),
                    dbc.RadioItems(
                        id="radio-alpha-plot-type",
                        options=[
                            {"label": " Box plot", "value": "box"},
                            {"label": " Violin plot", "value": "violin"},
                        ],
                        value="box", style={"fontSize": "0.83rem"},
                    ),

                    section_label("Sample points"),
                    dbc.Checklist(
                        id="checklist-alpha-show-points",
                        options=[{"label": " Show individual samples", "value": "show"}],
                        value=["show"], style={"fontSize": "0.82rem"},
                        switch=True,
                    ),

                    section_label("Point jitter"),
                    dcc.Slider(id="slider-alpha-jitter", min=0, max=1, step=0.05, value=0.3,
                               marks={0: "0", 0.5: "0.5", 1: "1"}, tooltip={"placement": "bottom"}),

                    section_label("Point size"),
                    dcc.Slider(id="slider-alpha-point-size", min=3, max=14, step=1, value=6,
                               marks={3: "3", 8: "8", 14: "14"}, tooltip={"placement": "bottom"}),

                    section_label("Export plot"),
                    dbc.Button("HTML", id="btn-export-alpha-html", size="sm", color="secondary",
                               outline=True, style={"width": "100%"}),

                    section_label("Settings"),
                    dbc.Button("Save settings", id="btn-save-alpha-settings", size="sm", color="secondary",
                               outline=True, style={"width": "100%", "marginBottom": "6px"}),
                    dcc.Upload(
                        id="upload-alpha-settings",
                        children=html.Div(["Load settings", html.Br(), html.Small(".json file")]),
                        style={**UPLOAD_STYLE, "marginTop": "2px"}, multiple=False,
                    ),
                    html.Div(style={"display": "flex", "alignItems": "center", "gap": "4px"}, children=[
                        html.Div(id="upload-alpha-settings-status",
                                 style={"fontSize": "0.75rem", "color": "#3a7d44", "marginTop": "4px", "flex": "1"}),
                        dbc.Button("✕", id="btn-clear-alpha-settings", size="sm", color="light",
                                   style={"padding": "0 6px", "fontSize": "0.7rem"}),
                    ]),
                ]),

                # MAIN PLOT
                dbc.Col(width=8, style={
                    "padding": "20px 24px", "backgroundColor": "#ffffff",
                    "height": "100vh", "overflowY": "auto",
                }, children=[
                    html.H5("Alpha diversity", style={"color": "#1a3a52", "marginBottom": "4px"}),
                    html.Div(id="alpha-plot-warning",
                             style={"color": "#c0392b", "fontSize": "0.85rem", "marginBottom": "8px"}),
                    dcc.Graph(
                        id="alpha-diversity-plot",
                        style={"height": "580px"},
                        config={
                            "toImageButtonOptions": {"format": "png", "filename": "alpha_diversity_export", "scale": 3},
                            "displayModeBar": True,
                            "modeBarButtonsToRemove": ["select2d", "lasso2d"],
                            "responsive": False,
                        },
                    ),
                ]),

                # RIGHT SIDEBAR — appearance
                dbc.Col(width=2, style=RIGHT_SIDEBAR_STYLE, children=[

                    section_label("Colour palette"),
                    dcc.Dropdown(
                        id="dropdown-alpha-palette",
                        options=[{"label": k, "value": k} for k in PALETTES],
                        value="Plotly (default)", clearable=False,
                        style={"fontSize": "0.82rem"},
                    ),

                    section_label("Font size"),
                    dcc.Slider(id="slider-alpha-fontsize", min=8, max=20, step=1, value=12,
                               marks={8: "8", 14: "14", 20: "20"}, tooltip={"placement": "bottom"}),

                    section_label("Figure width (px)"),
                    dbc.Input(id="input-alpha-fig-width", type="number", value=900, min=400, max=3000, step=50,
                              style={"fontSize": "0.83rem"}),

                    section_label("Figure height (px)"),
                    dbc.Input(id="input-alpha-fig-height", type="number", value=600, min=300, max=2000, step=50,
                              style={"fontSize": "0.83rem"}),

                    section_label("X-axis label rotation"),
                    dcc.Slider(id="slider-alpha-xangle", min=0, max=90, step=15, value=0,
                               marks={0: "0°", 45: "45°", 90: "90°"}, tooltip={"placement": "bottom"}),

                    section_label("Y-axis title"),
                    dbc.Input(id="input-alpha-ytitle", type="text", value="",
                              placeholder="defaults to metric name", debounce=True,
                              style={"fontSize": "0.83rem"}),

                    section_label("Plot title"),
                    dbc.Input(id="input-alpha-title", type="text", value="",
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
    Output("alpha-groups-included", "options"),
    Output("alpha-groups-included", "value"),
    Input("store-abundance", "data"),
    Input("store-samplesheet", "data"),
)
def update_alpha_group_options(abundance_json, ss_json):
    if not abundance_json:
        return [], []
    df = df_from_store(abundance_json)
    ss = df_from_store(ss_json)
    _, _, groups, _ = apply_samplesheet(df, ss)

    named_groups = [g for g in groups if g != "All"]
    display_groups = ["All", *named_groups]
    options = [{"label": g, "value": g} for g in display_groups]
    return options, display_groups


# 2. Compute per-sample diversity values + which group(s) each sample belongs to
@callback(
    Output("store-alpha-data", "data"),
    Input("store-abundance", "data"),
    Input("store-samplesheet", "data"),
    Input("dropdown-alpha-metric", "value"),
)
def update_alpha_data(abundance_json, ss_json, metric):
    if not abundance_json:
        return None
    try:
        df = df_from_store(abundance_json)
        ss = df_from_store(ss_json)
        df, _, groups, _ = apply_samplesheet(df, ss)
        diversity_df = compute_alpha_diversity(df, metric or "shannon")

        named_groups = [g for g in groups if g != "All"]
        sample_to_groups: dict[str, list[str]] = {
            s: ["All"] for s in groups["All"]
        }
        for g in named_groups:
            for s in groups[g]:
                sample_to_groups.setdefault(s, []).append(g)

        records = [
            {
                "sample": row["sample"],
                "value": row["value"],
                "groups": sample_to_groups.get(row["sample"], ["All"]),
            }
            for _, row in diversity_df.iterrows()
        ]
        return json.dumps(records)
    except Exception:
        return None


# 3. Render the box/violin plot
@callback(
    Output("alpha-diversity-plot", "figure"),
    Output("alpha-plot-warning", "children"),
    Input("store-alpha-data", "data"),
    Input("alpha-groups-included", "value"),
    Input("dropdown-alpha-metric", "value"),
    Input("radio-alpha-plot-type", "value"),
    Input("checklist-alpha-show-points", "value"),
    Input("slider-alpha-jitter", "value"),
    Input("slider-alpha-point-size", "value"),
    Input("dropdown-alpha-palette", "value"),
    Input("slider-alpha-fontsize", "value"),
    Input("input-alpha-fig-width", "value"),
    Input("input-alpha-fig-height", "value"),
    Input("slider-alpha-xangle", "value"),
    Input("input-alpha-ytitle", "value"),
    Input("input-alpha-title", "value"),
)
def render_alpha_plot(
    data_json, included_groups, metric, plot_type, show_points_val,
    jitter, point_size, palette_name, font_size, fig_width, fig_height,
    x_angle, y_title, plot_title,
):
    fig_w = int(fig_width or 900)
    fig_h = int(fig_height or 600)
    font_size = int(font_size or 12)
    x_angle = int(x_angle or 0)
    jitter = float(jitter if jitter is not None else 0.3)
    point_size = int(point_size or 6)

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
        records = json.loads(data_json)
        palette = PALETTES.get(palette_name, PALETTES["Plotly (default)"])
        show_points = bool(show_points_val) and "show" in show_points_val
        metric_label = METRIC_LABELS.get(metric, "Alpha diversity")

        fig = go.Figure()
        for i, g in enumerate(included_groups):
            color = palette[i % len(palette)]
            group_records = [r for r in records if g in r["groups"]]
            if not group_records:
                continue
            values = [r["value"] for r in group_records]
            samples = [r["sample"] for r in group_records]

            if plot_type == "violin":
                fig.add_trace(go.Violin(
                    x=[g] * len(values), y=values, name=g,
                    line_color=color, fillcolor=_hex_to_rgba(color, 0.35),
                    box_visible=True, box_line_color="#333333", box_line_width=1.5,
                    meanline_visible=True, meanline_color="#333333",
                    points="all" if show_points else False,
                    # offset points beside the violin — pointpos=0 hides them behind box_visible's box
                    pointpos=-1.5, jitter=jitter,
                    marker=dict(size=point_size, color=color),
                    # only the sample points respond to hover — avoids the violin/kde
                    # hover comparison line bleeding into neighboring violins
                    hoveron="points",
                    text=samples,
                    hovertemplate=f"<b>%{{text}}</b><br>{metric_label}: %{{y:.3f}}<extra></extra>",
                    showlegend=False,
                ))
            else:
                fig.add_trace(go.Box(
                    x=[g] * len(values), y=values, name=g,
                    marker_color=color, line_color=color,
                    boxpoints="all" if show_points else "outliers",
                    pointpos=0, jitter=jitter,
                    marker=dict(size=point_size, color=color),
                    text=samples,
                    hovertemplate=f"<b>%{{text}}</b><br>{metric_label}: %{{y:.3f}}<extra></extra>",
                    showlegend=False,
                ))

        fig.update_layout(
            template="simple_white",
            autosize=False, width=fig_w, height=fig_h,
            title=dict(text=plot_title, font=dict(size=font_size + 2)) if plot_title else None,
            xaxis=dict(categoryorder="array", categoryarray=included_groups,
                       tickangle=-x_angle, tickfont=dict(size=max(font_size - 1, 1))),
            yaxis=dict(title=dict(text=y_title or metric_label, font=dict(size=font_size)),
                       tickfont=dict(size=max(font_size - 1, 1))),
            font=dict(size=font_size),
            margin=dict(l=60, r=20, t=40, b=80),
            hovermode="closest",
        )

        return fig, ""

    except Exception as e:
        return empty(f"Error: {e}", error=True), ""


# 4. HTML export
@callback(
    Output("download-alpha-html", "data"),
    Input("btn-export-alpha-html", "n_clicks"),
    State("alpha-diversity-plot", "figure"),
    prevent_initial_call=True,
)
def export_alpha_html(n, figure):
    if not n or not figure:
        return dash.no_update
    html_str = go.Figure(figure).to_html(full_html=True, include_plotlyjs="cdn")
    return dict(content=html_str, filename="alpha_diversity_export.html", type="text/html")


# Save alpha-diversity controls to JSON
@callback(
    Output("download-alpha-settings", "data"),
    Input("btn-save-alpha-settings", "n_clicks"),
    State("dropdown-alpha-metric", "value"),
    State("alpha-groups-included", "value"),
    State("radio-alpha-plot-type", "value"),
    State("checklist-alpha-show-points", "value"),
    State("slider-alpha-jitter", "value"),
    State("slider-alpha-point-size", "value"),
    State("dropdown-alpha-palette", "value"),
    State("slider-alpha-fontsize", "value"),
    State("input-alpha-fig-width", "value"),
    State("input-alpha-fig-height", "value"),
    State("slider-alpha-xangle", "value"),
    State("input-alpha-ytitle", "value"),
    State("input-alpha-title", "value"),
    prevent_initial_call=True,
)
def save_alpha_settings(n, metric, groups, plot_type, show_points, jitter,
                       point_size, palette, font_size, fig_width, fig_height,
                       x_angle, y_title, plot_title):
    if not n:
        return dash.no_update
    settings = {
        "metric": metric,
        "groups": groups,
        "plot_type": plot_type,
        "show_points": show_points,
        "jitter": jitter,
        "point_size": point_size,
        "palette": palette,
        "font_size": font_size,
        "fig_width": fig_width,
        "fig_height": fig_height,
        "x_angle": x_angle,
        "y_title": y_title,
        "plot_title": plot_title,
    }
    return dict(content=json.dumps(settings, indent=2),
                filename="alpha_diversity_settings.json", type="application/json")


# Load alpha-diversity settings from JSON
@callback(
    Output("dropdown-alpha-metric", "value", allow_duplicate=True),
    Output("alpha-groups-included", "value", allow_duplicate=True),
    Output("radio-alpha-plot-type", "value", allow_duplicate=True),
    Output("checklist-alpha-show-points", "value", allow_duplicate=True),
    Output("slider-alpha-jitter", "value", allow_duplicate=True),
    Output("slider-alpha-point-size", "value", allow_duplicate=True),
    Output("dropdown-alpha-palette", "value", allow_duplicate=True),
    Output("slider-alpha-fontsize", "value", allow_duplicate=True),
    Output("input-alpha-fig-width", "value", allow_duplicate=True),
    Output("input-alpha-fig-height", "value", allow_duplicate=True),
    Output("slider-alpha-xangle", "value", allow_duplicate=True),
    Output("input-alpha-ytitle", "value", allow_duplicate=True),
    Output("input-alpha-title", "value", allow_duplicate=True),
    Output("upload-alpha-settings-status", "children"),
    Input("upload-alpha-settings", "contents"),
    State("upload-alpha-settings", "filename"),
    State("alpha-groups-included", "options"),
    prevent_initial_call=True,
)
def load_alpha_settings(contents, filename, group_options):
    if not contents:
        return (dash.no_update,) * 13 + ("",)
    try:
        _header, encoded = contents.split(",", 1)
        settings = json.loads(base64.b64decode(encoded).decode("utf-8"))
        available_groups = {option["value"] for option in (group_options or [])}
        selected_groups = [
            group for group in settings.get("groups", list(available_groups))
            if group in available_groups
        ]
        return (
            settings.get("metric", "shannon"),
            selected_groups,
            settings.get("plot_type", "box"),
            settings.get("show_points", ["show"]),
            settings.get("jitter", 0.3),
            settings.get("point_size", 6),
            settings.get("palette", "Plotly (default)"),
            settings.get("font_size", 12),
            settings.get("fig_width", 900),
            settings.get("fig_height", 600),
            settings.get("x_angle", 0),
            settings.get("y_title", ""),
            settings.get("plot_title", ""),
            str(filename or "Loaded settings"),
        )
    except (ValueError, KeyError, TypeError) as error:
        return (dash.no_update,) * 13 + (f"Could not load settings: {error}",)


# Clear alpha-diversity settings and restore defaults
@callback(
    Output("upload-alpha-settings-status", "children", allow_duplicate=True),
    Output("upload-alpha-settings", "contents"),
    Output("upload-alpha-settings", "filename"),
    Output("dropdown-alpha-metric", "value", allow_duplicate=True),
    Output("alpha-groups-included", "value", allow_duplicate=True),
    Output("radio-alpha-plot-type", "value", allow_duplicate=True),
    Output("checklist-alpha-show-points", "value", allow_duplicate=True),
    Output("slider-alpha-jitter", "value", allow_duplicate=True),
    Output("slider-alpha-point-size", "value", allow_duplicate=True),
    Output("dropdown-alpha-palette", "value", allow_duplicate=True),
    Output("slider-alpha-fontsize", "value", allow_duplicate=True),
    Output("input-alpha-fig-width", "value", allow_duplicate=True),
    Output("input-alpha-fig-height", "value", allow_duplicate=True),
    Output("slider-alpha-xangle", "value", allow_duplicate=True),
    Output("input-alpha-ytitle", "value", allow_duplicate=True),
    Output("input-alpha-title", "value", allow_duplicate=True),
    Input("btn-clear-alpha-settings", "n_clicks"),
    State("alpha-groups-included", "options"),
    prevent_initial_call=True,
)
def clear_alpha_settings(n, group_options):
    if not n:
        return (dash.no_update,) * 16
    all_groups = [option["value"] for option in (group_options or [])]
    return (
        "", None, None,
        "shannon", all_groups, "box", ["show"], 0.3, 6,
        "Plotly (default)", 12, 900, 600, 0, "", "",
    )