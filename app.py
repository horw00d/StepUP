import dash
from dash import html, dcc, Input, Output, State, ctx, ALL, no_update
import plotly.graph_objects as go
import plotly.express as px
from sqlalchemy import select
import pandas as pd
from database import Session, engine
from models import Trial, Footstep
from layout import create_layout
import physics 

# 1. Setup
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets, title="StepUP Analyst")

# 2. Inject Layout
app.layout = create_layout()

# 3. Callbacks

# A. Update Views
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
     Input('color-dd', 'value')]
)
def update_views(part, shoe, speed, x_col, y_col, rug_col, color_col):
    if not (part and shoe and speed):
        return no_update, no_update, [], ""

    with Session(engine) as session:
        stmt = select(Trial).where(Trial.participant_id == part, Trial.footwear == shoe, Trial.speed == speed)
        trial = session.scalar(stmt)
        
        if not trial:
            empty = px.scatter(title="No Data")
            return empty, empty, html.Div("No Data"), "Status: No Trial Found"

        steps = session.scalars(
            select(Footstep).where(Footstep.trial_id == trial.id).order_by(Footstep.footstep_index)
        ).all()
        
        # Data generation
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

        # Scatter
        scatter_fig = px.scatter(
            df, x=x_col, y=y_col, color=color_col,
            hover_data=['footstep_index', 'id'],
            custom_data=['id'], 
            title=f"2D Feature Analysis: {x_col} vs {y_col}"
        )
        scatter_fig.update_layout(clickmode='event+select', margin=dict(l=20, r=20, t=30, b=20))
        scatter_fig.update_traces(marker_size=10)

        # Rug
        rug_fig = px.strip(
            df, x=rug_col, color=color_col, stripmode='overlay',
            hover_data=['footstep_index', 'id'],
            custom_data=['id'],
            title=f"1D Distribution: {rug_col}"
        )
        rug_fig.update_layout(clickmode='event+select', margin=dict(l=20, r=20, t=30, b=20), yaxis={'visible': False}, height=150)
        rug_fig.update_traces(marker_size=8, jitter=0.5)

        # Grid
        grid_items = []
        for step in steps:
            item = html.Div(
                id={'type': 'grid-card', 'index': step.id},
                n_clicks=0,
                style={'cursor': 'pointer', 'textAlign': 'center', 'border': '1px solid #eee', 'borderRadius': '5px', 'padding': '5px'},
                children=[
                    html.Img(src=f"/assets/footsteps/step_{step.id}.png", style={'width': '100%'}),
                    html.Div(f"Step {step.footstep_index}", style={'fontSize': '0.8em', 'color': '#555'})
                ]
            )
            grid_items.append(item)

        return scatter_fig, rug_fig, grid_items, f"Trial: {part}-{shoe}-{speed} ({len(steps)} steps)"


# B. Unified selection
@app.callback(
    Output('selected-step-store', 'data'),
    [Input('main-scatter', 'clickData'),
     Input('rug-plot', 'clickData'),
     Input({'type': 'grid-card', 'index': ALL}, 'n_clicks')],
    prevent_initial_call=True
)
def handle_selection(scatter_click, rug_click, grid_clicks):
    trigger_id = ctx.triggered_id
    if not trigger_id: return no_update

    if trigger_id == 'main-scatter' and scatter_click:
        return scatter_click['points'][0]['customdata'][0]
    
    if trigger_id == 'rug-plot' and rug_click:
        return rug_click['points'][0]['customdata'][0]

    if isinstance(trigger_id, dict) and trigger_id.get('type') == 'grid-card':
        return trigger_id['index']
    
    return no_update


# C. Physics rendering
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


if __name__ == '__main__':
    app.run(debug=True, port=8000)