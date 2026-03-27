from helpers import filter_dataframe
from dash import html, Input, Output, State, ctx, ALL, no_update
import plotly.graph_objects as go
import pandas as pd
import data
import graphics

# =====================================================================
# STEPUP CALLBACK ARCHITECTURE (SINGLE-TRIAL PHASE)
# =====================================================================
# MASTER: Master Data Controller   -> Fetches & filters data, broadcasts valid IDs
# A. UPDATE FEATURE PLOTS          -> Renders Scatter and Rug plots
# B. UPDATE PHYSICS PLOTS          -> Renders GRF & COP lines (with Ghost Line logic)
# C. UPDATE WALKWAY PLOT           -> Renders Spatial Walkway map
# D. UPDATE PRESSURE PLOTS         -> Renders Heatmap & Histogram for specific step
# E. UPDATE IMAGE GRID             -> Renders DOM for Footstep Library
# F. UNIFIED SELECTION             -> Maps clicks across all plots to a single step ID
# G. MANAGE PASS SELECTOR          -> Dynamically populates pass dropdown
# H. CLEAR QUERY BUTTON LOGIC      -> Resets Advanced Query Input
# I. UPDATE CROSS-TRIAL PLOTS      -> Renders Box/Violin/Bivariate/AggregateWave for multi-trial comparisons
# J. THE BRIDGE (Part 1: Capture the Click)
# K. THE BRIDGE (Part 2: Execute Navigation)
# =====================================================================

def register_callbacks(app):

    # MASTER: Master Data Controller
    @app.callback(
        [Output('filtered-data-store', 'data'),
         Output('trial-status', 'children'),
         Output('query-error-msg', 'children')],
        [Input('part-dd', 'value'),
         Input('shoe-dd', 'value'),
         Input('speed-dd', 'value'),
         Input('filter-side', 'value'),
         Input('filter-outlier', 'value'),
         Input('filter-tile', 'value'),
         Input('filter-pass', 'value'),
         Input('apply-query-btn', 'n_clicks'),
         Input('query-input', 'value')]
    )
    def master_data_controller(part, shoe, speed, sides, outliers, tiles, passes, apply_clicks, query_string):
        if not (part and shoe and speed):
            return {'valid_ids': []}, "No Trial Selected", ""

        # Fetch from DB exactly ONE time per user interaction
        trial, steps, df = data.fetch_trial_data(part, shoe, speed)
        if not trial:
            return {'valid_ids': []}, "No Data", ""

        # Run the heavy Pandas filtering logic exactly ONE time
        df_filtered, error_msg = filter_dataframe(df, sides, outliers, tiles, passes, query_string)

        valid_ids = df_filtered['id'].tolist() if not df_filtered.empty else []
        status = f"Trial: {part}-{shoe}-{speed} ({len(valid_ids)} steps)"

        # Broadcast the state to the front-end
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
        #handle empty state
        if not step_id:
            return graphics.create_heatmap_and_histogram(None, None)
            
        #fetch the matrix
        matrix = data.fetch_footstep_matrix(step_id)
        
        #determine the scaling mode
        is_dynamic = (scale_mode == 'dynamic')
        
        #generate Plots with the toggle state passed down
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
            return scatter_click['points'][0]['customdata'][0]
        
        if trigger_id == 'rug-plot' and rug_click:
            return rug_click['points'][0]['customdata'][0]

        if trigger_id == 'walkway-plot' and walkway_click:
            return walkway_click['points'][0]['customdata'][0]

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
         # Removed 'selected-step-store' from Inputs!
    )
    def manage_pass_selector(part, shoe, speed):
        # Only runs when trial changes
        if part and shoe and speed:
            options, _ = data.fetch_pass_options(part, shoe, speed)
            return options, [] # Default to empty (All)

        return [], []

    # H. CLEAR QUERY BUTTON LOGIC
    @app.callback(
        Output('query-input', 'value'),
        Input('clear-query-btn', 'n_clicks'),
        prevent_initial_call=True
    )
    def clear_query(n_clicks):
        return ""

    # =====================================================================
    # CROSS-TRIAL CALLBACKS
    # =====================================================================

    # I. UPDATE CROSS-TRIAL PLOTS
    @app.callback(
        [Output('ct-box-plot', 'figure'),
         Output('ct-violin-plot', 'figure'),
         Output('ct-bivariate-scatter', 'figure'),
         Output('ct-aggregate-waveform', 'figure')],
        [Input('ct-update-btn', 'n_clicks')], 
        [State('ct-part-dd', 'value'),        
         State('ct-shoe-dd', 'value'),
         State('ct-speed-dd', 'value'),
         State('ct-metric-dd', 'value'),
         State('ct-scatter-x-dd', 'value'),
         State('ct-group-dd', 'value'),
         State('ct-color-dd', 'value'),
         State('ct-granularity-dd', 'value')] # <--- NEW STATE INPUT
    )
    def update_cross_trial_plots(n_clicks, parts, shoes, speeds, metric_y, metric_x, group, color, granularity):
        if n_clicks == 0:
            empty_fig = graphics.get_empty_physics_layout("Awaiting Execution")
            return go.Figure(layout=empty_fig), go.Figure(layout=empty_fig), go.Figure(layout=empty_fig), go.Figure(layout=empty_fig)
        
        # 1. Fetch RAW Data
        df = data.fetch_cross_trial_data(part_ids=parts, shoes=shoes, speeds=speeds) 
        
        if df.empty:
            empty_fig = graphics.get_empty_physics_layout("No Data Matching Criteria")
            return go.Figure(layout=empty_fig), go.Figure(layout=empty_fig), go.Figure(layout=empty_fig), go.Figure(layout=empty_fig)

        # 2. Extract RAW step IDs for the Waveform (which calculates its own aggregates)
        raw_step_ids = df['footstep_id'].tolist() if 'footstep_id' in df.columns else []

        # 3. Apply Granularity Aggregation for the statistical distribution plots
        from helpers import apply_data_granularity # Import our new helper
        df_agg = apply_data_granularity(df, granularity)
        
        # Safety Check: If the user selects "Participant Baseline", columns like "footwear" are averaged out.
        # We must prevent Plotly from crashing if it tries to group by a column that no longer exists.
        safe_group = group if group in df_agg.columns else None
        safe_color = color if color in df_agg.columns else None

        # 4. Generate Plots using the aggregated DataFrame
        box_fig = graphics.create_box_plot(df_agg, y_col=metric_y, x_col=safe_group, color_col=safe_color)
        violin_fig = graphics.create_violin_plot(df_agg, y_col=metric_y, x_col=safe_group, color_col=safe_color)
        scatter_fig = graphics.create_bivariate_scatter_plot(df_agg, y_col=metric_y, x_col=metric_x, color_col=safe_color)
        
        # 5. Generate Waveform using the RAW Step IDs
        time_pct, mean_grf, upper_bound, lower_bound = data.fetch_aggregate_waveforms(raw_step_ids)
        wave_fig = graphics.create_aggregate_waveform_plot(time_pct, mean_grf, upper_bound, lower_bound)
        
        return box_fig, violin_fig, scatter_fig, wave_fig
    
    # J. THE BRIDGE (Part 1: Capture the Click)
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
                    'part': c_data[0] if len(c_data) > 0 else None,
                    'shoe': c_data[1] if len(c_data) > 1 else None,
                    'speed': c_data[2] if len(c_data) > 2 else None
                }
        return no_update

    # K. THE BRIDGE (Part 2: Execute Navigation)
    @app.callback(
        [Output('part-dd', 'value'),
         Output('shoe-dd', 'value'),
         Output('speed-dd', 'value'),
         Output('master-tabs', 'value')], # forces the UI to flip back to Single-Trial
        Input('bridge-store', 'data'),
        prevent_initial_call=True
    )
    def execute_bridge(bridge_data):
        if bridge_data:
            return bridge_data['part'], bridge_data['shoe'], bridge_data['speed'], 'tab-single-trial'
        return no_update