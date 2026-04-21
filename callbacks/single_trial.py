from helpers import apply_dynamic_outliers, filter_dataframe
from dash import html, Input, Output, State, ctx, ALL, no_update
import plotly.graph_objects as go
import pandas as pd
import data
from graphics.single_trial_graphics import (
    create_grf_plot,
    create_cop_plot,
    create_heatmap_and_histogram,
    create_rug_plot,
    create_scatter_plot,
    create_walkway_plot,
)


def register_single_trial_callbacks(app):
    # MASTER: Master Data Controller
    @app.callback(
        [
            Output("filtered-data-store", "data"),
            Output("trial-status", "children"),
            Output("st-query-error-msg", "children"),
        ],
        [
            Input("part-dd", "value"),
            Input("shoe-dd", "value"),
            Input("speed-dd", "value"),
            Input("filter-side", "value"),
            Input("filter-outlier", "value"),
            Input("filter-tile", "value"),
            Input("filter-pass", "value"),
            Input("st-apply-query-btn", "n_clicks"),
            Input({"type": "query-input", "tab": "single"}, "value"),
            Input({"type": "outlier-apply-btn", "tab": "single"}, "n_clicks"),
        ],
        [
            State({"type": "outlier-metric", "tab": "single"}, "value"),
            State({"type": "outlier-operator", "tab": "single"}, "value"),
            State({"type": "outlier-threshold", "tab": "single"}, "value"),
        ],
    )
    def st_master_data_controller(
        part,
        shoe,
        speed,
        sides,
        outliers,
        tiles,
        passes,
        query_clicks,
        query_string,
        out_clicks,
        out_metric,
        out_op,
        out_thresh,
    ):
        if not (part and shoe and speed):
            return {"valid_ids": []}, "No Trial Selected", ""

        # 1. Fetch from DB
        trial, steps, df = data.fetch_trial_data(part, shoe, speed)
        if not trial:
            return {"valid_ids": []}, "No Data", ""

        # 2. Apply Dynamic Outlier Reclassification

        df = apply_dynamic_outliers(df, out_metric, out_op, out_thresh)

        # 3. Apply standard UI and Advanced Query filters
        df_filtered, error_msg = filter_dataframe(
            df, sides, outliers, tiles, passes, query_string
        )

        valid_ids = df_filtered["id"].tolist() if not df_filtered.empty else []
        status = f"Trial: {part}-{shoe}-{speed} ({len(valid_ids)} steps)"

        return {"valid_ids": valid_ids}, status, error_msg

    # A. UPDATE FEATURE PLOTS
    @app.callback(
        [Output("main-scatter", "figure"), Output("rug-plot", "figure")],
        [
            Input("filtered-data-store", "data"),
            Input("part-dd", "value"),
            Input("shoe-dd", "value"),
            Input("speed-dd", "value"),
            Input("xaxis-dd", "value"),
            Input("yaxis-dd", "value"),
            Input("rug-dd", "value"),
            Input("color-dd", "value"),
            Input("selected-step-store", "data"),
        ],
    )
    def update_feature_plots(
        filtered_data,
        part,
        shoe,
        speed,
        x_col,
        y_col,
        rug_col,
        color_col,
        selected_step_id,
    ):
        if not filtered_data or not (part and shoe and speed):
            return create_scatter_plot(pd.DataFrame(), "", "", ""), create_rug_plot(
                pd.DataFrame(), "", ""
            )

        valid_ids = filtered_data.get("valid_ids", [])
        trial, steps, df = data.fetch_trial_data(part, shoe, speed)

        if not trial or df.empty:
            return create_scatter_plot(pd.DataFrame(), "", "", ""), create_rug_plot(
                pd.DataFrame(), "", ""
            )

        df_filtered = df[df["id"].isin(valid_ids)]

        scatter_fig = create_scatter_plot(
            df_filtered, x_col, y_col, color_col, selected_step_id
        )
        rug_fig = create_rug_plot(df_filtered, rug_col, color_col, selected_step_id)

        return scatter_fig, rug_fig

    # B. UPDATE PHYSICS PLOTS
    @app.callback(
        [
            Output("grf-plot", "figure"),
            Output("cop-plot", "figure"),
            Output("physics-cache", "data"),
        ],
        [
            Input("filtered-data-store", "data"),
            Input("part-dd", "value"),
            Input("shoe-dd", "value"),
            Input("speed-dd", "value"),
            Input("selected-step-store", "data"),
            Input("physics-overlay-toggle", "value"),
        ],
        [State("physics-cache", "data")],
    )
    def update_physics_plots(
        filtered_data, part, shoe, speed, selected_step_id, overlay_mode, cache
    ):
        # Guard first and build key when inputs are valid
        if not filtered_data or not (part and shoe and speed):
            return (
                create_grf_plot([]),
                create_cop_plot([]),
                cache or {},
            )

        current_trial_key = f"{part}-{shoe}-{speed}"
        if not cache or cache.get("trial_key") != current_trial_key:
            cache = {"trial_key": current_trial_key, "metrics": []}

        if not filtered_data or not (part and shoe and speed):
            return create_grf_plot([]), create_cop_plot([]), cache

        valid_ids = filtered_data.get("valid_ids", [])
        is_overlay = overlay_mode == "overlay"

        # Determine exactly which footsteps we need to draw
        target_ids = (
            valid_ids
            if is_overlay
            else ([selected_step_id] if selected_step_id else [])
        )

        cached_metrics = cache.get("metrics", [])
        cached_ids = [m["step_id"] for m in cached_metrics]
        missing_ids = list(set(target_ids) - set(cached_ids))

        if missing_ids:
            new_metrics = data.fetch_physics_arrays(missing_ids)
            cached_metrics.extend(new_metrics)
            cache["metrics"] = cached_metrics

        required_metrics = [m for m in cached_metrics if m["step_id"] in target_ids]

        fig_grf = create_grf_plot(
            required_metrics, selected_step_id, overlay_mode=is_overlay
        )
        fig_cop = create_cop_plot(
            required_metrics, selected_step_id, overlay_mode=is_overlay
        )

        return fig_grf, fig_cop, cache

    # C. UPDATE WALKWAY PLOT
    @app.callback(
        Output("walkway-plot", "figure"),
        [
            Input("filtered-data-store", "data"),
            Input("part-dd", "value"),
            Input("shoe-dd", "value"),
            Input("speed-dd", "value"),
            Input("selected-step-store", "data"),
            Input("isolate-pass-check", "value"),
        ],
    )
    def update_walkway_plot(
        filtered_data, part, shoe, speed, selected_step_id, isolate_mode
    ):
        if not filtered_data or not (part and shoe and speed):
            return go.Figure()

        trial, steps, df = data.fetch_trial_data(part, shoe, speed)
        if not trial or df.empty:
            return go.Figure()

        valid_ids = filtered_data.get("valid_ids", [])

        # Apply the master filter
        df_filtered = df[df["id"].isin(valid_ids)]

        # Apply localized "Isolate Pass" logic on top of the master filter
        if selected_step_id and ("isolate" in isolate_mode):
            selected_step = next((s for s in steps if s.id == selected_step_id), None)
            if selected_step and selected_step.pass_id is not None:
                df_filtered = df_filtered[
                    df_filtered["pass_id"] == selected_step.pass_id
                ]

        if df_filtered.empty:
            return create_walkway_plot([], selected_step_id)

        final_valid_ids = set(df_filtered["id"])
        filtered_steps_list = [s for s in steps if s.id in final_valid_ids]

        return create_walkway_plot(filtered_steps_list, selected_step_id)

    # D. UPDATE PRESSURE PLOTS
    @app.callback(
        [Output("heatmap-plot", "figure"), Output("histogram-plot", "figure")],
        [Input("selected-step-store", "data"), Input("color-scale-toggle", "value")],
    )
    def update_pressure_plots(step_id, scale_mode):
        if not step_id:
            return create_heatmap_and_histogram(None, None)

        matrix = data.fetch_footstep_matrix(step_id)
        is_dynamic = scale_mode == "dynamic"

        return create_heatmap_and_histogram(matrix, step_id, dynamic_scale=is_dynamic)

    # E. UPDATE IMAGE GRID
    @app.callback(
        Output("image-grid", "children"),
        [
            Input("filtered-data-store", "data"),
            Input("part-dd", "value"),
            Input("shoe-dd", "value"),
            Input("speed-dd", "value"),
            Input("selected-step-store", "data"),
        ],
    )
    def update_image_grid(filtered_data, part, shoe, speed, selected_step_id):
        if not filtered_data or not (part and shoe and speed):
            return []

        valid_ids = filtered_data.get("valid_ids", [])
        trial, steps, df = data.fetch_trial_data(part, shoe, speed)

        if not trial or not steps:
            return []

        filtered_steps_list = [s for s in steps if s.id in valid_ids]

        grid_items = []
        for step in filtered_steps_list:
            is_selected = step.id == selected_step_id
            border_style = "3px solid #FF0000" if is_selected else "1px solid #eee"
            bg_color = "#fff0f0" if is_selected else "white"

            item = html.Div(
                id={"type": "grid-card", "index": step.id},
                n_clicks=0,
                style={
                    "cursor": "pointer",
                    "textAlign": "center",
                    "border": border_style,
                    "backgroundColor": bg_color,
                    "borderRadius": "5px",
                    "padding": "5px",
                },
                children=[
                    html.Img(
                        src=f"/assets/footsteps/step_{step.id}.png",
                        style={"width": "100%"},
                    ),
                    html.Div(
                        f"Step {step.footstep_index}",
                        style={"fontSize": "0.8em", "color": "#555"},
                    ),
                ],
            )
            grid_items.append(item)

        return grid_items

    # F. UNIFIED SELECTION
    @app.callback(
        Output("selected-step-store", "data"),
        [
            Input("main-scatter", "clickData"),
            Input("rug-plot", "clickData"),
            Input("walkway-plot", "clickData"),
            Input({"type": "grid-card", "index": ALL}, "n_clicks"),
        ],
        prevent_initial_call=True,
    )
    def update_selection(scatter_click, rug_click, walkway_click, grid_clicks):
        trigger_id = ctx.triggered_id
        if not trigger_id:
            return no_update

        if trigger_id == "main-scatter" and scatter_click:
            points = scatter_click.get("points", [])
            if not points:
                return no_update
            point = points[0]
            if "customdata" in point:
                return point["customdata"][0]

        if trigger_id == "rug-plot" and rug_click:
            points = rug_click.get("points", [])
            if not points:
                return no_update
            point = points[0]
            if "customdata" in point:
                return point["customdata"][0]

        if trigger_id == "walkway-plot" and walkway_click:
            points = walkway_click.get("points", [])
            if not points:
                return no_update
            point = points[0]
            if "customdata" in point:
                return point["customdata"][0]

        if isinstance(trigger_id, dict) and trigger_id.get("type") == "grid-card":
            return trigger_id["index"]

        return no_update

    # G. UPDATE PASS OPTIONS
    @app.callback(
        [Output("filter-pass", "options"), Output("filter-pass", "value")],
        [
            Input("part-dd", "value"),
            Input("shoe-dd", "value"),
            Input("speed-dd", "value"),
        ],
    )
    def update_pass_options(part, shoe, speed):
        if part and shoe and speed:
            options, _ = data.fetch_pass_options(part, shoe, speed)
            return options, []

        return [], []
