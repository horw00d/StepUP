from dash import html, dcc
from layout.cross_trial_layout import get_cross_trial_layout
from layout.single_trial_layout import get_single_trial_layout

# =====================================================================
# MASTER SHELL
# =====================================================================


def create_layout() -> html.Div:
    return html.Div(
        style={
            "minHeight": "100vh",
            "display": "flex",
            "flexDirection": "column",
            "padding": "20px",
        },
        children=[
            # Global state stores — grouped together for clarity
            dcc.Store(id="selected-step-store"),
            dcc.Store(id="physics-cache", storage_type="memory"),
            dcc.Store(id="filtered-data-store"),
            dcc.Store(id="ct-filtered-data-store"),
            dcc.Store(id="bridge-store"),
            html.H2("StepUP Analysis", style={"marginBottom": "20px"}),
            dcc.Tabs(
                id="master-tabs",
                value="tab-single-trial",
                children=[
                    dcc.Tab(
                        label="Single-Trial Analysis",
                        value="tab-single-trial",
                        children=[
                            html.Div(
                                style={"paddingTop": "20px"},
                                children=[get_single_trial_layout()],
                            )
                        ],
                    ),
                    dcc.Tab(
                        label="Cross-Trial Analysis",
                        value="tab-cross-trial",
                        children=[
                            html.Div(
                                style={"paddingTop": "20px"},
                                children=[get_cross_trial_layout()],
                            )
                        ],
                    ),
                ],
            ),
        ],
    )
