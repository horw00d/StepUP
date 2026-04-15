# =====================================================================
# TAB 1: SINGLE-TRIAL ANALYSIS LAYOUT
# =====================================================================

from dash import dcc, html
from config import FEATURE_OPTIONS, ST_COLOR_OPTIONS
from layout.primitives import chart_card, labeled_dropdown, spinnable_graph
from layout.shared_layout import (
    OPTIONS_PART,
    OPTIONS_SHOE,
    OPTIONS_SPEED,
    _get_query_builder,
    get_dynamic_outlier_layout,
)
from layout.styles import FILTER_BOX, LABEL_BOLD, LABEL_BOLD_SM


def get_single_trial_layout() -> html.Div:
    """
    Top-level assembler for the Single-Trial tab.
    Each section is its own private function so it can be read, tested,
    and modified in isolation without touching the others.
    """
    return html.Div(
        children=[
            _get_st_header(),
            _get_st_filters(),
            _get_st_feature_section(),
            _get_st_physics_spatial_section(),
            _get_st_pressure_section(),
        ]
    )


def _get_st_header() -> html.Div:
    """Participant / footwear / speed selectors and trial-status badge."""
    def first(opts):
        return opts[0]["value"] if opts else None
    return html.Div(
        style={
            "borderBottom": "1px solid #ddd",
            "paddingBottom": "15px",
            "marginBottom": "10px",
        },
        children=[
            html.Div(
                style={"display": "flex", "gap": "20px", "alignItems": "center"},
                children=[
                    dcc.Dropdown(
                        id="part-dd",
                        options=OPTIONS_PART,
                        value=first(OPTIONS_PART),
                        placeholder="Participant",
                        style={"width": "120px"},
                    ),
                    dcc.Dropdown(
                        id="shoe-dd",
                        options=OPTIONS_SHOE,
                        value=first(OPTIONS_SHOE),
                        placeholder="Footwear",
                        style={"width": "120px"},
                    ),
                    dcc.Dropdown(
                        id="speed-dd",
                        options=OPTIONS_SPEED,
                        value=first(OPTIONS_SPEED),
                        placeholder="Speed",
                        style={"width": "120px"},
                    ),
                    html.Div(
                        id="trial-status",
                        style={
                            "marginLeft": "auto",
                            "fontWeight": "bold",
                            "color": "#555",
                        },
                    ),
                ],
            )
        ],
    )


def _get_st_filters() -> html.Div:
    """Standard checkbox / dropdown filters + dynamic outlier widget + query builder."""
    return html.Div(
        style={
            **FILTER_BOX,
            "display": "flex",
            "flexDirection": "column",
            "gap": "15px",
        },
        children=[
            # Row 1: standard UI filters
            html.Div(
                style={"display": "flex", "gap": "30px", "alignItems": "flex-end"},
                children=[
                    html.Div(
                        [
                            html.Label("Side:", style=LABEL_BOLD_SM),
                            dcc.Checklist(
                                id="filter-side",
                                options=[
                                    {"label": "Left", "value": "Left"},
                                    {"label": "Right", "value": "Right"},
                                ],
                                value=["Left", "Right"],
                                inline=True,
                                inputStyle={"marginRight": "5px", "marginLeft": "10px"},
                            ),
                        ]
                    ),
                    html.Div(
                        [
                            html.Label("Status:", style=LABEL_BOLD_SM),
                            dcc.Checklist(
                                id="filter-outlier",
                                options=[
                                    {"label": "Normal", "value": "Normal"},
                                    {"label": "Outlier", "value": "Outlier"},
                                ],
                                value=["Normal", "Outlier"],
                                inline=True,
                                inputStyle={"marginRight": "5px", "marginLeft": "10px"},
                            ),
                        ]
                    ),
                    html.Div(
                        style={"width": "200px"},
                        children=[
                            html.Label("Filter by Tile:", style=LABEL_BOLD_SM),
                            dcc.Dropdown(
                                id="filter-tile",
                                options=[
                                    {"label": f"Tile {i}", "value": i}
                                    for i in range(1, 13)
                                ],
                                multi=True,
                                placeholder="All Tiles",
                                style={"fontSize": "0.9em"},
                            ),
                        ],
                    ),
                    html.Div(
                        style={"width": "200px"},
                        children=[
                            html.Label("Filter by Pass:", style=LABEL_BOLD_SM),
                            dcc.Dropdown(
                                id="filter-pass",
                                multi=True,
                                placeholder="All Passes",
                                style={"fontSize": "0.9em"},
                            ),
                        ],
                    ),
                ],
            ),
            get_dynamic_outlier_layout("single"),
            _get_query_builder("single"),
        ],
    )


def _get_st_feature_section() -> dcc.Tabs:
    """Feature Analysis chart tab and Footstep Library image-grid tab."""
    return dcc.Tabs(
        id="view-tabs",
        value="tab-feature",
        children=[
            dcc.Tab(
                label="Feature Analysis",
                value="tab-feature",
                children=[
                    html.Div(
                        style={
                            "display": "flex",
                            "gap": "20px",
                            "height": "450px",
                            "padding": "20px",
                        },
                        children=[
                            # Charts column
                            html.Div(
                                style={
                                    "flex": "3",
                                    "display": "flex",
                                    "flexDirection": "column",
                                    "gap": "15px",
                                },
                                children=[
                                    chart_card(
                                        spinnable_graph("main-scatter"),
                                        extra_style={
                                            "flex": "2",
                                            "border": "1px solid #ccc",
                                        },
                                    ),
                                    chart_card(
                                        spinnable_graph("rug-plot"),
                                        extra_style={
                                            "flex": "1",
                                            "border": "1px solid #ccc",
                                        },
                                    ),
                                ],
                            ),
                            # Axis controls column
                            html.Div(
                                style={
                                    "flex": "1",
                                    "backgroundColor": "#f9f9f9",
                                    "padding": "20px",
                                    "borderRadius": "5px",
                                    "overflowY": "auto",
                                },
                                children=[
                                    html.H5("Axis Controls"),
                                    labeled_dropdown(
                                        "Scatter X-Axis:",
                                        id="xaxis-dd",
                                        options=FEATURE_OPTIONS,
                                        value="start_frame",
                                        clearable=False,
                                    ),
                                    html.Br(),
                                    labeled_dropdown(
                                        "Scatter Y-Axis:",
                                        id="yaxis-dd",
                                        options=FEATURE_OPTIONS,
                                        value="mean_grf",
                                        clearable=False,
                                    ),
                                    html.Br(),
                                    html.Hr(),
                                    labeled_dropdown(
                                        "Rug Plot Feature:",
                                        id="rug-dd",
                                        options=FEATURE_OPTIONS,
                                        value="r_score",
                                        clearable=False,
                                    ),
                                    html.Br(),
                                    html.Hr(),
                                    labeled_dropdown(
                                        "Color By:",
                                        id="color-dd",
                                        options=ST_COLOR_OPTIONS,
                                        value="side",
                                        clearable=False,
                                    ),
                                ],
                            ),
                        ],
                    )
                ],
            ),
            dcc.Tab(
                label="Footstep Library",
                value="tab-library",
                children=[
                    html.Div(
                        style={
                            "height": "450px",
                            "overflowY": "auto",
                            "padding": "20px",
                        },
                        children=[
                            html.Div(
                                id="image-grid",
                                style={
                                    "display": "grid",
                                    "gridTemplateColumns": "repeat(auto-fill, minmax(140px, 1fr))",
                                    "gap": "20px",
                                },
                            )
                        ],
                    )
                ],
            ),
        ],
    )


def _get_st_physics_spatial_section() -> html.Div:
    """GRF / COP physics plots and the spatial walkway map, displayed side by side."""
    return html.Div(
        style={
            "flex": "1",
            "marginTop": "10px",
            "borderTop": "2px solid #ddd",
            "paddingTop": "10px",
            "display": "flex",
            "gap": "20px",
            "minHeight": "600px",
        },
        children=[
            # Physics column
            html.Div(
                style={
                    "flex": "1",
                    "display": "flex",
                    "flexDirection": "column",
                    "gap": "10px",
                },
                children=[
                    html.Div(
                        style={
                            "display": "flex",
                            "justifyContent": "space-between",
                            "alignItems": "center",
                        },
                        children=[
                            html.H4("Physics", style={"marginBottom": "5px"}),
                            dcc.RadioItems(
                                id="physics-overlay-toggle",
                                options=[
                                    {
                                        "label": " Individual Step ",
                                        "value": "individual",
                                    },
                                    {
                                        "label": " Overlay All Filtered ",
                                        "value": "overlay",
                                    },
                                ],
                                value="individual",
                                inline=True,
                                style={"fontSize": "0.9em"},
                            ),
                        ],
                    ),
                    chart_card(
                        spinnable_graph("grf-plot"),
                        extra_style={"flex": "1", "border": "1px solid #eee"},
                    ),
                    chart_card(
                        spinnable_graph("cop-plot"),
                        extra_style={"flex": "1", "border": "1px solid #eee"},
                    ),
                ],
            ),
            # Spatial column
            html.Div(
                style={
                    "flex": "1",
                    "display": "flex",
                    "flexDirection": "column",
                    "gap": "10px",
                },
                children=[
                    html.Div(
                        style={
                            "display": "flex",
                            "justifyContent": "space-between",
                            "alignItems": "center",
                        },
                        children=[
                            html.H4(
                                "Spatial Footstep Map", style={"marginBottom": "5px"}
                            ),
                            dcc.Checklist(
                                id="isolate-pass-check",
                                options=[
                                    {
                                        "label": " Isolate Pass on Click",
                                        "value": "isolate",
                                    }
                                ],
                                value=["isolate"],
                                inputStyle={"marginRight": "5px"},
                            ),
                        ],
                    ),
                    chart_card(
                        spinnable_graph("walkway-plot"),
                        extra_style={"flex": "1", "border": "1px solid #ccc"},
                    ),
                ],
            ),
        ],
    )


def _get_st_pressure_section() -> html.Div:
    """Heatmap and histogram pressure-detail panels."""
    _shadow_card = {
        "flex": "1",
        "backgroundColor": "white",
        "padding": "15px",
        "borderRadius": "5px",
        "boxShadow": "0 2px 4px rgba(0,0,0,0.1)",
    }
    return html.Div(
        style={
            "marginTop": "20px",
            "paddingTop": "20px",
            "borderTop": "2px solid #ddd",
        },
        children=[
            html.Div(
                style={
                    "display": "flex",
                    "justifyContent": "space-between",
                    "alignItems": "center",
                    "marginBottom": "10px",
                },
                children=[
                    html.H3("Pressure Detail", style={"margin": "0"}),
                    html.Div(
                        children=[
                            html.Label(
                                "Color Scale:",
                                style={**LABEL_BOLD, "marginRight": "10px"},
                            ),
                            dcc.RadioItems(
                                id="color-scale-toggle",
                                options=[
                                    {
                                        "label": " Dynamic (Step Peak) ",
                                        "value": "dynamic",
                                    },
                                    {
                                        "label": " Absolute (800 kPa) ",
                                        "value": "absolute",
                                    },
                                ],
                                value="dynamic",
                                inline=True,
                            ),
                        ]
                    ),
                ],
            ),
            html.Div(
                style={"display": "flex", "gap": "20px"},
                children=[
                    html.Div(
                        style=_shadow_card,
                        children=[spinnable_graph("heatmap-plot", height="400px")],
                    ),
                    html.Div(
                        style=_shadow_card,
                        children=[spinnable_graph("histogram-plot", height="400px")],
                    ),
                ],
            ),
        ],
    )
