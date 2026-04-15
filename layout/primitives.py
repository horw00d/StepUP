from dash import dcc, html

from layout.styles import CHART_CARD, LABEL_BOLD_SM


def with_spinner(component):
    """Wraps any Dash component in a uniform loading spinner."""
    return dcc.Loading(
        type="circle",
        color="#007BFF",
        parent_style={"height": "100%", "width": "100%"},
        children=component,
    )


def spinnable_graph(graph_id: str, height: str = "100%"):
    """
    Canonical spinner-wrapped dcc.Graph.

    Replaces the ~10 identical
        with_spinner(dcc.Graph(id=..., style={"height": "100%"}))
    blocks that were scattered across the original file.
    """
    return with_spinner(dcc.Graph(id=graph_id, style={"height": height}))


def chart_card(*children, extra_style: dict | None = None) -> html.Div:
    """
    Standard bordered card container for housing a chart.
    Pass extra_style to override individual keys, e.g. {"flex": "2"} or
    {"border": "1px solid #eee"} for the physics panels.
    """
    return html.Div(
        style={**CHART_CARD, **(extra_style or {})},
        children=list(children),
    )


def labeled_dropdown(label_text: str, **dropdown_kwargs) -> html.Div:
    """
    Consistent label + Dropdown pair used across both control panels.
    Centralises the repeated pattern of an html.Label followed by a dcc.Dropdown.
    """
    return html.Div(
        [
            html.Label(label_text, style=LABEL_BOLD_SM),
            dcc.Dropdown(**dropdown_kwargs),
        ]
    )
