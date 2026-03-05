from helpers import filter_dataframe
from dash import html, Input, Output, State, ctx, ALL, no_update
import plotly.graph_objects as go
import pandas as pd
import data
import graphics
import physics 
import time

def register_callbacks(app):

    # A. UPDATE MAIN VIEWS (Scatter, Rug, Grid)
    @app.callback(
        [Output('main-scatter', 'figure'),
         Output('rug-plot', 'figure'),
         Output('image-grid', 'children'),
         Output('trial-status', 'children'),
         Output('query-error-msg', 'children')],
        [Input('part-dd', 'value'),
         Input('shoe-dd', 'value'),
         Input('speed-dd', 'value'),
         Input('xaxis-dd', 'value'),
         Input('yaxis-dd', 'value'),
         Input('rug-dd', 'value'),
         Input('color-dd', 'value'),
         Input('selected-step-store', 'data'),
         Input('filter-side', 'value'),
         Input('filter-outlier', 'value'),
         Input('filter-tile', 'value'),
         Input('filter-pass', 'value'),
         Input('apply-query-btn', 'n_clicks'), 
         Input('query-input', 'value')]
    )
    def update_views(part, shoe, speed, x_col, y_col, rug_col, color_col, selected_step_id, 
                     sides, outliers, tiles, passes, apply_clicks, query_string):
        
        if not (part and shoe and speed):
            return no_update, no_update, [], "", ""

        trial, steps, df = data.fetch_trial_data(part, shoe, speed)
        if not trial:
            return graphics.create_scatter_plot(pd.DataFrame(), "","", ""), \
                   graphics.create_rug_plot(pd.DataFrame(), "", ""), [], "No Data", ""

        # Apply Filters & Catch Errors
        df_filtered, error_msg = filter_dataframe(df, sides, outliers, tiles, passes, query_string)

        if not df_filtered.empty:
            valid_ids = set(df_filtered['id'])
            filtered_steps_list = [s for s in steps if s.id in valid_ids]
        else:
            filtered_steps_list = []

        scatter_fig = graphics.create_scatter_plot(df_filtered, x_col, y_col, color_col, selected_step_id)
        rug_fig = graphics.create_rug_plot(df_filtered, rug_col, color_col, selected_step_id)

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

        status = f"Trial: {part}-{shoe}-{speed} ({len(filtered_steps_list)} steps)"
        return scatter_fig, rug_fig, grid_items, status, error_msg


    # B. UNIFIED SELECTION (Unchanged)
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

    # C. UPDATE PHYSICS PLOTS (GRF & COP with Ghost Lines)
    @app.callback(
        [Output('grf-plot', 'figure'),
         Output('cop-plot', 'figure'),
         Output('physics-cache', 'data')],
        [Input('part-dd', 'value'),
         Input('shoe-dd', 'value'),
         Input('speed-dd', 'value'),
         Input('selected-step-store', 'data'),
         Input('physics-overlay-toggle', 'value'),
         Input('filter-side', 'value'),
         Input('filter-outlier', 'value'),
         Input('filter-tile', 'value'),
         Input('filter-pass', 'value'),
         Input('query-input', 'value')],
        [State('physics-cache', 'data')]
    )
    def update_physics(part, shoe, speed, selected_step_id, overlay_mode, 
                       sides, outliers, tiles, passes, query_string, cache):
        current_trial_key = f"{part}-{shoe}-{speed}"
        if not cache or cache.get('trial_key') != current_trial_key:
            cache = {'trial_key': current_trial_key, 'metrics': []}
            
        if not (part and shoe and speed):
            return graphics.create_grf_plot([]), graphics.create_cop_plot([]), cache

        trial, steps, df = data.fetch_trial_data(part, shoe, speed)
        if not trial:
            return graphics.create_grf_plot([]), graphics.create_cop_plot([]), cache
        
        df_filtered, _ = filter_dataframe(df, sides, outliers, tiles, passes, query_string)
        if df_filtered.empty:
            return graphics.create_grf_plot([]), graphics.create_cop_plot([]), cache

        is_overlay = (overlay_mode == 'overlay')
        target_ids = df_filtered['id'].tolist() if is_overlay else ([selected_step_id] if selected_step_id else [])

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


    # D. UPDATE WALKWAY PLOT
    @app.callback(
        Output('walkway-plot', 'figure'),
        [Input('part-dd', 'value'),
         Input('shoe-dd', 'value'),
         Input('speed-dd', 'value'),
         Input('selected-step-store', 'data'),
         Input('filter-side', 'value'),
         Input('filter-outlier', 'value'),
         Input('filter-tile', 'value'),
         Input('filter-pass', 'value'),
         Input('isolate-pass-check', 'value'),
         Input('apply-query-btn', 'n_clicks'), 
         Input('query-input', 'value')]        
    )
    def update_walkway(part, shoe, speed, selected_step_id, sides, outliers, tiles, passes, isolate_mode, apply_clicks, query_string):
        if not (part and shoe and speed):
            return go.Figure()

        trial, steps, df = data.fetch_trial_data(part, shoe, speed)
        if not trial: return go.Figure()

        # The walkway ignores the error_msg output (it is already handled by update_views)
        df_filtered, _ = filter_dataframe(df, sides, outliers, tiles, passes, query_string)
        
        if selected_step_id and ('isolate' in isolate_mode):
            selected_step = next((s for s in steps if s.id == selected_step_id), None)
            if selected_step and selected_step.pass_id is not None:
                df_filtered = df_filtered[df_filtered['pass_id'] == selected_step.pass_id]

        if df_filtered.empty:
             return graphics.create_walkway_plot([], selected_step_id)

        valid_ids = set(df_filtered['id'])
        filtered_steps_list = [s for s in steps if s.id in valid_ids]

        return graphics.create_walkway_plot(filtered_steps_list, selected_step_id)

    # E. MANAGE PASS SELECTOR
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

    # F. UPDATE DETAIL VIEWS (Heatmap & Histogram)
    @app.callback(
        [Output('heatmap-plot', 'figure'),
         Output('histogram-plot', 'figure')],
        [Input('selected-step-store', 'data'),
         Input('color-scale-toggle', 'value')]
    )
    def update_step_details(step_id, scale_mode):
        #handle empty state
        if not step_id:
            return graphics.create_heatmap_and_histogram(None, None)
            
        #fetch the matrix
        matrix = data.fetch_footstep_matrix(step_id)
        
        #determine the scaling mode
        is_dynamic = (scale_mode == 'dynamic')
        
        #generate Plots with the toggle state passed down
        return graphics.create_heatmap_and_histogram(matrix, step_id, dynamic_scale=is_dynamic)

    # G. CLEAR QUERY BUTTON LOGIC
    @app.callback(
        Output('query-input', 'value'),
        Input('clear-query-btn', 'n_clicks'),
        prevent_initial_call=True
    )
    def clear_query(n_clicks):
        return ""