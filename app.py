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
    {'label': 'Mean GRF (Pressure)', 'value': 'mean_grf'}
    # {'label': 'Foot Length', 'value': 'foot_length'},
    # {'label': 'Foot Width', 'value': 'foot_width'},
    # {'label': 'Rotation Angle', 'value': 'rotation_angle'},
]

def get_dropdown_options(model_col):
    with Session(engine) as session:
        results = session.scalars(select(distinct(model_col)).order_by(model_col)).all()
        return [{'label': str(x), 'value': str(x)} for x in results]

# 2. LAYOUT
app.layout = html.Div(style={'height': '100vh', 'display': 'flex', 'flexDirection': 'column', 'padding': '20px'}, children=[
    
    # --- STORE (The Invisible "Brain") ---
    # This holds the ID of the selected footstep, no matter which tab you clicked it in.
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
        
        # TAB 1: FEATURE ANALYSIS (Scatter Plot)
        dcc.Tab(label='Feature Analysis', value='tab-feature', children=[
            html.Div(style={'display': 'flex', 'gap': '20px', 'height': '450px', 'padding': '20px'}, children=[
                # Left: Scatter
                html.Div(style={'flex': '3', 'border': '1px solid #ccc', 'borderRadius': '5px', 'padding': '10px'}, children=[
                    dcc.Graph(id='main-scatter', style={'height': '100%'})
                ]),
                # Right: Controls
                html.Div(style={'flex': '1', 'backgroundColor': '#f9f9f9', 'padding': '20px', 'borderRadius': '5px', 'overflowY': 'auto'}, children=[
                    html.H5("Axis Controls"),
                    html.Label("X-Axis Feature:"),
                    dcc.Dropdown(id='xaxis-dd', options=FEATURE_OPTIONS, value='start_frame', clearable=False),
                    html.Br(),
                    html.Label("Y-Axis Feature:"),
                    dcc.Dropdown(id='yaxis-dd', options=FEATURE_OPTIONS, value='mean_grf', clearable=False),
                    html.Br(),
                    html.Label("Color By:"),
                    dcc.Dropdown(id='color-dd', options=[
                        {'label': 'Side (L/R)', 'value': 'side'},
                        {'label': 'Outlier Status', 'value': 'is_outlier'}
                    ], value='side', clearable=False),
                    html.Hr(),
                    html.P("Click points to view physics below.", style={'color': '#666', 'fontSize': '0.9em'})
                ])
            ])
        ]),

        # TAB 2: FOOTSTEP LIBRARY (Image Grid)
        dcc.Tab(label='Footstep Library', value='tab-library', children=[
            html.Div(style={'height': '450px', 'overflowY': 'auto', 'padding': '20px'}, children=[
                # The Grid Container
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
            # Graph 1: GRF
            html.Div(style={'flex': '1', 'border': '1px solid #eee'}, children=[
                dcc.Graph(id='grf-plot', style={'height': '100%'})
            ]),
            # Graph 2: COP
            html.Div(style={'flex': '1', 'border': '1px solid #eee'}, children=[
                dcc.Graph(id='cop-plot', style={'height': '100%'})
            ])
        ])
    ])
])


# 3. CALLBACKS

# A. Update BOTH Views (Scatter & Grid) when Trial Changes
# Note: We update both even if one is hidden, so they are ready when you switch tabs.
@app.callback(
    [Output('main-scatter', 'figure'),
     Output('image-grid', 'children'),
     Output('trial-status', 'children')],
    [Input('part-dd', 'value'),
     Input('shoe-dd', 'value'),
     Input('speed-dd', 'value'),
     Input('xaxis-dd', 'value'),
     Input('yaxis-dd', 'value'),
     Input('color-dd', 'value')]
)
def update_views(part, shoe, speed, x_col, y_col, color_col):
    if not (part and shoe and speed):
        return no_update, [], ""

    with Session(engine) as session:
        # Find Trial
        stmt = select(Trial).where(Trial.participant_id == part, Trial.footwear == shoe, Trial.speed == speed)
        trial = session.scalar(stmt)
        
        if not trial:
            empty_fig = px.scatter(title="No Data")
            return empty_fig, html.Div("No Data"), "Status: No Trial Found"

        # Fetch Steps
        steps = session.scalars(
            select(Footstep).where(Footstep.trial_id == trial.id).order_by(Footstep.footstep_index)
        ).all()
        
        # 1. GENERATE SCATTER DATA
        data = [{
            'id': s.id,
            'footstep_index': s.footstep_index,
            'start_frame': s.start_frame,
            'mean_grf': s.mean_grf,
            'r_score': s.r_score,
            # 'foot_length': s.foot_length,
            # 'foot_width': s.foot_width,
            # 'rotation_angle': s.rotation_angle,
            'side': s.side,
            'is_outlier': "Outlier" if s.is_outlier else "Normal"
        } for s in steps]
        
        df = pd.DataFrame(data)

        # 2. BUILD SCATTER FIGURE
        if df.empty:
            fig = px.scatter(title="Empty Trial")
        else:
            fig = px.scatter(
                df, x=x_col, y=y_col, color=color_col,
                hover_data=['footstep_index', 'id'],
                custom_data=['id'], # Critical for click tracking
                title=f"Trial Feature Analysis"
            )
            fig.update_layout(clickmode='event+select', margin=dict(l=20, r=20, t=30, b=20))
            fig.update_traces(marker_size=10)

        # 3. BUILD IMAGE GRID
        grid_items = []
        for step in steps:
            # We wrap the image in a Div that has an 'index' equal to the Database ID
            # This allows pattern matching in the next callback
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
        
        return fig, grid_items, status


# B. UNIFIED SELECTION HANDLER
# This listens to BOTH the Scatter Plot AND the Grid Items
@app.callback(
    Output('selected-step-store', 'data'),
    [Input('main-scatter', 'clickData'),
     Input({'type': 'grid-card', 'index': ALL}, 'n_clicks')], # Pattern Matching
    prevent_initial_call=True
)
def handle_selection(scatter_click, grid_clicks):
    # We use dash.ctx to determine WHO triggered the callback
    trigger_id = ctx.triggered_id
    
    if not trigger_id:
        return no_update

    # Case 1: Scatter Plot Clicked
    if trigger_id == 'main-scatter':
        if not scatter_click: return no_update
        # Extract ID from customdata
        return scatter_click['points'][0]['customdata'][0]

    # Case 2: Grid Item Clicked
    # trigger_id will look like {'type': 'grid-card', 'index': 12345}
    if isinstance(trigger_id, dict) and trigger_id.get('type') == 'grid-card':
        # The 'index' in the dictionary IS the footstep database ID
        return trigger_id['index']
    
    return no_update


# C. UPDATE PHYSICS GRAPHS (Listens only to the Store)
@app.callback(
    [Output('grf-plot', 'figure'),
     Output('cop-plot', 'figure')],
    Input('selected-step-store', 'data')
)
def render_physics(footstep_id):
    empty_layout = go.Layout(
        xaxis={"visible": False}, yaxis={"visible": False}, 
        annotations=[{"text": "Select a step from Analysis or Library", "showarrow": False, "font": {"size": 16}}]
    )
    
    if not footstep_id:
        return go.Figure(layout=empty_layout), go.Figure(layout=empty_layout)

    # Call Physics Module
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