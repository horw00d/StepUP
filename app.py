import dash
from dash import html, dcc, Input, Output, State, ctx, ALL, no_update
import plotly.graph_objects as go
import plotly.express as px
from sqlalchemy import select
import pandas as pd
from database import Session, engine
from models import Trial, Footstep
from layout import create_layout
from graphics import create_walkway_plot
import physics 

#1 setup
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets, title="StepUP Analyst")

#2 inject Layout
app.layout = create_layout()

#3 Callbacks

#update views
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
def update_views(part, shoe, speed, x_col, y_col, rug_col, color_col, selected_step_id):
    if not (part and shoe and speed):
        return no_update, no_update, [], ""

    with Session(engine) as session:
        #1 fetch Trial
        stmt = select(Trial).where(Trial.participant_id == part, Trial.footwear == shoe, Trial.speed == speed)
        trial = session.scalar(stmt)
        
        if not trial:
            empty = px.scatter(title="No Data")
            return empty, empty, html.Div("No Data"), "Status: No Trial Found"

        #2 fetch Steps
        steps = session.scalars(
            select(Footstep).where(Footstep.trial_id == trial.id).order_by(Footstep.footstep_index)
        ).all()
        
        #3 build Dataframe
        data = [{
            'id': s.id,
            'footstep_index': s.footstep_index,
            'start_frame': s.start_frame,
            'mean_grf': s.mean_grf,
            'r_score': s.r_score,
            'foot_length': s.foot_length,
            'foot_width': s.foot_width,
            'rotation_angle': s.rotation_angle,
            'side': s.side,
            'is_outlier': "Outlier" if s.is_outlier else "Normal"
        } for s in steps]
        
        df = pd.DataFrame(data)

        if df.empty:
            empty = px.scatter(title="Empty Trial")
            return empty, empty, [], f"Trial: {part} (Empty)"

        #generate base figures
        #scatter
        scatter_fig = px.scatter(
            df, x=x_col, y=y_col, color=color_col,
            hover_data=['footstep_index', 'id'],
            custom_data=['id'], 
            title=f"2D Feature Analysis: {x_col} vs {y_col}"
        )
        scatter_fig.update_layout(clickmode='event+select', margin=dict(l=20, r=20, t=30, b=20))
        scatter_fig.update_traces(marker_size=10, unselected=dict(marker=dict(opacity=0.3))) # Fade others if needed

        #rug
        rug_fig = px.strip(
            df, x=rug_col, color=color_col, stripmode='overlay',
            hover_data=['footstep_index', 'id'],
            custom_data=['id'],
            title=f"1D Distribution: {rug_col}"
        )
        rug_fig.update_layout(clickmode='event+select', margin=dict(l=20, r=20, t=30, b=20), yaxis={'visible': False}, height=150)
        rug_fig.update_traces(marker_size=8, jitter=0.5)

        # 5. apply highlighting (for extensibility)
        if selected_step_id:
            # Check if selected step exists in this trial (important when switching trials)
            selected_row = df[df['id'] == selected_step_id]
            
            if not selected_row.empty:
                # Highlight Scatter
                scatter_fig.add_trace(go.Scatter(
                    x=selected_row[x_col], 
                    y=selected_row[y_col],
                    mode='markers',
                    marker=dict(color='red', size=15, line=dict(width=2, color='black')),
                    name='Selected',
                    hoverinfo='skip'
                ))
                
                # Highlight Rug
                rug_fig.add_trace(go.Scatter(
                    x=selected_row[rug_col], 
                    y=[0] * len(selected_row), # Rug plots are essentially y=0
                    mode='markers',
                    marker=dict(color='red', size=12, symbol='line-ns-open', line=dict(width=3)),
                    name='Selected',
                    hoverinfo='skip'
                ))

        # 6. Generate Grid (with Dynamic Styling)
        grid_items = []
        for step in steps:
            # Dynamic Style Logic
            is_selected = (step.id == selected_step_id)
            border_style = '3px solid #FF0000' if is_selected else '1px solid #eee'
            bg_color = '#fff0f0' if is_selected else 'white'
            
            item = html.Div(
                id={'type': 'grid-card', 'index': step.id},
                n_clicks=0,
                style={
                    'cursor': 'pointer', 
                    'textAlign': 'center', 
                    'border': border_style, 
                    'backgroundColor': bg_color,
                    'borderRadius': '5px', 
                    'padding': '5px',
                    'transition': '0.2s' # Smooth transition
                },
                children=[
                    html.Img(src=f"/assets/footsteps/step_{step.id}.png", style={'width': '100%'}),
                    html.Div(f"Step {step.footstep_index}", style={'fontSize': '0.8em', 'color': '#555'})
                ]
            )
            grid_items.append(item)

        return scatter_fig, rug_fig, grid_items, f"Trial: {part}-{shoe}-{speed} ({len(steps)} steps)"


#unified selection
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

    #allows for selection on walkway plot
    if trigger_id == 'walkway-plot' and walkway_click:
        return walkway_click['points'][0]['customdata'][0]

    if isinstance(trigger_id, dict) and trigger_id.get('type') == 'grid-card':
        return trigger_id['index']
    
    return no_update


# C. Render physics module
@app.callback(
    [Output('grf-plot', 'figure'),
     Output('cop-plot', 'figure')],
    Input('selected-step-store', 'data')
)
def render_physics(footstep_id):
    empty_layout = go.Layout(
        xaxis={"visible": False}, yaxis={"visible": False}, 
        annotations=[{"text": "Select a step", "showarrow": False, "font": {"size": 16}}]
    )
    
    if not footstep_id: return go.Figure(layout=empty_layout), go.Figure(layout=empty_layout)

    metrics = physics.get_footstep_physics(footstep_id)
    if not metrics: return go.Figure(layout=empty_layout), go.Figure(layout=empty_layout)

    # GRF
    fig_grf = go.Figure()
    fig_grf.add_trace(go.Scatter(x=metrics['time_pct'], y=metrics['grf'], mode='lines', line=dict(color='blue', width=3)))
    fig_grf.update_layout(title=f"Vertical GRF (Step {metrics['step_id']})", xaxis_title="% Stance", yaxis_title="Force (N)", margin=dict(l=40, r=40, t=40, b=40))

    # COP
    fig_cop = go.Figure()
    fig_cop.add_trace(go.Scatter(x=metrics['cop_ml'], y=metrics['cop_ap'], mode='lines+markers', marker=dict(size=4, color=metrics['time_pct'], colorscale='Viridis')))
    fig_cop.update_layout(title="COP Trajectory", xaxis_title="Mediolateral (cm)", yaxis_title="Anteroposterior (cm)", yaxis=dict(scaleanchor="x", scaleratio=1), margin=dict(l=40, r=40, t=40, b=40))

    return fig_grf, fig_cop

#update walkway plot
@app.callback(
    Output('walkway-plot', 'figure'),
    [Input('part-dd', 'value'),
     Input('shoe-dd', 'value'),
     Input('speed-dd', 'value'),
     Input('selected-step-store', 'data'),
     Input('pass-selector', 'value')]
)
def update_walkway(part, shoe, speed, selected_step_id, visible_passes):
    # safety check, visible_passes can be None
    if visible_passes is None: visible_passes = []

    if not (part and shoe and speed):
        return go.Figure()

    with Session(engine) as session:
        #grab trial
        stmt = select(Trial).where(Trial.participant_id == part, Trial.footwear == shoe, Trial.speed == speed)
        trial = session.scalar(stmt)
        
        if not trial:
            return go.Figure()

        #grab steps
        steps = session.scalars(
            select(Footstep).where(Footstep.trial_id == trial.id).order_by(Footstep.footstep_index)
        ).all()

        filtered_steps = [s for s in steps if s.pass_id in visible_passes]

        return create_walkway_plot(filtered_steps, selected_step_id)

@app.callback(
    [Output('pass-selector', 'options'),
     Output('pass-selector', 'value')],
    [Input('part-dd', 'value'),
     Input('shoe-dd', 'value'),
     Input('speed-dd', 'value'),
     Input('selected-step-store', 'data')] # Listens to global click
)
def manage_pass_selector(part, shoe, speed, selected_step_id):
    trigger = ctx.triggered_id
    
    # CASE 1: User Clicked a Step (Drill-Down Logic)
    if trigger == 'selected-step-store' and selected_step_id:
        with Session(engine) as session:
            # Find which pass this step belongs to
            step = session.get(Footstep, selected_step_id)
            if step and step.pass_id is not None:
                # REQUIREMENT: "Only pass 2 footsteps are shown"
                return no_update, [step.pass_id]
        return no_update, no_update

    #new trial is loaded (reset logic)
    if part and shoe and speed:
        with Session(engine) as session:
            stmt = select(Trial).where(Trial.participant_id == part, Trial.footwear == shoe, Trial.speed == speed)
            trial = session.scalar(stmt)
            
            if trial:
                # Get distinct pass ids for this trial
                steps = session.scalars(select(Footstep).where(Footstep.trial_id == trial.id)).all()
                unique_passes = sorted(list(set([s.pass_id for s in steps if s.pass_id is not None])))
                
                options = [{'label': f"Pass {p}", 'value': p} for p in unique_passes]
                
                return options, unique_passes

    return [], []

if __name__ == '__main__':
    app.run(debug=True, port=8000)