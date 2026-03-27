from dash import html, dcc
from sqlalchemy import select, distinct
from models import Trial, Participant
from database import engine, Session

# Constants
FEATURE_OPTIONS = [
    {'label': 'Footstep Sequence ID', 'value': 'footstep_index'},
    {'label': 'Start Frame (Time)', 'value': 'start_frame'},
    {'label': 'R-Score (Quality)', 'value': 'r_score'},
    {'label': 'Mean GRF (Pressure)', 'value': 'mean_grf'},
    {'label': 'Peak GRF (Pressure)', 'value': 'peak_grf'},
    {'label': 'Stance Duration', 'value': 'stance_duration_frames'},
    {'label': 'Foot Length', 'value': 'foot_length'},
    {'label': 'Foot Width', 'value': 'foot_width'},
    {'label': 'Rotation Angle', 'value': 'rotation_angle'},
]

# Helpers
def get_dropdown_options(model_col):
    with Session(engine) as session:
        results = session.scalars(select(distinct(model_col)).order_by(model_col)).all()
        return [{'label': str(x), 'value': str(x)} for x in results]

OPTIONS_PART = get_dropdown_options(Participant.id)
OPTIONS_SHOE = get_dropdown_options(Trial.footwear)
OPTIONS_SPEED = get_dropdown_options(Trial.speed)

def with_spinner(component):
    """
    Wraps any Dash component in a uniform loading spinner.
    Ensures identical UX across both Single and Cross-Trial tabs.
    """
    return dcc.Loading(
        type="circle",
        color="#007BFF",
        parent_style={'height': '100%', 'width': '100%'},
        children=component
    )


# =====================================================================
# TAB 1: SINGLE-TRIAL ANALYSIS LAYOUT (Phase 1)
# =====================================================================
def get_single_trial_layout():
    return html.Div(children=[
        # --- HEADER & SELECTION ---
        html.Div(style={'borderBottom': '1px solid #ddd', 'paddingBottom': '15px', 'marginBottom': '10px'}, children=[
            html.Div(style={'display': 'flex', 'gap': '20px', 'alignItems': 'center'}, children=[
                dcc.Dropdown(id='part-dd', options=OPTIONS_PART, value=OPTIONS_PART[0]['value'] if OPTIONS_PART else None, placeholder="Participant", style={'width': '120px'}),
                dcc.Dropdown(id='shoe-dd', options=OPTIONS_SHOE, value=OPTIONS_SHOE[0]['value'] if OPTIONS_SHOE else None, placeholder="Footwear", style={'width': '120px'}),
                dcc.Dropdown(id='speed-dd', options=OPTIONS_SPEED, value=OPTIONS_SPEED[0]['value'] if OPTIONS_SPEED else None, placeholder="Speed", style={'width': '120px'}),
                html.Div(id='trial-status', style={'marginLeft': 'auto', 'fontWeight': 'bold', 'color': '#555'})
            ])
        ]),

        # --- FILTERS & QUERY BUILDER ---
        html.Div(style={'backgroundColor': '#f1f1f1', 'padding': '15px', 'borderRadius': '5px', 'marginBottom': '20px', 'display': 'flex', 'flexDirection': 'column', 'gap': '15px'}, children=[
            
            # STANDARD UI FILTERS (Row 1)
            html.Div(style={'display': 'flex', 'gap': '30px', 'alignItems': 'flex-end'}, children=[
                html.Div([
                    html.Label("Side:", style={'fontWeight': 'bold', 'fontSize': '0.9em'}),
                    dcc.Checklist(id='filter-side', options=[{'label': 'Left', 'value': 'Left'}, {'label': 'Right', 'value': 'Right'}], value=['Left', 'Right'], inline=True, inputStyle={"margin-right": "5px", "margin-left": "10px"})
                ]),
                html.Div([
                    html.Label("Status:", style={'fontWeight': 'bold', 'fontSize': '0.9em'}),
                    dcc.Checklist(id='filter-outlier', options=[{'label': 'Normal', 'value': 'Normal'}, {'label': 'Outlier', 'value': 'Outlier'}], value=['Normal', 'Outlier'], inline=True, inputStyle={"margin-right": "5px", "margin-left": "10px"})
                ]),
                html.Div(style={'width': '200px'}, children=[
                    html.Label("Filter by Tile:", style={'fontWeight': 'bold', 'fontSize': '0.9em'}),
                    dcc.Dropdown(id='filter-tile', options=[{'label': f"Tile {i}", 'value': i} for i in range(1, 13)], multi=True, placeholder="All Tiles", style={'fontSize': '0.9em'})
                ]),
                html.Div(style={'width': '200px'}, children=[
                    html.Label("Filter by Pass:", style={'fontWeight': 'bold', 'fontSize': '0.9em'}),
                    dcc.Dropdown(id='filter-pass', multi=True, placeholder="All Passes", style={'fontSize': '0.9em'})
                ]),
            ]),

            # ADVANCED QUERY BUILDER (Row 2)
            html.Div(style={'borderTop': '1px solid #ccc', 'paddingTop': '15px', 'display': 'flex', 'flexDirection': 'column', 'gap': '10px'}, children=[
                html.Div(style={'display': 'flex', 'alignItems': 'center', 'gap': '10px'}, children=[
                    html.Label("Advanced Query:", style={'fontWeight': 'bold', 'whiteSpace': 'nowrap'}),
                    dcc.Input(id='query-input', type='text', placeholder="e.g., mean_grf > 200 and side == 'Left'", debounce=True, style={'flex': '1', 'padding': '0 12px', 'height': '38px', 'boxSizing': 'border-box', 'borderRadius': '4px', 'border': '1px solid #ccc'}),
                    html.Button('Apply', id='apply-query-btn', n_clicks=0, style={'height': '38px', 'padding': '0 15px', 'backgroundColor': '#007BFF', 'color': 'white', 'border': 'none', 'borderRadius': '4px', 'cursor': 'pointer', 'fontWeight': 'bold'}),
                    html.Button('Clear', id='clear-query-btn', n_clicks=0, style={'height': '38px', 'padding': '0 15px', 'backgroundColor': '#6c757d', 'color': 'white', 'border': 'none', 'borderRadius': '4px', 'cursor': 'pointer'})
                ]),
                html.Div(id='query-error-msg', style={'color': 'red', 'fontWeight': 'bold', 'fontSize': '0.9em', 'minHeight': '15px'}),
            ])
        ]),

        # --- VISUALIZATION SECTIONS ---
        
        # Section A: Feature Analysis & Library (Nested Tabs)
        dcc.Tabs(id="view-tabs", value='tab-feature', children=[
            dcc.Tab(label='Feature Analysis', value='tab-feature', children=[
                html.Div(style={'display': 'flex', 'gap': '20px', 'height': '450px', 'padding': '20px'}, children=[
                    html.Div(style={'flex': '3', 'display': 'flex', 'flexDirection': 'column', 'gap': '15px'}, children=[
                        html.Div(style={'flex': '2', 'border': '1px solid #ccc', 'borderRadius': '5px', 'padding': '10px'}, children=[
                            with_spinner(dcc.Graph(id='main-scatter', style={'height': '100%'}))
                        ]),
                        html.Div(style={'flex': '1', 'border': '1px solid #ccc', 'borderRadius': '5px', 'padding': '10px'}, children=[
                            with_spinner(dcc.Graph(id='rug-plot', style={'height': '100%'}))
                        ]),
                    ]),
                    html.Div(style={'flex': '1', 'backgroundColor': '#f9f9f9', 'padding': '20px', 'borderRadius': '5px', 'overflowY': 'auto'}, children=[
                        html.H5("Axis Controls"),
                        html.Label("Scatter X-Axis:"), dcc.Dropdown(id='xaxis-dd', options=FEATURE_OPTIONS, value='start_frame', clearable=False), html.Br(),
                        html.Label("Scatter Y-Axis:"), dcc.Dropdown(id='yaxis-dd', options=FEATURE_OPTIONS, value='mean_grf', clearable=False), html.Br(), html.Hr(),
                        html.Label("Rug Plot Feature:"), dcc.Dropdown(id='rug-dd', options=FEATURE_OPTIONS, value='r_score', clearable=False), html.Br(), html.Hr(),
                        html.Label("Color By:"), dcc.Dropdown(id='color-dd', options=[{'label': 'Side (L/R)', 'value': 'side'}, {'label': 'Outlier Status', 'value': 'is_outlier'}, {'label': 'Tile ID', 'value': 'tile_id'}, {'label': 'Pass ID', 'value': 'pass_id'}], value='side', clearable=False),
                    ])
                ])
            ]),
            dcc.Tab(label='Footstep Library', value='tab-library', children=[
                html.Div(style={'height': '450px', 'overflowY': 'auto', 'padding': '20px'}, children=[
                    html.Div(id='image-grid', style={'display': 'grid', 'gridTemplateColumns': 'repeat(auto-fill, minmax(140px, 1fr))', 'gap': '20px'})
                ])
            ]),
        ]),

        # Section B: Consolidated (Physics + Spatial)
        html.Div(style={'flex': '1', 'marginTop': '10px', 'borderTop': '2px solid #ddd', 'paddingTop': '10px', 'display': 'flex', 'gap': '20px', 'minHeight': '600px'}, children=[
            html.Div(style={'flex': '1', 'display': 'flex', 'flexDirection': 'column', 'gap': '10px'}, children=[
                html.Div(style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center'}, children=[
                    html.H4("Physics", style={'marginBottom': '5px'}),
                    dcc.RadioItems(id='physics-overlay-toggle', options=[{'label': ' Individual Step ', 'value': 'individual'}, {'label': ' Overlay All Filtered ', 'value': 'overlay'}], value='individual', inline=True, style={'fontSize': '0.9em'})
                ]),
                html.Div(style={'flex': '1', 'border': '1px solid #eee', 'borderRadius': '5px', 'padding': '5px'}, children=[
                    with_spinner(dcc.Graph(id='grf-plot', style={'height': '100%'}))
                ]),
                html.Div(style={'flex': '1', 'border': '1px solid #eee', 'borderRadius': '5px', 'padding': '5px'}, children=[
                    with_spinner(dcc.Graph(id='cop-plot', style={'height': '100%'}))
                ])
            ]),
            html.Div(style={'flex': '1', 'display': 'flex', 'flexDirection': 'column', 'gap': '10px'}, children=[
                html.Div(style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center'}, children=[
                    html.H4("Spatial Footstep Map", style={'marginBottom': '5px'}),
                    dcc.Checklist(id='isolate-pass-check', options=[{'label': ' Isolate Pass on Click', 'value': 'isolate'}], value=['isolate'], inputStyle={"margin-right": "5px"})
                ]),
                html.Div(style={'flex': '1', 'border': '1px solid #ccc', 'borderRadius': '5px', 'padding': '10px'}, children=[
                    with_spinner(dcc.Graph(id='walkway-plot', style={'height': '100%'}))
                ])
            ])
        ]),

        # Section C: Heatmap + Histogram
        html.Div(style={'marginTop': '20px', 'paddingTop': '20px', 'borderTop': '2px solid #ddd'}, children=[
            html.Div(style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '10px'}, children=[
                html.H3("Pressure Detail", style={'margin': '0'}),
                html.Div(children=[
                    html.Label("Color Scale:", style={'fontWeight': 'bold', 'marginRight': '10px'}),
                    dcc.RadioItems(id='color-scale-toggle', options=[{'label': ' Dynamic (Step Peak) ', 'value': 'dynamic'}, {'label': ' Absolute (800 kPa) ', 'value': 'absolute'}], value='dynamic', inline=True)
                ])
            ]),
            html.Div(style={'display': 'flex', 'gap': '20px'}, children=[
                html.Div(style={'flex': '1', 'backgroundColor': 'white', 'padding': '15px', 'borderRadius': '5px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'}, children=[
                    with_spinner(dcc.Graph(id='heatmap-plot', style={'height': '400px'}))
                ]),
                html.Div(style={'flex': '1', 'backgroundColor': 'white', 'padding': '15px', 'borderRadius': '5px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'}, children=[
                    with_spinner(dcc.Graph(id='histogram-plot', style={'height': '400px'}))
                ]),
            ])
        ])
    ])

# =====================================================================
# TAB 2: CROSS-TRIAL ANALYSIS LAYOUT (Phase 2 - Placeholder)
# =====================================================================
def get_cross_trial_layout():
    return html.Div(children=[
        
        # --- ZONE 1: COHORT SELECTION ---
        html.Div(style={'backgroundColor': '#eef2f5', 'padding': '15px', 'borderRadius': '5px', 'marginBottom': '20px', 'display': 'flex', 'gap': '20px'}, children=[
            html.Div(style={'flex': '1'}, children=[
                html.Label("1. Filter Participants (Leave blank for all):", style={'fontWeight': 'bold', 'fontSize': '0.9em'}),
                dcc.Dropdown(id='ct-part-dd', options=OPTIONS_PART, multi=True, placeholder="All Participants")
            ]),
            html.Div(style={'flex': '1'}, children=[
                html.Label("2. Filter Footwear:", style={'fontWeight': 'bold', 'fontSize': '0.9em'}),
                dcc.Dropdown(id='ct-shoe-dd', options=OPTIONS_SHOE, multi=True, placeholder="All Footwear")
            ]),
            html.Div(style={'flex': '1'}, children=[
                html.Label("3. Filter Speeds:", style={'fontWeight': 'bold', 'fontSize': '0.9em'}),
                dcc.Dropdown(id='ct-speed-dd', options=OPTIONS_SPEED, multi=True, placeholder="All Speeds")
            ])
        ]),

        # --- ZONE 2: PLOT CONFIGURATION & EXECUTION ---
        html.Div(style={'display': 'flex', 'gap': '15px', 'marginBottom': '20px', 'alignItems': 'stretch'}, children=[
            html.Div(style={'flex': '1', 'border': '1px solid #ccc', 'padding': '10px', 'borderRadius': '5px', 'backgroundColor': '#f9f9f9'}, children=[
                html.Label("Primary Metric (Y-Axis):", style={'fontWeight': 'bold', 'fontSize': '0.9em'}),
                dcc.Dropdown(id='ct-metric-dd', options=FEATURE_OPTIONS, value='peak_grf', clearable=False)
            ]),
            # NEW: Scatter X-Axis
            html.Div(style={'flex': '1', 'border': '1px solid #ccc', 'padding': '10px', 'borderRadius': '5px', 'backgroundColor': '#f9f9f9'}, children=[
                html.Label("Scatter Metric (X-Axis):", style={'fontWeight': 'bold', 'fontSize': '0.9em'}),
                dcc.Dropdown(id='ct-scatter-x-dd', options=FEATURE_OPTIONS, value='stance_duration_frames', clearable=False)
            ]),
            html.Div(style={'flex': '1', 'border': '1px solid #ccc', 'padding': '10px', 'borderRadius': '5px', 'backgroundColor': '#f9f9f9'}, children=[
                html.Label("Group By (Distributions):", style={'fontWeight': 'bold', 'fontSize': '0.9em'}),
                dcc.Dropdown(id='ct-group-dd', options=[
                    {'label': 'Footwear Type', 'value': 'footwear'},
                    {'label': 'Walking Speed', 'value': 'speed'},
                    {'label': 'Biological Sex', 'value': 'sex'},
                    {'label': 'Participant ID', 'value': 'participant_id'}
                ], value='footwear', clearable=False)
            ]),
            html.Div(style={'flex': '1', 'border': '1px solid #ccc', 'padding': '10px', 'borderRadius': '5px', 'backgroundColor': '#f9f9f9'}, children=[
                html.Label("Sub-Group (Color):", style={'fontWeight': 'bold', 'fontSize': '0.9em'}),
                dcc.Dropdown(id='ct-color-dd', options=[
                    {'label': 'None', 'value': 'none'},
                    {'label': 'Footwear Type', 'value': 'footwear'},
                    {'label': 'Walking Speed', 'value': 'speed'},
                    {'label': 'Biological Sex', 'value': 'sex'},
                    {'label': 'Side (Left/Right)', 'value': 'side'}
                ], value='speed', clearable=False)
            ]),
            html.Div(style={'flex': '0.7', 'display': 'flex', 'alignItems': 'flex-end'}, children=[
                html.Button('Update Charts', id='ct-update-btn', n_clicks=0, style={
                    'height': '100%', 'width': '100%', 'minHeight': '50px', 
                    'backgroundColor': '#28a745', 'color': 'white', 'border': 'none', 
                    'borderRadius': '5px', 'fontWeight': 'bold', 'cursor': 'pointer', 'fontSize': '1.05em'
                })
            ])
        ]),

        # --- ZONE 3: VISUALIZATIONS (2x2 Grid)
        html.Div(style={'display': 'flex', 'flexDirection': 'column', 'gap': '20px'}, children=[
            
            # Row 1: Distributions
            html.Div(style={'display': 'flex', 'gap': '20px', 'height': '450px'}, children=[
                html.Div(style={'flex': '1', 'border': '1px solid #ddd', 'borderRadius': '5px', 'backgroundColor': 'white', 'padding': '10px'}, children=[
                    with_spinner(dcc.Graph(id='ct-box-plot', style={'height': '100%'}))
                ]),
                html.Div(style={'flex': '1', 'border': '1px solid #ddd', 'borderRadius': '5px', 'backgroundColor': 'white', 'padding': '10px'}, children=[
                    with_spinner(dcc.Graph(id='ct-violin-plot', style={'height': '100%'}))
                ])
            ]),
            
            # Row 2: Correlations and Time-Series
            html.Div(style={'display': 'flex', 'gap': '20px', 'height': '450px'}, children=[
                #Bivariate Scatter Plot
                html.Div(style={'flex': '1', 'border': '1px solid #ddd', 'borderRadius': '5px', 'backgroundColor': 'white', 'padding': '10px'}, children=[
                    with_spinner(dcc.Graph(id='ct-bivariate-scatter', style={'height': '100%'}))
                ]),
                #Aggregate Waveform Plot
                html.Div(style={'flex': '1', 'border': '1px solid #ddd', 'borderRadius': '5px', 'backgroundColor': 'white', 'padding': '10px'}, children=[
                    with_spinner(dcc.Graph(id='ct-aggregate-waveform', style={'height': '100%'}))
                ])
            ])
        ])
    ])

# =====================================================================
# MASTER SHELL
# =====================================================================
def create_layout():
    return html.Div(style={'height': '100vh', 'display': 'flex', 'flexDirection': 'column', 'padding': '20px'}, children=[
        
        # Global State Stores (Accessible to ALL tabs)
        dcc.Store(id='selected-step-store'),
        dcc.Store(id='physics-cache', storage_type='memory'),
        dcc.Store(id='filtered-data-store'),
        
        #bridge store: Used to command the single-trial view to load a specific trial
        dcc.Store(id='bridge-store'), 

        html.H2("StepUP Analysis", style={'marginBottom': '20px'}),

        # The Master Application Tabs
        dcc.Tabs(id="master-tabs", value='tab-single-trial', children=[
            
            dcc.Tab(label='Single-Trial Analysis', value='tab-single-trial', children=[
                html.Div(style={'paddingTop': '20px'}, children=[
                    get_single_trial_layout()
                ])
            ]),
            
            dcc.Tab(label='Cross-Trial Analysis', value='tab-cross-trial', children=[
                html.Div(style={'paddingTop': '20px'}, children=[
                    get_cross_trial_layout()
                ])
            ]),
        ])
    ])