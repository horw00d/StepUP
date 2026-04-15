# =====================================================================
# TAB 2: CROSS-TRIAL ANALYSIS LAYOUT
# =====================================================================

from dash import dcc, html
from layout.primitives import chart_card, spinnable_graph
from layout.shared_layout import (
    OPTIONS_PART,
    OPTIONS_SHOE,
    OPTIONS_SPEED,
    _get_query_builder,
    get_dynamic_outlier_layout,
)
from config import FEATURE_OPTIONS
from layout.styles import BTN_SUCCESS, COHORT_BOX, LABEL_BOLD_SM, SECTION_BOX


def get_cross_trial_layout() -> html.Div:
    """
    Top-level assembler for the Cross-Trial tab.
    Mirrors the single-trial decomposition pattern for consistency.
    """
    return html.Div(
        children=[
            _get_ct_cohort_section(),
            get_dynamic_outlier_layout("cross"),
            _get_query_builder("cross"),
            _get_ct_controls_row(),
            _get_ct_chart_grid(),
        ]
    )


def _get_ct_cohort_section() -> html.Div:
    """Multi-select participant / footwear / speed cohort filters."""
    return html.Div(
        style={**COHORT_BOX, "display": "flex", "gap": "20px"},
        children=[
            html.Div(
                style={"flex": "1"},
                children=[
                    html.Label(
                        "1. Filter Participants (Leave blank for all):",
                        style=LABEL_BOLD_SM,
                    ),
                    dcc.Dropdown(
                        id="ct-part-dd",
                        options=OPTIONS_PART,
                        multi=True,
                        placeholder="All Participants",
                    ),
                ],
            ),
            html.Div(
                style={"flex": "1"},
                children=[
                    html.Label("2. Filter Footwear:", style=LABEL_BOLD_SM),
                    dcc.Dropdown(
                        id="ct-shoe-dd",
                        options=OPTIONS_SHOE,
                        multi=True,
                        placeholder="All Footwear",
                    ),
                ],
            ),
            html.Div(
                style={"flex": "1"},
                children=[
                    html.Label("3. Filter Speeds:", style=LABEL_BOLD_SM),
                    dcc.Dropdown(
                        id="ct-speed-dd",
                        options=OPTIONS_SPEED,
                        multi=True,
                        placeholder="All Speeds",
                    ),
                ],
            ),
        ],
    )


def _get_ct_controls_row() -> html.Div:
    """
    Plot-configuration dropdowns and the Update Charts button.
    """

    def _ctrl(label: str, dd_id: str, **kw) -> html.Div:
        return html.Div(
            style=SECTION_BOX,
            children=[
                html.Label(label, style=LABEL_BOLD_SM),
                dcc.Dropdown(id=dd_id, **kw),
            ],
        )

    return html.Div(
        style={
            "display": "flex",
            "gap": "15px",
            "marginBottom": "20px",
            "alignItems": "stretch",
        },
        children=[
            _ctrl(
                "Data Granularity:",
                "ct-granularity-dd",
                options=[
                    {"label": "Footstep", "value": "footstep"},
                    {"label": "Trial", "value": "trial"},
                    {"label": "Participant", "value": "participant"},
                ],
                value="footstep",
                clearable=False,
            ),
            _ctrl(
                "Primary Metric (Y-Axis):",
                "ct-metric-dd",
                options=FEATURE_OPTIONS,
                value="peak_grf",
                clearable=False,
            ),
            _ctrl(
                "Scatter Metric (X-Axis):",
                "ct-scatter-x-dd",
                options=FEATURE_OPTIONS,
                value="stance_duration_frames",
                clearable=False,
            ),
            # Options for these two are populated dynamically by callback M.
            _ctrl(
                "Group By (Distributions):",
                "ct-group-dd",
                value="footwear",
                clearable=False,
            ),
            _ctrl("Sub-Group (Color):", "ct-color-dd", value="speed", clearable=False),
            html.Div(
                style={"flex": "0.7", "display": "flex", "alignItems": "flex-end"},
                children=[
                    html.Button(
                        "Update Charts",
                        id="ct-update-btn",
                        n_clicks=0,
                        style=BTN_SUCCESS,
                    )
                ],
            ),
        ],
    )


def _get_ct_chart_grid() -> html.Div:
    """2×2 grid: box plot, violin plot, bivariate scatter, aggregate waveform."""

    def _row(*cards) -> html.Div:
        return html.Div(
            style={"display": "flex", "gap": "20px", "height": "450px"},
            children=list(cards),
        )

    return html.Div(
        style={"display": "flex", "flexDirection": "column", "gap": "20px"},
        children=[
            _row(
                chart_card(spinnable_graph("ct-box-plot")),
                chart_card(spinnable_graph("ct-violin-plot")),
            ),
            _row(
                chart_card(spinnable_graph("ct-bivariate-scatter")),
                chart_card(spinnable_graph("ct-aggregate-waveform")),
            ),
        ],
    )
