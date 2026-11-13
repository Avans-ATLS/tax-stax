"""
Shared style dicts and small layout helpers reused across TaxStax pages.
"""

from dash import html

UPLOAD_STYLE = {
    "borderWidth": "1px",
    "borderStyle": "dashed",
    "borderRadius": "6px",
    "borderColor": "#9ab0c8",
    "backgroundColor": "#f8fbfd",
    "padding": "10px",
    "textAlign": "center",
    "cursor": "pointer",
    "fontSize": "0.82rem",
    "color": "#5a7a96",
}

SIDEBAR_STYLE = {
    "backgroundColor": "#f4f7fa",
    "borderRight": "1px solid #dce6ef",
    "minHeight": "100vh",
    "padding": "20px 16px",
    "overflowY": "auto",
}

RIGHT_SIDEBAR_STYLE = {
    "backgroundColor": "#f4f7fa",
    "borderLeft": "1px solid #dce6ef",
    "minHeight": "100vh",
    "padding": "20px 16px",
    "overflowY": "auto",
}


def section_label(text: str) -> html.Div:
    return html.Div(text, style={
        "fontSize": "0.70rem",
        "fontWeight": "600",
        "letterSpacing": "0.08em",
        "textTransform": "uppercase",
        "color": "#7a95aa",
        "marginBottom": "6px",
        "marginTop": "14px",
    })
