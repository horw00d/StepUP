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
    {'label': 'Foot Length', 'value': 'foot_length'},
    {'label': 'Foot Width', 'value': 'foot_width'},
    {'label': 'Rotation Angle', 'value': 'rotation_angle'},
]

# Helpers
def get_dropdown_options(model_col):
    with Session(engine) as session:
        results = session.scalars(select(distinct(model_col)).order_by(model_col)).all()
        return [{'label': str(x), 'value': str(x)} for x in results]

# Main layout function
def create_layout():
    return html.Div(style={'height': '100vh', 'display': 'flex', 'flexDirection': 'column', 'padding': '20px'}, children=[
        
        # Store
        dcc.Store(id='selected-step-store'),

        # Header
        html.Div(style={'borderBottom': '1px solid #ddd', 'paddingBottom': '15px', 'marginBottom': '10px'}, children=[
            html.H2("StepUP: Trial Analysis Dashboard", style={'display': 'inline-block', 'marginRight': '30px'}),
            html.Div(style={'display': 'flex', 'gap': '20px', 'alignItems': 'center'}, children=[
                dcc.Dropdown(id='part-dd', options=get_dropdown_options(Participant.id), value='001', placeholder="Participant", style={'width': '120px'}),
                dcc.Dropdown(id='shoe-dd', options=get_dropdown_options(Trial.footwear), value='BF', placeholder="Footwear", style={'width': '120px'}),
                dcc.Dropdown(id='speed-dd', options=get_dropdown_options(Trial.speed), value='W1', placeholder="Speed", style={'width': '120px'}),
                html.Div(id='trial-status', style={'marginLeft': 'auto', 'fontWeight': 'bold', 'color': '#555'})
            ])
        ]),

        html.Div(style={'backgroundColor': '#f1f1f1', 'padding': '15px', 'borderRadius': '5px', 'marginBottom': '20px', 'display': 'flex', 'gap': '30px', 'alignItems': 'flex-end'}, children=[
            
            # Side Filter
            html.Div([
                html.Label("Side:", style={'fontWeight': 'bold', 'fontSize': '0.9em'}),
                dcc.Checklist(
                    id='filter-side',
                    options=[{'label': 'Left', 'value': 'Left'}, {'label': 'Right', 'value': 'Right'}],
                    value=['Left', 'Right'], # Default All
                    inline=True,
                    inputStyle={"margin-right": "5px", "margin-left": "10px"}
                )
            ]),

            # Outlier Filter
            html.Div([
                html.Label("Status:", style={'fontWeight': 'bold', 'fontSize': '0.9em'}),
                dcc.Checklist(
                    id='filter-outlier',
                    options=[{'label': 'Normal', 'value': 'Normal'}, {'label': 'Outlier', 'value': 'Outlier'}],
                    value=['Normal', 'Outlier'], # Default All
                    inline=True,
                    inputStyle={"margin-right": "5px", "margin-left": "10px"}
                )
            ]),

            # Tile Filter (1-12)
            html.Div(style={'width': '200px'}, children=[
                html.Label("Filter by Tile:", style={'fontWeight': 'bold', 'fontSize': '0.9em'}),
                dcc.Dropdown(
                    id='filter-tile',
                    options=[{'label': f"Tile {i}", 'value': i} for i in range(1, 13)],
                    multi=True,
                    placeholder="All Tiles",
                    style={'fontSize': '0.9em'}
                )
            ]),

            # Pass Filter (Moved from Spatial Tab to here for Global control)
            html.Div(style={'width': '200px'}, children=[
                html.Label("Filter by Pass:", style={'fontWeight': 'bold', 'fontSize': '0.9em'}),
                dcc.Dropdown(
                    id='filter-pass', # Renamed from pass-selector
                    multi=True,
                    placeholder="All Passes",
                    style={'fontSize': '0.9em'}
                )
            ]),
        ]),

        # 1st Section: Feature Analysis & Library (Tabs)
        dcc.Tabs(id="view-tabs", value='tab-feature', children=[
            # TAB 1: SCATTER & RUG
            dcc.Tab(label='Feature Analysis', value='tab-feature', children=[
                html.Div(style={'display': 'flex', 'gap': '20px', 'height': '450px', 'padding': '20px'}, children=[
                    # Left col: graphs
                    html.Div(style={'flex': '3', 'display': 'flex', 'flexDirection': 'column', 'gap': '15px'}, children=[
                        html.Div(style={'flex': '2', 'border': '1px solid #ccc', 'borderRadius': '5px', 'padding': '10px'}, children=[
                            dcc.Graph(id='main-scatter', style={'height': '100%'})
                        ]),
                        html.Div(style={'flex': '1', 'border': '1px solid #ccc', 'borderRadius': '5px', 'padding': '10px'}, children=[
                            dcc.Graph(id='rug-plot', style={'height': '100%'})
                        ]),
                    ]),
                    # Right col: controls
                    html.Div(style={'flex': '1', 'backgroundColor': '#f9f9f9', 'padding': '20px', 'borderRadius': '5px', 'overflowY': 'auto'}, children=[
                        html.H5("Axis Controls"),
                        html.Label("Scatter X-Axis:"),
                        dcc.Dropdown(id='xaxis-dd', options=FEATURE_OPTIONS, value='start_frame', clearable=False),
                        html.Br(),
                        html.Label("Scatter Y-Axis:"),
                        dcc.Dropdown(id='yaxis-dd', options=FEATURE_OPTIONS, value='mean_grf', clearable=False),
                        html.Br(),
                        html.Hr(),
                        html.Label("Rug Plot Feature:"),
                        dcc.Dropdown(id='rug-dd', options=FEATURE_OPTIONS, value='r_score', clearable=False),
                        html.Br(),
                        html.Hr(),
                        html.Label("Color By:"),
                        dcc.Dropdown(id='color-dd', options=[
                            {'label': 'Side (L/R)', 'value': 'side'},
                            {'label': 'Outlier Status', 'value': 'is_outlier'},
                            {'label': 'Tile ID', 'value': 'tile_id'},
                            {'label': 'Pass ID', 'value': 'pass_id'}
                        ], value='side', clearable=False),
                    ])
                ])
            ]),
            
            # TAB 2: IMAGE LIBRARY
            dcc.Tab(label='Footstep Library', value='tab-library', children=[
                html.Div(style={'height': '450px', 'overflowY': 'auto', 'padding': '20px'}, children=[
                    html.Div(id='image-grid', style={
                        'display': 'grid',
                        'gridTemplateColumns': 'repeat(auto-fill, minmax(140px, 1fr))',
                        'gap': '20px'
                    })
                ])
            ]),
        ]),

        # 2nd Section: Consolidated (Physics + Spatial)
        html.Div(style={'flex': '1', 'marginTop': '10px', 'borderTop': '2px solid #ddd', 'paddingTop': '10px', 'display': 'flex', 'gap': '20px', 'minHeight': '600px'}, children=[
            
            # LEFT COLUMN: Physics (Stacked Vertically)
            html.Div(style={'flex': '1', 'display': 'flex', 'flexDirection': 'column', 'gap': '10px'}, children=[
                html.H4("Physics", style={'marginBottom': '5px'}),
                
                # GRF Plot (Top Half)
                html.Div(style={'flex': '1', 'border': '1px solid #eee', 'borderRadius': '5px', 'padding': '5px'}, children=[
                    dcc.Graph(id='grf-plot', style={'height': '100%'})
                ]),
                
                # COP Plot (Bottom Half)
                html.Div(style={'flex': '1', 'border': '1px solid #eee', 'borderRadius': '5px', 'padding': '5px'}, children=[
                    dcc.Graph(id='cop-plot', style={'height': '100%'})
                ])
            ]),

            # RIGHT COLUMN: Walkway (Spatial Map)
            html.Div(style={'flex': '1', 'display': 'flex', 'flexDirection': 'column', 'gap': '10px'}, children=[
                html.Div(style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center'}, children=[
                    html.H4("Spatial Footstep Map", style={'marginBottom': '5px'}),
                    
                    #new toggle to show all passes or isolate the clicked pass
                    dcc.Checklist(
                        id='isolate-pass-check',
                        options=[{'label': ' Isolate Pass on Click', 'value': 'isolate'}],
                        value=['isolate'], # Default to ON
                        inputStyle={"margin-right": "5px"}
                    )
                ]),
                
                # The Walkway Plot
                html.Div(style={'flex': '1', 'border': '1px solid #ccc', 'borderRadius': '5px', 'padding': '10px'}, children=[
                    dcc.Graph(id='walkway-plot', style={'height': '100%'})
                ])
            ])
        ]),

        # 3rd Section: Heatmap + Histogram for Selected Step
        html.Div(style={'marginTop': '20px', 'paddingTop': '20px', 'borderTop': '2px solid #ddd'}, children=[
            
            #updated header with color scale toggle
            html.Div(style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '10px'}, children=[
                html.H3("Pressure Detail", style={'margin': '0'}),
                
                html.Div(children=[
                    html.Label("Color Scale:", style={'fontWeight': 'bold', 'marginRight': '10px'}),
                    dcc.RadioItems(
                        id='color-scale-toggle',
                        options=[
                            {'label': ' Dynamic (Step Peak) ', 'value': 'dynamic'},
                            {'label': ' Absolute (800 kPa) ', 'value': 'absolute'}
                        ],
                        value='dynamic', #default state
                        inline=True,
                        inputStyle={"marginRight": "5px", "marginLeft": "15px"}
                    )
                ])
            ]),
            
            html.Div(style={'display': 'flex', 'gap': '20px'}, children=[
                #Heatmap
                html.Div(style={'flex': '1', 'backgroundColor': 'white', 'padding': '15px', 'borderRadius': '5px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'}, 
                children=[
                    dcc.Graph(id='heatmap-plot', style={'height': '400px'})
                ]),

                #Histogram
                html.Div(style={'flex': '1', 'backgroundColor': 'white', 'padding': '15px', 'borderRadius': '5px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'}, 
                children=[
                    dcc.Graph(id='histogram-plot', style={'height': '400px'})
                ]),
            ])
        ])
    ])