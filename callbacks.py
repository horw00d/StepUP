from helpers import filter_dataframe, apply_advanced_query, apply_data_granularity
from dash import html, Input, Output, State, ctx, ALL, no_update, MATCH
from config import GRANULARITY_COMPATIBLE_GROUPS
from config import NO_COLOR_SENTINEL
import plotly.graph_objects as go
import io
import pandas as pd
import data
import graphics

# =====================================================================
# MASTER: Master Data Controller   -> Fetches & filters data, broadcasts valid IDs
# A. UPDATE FEATURE PLOTS          -> Renders Scatter and Rug plots
# B. UPDATE PHYSICS PLOTS          -> Renders GRF & COP lines (with Ghost Line logic)
# C. UPDATE WALKWAY PLOT           -> Renders Spatial Walkway map
# D. UPDATE PRESSURE PLOTS         -> Renders Heatmap & Histogram for specific step
# E. UPDATE IMAGE GRID             -> Renders DOM for Footstep Library
# F. UNIFIED SELECTION             -> Maps clicks across all plots to a single step ID
# G. MANAGE PASS SELECTOR          -> Dynamically populates pass dropdown
# H. CLEAR QUERY                   -> Resets Advanced Query Input
# I. CROSS-TRIAL DATA CONTROLLER   -> Fetches, queries, and broadcasts clean CT data
# J. UPDATE CROSS-TRIAL PLOTS      -> Renders Box/Violin/Bivariate/AggregateWave
# K. THE BRIDGE (Part 1: Capture the Click)
# L. THE BRIDGE (Part 2: Execute Navigation)
# M. CONSTRAIN GROUP/COLOR DROPDOWNS BASED ON GRANULARITY
# =====================================================================


def _empty_ct_figures(title: str):
    """
    Returns the standard four-figure empty-state tuple for cross-trial plots,
    paired with an error message string. Eliminates repeated boilerplate across
    the early-return branches of the cross-trial plot renderer.
    """
    fig = go.Figure(layout=graphics.get_empty_physics_layout(title))
    return fig, fig, fig, fig


def register_callbacks(app):

    # =====================================================================
    # SINGLE-TRIAL CALLBACKS
    # =====================================================================

    # MASTER: Master Data Controller
    @app.callback(
        [Output('filtered-data-store', 'data'),
         Output('trial-status', 'children'), 
         Output('st-query-error-msg', 'children')],
        [Input('part-dd', 'value'),
         Input('shoe-dd', 'value'),
         Input('speed-dd', 'value'),
         Input('filter-side', 'value'),       
         Input('filter-outlier', 'value'),    
         Input('filter-tile', 'value'),       
         Input('filter-pass', 'value'),       
         Input('st-apply-query-btn', 'n_clicks'),
         Input({'type': 'query-input', 'tab': 'single'}, 'value'),
         Input({'type': 'outlier-apply-btn', 'tab': 'single'}, 'n_clicks')], 
        [
         State({'type': 'outlier-metric', 'tab': 'single'}, 'value'),
         State({'type': 'outlier-operator', 'tab': 'single'}, 'value'),
         State({'type': 'outlier-threshold', 'tab': 'single'}, 'value')]
    )
    def master_data_controller(part, shoe, speed, sides, outliers, tiles, passes, query_clicks, query_string, out_clicks, out_metric, out_op, out_thresh):
        if not (part and shoe and speed):
            return {'valid_ids': []}, "No Trial Selected", ""

        # 1. Fetch from DB
        trial, steps, df = data.fetch_trial_data(part, shoe, speed)
        if not trial:
            return {'valid_ids': []}, "No Data", ""

        # 2. Apply Dynamic Outlier Reclassification
        from helpers import apply_dynamic_outliers
        df = apply_dynamic_outliers(df, out_metric, out_op, out_thresh)

        # 3. Apply standard UI and Advanced Query filters
        df_filtered, error_msg = filter_dataframe(df, sides, outliers, tiles, passes, query_string)

        valid_ids = df_filtered['id'].tolist() if not df_filtered.empty else []
        status = f"Trial: {part}-{shoe}-{speed} ({len(valid_ids)} steps)"

        return {'valid_ids': valid_ids}, status, error_msg


    # A. UPDATE FEATURE PLOTS
    @app.callback(
        [Output('main-scatter', 'figure'),
         Output('rug-plot', 'figure')],
        [Input('filtered-data-store', 'data'),
         Input('part-dd', 'value'),
         Input('shoe-dd', 'value'),
         Input('speed-dd', 'value'),
         Input('xaxis-dd', 'value'),
         Input('yaxis-dd', 'value'),
         Input('rug-dd', 'value'),
         Input('color-dd', 'value'),
         Input('selected-step-store', 'data')]
    )
    def update_feature_plots(filtered_data, part, shoe, speed, x_col, y_col, rug_col, color_col, selected_step_id):
        if not filtered_data or not (part and shoe and speed):
            return graphics.create_scatter_plot(pd.DataFrame(), "","", ""), graphics.create_rug_plot(pd.DataFrame(), "", "")

        valid_ids = filtered_data.get('valid_ids', [])
        trial, steps, df = data.fetch_trial_data(part, shoe, speed)
        
        if not trial or df.empty:
            return graphics.create_scatter_plot(pd.DataFrame(), "","", ""), graphics.create_rug_plot(pd.DataFrame(), "", "")

        df_filtered = df[df['id'].isin(valid_ids)]

        scatter_fig = graphics.create_scatter_plot(df_filtered, x_col, y_col, color_col, selected_step_id)
        rug_fig = graphics.create_rug_plot(df_filtered, rug_col, color_col, selected_step_id)

        return scatter_fig, rug_fig

    # B. UPDATE PHYSICS PLOTS
    @app.callback(
        [Output('grf-plot', 'figure'),
         Output('cop-plot', 'figure'),
         Output('physics-cache', 'data')],
        [Input('filtered-data-store', 'data'),
         Input('part-dd', 'value'),
         Input('shoe-dd', 'value'),
         Input('speed-dd', 'value'),
         Input('selected-step-store', 'data'),
         Input('physics-overlay-toggle', 'value')],
        [State('physics-cache', 'data')]
    )
    def update_physics_plots(filtered_data, part, shoe, speed, selected_step_id, overlay_mode, cache):
        current_trial_key = f"{part}-{shoe}-{speed}"
        if not cache or cache.get('trial_key') != current_trial_key:
            cache = {'trial_key': current_trial_key, 'metrics': []}
            
        if not filtered_data or not (part and shoe and speed):
            return graphics.create_grf_plot([]), graphics.create_cop_plot([]), cache

        valid_ids = filtered_data.get('valid_ids', [])
        is_overlay = (overlay_mode == 'overlay')
        
        # Determine exactly which footsteps we need to draw
        target_ids = valid_ids if is_overlay else ([selected_step_id] if selected_step_id else [])

        cached_metrics = cache.get('metrics', [])
        cached_ids = [m['step_id'] for m in cached_metrics]
        missing_ids = list(set(target_ids) - set(cached_ids))
        
        if missing_ids:
            new_metrics = data.fetch_physics_arrays(missing_ids)
            cached_metrics.extend(new_metrics)
            cache['metrics'] = cached_metrics

        required_metrics = [m for m in cached_metrics if m['step_id'] in target_ids]

        fig_grf = graphics.create_grf_plot(required_metrics, selected_step_id, overlay_mode=is_overlay)
        fig_cop = graphics.create_cop_plot(required_metrics, selected_step_id, overlay_mode=is_overlay)

        return fig_grf, fig_cop, cache

    # C. UPDATE WALKWAY PLOT
    @app.callback(
        Output('walkway-plot', 'figure'),
        [Input('filtered-data-store', 'data'),
         Input('part-dd', 'value'),
         Input('shoe-dd', 'value'),
         Input('speed-dd', 'value'),
         Input('selected-step-store', 'data'),
         Input('isolate-pass-check', 'value')]        
    )
    def update_walkway_plot(filtered_data, part, shoe, speed, selected_step_id, isolate_mode):
        if not filtered_data or not (part and shoe and speed):
            return go.Figure()

        trial, steps, df = data.fetch_trial_data(part, shoe, speed)
        if not trial or df.empty: return go.Figure()

        valid_ids = filtered_data.get('valid_ids', [])
        
        # Apply the master filter
        df_filtered = df[df['id'].isin(valid_ids)]
        
        # Apply localized "Isolate Pass" logic on top of the master filter
        if selected_step_id and ('isolate' in isolate_mode):
            selected_step = next((s for s in steps if s.id == selected_step_id), None)
            if selected_step and selected_step.pass_id is not None:
                df_filtered = df_filtered[df_filtered['pass_id'] == selected_step.pass_id]

        if df_filtered.empty:
             return graphics.create_walkway_plot([], selected_step_id)

        final_valid_ids = set(df_filtered['id'])
        filtered_steps_list = [s for s in steps if s.id in final_valid_ids]

        return graphics.create_walkway_plot(filtered_steps_list, selected_step_id)
    
    # D. UPDATE PRESSURE PLOTS
    @app.callback(
        [Output('heatmap-plot', 'figure'),
         Output('histogram-plot', 'figure')],
        [Input('selected-step-store', 'data'),
         Input('color-scale-toggle', 'value')]
    )
    def update_pressure_plots(step_id, scale_mode):
        if not step_id:
            return graphics.create_heatmap_and_histogram(None, None)
            
        matrix = data.fetch_footstep_matrix(step_id)
        is_dynamic = (scale_mode == 'dynamic')
        
        return graphics.create_heatmap_and_histogram(matrix, step_id, dynamic_scale=is_dynamic)

    # E. UPDATE IMAGE GRID
    @app.callback(
        Output('image-grid', 'children'),
        [Input('filtered-data-store', 'data'),
         Input('part-dd', 'value'),
         Input('shoe-dd', 'value'),
         Input('speed-dd', 'value'),
         Input('selected-step-store', 'data')]
    )
    def update_image_grid(filtered_data, part, shoe, speed, selected_step_id):
        if not filtered_data or not (part and shoe and speed):
            return []

        valid_ids = filtered_data.get('valid_ids', [])
        trial, steps, df = data.fetch_trial_data(part, shoe, speed)
        
        if not trial or not steps:
            return []

        filtered_steps_list = [s for s in steps if s.id in valid_ids]

        grid_items = []
        for step in filtered_steps_list: 
            is_selected = (step.id == selected_step_id)
            border_style = '3px solid #FF0000' if is_selected else '1px solid #eee'
            bg_color = '#fff0f0' if is_selected else 'white'
            
            item = html.Div(
                id={'type': 'grid-card', 'index': step.id}, n_clicks=0,
                style={'cursor': 'pointer', 'textAlign': 'center', 'border': border_style, 'backgroundColor': bg_color, 'borderRadius': '5px', 'padding': '5px'},
                children=[
                    html.Img(src=f"/assets/footsteps/step_{step.id}.png", style={'width': '100%'}),
                    html.Div(f"Step {step.footstep_index}", style={'fontSize': '0.8em', 'color': '#555'})
                ]
            )
            grid_items.append(item)

        return grid_items

    # F. UNIFIED SELECTION
    @app.callback(
        Output('selected-step-store', 'data'),
        [Input('main-scatter', 'clickData'),
         Input('rug-plot', 'clickData'),
         Input('walkway-plot', 'clickData'),
         Input({'type': 'grid-card', 'index': ALL}, 'n_clicks')],
        prevent_initial_call=True
    )
    def handle_selection(scatter_click, rug_click, walkway_click, grid_clicks):
        trigger_id = ctx.triggered_id
        if not trigger_id: return no_update

        if trigger_id == 'main-scatter' and scatter_click:
            point = scatter_click['points'][0]
            if 'customdata' in point:
                return point['customdata'][0]

        if trigger_id == 'rug-plot' and rug_click:
            point = rug_click['points'][0]
            if 'customdata' in point:
                return point['customdata'][0]

        if trigger_id == 'walkway-plot' and walkway_click:
            point = walkway_click['points'][0]
            if 'customdata' in point:
                return point['customdata'][0]

        if isinstance(trigger_id, dict) and trigger_id.get('type') == 'grid-card':
            return trigger_id['index']
        
        return no_update

    # G. MANAGE PASS SELECTOR
    @app.callback(
        [Output('filter-pass', 'options'),
         Output('filter-pass', 'value')],
        [Input('part-dd', 'value'),
         Input('shoe-dd', 'value'),
         Input('speed-dd', 'value')]
    )
    def manage_pass_selector(part, shoe, speed):
        if part and shoe and speed:
            options, _ = data.fetch_pass_options(part, shoe, speed)
            return options, []

        return [], []

    # H. CLEAR QUERY
    @app.callback(
        Output({'type': 'query-input', 'tab': MATCH}, 'value'),
        Input({'type': 'clear-query-btn', 'tab': MATCH}, 'n_clicks'),
        prevent_initial_call=True
    )
    def clear_query(n_clicks):
        return ""

    # =====================================================================
    # CROSS-TRIAL CALLBACKS
    # =====================================================================

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
        [Output('ct-filtered-data-store', 'data'),
         Output('ct-query-error-msg', 'children')],
        [Input('ct-update-btn', 'n_clicks'),
         Input('ct-apply-query-btn', 'n_clicks'),
         Input({'type': 'outlier-apply-btn', 'tab': 'cross'}, 'n_clicks')],
        [State('ct-part-dd', 'value'),        
         State('ct-shoe-dd', 'value'),
         State('ct-speed-dd', 'value'),
         State({'type': 'query-input', 'tab': 'cross'}, 'value'),
         State({'type': 'outlier-metric', 'tab': 'cross'}, 'value'),
         State({'type': 'outlier-operator', 'tab': 'cross'}, 'value'),
         State({'type': 'outlier-threshold', 'tab': 'cross'}, 'value')]
    )
    def ct_master_data_controller(update_clicks, query_clicks, out_clicks, parts, shoes, speeds, query_string, out_metric, out_op, out_thresh):
        # We check all three buttons to prevent initial load firing if desired
        if update_clicks == 0 and query_clicks == 0 and out_clicks == 0:
            return None, ""
            
        # 1. Fetch RAW Data
        df = data.fetch_cross_trial_data(part_ids=parts, shoes=shoes, speeds=speeds) 
        if df.empty:
            return {'raw_df_json': None, 'raw_step_ids': []}, ""

        # 2. Apply Dynamic Outlier Reclassification
        from helpers import apply_dynamic_outliers
        df = apply_dynamic_outliers(df, out_metric, out_op, out_thresh)

        # 3. Apply Free-Form Query Filtering
        error_msg = ""
        if query_string:
            from helpers import apply_advanced_query
            df, error_msg = apply_advanced_query(df, query_string)
            if error_msg or df.empty: 
                return {'raw_df_json': None, 'raw_step_ids': []}, error_msg

        # 4. Extract RAW step IDs and serialize
        raw_step_ids = df['footstep_id'].tolist() if 'footstep_id' in df.columns else []
        raw_df_json = df.to_json(orient='split')
        
        return {'raw_df_json': raw_df_json, 'raw_step_ids': raw_step_ids}, ""


    # J. UPDATE CROSS-TRIAL PLOTS
    #
    # Pure renderer: reads pre-filtered data from ct-filtered-data-store,
    # applies granularity aggregation, and builds the four figures.
    # No data fetching, no query logic — those live in ct_master_data_controller.
    @app.callback(
        [Output('ct-box-plot', 'figure'),
         Output('ct-violin-plot', 'figure'),
         Output('ct-bivariate-scatter', 'figure'),
         Output('ct-aggregate-waveform', 'figure')],
        [Input('ct-filtered-data-store', 'data'),
         Input('ct-granularity-dd', 'value'),
         Input('ct-metric-dd', 'value'),
         Input('ct-scatter-x-dd', 'value'),
         Input('ct-group-dd', 'value'),
         Input('ct-color-dd', 'value')]
    )
    def update_cross_trial_plots(ct_store, granularity, metric_y, metric_x, group, color):
        # Store is None on initial load (before either button is clicked)
        if ct_store is None:
            return _empty_ct_figures("Awaiting Execution")

        raw_df_json = ct_store.get('raw_df_json')
        raw_step_ids = ct_store.get('raw_step_ids', [])

        if not raw_df_json:
            return _empty_ct_figures("No Data Matching Criteria")

        # 1. Deserialise the pre-filtered DataFrame
        df = pd.read_json(io.StringIO(raw_df_json), orient='split')

        if df.empty:
            return _empty_ct_figures("No Data Matching Criteria")

        # 2. Apply granularity aggregation
        df_agg = apply_data_granularity(df, granularity)
        safe_group = group if group in df_agg.columns else None
        safe_color = color if color in df_agg.columns else None

        # 3. Build figures
        box_fig     = graphics.create_box_plot(df_agg, y_col=metric_y, x_col=safe_group, color_col=safe_color)
        violin_fig  = graphics.create_violin_plot(df_agg, y_col=metric_y, x_col=safe_group, color_col=safe_color)
        scatter_fig = graphics.create_bivariate_scatter_plot(df_agg, y_col=metric_y, x_col=metric_x, color_col=safe_color)

        time_pct, mean_grf, upper_bound, lower_bound = data.fetch_aggregate_waveforms(raw_step_ids)
        wave_fig = graphics.create_aggregate_waveform_plot(time_pct, mean_grf, upper_bound, lower_bound)

        return box_fig, violin_fig, scatter_fig, wave_fig

    # K. THE BRIDGE (Part 1: Capture the Click)
    @app.callback(
        Output('bridge-store', 'data'),
        [Input('ct-box-plot', 'clickData'),
         Input('ct-violin-plot', 'clickData'),
         Input('ct-bivariate-scatter', 'clickData')],
        prevent_initial_call=True
    )
    def capture_cross_trial_click(box_click, violin_click, scatter_click):
        trigger_id = ctx.triggered_id
        
        if trigger_id == 'ct-box-plot': click_data = box_click
        elif trigger_id == 'ct-violin-plot': click_data = violin_click
        else: click_data = scatter_click
        
        if click_data and 'points' in click_data:
            point = click_data['points'][0]
            if 'customdata' in point:
                c_data = point['customdata']
                
                return {
                    'part': str(c_data[0]).zfill(3) if c_data[0] is not None else None,
                    'shoe': str(c_data[1]) if c_data[1] is not None else None,
                    'speed': str(c_data[2]) if c_data[2] is not None else None
                }
        return no_update

    # L. THE BRIDGE (Part 2: Execute Navigation)
    @app.callback(
        [Output('part-dd', 'value'),
         Output('shoe-dd', 'value'),
         Output('speed-dd', 'value'),
         Output('master-tabs', 'value')],
        Input('bridge-store', 'data'),
        prevent_initial_call=True
    )
    def execute_bridge(bridge_data):
        if bridge_data:
            return bridge_data['part'], bridge_data['shoe'], bridge_data['speed'], 'tab-single-trial'
        return no_update

    # M. CONSTRAIN GROUP/COLOR DROPDOWNS BASED ON GRANULARITY
    @app.callback(
        [Output('ct-group-dd', 'options'),
         Output('ct-group-dd', 'value'),
         Output('ct-color-dd', 'options'),
         Output('ct-color-dd', 'value')],
        [Input('ct-granularity-dd', 'value')],
        [State('ct-group-dd', 'value'),
         State('ct-color-dd', 'value')]
    )
    def constrain_group_color_dropdowns(granularity, current_group, current_color):
        """
        Dynamically enables/disables Group By and Color By options based on the
        selected granularity level. Prevents the user from selecting combinations
        that would produce meaningless aggregations (e.g., grouping by 'footwear'
        at participant granularity, where footwear has been averaged out).
        """
        compatible = GRANULARITY_COMPATIBLE_GROUPS.get(granularity, set())

        all_group_options = [
            {'label': 'Footwear Type',     'value': 'footwear'},
            {'label': 'Walking Speed',     'value': 'speed'},
            {'label': 'Biological Sex',    'value': 'sex'},
            {'label': 'Participant ID',    'value': 'participant_id'},
        ]
        all_color_options = [
            {'label': 'None',              'value': NO_COLOR_SENTINEL},
            {'label': 'Footwear Type',     'value': 'footwear'},
            {'label': 'Walking Speed',     'value': 'speed'},
            {'label': 'Biological Sex',    'value': 'sex'},
            {'label': 'Side (Left/Right)', 'value': 'side'},
            {'label': 'Outlier Status',     'value': 'is_outlier'},
        ]

        group_options = [
            {**opt, 'disabled': opt['value'] not in compatible}
            for opt in all_group_options
        ]
        color_options = [
            {**opt, 'disabled': opt['value'] not in compatible and opt['value'] != NO_COLOR_SENTINEL}
            for opt in all_color_options
        ]

        valid_group = current_group if current_group in compatible else next(
            (opt['value'] for opt in all_group_options if opt['value'] in compatible), None
        )
        valid_color = current_color if (
            current_color == NO_COLOR_SENTINEL or current_color in compatible
        ) else NO_COLOR_SENTINEL

        return group_options, valid_group, color_options, valid_color