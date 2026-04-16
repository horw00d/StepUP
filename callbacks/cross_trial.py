from helpers import apply_advanced_query, apply_dynamic_outliers, apply_data_granularity
from dash import Input, Output, State, ctx, no_update
from config import GRANULARITY_COMPATIBLE_GROUPS
from config import NO_COLOR_SENTINEL
import plotly.graph_objects as go
import io
import pandas as pd
import data
from graphics.cross_trial_graphics import (
    create_box_plot,
    create_violin_plot,
    create_bivariate_scatter_plot,
    create_aggregate_waveform_plot,
)
from graphics.single_trial_graphics import (
    create_grf_plot,
    create_cop_plot,
    get_empty_physics_layout,
)

# =====================================================================
# CROSS-TRIAL CALLBACKS
# =====================================================================

# Consistent empty state
_EMPTY_CT_STORE = {"raw_df_json": None, "raw_step_ids": []}


def _empty_ct_figures(title: str):
    """
    Returns a four-figure tuple of empty Plotly figures for the cross-trial
    plot outputs, each displaying the given title as a placeholder message.
    Used to populate all four chart outputs in a single early-return statement.
    """
    fig = go.Figure(layout=get_empty_physics_layout(title))
    return fig, fig, fig, fig


def register_cross_trial_callbacks(app):
    # I. CROSS-TRIAL DATA CONTROLLER
    #
    # Mirrors the single-trial master_data_controller pattern. Owns all data
    # access and query logic for the cross-trial tab, then broadcasts clean
    # state to ct-filtered-data-store for downstream plot callbacks to consume.
    #
    # Triggers: any change to the cohort dropdowns, the apply button, or the
    # update button — the same inputs that previously drove the mega-callback.
    # The update button is kept here so the controller always runs before the
    # renderer (Dash fires callbacks in dependency order).
    #
    # Outputs:
    #   ct-filtered-data-store — {raw_step_ids, valid_footstep_ids, raw_df_json}
    #     raw_step_ids:      footstep DB IDs before granularity aggregation,
    #                        used by the aggregate waveform plot.
    #     valid_footstep_ids: same list, kept for any future per-step consumers.
    #     raw_df_json:       the fully-filtered DataFrame serialised to JSON so
    #                        the renderer can apply granularity without hitting
    #                        the DB again.
    #   ct-query-error-msg  — validation/execution error string, or "".
    @app.callback(
        [
            Output("ct-filtered-data-store", "data"),
            Output("ct-query-error-msg", "children"),
        ],
        [
            Input("ct-update-btn", "n_clicks"),
            Input("ct-apply-query-btn", "n_clicks"),
            Input({"type": "outlier-apply-btn", "tab": "cross"}, "n_clicks"),
        ],
        [
            State("ct-part-dd", "value"),
            State("ct-shoe-dd", "value"),
            State("ct-speed-dd", "value"),
            State({"type": "query-input", "tab": "cross"}, "value"),
            State({"type": "outlier-metric", "tab": "cross"}, "value"),
            State({"type": "outlier-operator", "tab": "cross"}, "value"),
            State({"type": "outlier-threshold", "tab": "cross"}, "value"),
        ],
    )
    def ct_master_data_controller(
        update_clicks,
        query_clicks,
        out_clicks,
        parts,
        shoes,
        speeds,
        query_string,
        out_metric,
        out_op,
        out_thresh,
    ):

        # Check all three buttons to prevent initial load firing if desired
        if update_clicks == 0 and query_clicks == 0 and out_clicks == 0:
            return _EMPTY_CT_STORE, ""

        # 1. Fetch RAW Data
        df = data.fetch_cross_trial_data(part_ids=parts, shoes=shoes, speeds=speeds)
        if df.empty:
            return _EMPTY_CT_STORE, ""

        # 2. Apply Dynamic Outlier Reclassification

        df = apply_dynamic_outliers(df, out_metric, out_op, out_thresh)

        # 3. Apply Free-Form Query Filtering
        error_msg = ""
        if query_string:
            df, error_msg = apply_advanced_query(df, query_string)
            if error_msg or df.empty:
                return _EMPTY_CT_STORE, error_msg

        # 4. Extract RAW step IDs and serialize
        raw_step_ids = df["footstep_id"].tolist() if "footstep_id" in df.columns else []
        raw_df_json = df.to_json(orient="split")

        return {"raw_df_json": raw_df_json, "raw_step_ids": raw_step_ids}, ""

    # J. UPDATE CROSS-TRIAL PLOTS
    #
    # Pure renderer: reads pre-filtered data from ct-filtered-data-store,
    # applies granularity aggregation, and builds the four figures.
    # No data fetching, no query logic — those live in ct_master_data_controller.
    @app.callback(
        [
            Output("ct-box-plot", "figure"),
            Output("ct-violin-plot", "figure"),
            Output("ct-bivariate-scatter", "figure"),
            Output("ct-aggregate-waveform", "figure"),
        ],
        [
            Input("ct-filtered-data-store", "data"),
            Input("ct-granularity-dd", "value"),
            Input("ct-metric-dd", "value"),
            Input("ct-scatter-x-dd", "value"),
            Input("ct-group-dd", "value"),
            Input("ct-color-dd", "value"),
        ],
    )
    def update_cross_trial_plots(
        ct_store, granularity, metric_y, metric_x, group, color
    ):
        # Store is None on initial load (before either button is clicked)
        if ct_store is None or not ct_store.get("raw_df_json"):
            return _empty_ct_figures("Awaiting Execution")

        raw_df_json = ct_store.get("raw_df_json")
        raw_step_ids = ct_store.get("raw_step_ids", [])

        if not raw_df_json:
            return _empty_ct_figures("No Data Matching Criteria")

        # 1. Deserialise the pre-filtered DataFrame
        df = pd.read_json(io.StringIO(raw_df_json), orient="split")

        if df.empty:
            return _empty_ct_figures("No Data Matching Criteria")

        # 2. Apply granularity aggregation
        df_agg = apply_data_granularity(df, granularity)
        safe_group = group if group in df_agg.columns else None
        safe_color = color if color in df_agg.columns else None

        # 3. Build figures
        box_fig = create_box_plot(
            df_agg, y_col=metric_y, x_col=safe_group, color_col=safe_color
        )
        violin_fig = create_violin_plot(
            df_agg, y_col=metric_y, x_col=safe_group, color_col=safe_color
        )
        scatter_fig = create_bivariate_scatter_plot(
            df_agg, y_col=metric_y, x_col=metric_x, color_col=safe_color
        )

        time_pct, mean_grf, upper_bound, lower_bound = data.fetch_aggregate_waveforms(
            raw_step_ids
        )
        wave_fig = create_aggregate_waveform_plot(
            time_pct, mean_grf, upper_bound, lower_bound
        )

        return box_fig, violin_fig, scatter_fig, wave_fig

    # K. THE BRIDGE (Part 1: Capture the Click)
    @app.callback(
        Output("bridge-store", "data"),
        [
            Input("ct-box-plot", "clickData"),
            Input("ct-violin-plot", "clickData"),
            Input("ct-bivariate-scatter", "clickData"),
        ],
        prevent_initial_call=True,
    )
    def capture_cross_trial_click(box_click, violin_click, scatter_click):
        trigger_id = ctx.triggered_id

        if trigger_id == "ct-box-plot":
            click_data = box_click
        elif trigger_id == "ct-violin-plot":
            click_data = violin_click
        elif trigger_id == "ct-bivariate-scatter":
            click_data = scatter_click
        else:
            return no_update

        if click_data and "points" in click_data:
            point = click_data["points"][0]
            if "customdata" in point:
                c_data = point["customdata"]
                # Validate shape before indexing
                if not isinstance(c_data, (list, tuple)) or len(c_data) < 3:
                    return no_update

                part, shoe, speed = c_data[0], c_data[1], c_data[2]
                return {
                    "part": str(part).zfill(3) if part is not None else None,
                    "shoe": str(shoe) if shoe is not None else None,
                    "speed": str(speed) if speed is not None else None,
                }
        return no_update

    # L. THE BRIDGE (Part 2: Execute Navigation)
    @app.callback(
        [
            Output("part-dd", "value"),
            Output("shoe-dd", "value"),
            Output("speed-dd", "value"),
            Output("master-tabs", "value"),
        ],
        Input("bridge-store", "data"),
        prevent_initial_call=True,
    )
    def execute_bridge(bridge_data):
        if not bridge_data:
            return no_update
        part = bridge_data.get("part")
        shoe = bridge_data.get("shoe")
        speed = bridge_data.get("speed")
        if not all([part, shoe, speed]):
            return no_update
        return part, shoe, speed, "tab-single-trial"

    # M. CONSTRAIN GROUP/COLOR DROPDOWNS BASED ON GRANULARITY
    @app.callback(
        [
            Output("ct-group-dd", "options"),
            Output("ct-group-dd", "value"),
            Output("ct-color-dd", "options"),
            Output("ct-color-dd", "value"),
        ],
        [Input("ct-granularity-dd", "value")],
        [State("ct-group-dd", "value"), State("ct-color-dd", "value")],
    )
    def update_group_color_dropdowns(granularity, current_group, current_color):
        """
        Dynamically enables/disables Group By and Color By options based on the
        selected granularity level. Prevents the user from selecting combinations
        that would produce meaningless aggregations (e.g., grouping by 'footwear'
        at participant granularity, where footwear has been averaged out).
        """
        compatible = GRANULARITY_COMPATIBLE_GROUPS.get(granularity, set())

        all_group_options = [
            {"label": "Footwear Type", "value": "footwear"},
            {"label": "Walking Speed", "value": "speed"},
            {"label": "Biological Sex", "value": "sex"},
            {"label": "Participant ID", "value": "participant_id"},
        ]
        all_color_options = [
            {"label": "None", "value": NO_COLOR_SENTINEL},
            {"label": "Footwear Type", "value": "footwear"},
            {"label": "Walking Speed", "value": "speed"},
            {"label": "Biological Sex", "value": "sex"},
            {"label": "Side (Left/Right)", "value": "side"},
            {"label": "Outlier Status", "value": "is_outlier"},
        ]

        group_options = [
            {**opt, "disabled": opt["value"] not in compatible}
            for opt in all_group_options
        ]
        color_options = [
            {
                **opt,
                "disabled": opt["value"] not in compatible
                and opt["value"] != NO_COLOR_SENTINEL,
            }
            for opt in all_color_options
        ]

        valid_group = (
            current_group
            if current_group in compatible
            else next(
                (
                    opt["value"]
                    for opt in all_group_options
                    if opt["value"] in compatible
                ),
                None,
            )
        )
        valid_color = (
            current_color
            if (current_color == NO_COLOR_SENTINEL or current_color in compatible)
            else NO_COLOR_SENTINEL
        )

        return group_options, valid_group, color_options, valid_color
