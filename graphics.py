import plotly.graph_objects as go
import plotly.express as px

def create_walkway_plot(footsteps, selected_step_id=None):
    
    SENSOR_SIZE_M = 0.005
    TILE_WIDTH_M = 0.6
    
    fig = go.Figure()

    #draw tiles
    tiles = []
    for x in [0, TILE_WIDTH_M]:
        for y in [i * TILE_WIDTH_M for i in range(6)]:
            tiles.append(dict(
                type="rect", x0=x, x1=x + TILE_WIDTH_M, y0=y, y1=y + TILE_WIDTH_M,
                line=dict(color="#dddddd", width=1), fillcolor="white", layer="below"
            ))
    fig.update_layout(shapes=tiles)

    #draw footsteps
    box_shapes = []
    valid_box_count = 0
    
    for step in footsteps:
        if step.box_xmin is None: 
            continue
        
        valid_box_count += 1
        
        x0, x1 = step.box_xmin * SENSOR_SIZE_M, step.box_xmax * SENSOR_SIZE_M
        y0, y1 = step.box_ymin * SENSOR_SIZE_M, step.box_ymax * SENSOR_SIZE_M
        
        is_selected = (step.id == selected_step_id)
        
        #highlighting selected step red
        if is_selected:
            color = "#FF0000"
            opacity = 0.8
            line_width = 3
        else:
            #currently hardcoding left/right foot colors, could be made enforced by main selection menu
            color = "#1f77b4" if step.side == 'Left' else "#2ca02c"
            opacity = 0.4
            line_width = 1

        box_shapes.append(dict(
            type="rect", x0=x0, x1=x1, y0=y0, y1=y1,
            line=dict(color=color, width=line_width),
            fillcolor=color, opacity=opacity, layer="above"
        ))

        #invisible scatter point for clicks
        fig.add_trace(go.Scatter(
            x=[(x0+x1)/2], y=[(y0+y1)/2],
            mode='markers', marker=dict(opacity=0),
            customdata=[[step.id, step.pass_id, step.footstep_index]], 
            
            #hover info
            hovertemplate="<b>Step %{customdata[2]}</b><br>Pass: %{customdata[1]}<br>ID: %{customdata[0]}<extra></extra>",
            showlegend=False
        ))
    
    fig.update_layout(shapes=tiles + box_shapes)
    fig.update_layout(
        title=f"Spatial Footstep Map ({valid_box_count} steps)",
        xaxis=dict(title="Width (m)", range=[-0.1, 1.3], scaleanchor="y", scaleratio=1),
        yaxis=dict(title="Length (m)", range=[-0.1, 3.7]),
        margin=dict(l=20, r=20, t=40, b=20),
        plot_bgcolor="#f9f9f9",
        clickmode='event+select'
    )
    return fig

def create_scatter_plot(df, x_col, y_col, color_col, selected_step_id=None):
    if df.empty: return px.scatter(title="No Data")
    
    fig = px.scatter(
        df, x=x_col, y=y_col, color=color_col,
        hover_data=['footstep_index', 'id'], custom_data=['id'],
        title=f"2D Feature Analysis: {x_col} vs {y_col}"
    )
    fig.update_layout(clickmode='event+select', margin=dict(l=20, r=20, t=30, b=20))
    fig.update_traces(marker_size=10, unselected=dict(marker=dict(opacity=0.3)))

    # Highlight Logic
    if selected_step_id:
        row = df[df['id'] == selected_step_id]
        if not row.empty:
            fig.add_trace(go.Scatter(
                x=row[x_col], y=row[y_col], mode='markers',
                marker=dict(color='red', size=15, line=dict(width=2, color='black')),
                name='Selected', hoverinfo='skip'
            ))
    return fig

def create_rug_plot(df, rug_col, color_col, selected_step_id=None):
    if df.empty: return px.strip(title="No Data")

    fig = px.strip(
        df, x=rug_col, color=color_col, stripmode='overlay',
        hover_data=['footstep_index', 'id'], custom_data=['id'],
        title=f"1D Distribution: {rug_col}"
    )
    fig.update_layout(clickmode='event+select', margin=dict(l=20, r=20, t=30, b=20), yaxis={'visible': False}, height=150)
    fig.update_traces(marker_size=8, jitter=0.5)

    if selected_step_id:
        row = df[df['id'] == selected_step_id]
        if not row.empty:
            fig.add_trace(go.Scatter(
                x=row[rug_col], y=[0]*len(row), mode='markers',
                marker=dict(color='red', size=12, symbol='line-ns-open', line=dict(width=3)),
                name='Selected', hoverinfo='skip'
            ))
    return fig

def create_physics_plots(metrics):
    """Returns (fig_grf, fig_cop)"""
    empty = go.Layout(xaxis={"visible": False}, yaxis={"visible": False}, annotations=[{"text": "Select a step", "showarrow": False}])
    if not metrics: return go.Figure(layout=empty), go.Figure(layout=empty)

    # GRF
    fig_grf = go.Figure()
    fig_grf.add_trace(go.Scatter(x=metrics['time_pct'], y=metrics['grf'], mode='lines', line=dict(color='blue', width=3)))
    fig_grf.update_layout(title=f"Vertical GRF (Step {metrics['step_id']})", xaxis_title="% Stance", yaxis_title="Force (N)", margin=dict(l=40, r=40, t=40, b=40))

    # COP
    fig_cop = go.Figure()
    fig_cop.add_trace(go.Scatter(x=metrics['cop_ml'], y=metrics['cop_ap'], mode='lines+markers', marker=dict(size=4, color=metrics['time_pct'], colorscale='Viridis')))
    fig_cop.update_layout(title="COP Trajectory", xaxis_title="Mediolateral (cm)", yaxis_title="Anteroposterior (cm)", yaxis=dict(scaleanchor="x", scaleratio=1), margin=dict(l=40, r=40, t=40, b=40))

    return fig_grf, fig_cop