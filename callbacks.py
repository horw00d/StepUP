from dash import Input, Output, ctx, ALL, no_update, html
from profiler import profile_callback
import plotly.graph_objects as go
import data
import graphics
import physics 

def register_callbacks(app):

    # A. UPDATE MAIN VIEWS
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
         Input('selected-step-store', 'data')]
    )
    #@profile_callback
    def update_views(part, shoe, speed, x_col, y_col, rug_col, color_col, selected_step_id):

        if not (part and shoe and speed):
            return no_update, no_update, [], ""

        # 1. Fetch Data
        trial, steps, df = data.fetch_trial_data(part, shoe, speed)
        
        if not trial:
            return graphics.create_scatter_plot(pd.DataFrame(), "","", ""), \
                   graphics.create_rug_plot(pd.DataFrame(), "", ""), [], "No Data"

        #2 use graphics module
        scatter_fig = graphics.create_scatter_plot(df, x_col, y_col, color_col, selected_step_id)
        rug_fig = graphics.create_rug_plot(df, rug_col, color_col, selected_step_id)

        # 3. grid generation
        grid_items = []
        for step in steps:
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

        return scatter_fig, rug_fig, grid_items, f"Trial: {part}-{shoe}-{speed}"


    # B. UNIFIED SELECTION
    @app.callback(
        Output('selected-step-store', 'data'),
        [Input('main-scatter', 'clickData'),
        Input('rug-plot', 'clickData'),
        Input('walkway-plot', 'clickData'),
        Input({'type': 'grid-card', 'index': ALL}, 'n_clicks')],
        prevent_initial_call=True
    )
    #@profile_callback
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


    # C. RENDER PHYSICS (Fixed to use Graphics Module)
    @app.callback(
        [Output('grf-plot', 'figure'),
        Output('cop-plot', 'figure')],
        Input('selected-step-store', 'data')
    )
    #@profile_callback
    def render_physics(footstep_id):
        # 1. Check ID
        if not footstep_id: 
            return graphics.create_physics_plots(None) # Use graphics to generate empties

        # 2. Get Metrics (Physics Logic)
        metrics = physics.get_footstep_physics(footstep_id)
        
        # 3. Get Plots (Graphics Logic)
        return graphics.create_physics_plots(metrics)


    # D. UPDATE WALKWAY PLOT
    @app.callback(
        Output('walkway-plot', 'figure'),
        [Input('part-dd', 'value'),
        Input('shoe-dd', 'value'),
        Input('speed-dd', 'value'),
        Input('selected-step-store', 'data'),
        Input('pass-selector', 'value')]
    )
    #@profile_callback
    def update_walkway(part, shoe, speed, selected_step_id, visible_passes):
        if visible_passes is None: visible_passes = []

        if not (part and shoe and speed):
            return go.Figure()

        # 1. Use Data Manager to get steps (No SQL here!)
        trial, steps, _ = data.fetch_trial_data(part, shoe, speed)
        
        if not trial:
            return go.Figure()

        # 2. Apply Filter Logic (Controller Logic)
        filtered_steps = [s for s in steps if s.pass_id in visible_passes]

        # 3. Call Graphics Module
        # FIX: Added 'graphics.' prefix
        return graphics.create_walkway_plot(filtered_steps, selected_step_id)


    # E. MANAGE PASS SELECTOR (Fixed DB calls)
    @app.callback(
        [Output('pass-selector', 'options'),
        Output('pass-selector', 'value')],
        [Input('part-dd', 'value'),
        Input('shoe-dd', 'value'),
        Input('speed-dd', 'value'),
        Input('selected-step-store', 'data')] 
    )
    #@profile_callback
    def manage_pass_selector(part, shoe, speed, selected_step_id):
        trigger = ctx.triggered_id
        
        # CASE 1: Drill-Down (Clicked a step)
        if trigger == 'selected-step-store' and selected_step_id:
            # Use Data Manager to get single step
            step = data.fetch_step_by_id(selected_step_id)
            if step and step.pass_id is not None:
                return no_update, [step.pass_id]
            return no_update, no_update

        # CASE 2: New Trial Loaded
        if part and shoe and speed:
            # Use the new helper in Data Manager
            return data.fetch_pass_options(part, shoe, speed)

        return [], []