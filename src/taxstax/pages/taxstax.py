"""
TaxStax page: customizable stacked relative-abundance barplot.
Reads shared stores (abundance/samplesheet/legend) populated on the Upload page.
"""

import base64
import json
import re

import dash
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import ALL, Input, Output, State, callback, callback_context, dcc, html

from components import RIGHT_SIDEBAR_STYLE, SIDEBAR_STYLE, UPLOAD_STYLE, section_label
from data import (
    OTHER_COLOR,
    PALETTES,
    apply_samplesheet,
    build_color_map,
    df_from_store,
    filter_species,
    species_order_by_abundance,
)

dash.register_page(__name__, path="/taxstax", name="TaxStax", title="TaxStax - Barplots")


layout = dbc.Container(
    fluid=True,
    style={"padding": "0"},
    children=[
        dbc.Row(
            style={"margin": "0"},
            children=[

                # LEFT SIDEBAR
                dbc.Col(width=2, style=SIDEBAR_STYLE, children=[

                    section_label("Group"),
                    dcc.Dropdown(
                        id="dropdown-group",
                        options=[{"label": "All", "value": "All"}],
                        value="All", clearable=False,
                        style={"fontSize": "0.85rem"},
                    ),

                    section_label("Sample order"),
                    html.Div(
                        id="sample-order-container",
                        style={"maxHeight": "260px", "overflowY": "auto"},
                        children=[html.Div("Upload data first.", style={"fontSize": "0.78rem", "color": "#aaa"})],
                    ),
                    dbc.Button("Reset order", id="btn-reset-order", size="sm", color="light",
                               style={"marginTop": "8px", "fontSize": "0.78rem", "width": "100%"}),

                    section_label("Species filter"),
                    dbc.RadioItems(
                        id="filter-mode",
                        options=[
                            {"label": " Top N species", "value": "topn"},
                            {"label": " Min abundance (%)", "value": "minpct"},
                        ],
                        value="topn", style={"fontSize": "0.83rem"},
                    ),
                    html.Div([
                        dbc.Label("Top N", style={"fontSize": "0.78rem", "marginTop": "6px"}),
                        dbc.Input(id="input-top-n", type="number", value=20, min=1, max=500,
                                  style={"fontSize": "0.83rem"}),
                    ], id="div-topn"),
                    html.Div([
                        dbc.Label("Min % abundance", style={"fontSize": "0.78rem", "marginTop": "6px"}),
                        dbc.Input(id="input-min-pct", type="number", value=1, min=0, max=100, step=0.1,
                                  style={"fontSize": "0.83rem"}),
                    ], id="div-minpct", style={"display": "none"}),

                    section_label("Export plot"),
                    dbc.Button("HTML", id="btn-export-html", size="sm", color="secondary",
                               outline=True, style={"width": "100%"}),

                    section_label("Settings"),
                    dbc.Button("Save settings", id="btn-save-settings", size="sm", color="secondary",
                               outline=True, style={"width": "100%", "marginBottom": "6px"}),
                    dcc.Upload(
                        id="upload-settings",
                        children=html.Div(["Load settings", html.Br(), html.Small(".json file")]),
                        style={**UPLOAD_STYLE, "marginTop": "2px"}, multiple=False,
                    ),
                    html.Div(style={"display": "flex", "alignItems": "center", "gap": "4px"}, children=[
                        html.Div(id="upload-settings-status",
                                 style={"fontSize": "0.75rem", "color": "#3a7d44", "marginTop": "4px", "flex": "1"}),
                        dbc.Button("✕", id="btn-clear-settings", size="sm", color="light",
                                   style={"padding": "0 6px", "fontSize": "0.7rem"}),
                    ]),
                ]),

                # MAIN PLOT
                dbc.Col(width=8, style={
                    "padding": "20px 24px", "backgroundColor": "#ffffff",
                    "height": "100vh", "overflowY": "auto",
                }, children=[
                    html.Div(id="plot-warning",
                             style={"color": "#c0392b", "fontSize": "0.85rem", "marginBottom": "8px"}),
                    dcc.Graph(
                        id="main-plot",
                        style={"height": "580px"},
                        config={
                            "toImageButtonOptions": {"format": "png", "filename": "taxstax_export", "scale": 3},
                            "displayModeBar": True,
                            "modeBarButtonsToRemove": ["select2d", "lasso2d"],
                            "responsive": False,
                        },
                    ),
                ]),

                # RIGHT SIDEBAR
                dbc.Col(width=2, style=RIGHT_SIDEBAR_STYLE, children=[

                    section_label("color palette"),
                    dcc.Dropdown(
                        id="dropdown-palette",
                        options=[{"label": k, "value": k} for k in PALETTES],
                        value="Plotly (default)", clearable=False,
                        style={"fontSize": "0.82rem"},
                    ),

                    section_label("Bar width"),
                    dcc.Slider(id="slider-bar-width", min=0.2, max=1.0, step=0.05, value=0.8,
                               marks={0.2: "0.2", 0.6: "0.6", 1.0: "1.0"},
                               tooltip={"placement": "bottom"}),

                    section_label("Font size"),
                    dcc.Slider(id="slider-fontsize", min=8, max=20, step=1, value=12,
                               marks={8: "8", 14: "14", 20: "20"}, tooltip={"placement": "bottom"}),

                    section_label("Figure width (px)"),
                    dbc.Input(id="input-fig-width", type="number", value=1200, min=400, max=3000, step=50,
                              style={"fontSize": "0.83rem"}),

                    section_label("Figure height (px)"),
                    dbc.Input(id="input-fig-height", type="number", value=800, min=300, max=2000, step=50,
                              style={"fontSize": "0.83rem"}),

                    section_label("Legend position"),
                    dcc.Dropdown(
                        id="dropdown-legend-pos",
                        options=[
                            {"label": "Right", "value": "right"},
                            {"label": "Bottom", "value": "bottom"},
                            {"label": "Top", "value": "top"},
                            {"label": "Hidden", "value": "hidden"},
                        ],
                        value="right", clearable=False,
                        style={"fontSize": "0.82rem"},
                    ),

                    section_label("X-axis label rotation"),
                    dcc.Slider(id="slider-xangle", min=0, max=90, step=15, value=45,
                               marks={0: "0°", 45: "45°", 90: "90°"}, tooltip={"placement": "bottom"}),

                    section_label("Y-axis title"),
                    dbc.Input(id="input-ytitle", type="text", value="Relative abundance (%)",
                              debounce=True, style={"fontSize": "0.83rem"}),

                    section_label("Plot title"),
                    dbc.Input(id="input-plot-title", type="text", value="",
                              placeholder="optional title", debounce=True,
                              style={"fontSize": "0.83rem"}),

                    dbc.Checklist(
                        id="checklist-show-total-reads",
                        options=[{"label": " Show total reads", "value": "show"}],
                        value=["show"],
                        switch=True,
                        style={"fontSize": "0.83rem", "marginTop": "10px"},
                    ),

                    dbc.Checklist(
                        id="checklist-show-pct-mapped",
                        options=[{"label": " Show % mapped reads", "value": "show"}],
                        value=["show"],
                        switch=True,
                        style={"fontSize": "0.83rem", "marginTop": "4px"},
                    ),

                    # Legend editor
                    section_label("Legend colors"),
                    html.Div(
                        id="legend-editor-container",
                        style={"maxHeight": "300px", "overflowY": "auto"},
                        children=[html.Div("Upload data first.", style={"fontSize": "0.78rem", "color": "#aaa"})],
                    ),
                    dbc.Button("Download legend TSV", id="btn-download-legend", size="sm",
                               color="secondary", outline=True,
                               style={"width": "100%", "marginTop": "8px", "fontSize": "0.78rem"}),
                ]),
            ],
        ),
    ],
)


# Build groups + initial sample order
@callback(
    Output("store-groups", "data"),
    Output("store-all-samples", "data"),
    Output("store-sample-order", "data"),
    Output("dropdown-group", "options"),
    Output("dropdown-group", "value"),
    Input("store-abundance", "data"),
    Input("store-samplesheet", "data"),
)
def update_groups(abundance_json, ss_json):
    if not abundance_json:
        return None, None, None, [{"label": "All", "value": "All"}], "All"
    df = df_from_store(abundance_json)
    ss = df_from_store(ss_json)
    _, ordered, groups, _ = apply_samplesheet(df, ss)
    group_options = [{"label": g, "value": g} for g in groups]
    return json.dumps(groups), json.dumps(ordered), json.dumps(ordered), group_options, "All"


# Show/hide filter inputs
@callback(
    Output("div-topn", "style"),
    Output("div-minpct", "style"),
    Input("filter-mode", "value"),
)
def toggle_filter_mode(mode):
    return ({}, {"display": "none"}) if mode == "topn" else ({"display": "none"}, {})


# Compute color map whenever relevant inputs change, store it
@callback(
    Output("store-color-map", "data"),
    Input("store-abundance", "data"),
    Input("store-samplesheet", "data"),
    Input("store-legend", "data"),
    Input("filter-mode", "value"),
    Input("input-top-n", "value"),
    Input("input-min-pct", "value"),
    Input("dropdown-palette", "value"),
)
def update_color_map(abundance_json, ss_json, legend_json, filter_mode, top_n, min_pct, palette_name):
    if not abundance_json:
        return None
    try:
        df = df_from_store(abundance_json)
        ss = df_from_store(ss_json)
        legend_df = df_from_store(legend_json)
        df, _, _, _ = apply_samplesheet(df, ss)
        df = filter_species(df, filter_mode, int(top_n or 20), float(min_pct or 1.0))
        sp_order = species_order_by_abundance(df)
        color_map = build_color_map(sp_order, palette_name, legend_df)
        return json.dumps(color_map)
    except Exception:
        return None


# Legend editor UI renders color swatches with inline color pickers
@callback(
    Output("legend-editor-container", "children"),
    Input("store-color-map", "data"),
)
def update_legend_editor(color_map_json):
    if not color_map_json:
        return [html.Div("Upload data first.", style={"fontSize": "0.78rem", "color": "#aaa"})]

    color_map = json.loads(color_map_json)
    # show all species except Other at the bottom
    species_list = [sp for sp in color_map if sp != "Other"] + (["Other"] if "Other" in color_map else [])

    rows = []
    for sp in species_list:
        color = color_map[sp]
        rows.append(html.Div(
            style={"display": "flex", "alignItems": "center", "gap": "6px",
                   "marginBottom": "4px", "flexWrap": "nowrap"},
            children=[
                dcc.Input(
                    id={"type": "color-picker", "species": sp},
                    type="color",
                    value=color,
                    style={"width": "28px", "height": "22px", "padding": "0",
                           "border": "none", "cursor": "pointer", "flexShrink": "0"},
                ),
                html.Span(sp, style={
                    "fontSize": "0.74rem",
                    "overflow": "hidden",
                    "textOverflow": "ellipsis",
                    "whiteSpace": "nowrap",
                    "flex": "1",
                    "title": sp,
                }),
            ],
        ))
    return rows


# Update color map when user edits a color in the legend editor
@callback(
    Output("store-color-map", "data", allow_duplicate=True),
    Input({"type": "color-picker", "species": ALL}, "value"),
    State({"type": "color-picker", "species": ALL}, "id"),
    State("store-color-map", "data"),
    prevent_initial_call=True,
)
def update_color_from_picker(values, ids, color_map_json):
    if not color_map_json or not values:
        return dash.no_update
    color_map = json.loads(color_map_json)
    for val, id_dict in zip(values, ids):
        sp = id_dict["species"]
        if val:
            color_map[sp] = val
    return json.dumps(color_map)


# Sample order UI read-only render
@callback(
    Output("sample-order-container", "children"),
    Input("store-sample-order", "data"),
    Input("store-groups", "data"),
    Input("dropdown-group", "value"),
)
def update_sample_order_ui(order_json, groups_json, selected_group):
    if not order_json:
        return [html.Div("Upload data first.", style={"fontSize": "0.78rem", "color": "#aaa"})]

    order = json.loads(order_json)
    if groups_json:
        groups = json.loads(groups_json)
        group_samples = set(groups.get(selected_group, order))
        order = [s for s in order if s in group_samples]

    items = []
    for i, s in enumerate(order):
        items.append(html.Div(
            style={"display": "flex", "alignItems": "center", "gap": "4px", "marginBottom": "3px"},
            children=[
                html.Span(s, style={
                    "flex": "1", "fontSize": "0.78rem",
                    "overflow": "hidden", "textOverflow": "ellipsis",
                    "whiteSpace": "nowrap", "maxWidth": "120px", "title": s,
                }),
                dbc.Button("▲", id={"type": "move-up", "index": i}, size="sm", color="light",
                           style={"padding": "0 5px", "fontSize": "0.65rem", "lineHeight": "1.4"},
                           disabled=(i == 0)),
                dbc.Button("▼", id={"type": "move-down", "index": i}, size="sm", color="light",
                           style={"padding": "0 5px", "fontSize": "0.65rem", "lineHeight": "1.4"},
                           disabled=(i == len(order) - 1)),
            ],
        ))
    return items


# ▲/▼ + reset + group switch mutate store-sample-order
@callback(
    Output("store-sample-order", "data", allow_duplicate=True),
    Input({"type": "move-up", "index": ALL}, "n_clicks"),
    Input({"type": "move-down", "index": ALL}, "n_clicks"),
    Input("btn-reset-order", "n_clicks"),
    Input("dropdown-group", "value"),
    State("store-sample-order", "data"),
    State("store-groups", "data"),
    State("store-all-samples", "data"),
    prevent_initial_call=True,
)
def mutate_sample_order(up_clicks, down_clicks, reset_clicks, selected_group,
                         order_json, groups_json, all_samples_json):
    if not order_json:
        return dash.no_update

    triggered = callback_context.triggered
    if not triggered:
        return dash.no_update

    prop = triggered[0]["prop_id"]
    order = json.loads(order_json)

    if "dropdown-group" in prop:
        # group filtering happens reactively elsewhere; keep the full order intact
        return dash.no_update

    if "btn-reset-order" in prop:
        return all_samples_json or order_json

    match = re.search(r'"index":(\d+).*"type":"(move-up|move-down)"', prop)
    if not match:
        return dash.no_update

    if groups_json:
        groups = json.loads(groups_json)
        group_samples = set(groups.get(selected_group, order))
    else:
        group_samples = set(order)

    visible = [s for s in order if s in group_samples]
    hidden = [s for s in order if s not in group_samples]

    idx = int(match.group(1))
    direction = match.group(2)

    if direction == "move-up" and idx > 0:
        visible[idx - 1], visible[idx] = visible[idx], visible[idx - 1]
    elif direction == "move-down" and idx < len(visible) - 1:
        visible[idx], visible[idx + 1] = visible[idx + 1], visible[idx]

    return json.dumps(visible + hidden)


# Render plot uses store-color-map directly
@callback(
    Output("main-plot", "figure"),
    Output("plot-warning", "children"),
    Input("store-abundance", "data"),
    Input("store-samplesheet", "data"),
    Input("store-color-map", "data"),
    Input("store-sample-order", "data"),
    Input("store-groups", "data"),
    Input("dropdown-group", "value"),
    Input("filter-mode", "value"),
    Input("input-top-n", "value"),
    Input("input-min-pct", "value"),
    Input("slider-bar-width", "value"),
    Input("slider-fontsize", "value"),
    Input("input-fig-width", "value"),
    Input("input-fig-height", "value"),
    Input("dropdown-legend-pos", "value"),
    Input("slider-xangle", "value"),
    Input("input-ytitle", "value"),
    Input("input-plot-title", "value"),
    Input("checklist-show-total-reads", "value"),
    Input("checklist-show-pct-mapped", "value"),
)
def render_plot(
    abundance_json, ss_json, color_map_json, order_json, groups_json, selected_group,
    filter_mode, top_n, min_pct, bar_width,
    font_size, fig_width, fig_height, legend_pos, x_angle, y_title, plot_title,
    show_total_reads, show_pct_mapped,
):
    fig_h = int(fig_height or 550)
    fig_w = int(fig_width or 900)

    def empty(msg="Upload an abundance TSV to get started.", error=False):
        f = go.Figure()
        f.update_layout(
            template="simple_white", autosize=False, width=fig_w, height=fig_h,
            annotations=[{"text": msg, "xref": "paper", "yref": "paper",
                          "x": 0.5, "y": 0.5, "showarrow": False,
                          "font": {"size": 13, "color": "#c0392b" if error else "#9ab0c8"}}],
        )
        return f

    if not abundance_json:
        return empty(), ""

    try:
        df = df_from_store(abundance_json)
        ss = df_from_store(ss_json)
        df, all_ordered, groups, read_totals = apply_samplesheet(df, ss)

        full_order = json.loads(order_json) if order_json else all_ordered
        grps = json.loads(groups_json) if groups_json else {"All": full_order}
        group_samples = set(grps.get(selected_group, full_order))
        sample_order = [s for s in full_order if s in group_samples]

        df = df[df["sample"].isin(sample_order)]
        df = filter_species(df, filter_mode, int(top_n or 20), float(min_pct or 1.0))

        sp_order = species_order_by_abundance(df)
        color_map = json.loads(color_map_json) if color_map_json else {}

        fig = go.Figure()
        for sp in reversed(sp_order):
            sp_vals = dict(zip(
                df[df["species"] == sp]["sample"],
                df[df["species"] == sp]["abundance"]
            ))
            counts = [sp_vals.get(s, 0) for s in sample_order]
            fig.add_trace(go.Bar(
                name=sp,
                x=sample_order,
                y=counts,
                customdata=counts,
                marker_color=color_map.get(sp, OTHER_COLOR),
                width=bar_width,
                hovertemplate=(
                    f"<b>%{{x}}</b><br>Species: {sp}<br>"
                    "Count: %{customdata:.0f}<br>"
                    "Relative abundance: %{y:.1f}%<extra></extra>"
                ),
            ))

        legend_positions = {
            "right":  dict(orientation="v", x=1.01, y=1, xanchor="left", yanchor="top"),
            "bottom": dict(orientation="h", x=0, y=-0.25, xanchor="left", yanchor="top"),
            "top":    dict(orientation="h", x=0, y=1.08, xanchor="left", yanchor="bottom"),
            "hidden": dict(visible=False),
        }

        read_total_annotations = []
        line_yshift = 12
        if show_total_reads:
            read_total_annotations += [
                dict(
                    x=s, y=100, xref="x", yref="y",
                    text=f"{read_totals[s]['total']:,.0f}",
                    showarrow=False, yshift=line_yshift,
                    font=dict(size=font_size - 1),
                )
                for s in sample_order if s in read_totals
            ]
            line_yshift += font_size + 2

        if show_pct_mapped:
            read_total_annotations += [
                dict(
                    x=s, y=100, xref="x", yref="y",
                    text=f"{read_totals[s]['mapped'] / read_totals[s]['total'] * 100:.1f}%",
                    showarrow=False, yshift=line_yshift,
                    font=dict(size=font_size - 1),
                )
                for s in sample_order if s in read_totals and read_totals[s]["total"] > 0
            ]

        fig.update_layout(
            barmode="stack", template="simple_white",
            autosize=False, width=fig_w, height=fig_h,
            title=dict(text=plot_title, font=dict(size=font_size + 2)) if plot_title else None,
            xaxis=dict(categoryorder="array", categoryarray=sample_order,
                       tickangle=-x_angle, tickfont=dict(size=font_size - 1)),
            yaxis=dict(title=dict(text=y_title or "Relative abundance (%)", font=dict(size=font_size)),
                       tickfont=dict(size=font_size - 1), range=[0, 100]),
            legend=legend_positions.get(legend_pos, legend_positions["right"]),
            font=dict(size=font_size),
            margin=dict(l=60, r=20, t=40, b=80),
            uniformtext_minsize=8, uniformtext_mode="hide",
            hovermode="closest",
            annotations=read_total_annotations,
        )

        warning = (f"⚠ {len(sample_order)} samples — consider filtering by group for clarity."
                   if len(sample_order) > 60 else "")
        return fig, warning

    except Exception as e:
        return empty(f"Error: {e}", error=True), ""


# HTML export
@callback(
    Output("download-html", "data"),
    Input("btn-export-html", "n_clicks"),
    State("main-plot", "figure"),
    prevent_initial_call=True,
)
def export_html(n, figure):
    if not n or not figure:
        return dash.no_update
    html_str = go.Figure(figure).to_html(full_html=True, include_plotlyjs="cdn")
    return dict(content=html_str, filename="taxstax_export.html", type="text/html")


# Save settings → JSON download
@callback(
    Output("download-settings", "data"),
    Input("btn-save-settings", "n_clicks"),
    State("filter-mode", "value"),
    State("input-top-n", "value"),
    State("input-min-pct", "value"),
    State("slider-bar-width", "value"),
    State("dropdown-palette", "value"),
    State("slider-fontsize", "value"),
    State("input-fig-width", "value"),
    State("input-fig-height", "value"),
    State("dropdown-legend-pos", "value"),
    State("slider-xangle", "value"),
    State("input-ytitle", "value"),
    State("input-plot-title", "value"),
    State("dropdown-group", "value"),
    State("checklist-show-total-reads", "value"),
    State("checklist-show-pct-mapped", "value"),
    prevent_initial_call=True,
)
def save_settings(n, filter_mode, top_n, min_pct, bar_width, palette,
                  fontsize, fig_width, fig_height, legend_pos, xangle, ytitle, plot_title, group,
                  show_total_reads, show_pct_mapped):
    if not n:
        return dash.no_update
    settings = {
        "filter_mode": filter_mode,
        "top_n": top_n,
        "min_pct": min_pct,
        "bar_width": bar_width,
        "palette": palette,
        "fontsize": fontsize,
        "fig_width": fig_width,
        "fig_height": fig_height,
        "legend_pos": legend_pos,
        "xangle": xangle,
        "ytitle": ytitle,
        "plot_title": plot_title,
        "group": group,
        "show_total_reads": show_total_reads,
        "show_pct_mapped": show_pct_mapped,
    }
    return dict(content=json.dumps(settings, indent=2), filename="taxstax_settings.json", type="application/json")


# Load settings from uploaded JSON → update all controls
@callback(
    Output("filter-mode", "value"),
    Output("input-top-n", "value"),
    Output("input-min-pct", "value"),
    Output("slider-bar-width", "value"),
    Output("dropdown-palette", "value"),
    Output("slider-fontsize", "value"),
    Output("input-fig-width", "value"),
    Output("input-fig-height", "value"),
    Output("dropdown-legend-pos", "value"),
    Output("slider-xangle", "value"),
    Output("input-ytitle", "value"),
    Output("input-plot-title", "value"),
    Output("checklist-show-total-reads", "value"),
    Output("checklist-show-pct-mapped", "value"),
    Output("upload-settings-status", "children"),
    Input("upload-settings", "contents"),
    State("upload-settings", "filename"),
    # current values as fallback
    State("filter-mode", "value"),
    State("input-top-n", "value"),
    State("input-min-pct", "value"),
    State("slider-bar-width", "value"),
    State("dropdown-palette", "value"),
    State("slider-fontsize", "value"),
    State("input-fig-width", "value"),
    State("input-fig-height", "value"),
    State("dropdown-legend-pos", "value"),
    State("slider-xangle", "value"),
    State("input-ytitle", "value"),
    State("input-plot-title", "value"),
    State("checklist-show-total-reads", "value"),
    State("checklist-show-pct-mapped", "value"),
    prevent_initial_call=True,
)
def load_settings(contents, filename,
                  cur_fm, cur_tn, cur_mp, cur_bw, cur_pal, cur_fs,
                  cur_fw, cur_fh, cur_lp, cur_xa, cur_yt, cur_pt,
                  cur_str, cur_spm):
    fallback = (cur_fm, cur_tn, cur_mp, cur_bw, cur_pal, cur_fs,
                cur_fw, cur_fh, cur_lp, cur_xa, cur_yt, cur_pt, cur_str, cur_spm)
    if not contents:
        return *fallback, ""
    try:
        _header, encoded = contents.split(",", 1)
        s = json.loads(base64.b64decode(encoded).decode("utf-8"))
        return (
            s.get("filter_mode", cur_fm),
            s.get("top_n", cur_tn),
            s.get("min_pct", cur_mp),
            s.get("bar_width", cur_bw),
            s.get("palette", cur_pal),
            s.get("fontsize", cur_fs),
            s.get("fig_width", cur_fw),
            s.get("fig_height", cur_fh),
            s.get("legend_pos", cur_lp),
            s.get("xangle", cur_xa),
            s.get("ytitle", cur_yt),
            s.get("plot_title", cur_pt),
            s.get("show_total_reads", cur_str),
            s.get("show_pct_mapped", cur_spm),
            f"{filename}",
        )
    except Exception as e:
        return *fallback, f"✗ {e}"


# Clear settings → reset controls to defaults
@callback(
    Output("upload-settings-status", "children", allow_duplicate=True),
    Output("upload-settings", "contents"),
    Output("upload-settings", "filename"),
    Output("filter-mode", "value", allow_duplicate=True),
    Output("input-top-n", "value", allow_duplicate=True),
    Output("input-min-pct", "value", allow_duplicate=True),
    Output("slider-bar-width", "value", allow_duplicate=True),
    Output("dropdown-palette", "value", allow_duplicate=True),
    Output("slider-fontsize", "value", allow_duplicate=True),
    Output("input-fig-width", "value", allow_duplicate=True),
    Output("input-fig-height", "value", allow_duplicate=True),
    Output("dropdown-legend-pos", "value", allow_duplicate=True),
    Output("slider-xangle", "value", allow_duplicate=True),
    Output("input-ytitle", "value", allow_duplicate=True),
    Output("input-plot-title", "value", allow_duplicate=True),
    Output("checklist-show-total-reads", "value", allow_duplicate=True),
    Output("checklist-show-pct-mapped", "value", allow_duplicate=True),
    Input("btn-clear-settings", "n_clicks"),
    prevent_initial_call=True,
)
def clear_settings(n):
    if not n:
        return (dash.no_update,) * 17
    return (
        "", None, None,
        "topn", 20, 1, 0.8, "Plotly (default)", 12,
        1200, 800, "right", 45, "Relative abundance (%)", "",
        ["show"], ["show"],
    )


# Download legend TSV (current color map)
@callback(
    Output("download-legend-tsv", "data"),
    Input("btn-download-legend", "n_clicks"),
    State("store-color-map", "data"),
    prevent_initial_call=True,
)
def download_legend(n, color_map_json):
    if not n or not color_map_json:
        return dash.no_update
    color_map = json.loads(color_map_json)
    # species order: named species by insertion order, Other last
    rows = [(sp, col) for sp, col in color_map.items() if sp != "Other"]
    if "Other" in color_map:
        rows.append(("Other", color_map["Other"]))
    tsv = "species\tcolor\n" + "\n".join(f"{sp}\t{col}" for sp, col in rows)
    return dict(content=tsv, filename="taxstax_legend.tsv", type="text/tab-separated-values")
