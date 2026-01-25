import dash
from dash import html, dcc, Input, Output, State, ctx, ALL, no_update
import plotly.graph_objects as go
import plotly.express as px
from sqlalchemy import create_engine, select, distinct
from sqlalchemy.orm import Session
import pandas as pd

# Import our modules
from models import Trial, Footstep, Participant
import physics 

# 1. SETUP
DATABASE_URL = "sqlite:///stepup.db"
engine = create_engine(DATABASE_URL)
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets, title="StepUP Analyst")

# Feature Options for Dropdowns
FEATURE_OPTIONS = [
    {'label': 'Footstep Sequence ID', 'value': 'footstep_index'},
    {'label': 'Start Frame (Time)', 'value': 'start_frame'},
    {'label': 'R-Score (Quality)', 'value': 'r_score'},
    {'label': 'Mean GRF (Pressure)', 'value': 'mean_grf'},
    {'label': 'Foot Length', 'value': 'foot_length'},
    {'label': 'Foot Width', 'value': 'foot_width'},
    {'label': 'Rotation Angle', 'value': 'rotation_angle'},
]

def get_dropdown_options(model_col):
    with Session(engine) as session:
        results = session.scalars(select(distinct(model_col)).order_by(model_col)).all()
        return [{'label': str(x), 'value': str(x)} for x in results]

# 2. LAYOUT
app.layout = html.Div(style={'height': '100vh', 'display': 'flex', 'flexDirection': 'column', 'padding': '20px'}, children=[
    
    # --- STORE (The Invisible "Brain") ---
    dcc.Store(id='selected-step-store'),

    # --- HEADER & CONTROLS ---
    html.Div(style={'borderBottom': '1px solid #ddd', 'paddingBottom': '15px', 'marginBottom': '10px'}, children=[
        html.H2("StepUP: Trial Analysis Dashboard", style={'display': 'inline-block', 'marginRight': '30px'}),
        
        # Trial Selection
        html.Div(style={'display': 'flex', 'gap': '20px', 'alignItems': 'center'}, children=[
            dcc.Dropdown(id='part-dd', options=get_dropdown_options(Participant.id), value='001', placeholder="Participant", style={'width': '120px'}),
            dcc.Dropdown(id='shoe-dd', options=get_dropdown_options(Trial.footwear), value='BF', placeholder="Footwear", style={'width': '120px'}),
            dcc.Dropdown(id='speed-dd', options=get_dropdown_options(Trial.speed), value='W1', placeholder="Speed", style={'width': '120px'}),
            html.Div(id='trial-status', style={'marginLeft': 'auto', 'fontWeight': 'bold', 'color': '#555'})
        ])
    ]),

    # --- MIDDLE: TABS (The Split View) ---
    dcc.Tabs(id="view-tabs", value='tab-feature', children=[
        
        # TAB 1: FEATURE ANALYSIS (Split: Scatter + Rug)
        dcc.Tab(label='Feature Analysis', value='tab-feature', children=[
            html.Div(style={'display': 'flex', 'gap': '20px', 'height': '550px', 'padding': '20px'}, children=[
                
                # LEFT COLUMN: Graphs (Scatter Top, Rug Bottom)
                html.Div(style={'flex': '3', 'display': 'flex', 'flexDirection': 'column', 'gap': '15px'}, children=[
                    # Top: Main 2D Scatter
                    html.Div(style={'flex': '2', 'border': '1px solid #ccc', 'borderRadius': '5px', 'padding': '10px'}, children=[
                        dcc.Graph(id='main-scatter', style={'height': '100%'})
                    ]),
                    # Bottom: 1D Rug Plot
                    html.Div(style={'flex': '1', 'border': '1px solid #ccc', 'borderRadius': '5px', 'padding': '10px'}, children=[
                        dcc.Graph(id='rug-plot', style={'height': '100%'})
                    ]),
                ]),

                # RIGHT COLUMN: Controls
                html.Div(style={'flex': '1', 'backgroundColor': '#f9f9f9', 'padding': '20px', 'borderRadius': '5px', 'overflowY': 'auto'}, children=[
                    html.H5("Axis Controls"),
                    html.Label("Scatter X-Axis:"),
                    dcc.Dropdown(id='xaxis-dd', options=FEATURE_OPTIONS, value='start_frame', clearable=False),
                    html.Br(),
                    html.Label("Scatter Y-Axis:"),
                    dcc.Dropdown(id='yaxis-dd', options=FEATURE_OPTIONS, value='mean_grf', clearable=False),
                    html.Br(),
                    html.Hr(),
                    
                    # NEW CONTROL FOR RUG PLOT
                    html.Label("Rug Plot Feature:"),
                    dcc.Dropdown(id='rug-dd', options=FEATURE_OPTIONS, value='r_score', clearable=False),
                    html.Br(),
                    
                    html.Hr(),
                    html.Label("Color By:"),
                    dcc.Dropdown(id='color-dd', options=[
                        {'label': 'Side (L/R)', 'value': 'side'},
                        {'label': 'Outlier Status', 'value': 'is_outlier'}
                    ], value='side', clearable=False),
                    html.Br(),
                    html.P("Click points on EITHER graph to view physics below.", style={'color': '#666', 'fontSize': '0.9em', 'fontStyle': 'italic'})
                ])
            ])
        ]),

        # TAB 2: FOOTSTEP LIBRARY (Image Grid)
        dcc.Tab(label='Footstep Library', value='tab-library', children=[
            html.Div(style={'height': '550px', 'overflowY': 'auto', 'padding': '20px'}, children=[
                html.Div(id='image-grid', style={
                    'display': 'grid',
                    'gridTemplateColumns': 'repeat(auto-fill, minmax(140px, 1fr))',
                    'gap': '20px'
                })
            ])
        ])
    ]),

    # --- BOTTOM: DETAILED PHYSICS (Global) ---
    html.Div(style={'flex': '1.5', 'marginTop': '10px', 'borderTop': '2px solid #eee', 'paddingTop': '10px'}, children=[
        html.H4("Deep Dive: Single Step Physics", style={'marginBottom': '10px'}),
        html.Div(style={'display': 'flex', 'gap': '20px', 'height': '300px'}, children=[
            html.Div(style={'flex': '1', 'border': '1px solid #eee'}, children=[dcc.Graph(id='grf-plot', style={'height': '100%'})]),
            html.Div(style={'flex': '1', 'border': '1px solid #eee'}, children=[dcc.Graph(id='cop-plot', style={'height': '100%'})])
        ])
    ])
])


# 3. CALLBACKS

# A. Update ALL Views (Scatter, Rug, Grid)
@app.callback(
    [Output('main-scatter', 'figure'),
     Output('rug-plot', 'figure'),     # NEW OUTPUT
     Output('image-grid', 'children'),
     Output('trial-status', 'children')],
    [Input('part-dd', 'value'),
     Input('shoe-dd', 'value'),
     Input('speed-dd', 'value'),
     Input('xaxis-dd', 'value'),
     Input('yaxis-dd', 'value'),
     Input('rug-dd', 'value'),         # NEW INPUT
     Input('color-dd', 'value')]
)
def update_views(part, shoe, speed, x_col, y_col, rug_col, color_col):
    if not (part and shoe and speed):
        return no_update, no_update, [], ""

    with Session(engine) as session:
        # Find Trial
        stmt = select(Trial).where(Trial.participant_id == part, Trial.footwear == shoe, Trial.speed == speed)
        trial = session.scalar(stmt)
        
        if not trial:
            empty = px.scatter(title="No Data")
            return empty, empty, html.Div("No Data"), "Status: No Trial Found"

        # Fetch Steps
        steps = session.scalars(
            select(Footstep).where(Footstep.trial_id == trial.id).order_by(Footstep.footstep_index)
        ).all()
        
        # 1. GENERATE DATA
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

        # 2. BUILD SCATTER FIGURE (2D)
        scatter_fig = px.scatter(
            df, x=x_col, y=y_col, color=color_col,
            hover_data=['footstep_index', 'id'],
            custom_data=['id'], 
            title=f"2D Feature Analysis: {x_col} vs {y_col}"
        )
        scatter_fig.update_layout(clickmode='event+select', margin=dict(l=20, r=20, t=30, b=20))
        scatter_fig.update_traces(marker_size=10)

        # 3. BUILD RUG FIGURE (1D Strip Plot)
        # 'stripmode="overlay"' makes it look like a classic rug plot but with clickable dots
        rug_fig = px.strip(
            df, 
            x=rug_col, 
            color=color_col, 
            stripmode='overlay',
            hover_data=['footstep_index', 'id'],
            custom_data=['id'], # Critical for click tracking
            title=f"1D Distribution: {rug_col}"
        )
        rug_fig.update_layout(
            clickmode='event+select', 
            margin=dict(l=20, r=20, t=30, b=20),
            yaxis={'visible': False, 'showticklabels': False}, # Hide Y axis to make it look like a 1D timeline
            height=150 # Force it to be shorter
        )
        rug_fig.update_traces(marker_size=8, jitter=0.5) # Jitter prevents overlap

        # 4. BUILD IMAGE GRID
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

        status = f"Trial: {part}-{shoe}-{speed} ({len(steps)} steps)"
        
        return scatter_fig, rug_fig, grid_items, status


# B. UNIFIED SELECTION HANDLER (Now listens to Rug Plot too!)
@app.callback(
    Output('selected-step-store', 'data'),
    [Input('main-scatter', 'clickData'),
     Input('rug-plot', 'clickData'),           # NEW LISTENER
     Input({'type': 'grid-card', 'index': ALL}, 'n_clicks')],
    prevent_initial_call=True
)
def handle_selection(scatter_click, rug_click, grid_clicks):
    trigger_id = ctx.triggered_id
    
    if not trigger_id:
        return no_update

    # Case 1: Scatter Plot Clicked
    if trigger_id == 'main-scatter' and scatter_click:
        return scatter_click['points'][0]['customdata'][0]

    # Case 2: Rug Plot Clicked
    if trigger_id == 'rug-plot' and rug_click:
        return rug_click['points'][0]['customdata'][0]

    # Case 3: Grid Item Clicked
    if isinstance(trigger_id, dict) and trigger_id.get('type') == 'grid-card':
        return trigger_id['index']
    
    return no_update


# C. UPDATE PHYSICS GRAPHS
@app.callback(
    [Output('grf-plot', 'figure'),
     Output('cop-plot', 'figure')],
    Input('selected-step-store', 'data')
)
def render_physics(footstep_id):
    empty_layout = go.Layout(
        xaxis={"visible": False}, yaxis={"visible": False}, 
        annotations=[{"text": "Select a step to view physics", "showarrow": False, "font": {"size": 16}}]
    )
    
    if not footstep_id:
        return go.Figure(layout=empty_layout), go.Figure(layout=empty_layout)

    metrics = physics.get_footstep_physics(footstep_id)
    if not metrics:
        return go.Figure(layout=empty_layout), go.Figure(layout=empty_layout)

    # GRF Graph
    fig_grf = go.Figure()
    fig_grf.add_trace(go.Scatter(x=metrics['time_pct'], y=metrics['grf'], mode='lines', line=dict(color='blue', width=3)))
    fig_grf.update_layout(title=f"Vertical GRF (Step {metrics['step_id']})", xaxis_title="% Stance", yaxis_title="Force (N)", margin=dict(l=40, r=40, t=40, b=40))

    # COP Graph
    fig_cop = go.Figure()
    fig_cop.add_trace(go.Scatter(x=metrics['cop_ml'], y=metrics['cop_ap'], mode='lines+markers', marker=dict(size=4, color=metrics['time_pct'], colorscale='Viridis')))
    fig_cop.update_layout(title="COP Trajectory", xaxis_title="Mediolateral (cm)", yaxis_title="Anteroposterior (cm)", yaxis=dict(scaleanchor="x", scaleratio=1), margin=dict(l=40, r=40, t=40, b=40))

    return fig_grf, fig_cop


if __name__ == '__main__':
    app.run(debug=True, port=8000)