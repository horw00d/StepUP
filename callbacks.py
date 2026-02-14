from dash import Input, Output, ctx, ALL, no_update
from dash import html
import plotly.graph_objects as go
import pandas as pd
import data
import graphics
import physics 

#helper function to apply all filters in one place
def filter_dataframe(df, sides, outliers, tiles, passes):
    if df.empty: return df
    
    # 1. Filter Side
    if sides:
        df = df[df['side'].isin(sides)]
        
    # 2. Filter Outlier Status
    if outliers:
        df = df[df['is_outlier'].isin(outliers)]
        
    # 3. Filter Tile ID (If selected)
    if tiles:
        # tile_id is an integer in the DF, filters are likely ints from the dropdown
        df = df[df['tile_id'].isin(tiles)]
        
    # 4. Filter Pass ID (If selected)
    if passes:
        df = df[df['pass_id'].isin(passes)]
        
    return df

def register_callbacks(app):

    # A. UPDATE MAIN VIEWS (Scatter, Rug, Grid)
    @app.callback(
        [Output('main-scatter', 'figure'),
         Output('rug-plot', 'figure'),
         Output('image-grid', 'children'),
         Output('trial-status', 'children')],
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
         Input('filter-pass', 'value')]
    )
    def update_views(part, shoe, speed, x_col, y_col, rug_col, color_col, selected_step_id, 
                     sides, outliers, tiles, passes):
        
        if not (part and shoe and speed):
            return no_update, no_update, [], ""

        # 1. Fetch Data (Optimized)
        trial, steps, df = data.fetch_trial_data(part, shoe, speed)
        
        if not trial:
            # Return empty states if no trial found
            return graphics.create_scatter_plot(pd.DataFrame(), "","", ""), \
                   graphics.create_rug_plot(pd.DataFrame(), "", ""), [], "No Data"

        # 2. Apply Unified Filters
        df_filtered = filter_dataframe(df, sides, outliers, tiles, passes)

        # 3. Sync the 'steps' list for the Grid
        # We only want to show steps that exist in the filtered DataFrame
        if not df_filtered.empty:
            valid_ids = set(df_filtered['id'])
            filtered_steps_list = [s for s in steps if s.id in valid_ids]
        else:
            filtered_steps_list = []

        # 4. Generate Plots using Filtered Data
        scatter_fig = graphics.create_scatter_plot(df_filtered, x_col, y_col, color_col, selected_step_id)
        rug_fig = graphics.create_rug_plot(df_filtered, rug_col, color_col, selected_step_id)

        # 5. Generate Grid (HTML Generation)
        # Note: We implement Pagination in the next step, for now this renders the filtered set.
        # Ideally, slicing filtered_steps_list[:20] prevents browser lag if filter is "All"
        grid_items = []
        for step in filtered_steps_list: 
            is_selected = (step.id == selected_step_id)
            border_style = '3px solid #FF0000' if is_selected else '1px solid #eee'
            bg_color = '#fff0f0' if is_selected else 'white'
            
            item = html.Div(
                id={'type': 'grid-card', 'index': step.id},
                n_clicks=0,
                style={'cursor': 'pointer', 'textAlign': 'center', 'border': border_style, 'backgroundColor': bg_color, 'borderRadius': '5px', 'padding': '5px'},
                children=[
                    html.Img(src=f"/assets/footsteps/step_{step.id}.png", style={'width': '100%'}),
                    html.Div(f"Step {step.footstep_index}", style={'fontSize': '0.8em', 'color': '#555'})
                ]
            )
            grid_items.append(item)

        return scatter_fig, rug_fig, grid_items, f"Trial: {part}-{shoe}-{speed} ({len(filtered_steps_list)} steps)"


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


    # C. RENDER PHYSICS (Unchanged)
    @app.callback(
        [Output('grf-plot', 'figure'),
         Output('cop-plot', 'figure')],
        Input('selected-step-store', 'data')
    )
    def render_physics(footstep_id):
        if not footstep_id: 
            return graphics.create_physics_plots(None)

        metrics = physics.get_footstep_physics(footstep_id)
        return graphics.create_physics_plots(metrics)


    # D. UPDATE WALKWAY PLOT (Updated with Filters)
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
         # --- NEW INPUT ---
         Input('isolate-pass-check', 'value')]
    )
    def update_walkway(part, shoe, speed, selected_step_id, sides, outliers, tiles, passes, isolate_mode):
        if not (part and shoe and speed):
            return go.Figure()

        # 1. Fetch Data
        trial, steps, df = data.fetch_trial_data(part, shoe, speed)
        
        if not trial: return go.Figure()

        # 2. Base Filtering (Global Filters)
        # If 'passes' is empty, filter_dataframe treats it as "All"
        df_filtered = filter_dataframe(df, sides, outliers, tiles, passes)
        
        # 3. Handle "Isolate Pass" Logic
        if selected_step_id and ('isolate' in isolate_mode):
            # If a step is selected AND isolation is on...
            # We override the global pass filter to show ONLY that step's pass
            selected_step = next((s for s in steps if s.id == selected_step_id), None)
            if selected_step and selected_step.pass_id is not None:
                # Filter the DF further to just this pass
                df_filtered = df_filtered[df_filtered['pass_id'] == selected_step.pass_id]

        # 4. Get Final Step List
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