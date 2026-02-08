import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import plotly.graph_objects as go
import pandas as pd

# define standard colors for consistency across app
COLOR_MAP = {
    'Left': '#1f77b4',  # Muted Blue
    'Right': '#2ca02c', # Muted Green
    'Normal': '#7f7f7f', # Gray
    'Outlier': '#d62728' # Red
}

# WALKWAY PLOT
def create_walkway_plot(footsteps, selected_step_id=None):
    SENSOR_SIZE_M = 0.005
    TILE_WIDTH_M = 0.6
    
    fig = go.Figure()

    # 1. Draw Tiles
    tiles = []
    for x in [0, TILE_WIDTH_M]:
        for y in [i * TILE_WIDTH_M for i in range(6)]:
            tiles.append(dict(
                type="rect", x0=x, x1=x + TILE_WIDTH_M, y0=y, y1=y + TILE_WIDTH_M,
                line=dict(color="#dddddd", width=1), fillcolor="white", layer="below"
            ))
    fig.update_layout(shapes=tiles)

    # 2. Draw Footsteps
    box_shapes = []
    
    for step in footsteps:
        if step.box_xmin is None: continue
        
        x0, x1 = step.box_xmin * SENSOR_SIZE_M, step.box_xmax * SENSOR_SIZE_M
        y0, y1 = step.box_ymin * SENSOR_SIZE_M, step.box_ymax * SENSOR_SIZE_M
        
        is_selected = (step.id == selected_step_id)
        
        if is_selected:
            color = "#FF0000"
            opacity = 0.8
            line_width = 3
        else:
            color = "#1f77b4" if step.side == 'Left' else "#2ca02c"
            opacity = 0.4
            line_width = 1

        box_shapes.append(dict(
            type="rect", x0=x0, x1=x1, y0=y0, y1=y1,
            line=dict(color=color, width=line_width),
            fillcolor=color, opacity=opacity, layer="above"
        ))

        # Invisible scatter for clicks
        fig.add_trace(go.Scatter(
            x=[(x0+x1)/2], y=[(y0+y1)/2],
            mode='markers', marker=dict(opacity=0),
            customdata=[[step.id, step.pass_id, step.footstep_index]], 
            hovertemplate="<b>Step %{customdata[2]}</b><br>Pass: %{customdata[1]}<br>ID: %{customdata[0]}<extra></extra>",
            showlegend=False
        ))

    fig.update_layout(shapes=tiles + box_shapes)
    fig.update_layout(
        title="Spatial Footstep Map",
        xaxis=dict(title="Width (m)", range=[-0.1, 1.3], scaleanchor="y", scaleratio=1),
        yaxis=dict(title="Length (m)", range=[-0.1, 3.7]),
        margin=dict(l=20, r=20, t=40, b=20),
        plot_bgcolor="#f9f9f9",
        clickmode='event+select'
    )
    return fig

#SCATTER & RUG PLOTS
def create_scatter_plot(df, x_col, y_col, color_col, selected_step_id=None):
    if df.empty: 
        return px.scatter(title="No Data")
    
    # PX is called here, but imported at TOP. This is correct.
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
    if df.empty: 
        return px.strip(title="No Data")

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

# WALKWAY PLOT
def create_walkway_plot(footsteps, selected_step_id=None):
    SENSOR_SIZE_M = 0.005
    TILE_WIDTH_M = 0.6
    
    fig = go.Figure()

    # 1. Draw Tiles
    tiles = []
    for x in [0, TILE_WIDTH_M]:
        for y in [i * TILE_WIDTH_M for i in range(6)]:
            tiles.append(dict(
                type="rect", x0=x, x1=x + TILE_WIDTH_M, y0=y, y1=y + TILE_WIDTH_M,
                line=dict(color="#dddddd", width=1), fillcolor="white", layer="below"
            ))
    fig.update_layout(shapes=tiles)

    # 2. Draw Footsteps
    box_shapes = []
    for step in footsteps:
        if step.box_xmin is None: continue
        
        x0, x1 = step.box_xmin * SENSOR_SIZE_M, step.box_xmax * SENSOR_SIZE_M
        y0, y1 = step.box_ymin * SENSOR_SIZE_M, step.box_ymax * SENSOR_SIZE_M
        
        is_selected = (step.id == selected_step_id)
        
        if is_selected:
            color = "#FF0000"
            opacity = 0.8
            line_width = 3
        else:
            color = "#1f77b4" if step.side == 'Left' else "#2ca02c"
            opacity = 0.4
            line_width = 1

        box_shapes.append(dict(
            type="rect", x0=x0, x1=x1, y0=y0, y1=y1,
            line=dict(color=color, width=line_width),
            fillcolor=color, opacity=opacity, layer="above"
        ))

        fig.add_trace(go.Scatter(
            x=[(x0+x1)/2], y=[(y0+y1)/2],
            mode='markers', marker=dict(opacity=0),
            customdata=[[step.id, step.pass_id, step.footstep_index]], 
            hovertemplate="<b>Step %{customdata[2]}</b><br>Pass: %{customdata[1]}<br>ID: %{customdata[0]}<extra></extra>",
            showlegend=False
        ))

    fig.update_layout(shapes=tiles + box_shapes)
    fig.update_layout(
        title="Spatial Footstep Map",
        xaxis=dict(title="Width (m)", range=[-0.1, 1.3], scaleanchor="y", scaleratio=1),
        yaxis=dict(title="Length (m)", range=[-0.1, 3.7]),
        margin=dict(l=20, r=20, t=40, b=20),
        plot_bgcolor="#f9f9f9",
        clickmode='event+select'
    )
    return fig

# SCATTER PLOT
def create_scatter_plot(df, x_col, y_col, color_col, selected_step_id=None):
    fig = go.Figure()
    
    if df.empty: 
        fig.update_layout(title="No Data")
        return fig
    
    # 1. Group by Color Column (Manual Legend Generation)
    # This replicates px.scatter's color grouping but is instant
    groups = df.groupby(color_col)
    
    for name, group in groups:
        # Determine specific color if in our map, else let Plotly pick
        marker_color = COLOR_MAP.get(name, None)
        
        fig.add_trace(go.Scatter(
            x=group[x_col],
            y=group[y_col],
            mode='markers',
            name=str(name),
            marker=dict(size=10, opacity=0.7, color=marker_color),
            customdata=group[['id', 'footstep_index']].values,
            hovertemplate=f"{x_col}: %{{x}}<br>{y_col}: %{{y}}<br>Step: %{{customdata[1]}}<extra></extra>"
        ))

    # 2. Highlight Selection
    if selected_step_id:
        row = df[df['id'] == selected_step_id]
        if not row.empty:
            fig.add_trace(go.Scatter(
                x=row[x_col], y=row[y_col], mode='markers',
                marker=dict(color='red', size=15, line=dict(width=2, color='black')),
                name='Selected', hoverinfo='skip'
            ))

    fig.update_layout(
        title=f"2D Feature Analysis: {x_col} vs {y_col}",
        clickmode='event+select',
        margin=dict(l=20, r=20, t=30, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig

# RUG PLOT
def create_rug_plot(df, rug_col, color_col, selected_step_id=None):
    fig = go.Figure()
    
    if df.empty: 
        fig.update_layout(title="No Data")
        return fig

    # 1. Group by Color Column
    groups = df.groupby(color_col)
    
    for name, group in groups:
        marker_color = COLOR_MAP.get(name, None)
        
        # Simulate Rug plot using Scatter where y=0
        fig.add_trace(go.Scatter(
            x=group[rug_col],
            y=[0] * len(group), # Flat line
            mode='markers',
            name=str(name),
            marker=dict(symbol='line-ns-open', size=10, line=dict(width=2), color=marker_color),
            customdata=group[['id', 'footstep_index']].values,
            hovertemplate=f"{rug_col}: %{{x}}<br>Step: %{{customdata[1]}}<extra></extra>"
        ))

    # 2. Highlight Selection
    if selected_step_id:
        row = df[df['id'] == selected_step_id]
        if not row.empty:
            fig.add_trace(go.Scatter(
                x=row[rug_col], y=[0]*len(row), mode='markers',
                marker=dict(color='red', size=14, symbol='line-ns-open', line=dict(width=4)),
                name='Selected', hoverinfo='skip'
            ))

    fig.update_layout(
        title=f"1D Distribution: {rug_col}",
        clickmode='event+select',
        margin=dict(l=20, r=20, t=30, b=20),
        yaxis=dict(visible=False, range=[-0.5, 0.5]),
        height=150,
        showlegend=False
    )
    return fig

# PHYSICS PLOTS
def create_physics_plots(metrics):
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