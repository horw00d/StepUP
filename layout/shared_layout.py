from dash import dcc, html
from config import _APPLY_BTN_ID, _QUERY_PLACEHOLDER, _TAB_PREFIX, _VALID_TAB_NAMES
from data import get_dropdown_options
from layout.styles import (
    BTN_PRIMARY,
    BTN_SECONDARY,
    COHORT_BOX,
    ERROR_MSG_STYLE,
    FILTER_BOX,
    INPUT_STYLE,
    LABEL_BOLD,
)
from models import Participant, Trial

try:
    OPTIONS_PART = get_dropdown_options(Participant.id)
    OPTIONS_SHOE = get_dropdown_options(Trial.footwear)
    OPTIONS_SPEED = get_dropdown_options(Trial.speed)
except Exception:
    OPTIONS_PART = OPTIONS_SHOE = OPTIONS_SPEED = []


def get_dynamic_outlier_layout(tab_name: str) -> html.Div:
    """
    Pattern-matched Dynamic Outlier Classification widget shared by both tabs.

    tab_name must be 'single' or 'cross'.  Validated eagerly so a typo
    surfaces as a clear ValueError at startup rather than a silent callback
    mismatch discovered only at interaction time.
    """
    if tab_name not in _VALID_TAB_NAMES:
        raise ValueError(
            f"tab_name must be one of {sorted(_VALID_TAB_NAMES)}, got {tab_name!r}"
        )
    return html.Div(
        style={
            **COHORT_BOX,
            "display": "flex",
            "flexDirection": "column",
            "gap": "10px",
        },
        children=[
            html.Label("Dynamic Outlier Classification:", style=LABEL_BOLD),
            html.Div(
                style={"display": "flex", "alignItems": "center", "gap": "10px"},
                children=[
                    dcc.Dropdown(
                        id={"type": "outlier-metric", "tab": tab_name},
                        options=[
                            {"label": "R-Score", "value": "r_score"},
                            {"label": "Peak GRF", "value": "peak_grf"},
                            {
                                "label": "Stance Duration",
                                "value": "stance_duration_frames",
                            },
                        ],
                        value="r_score",
                        clearable=False,
                        style={"minWidth": "180px"},
                    ),
                    dcc.Dropdown(
                        id={"type": "outlier-operator", "tab": tab_name},
                        options=[
                            {"label": "Less Than (<)", "value": "<"},
                            {"label": "Greater Than (>)", "value": ">"},
                        ],
                        value="<",
                        clearable=False,
                        style={"minWidth": "150px"},
                    ),
                    dcc.Input(
                        id={"type": "outlier-threshold", "tab": tab_name},
                        type="number",
                        value=0.85,
                        step=0.01,
                        style=INPUT_STYLE,
                    ),
                    html.Button(
                        "Apply Threshold",
                        id={"type": "outlier-apply-btn", "tab": tab_name},
                        n_clicks=0,
                        style=BTN_PRIMARY,
                    ),
                ],
            ),
        ],
    )


def _get_query_builder(tab_name: str) -> html.Div:
    """
    Advanced Query Builder row — previously duplicated verbatim in both tabs.
    All tab-specific values (component IDs, placeholder) are resolved from the
    module-level mapping dicts above, keeping the logic in one place.
    """
    prefix = _TAB_PREFIX[tab_name]
    return html.Div(
        style={
            **FILTER_BOX,
            "display": "flex",
            "flexDirection": "column",
            "gap": "10px",
        },
        children=[
            html.Div(
                style={"display": "flex", "alignItems": "center", "gap": "10px"},
                children=[
                    html.Label(
                        "Advanced Query:",
                        style={**LABEL_BOLD, "whiteSpace": "nowrap"},
                    ),
                    dcc.Input(
                        id={"type": "query-input", "tab": tab_name},
                        type="text",
                        placeholder=_QUERY_PLACEHOLDER[tab_name],
                        debounce=True,
                        style=INPUT_STYLE,
                    ),
                    html.Button(
                        "Apply",
                        id=_APPLY_BTN_ID[tab_name],
                        n_clicks=0,
                        style=BTN_PRIMARY,
                    ),
                    html.Button(
                        "Clear",
                        id={"type": "clear-query-btn", "tab": tab_name},
                        n_clicks=0,
                        style=BTN_SECONDARY,
                    ),
                ],
            ),
            html.Div(id=f"{prefix}-query-error-msg", style=ERROR_MSG_STYLE),
        ],
    )
