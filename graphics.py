import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

# define standard colors for consistency across app
COLOR_MAP = {
    'Left': '#1f77b4',  # Muted Blue
    'Right': '#2ca02c', # Muted Green
    'Normal': '#7f7f7f', # Gray
    'Outlier': '#d62728' # Red
}

#HELPERS

def generate_dynamic_hover_data(df):
    """
    Dynamically generates Plotly hover_data dictionary.
    Only includes keys that currently exist in the DataFrame to prevent Plotly validation errors.
    """
    # List all the columns you ever want to see in a tooltip, in the order you want them
    desired_hover_cols = [
        'participant_id', 
        'side', 
        'footwear', 
        'speed',  
        'n_footsteps'
    ]
    
    # Build the dictionary dynamically: only add the column if it survived the aggregation
    return {col: True for col in desired_hover_cols if col in df.columns}

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
            mode='markers', 
            marker=dict(opacity=0),
            customdata=[[step.id, step.tile_id, step.pass_id, step.footstep_index]], 
            hovertemplate=(
                "<b>Step %{customdata[3]}</b><br>"
                "TileID: %{customdata[1]}<br>"
                "Pass: %{customdata[2]}<br>"
                "ID: %{customdata[0]}<extra></extra>"
            ),
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
    
    # 1. Group by Color Column
    groups = df.groupby(color_col)
    
    for name, group in groups:
        # check if there is a preset color (e.g., Left/Right), otherwise let Plotly cycle defaults
        preset_color = COLOR_MAP.get(name, None)
        
        marker_settings = dict(size=10, opacity=0.7)
        if preset_color:
            marker_settings['color'] = preset_color
        
        fig.add_trace(go.Scatter(
            x=group[x_col],
            y=group[y_col],
            mode='markers',
            name=str(name),
            marker=marker_settings,
            customdata=group[['id', 'footstep_index']].values,
            hovertemplate=f"{x_col}: %{{x}}<br>{y_col}: %{{y}}<br>Step: %{{customdata[1]}}<extra></extra>"
        ))

    #2 highlight selection
    if selected_step_id:
        row = df[df['id'] == selected_step_id]
        if not row.empty:
            fig.add_trace(go.Scatter(
                x=row[x_col], y=row[y_col], mode='markers',
                marker=dict(color='red', size=15, line=dict(width=2, color='black')),
                name='Selected', hoverinfo='skip'
            ))

    # if > 5 categories (e.g., Pass ID), move legend to the right to prevent overlap.
    if len(groups) > 5:
        legend_config = dict(
            orientation="v",
            yanchor="top", y=1,
            xanchor="left", x=1.02 # place cleanly on the right
        )
    else:
        legend_config = dict(
            orientation="h",
            yanchor="bottom", y=1.02,
            xanchor="right", x=1
        )

    fig.update_layout(
        title=f"2D Feature Analysis: {x_col} vs {y_col}",
        clickmode='event+select',
        margin=dict(l=20, r=20, t=30, b=20),
        legend=legend_config
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

def get_empty_physics_layout(title="No Data"):
    """Helper to return a clean empty state for physics plots."""
    return go.Layout(
        title=title, xaxis={"visible": False}, yaxis={"visible": False}, 
        annotations=[{"text": "Select a step or enable Overlay", "showarrow": False}],
        plot_bgcolor='white'
    )

def create_grf_plot(all_metrics, selected_step_id=None, overlay_mode=False):
    """
    Generates the Vertical Ground Reaction Force (GRF) plot.
    Supports 'Ghost Line' overlay for contextual variance analysis.
    """
    if not all_metrics:
        return go.Figure(layout=get_empty_physics_layout("Vertical GRF"))

    fig = go.Figure()
    selected_metric = None

    # 1. Plot the Background (Ghost Lines)
    if overlay_mode:
        for m in all_metrics:
            if m['step_id'] == selected_step_id:
                selected_metric = m # Save for later so it renders on top
                continue
            
            # Plot faded background line
            fig.add_trace(go.Scatter(
                x=m['time_pct'], y=m['grf'], 
                mode='lines', 
                line=dict(color='lightgrey', width=1), 
                opacity=0.3, 
                hoverinfo='skip', # Don't overwhelm the user with tooltips
                showlegend=False
            ))
    else:
        # If not in overlay mode, just find the selected metric
        selected_metric = next((m for m in all_metrics if m['step_id'] == selected_step_id), None)

    # 2. Plot the Foreground (Selected Step)
    if selected_metric:
        fig.add_trace(go.Scatter(
            x=selected_metric['time_pct'], y=selected_metric['grf'], 
            mode='lines', 
            line=dict(color='#007BFF', width=3), # Bold Blue
            name=f"Step {selected_metric['step_id']}",
            hovertemplate="Stance: %{x:.1f}%<br>Force: %{y:.1f} N<extra></extra>"
        ))

    # 3. Layout Formatting
    title_text = f"Vertical GRF (Step {selected_step_id})" if selected_step_id else "Vertical GRF"
    fig.update_layout(
        title=title_text, 
        xaxis_title="% Stance", 
        yaxis_title="Force (N)", 
        margin=dict(l=40, r=20, t=40, b=40),
        plot_bgcolor='#f9f9f9',
        showlegend=False
    )
    return fig


def create_cop_plot(all_metrics, selected_step_id=None, overlay_mode=False):
    """
    Generates the Center of Pressure (COP) trajectory plot.
    Supports 'Ghost Line' overlay for contextual variance analysis.
    """
    if not all_metrics:
        return go.Figure(layout=get_empty_physics_layout("COP Trajectory"))

    fig = go.Figure()
    selected_metric = None

    # 1. Plot the Background (Ghost Trajectories)
    if overlay_mode:
        for m in all_metrics:
            if m['step_id'] == selected_step_id:
                selected_metric = m
                continue
            
            fig.add_trace(go.Scatter(
                x=m['cop_ml'], y=m['cop_ap'], 
                mode='lines', # Just lines for the ghosts to reduce visual clutter
                line=dict(color='lightgrey', width=1), 
                opacity=0.3, 
                hoverinfo='skip',
                showlegend=False
            ))
    else:
        selected_metric = next((m for m in all_metrics if m['step_id'] == selected_step_id), None)

    # 2. Plot the Foreground (Selected Trajectory with Time Gradient)
    if selected_metric:
        fig.add_trace(go.Scatter(
            x=selected_metric['cop_ml'], y=selected_metric['cop_ap'], 
            mode='lines+markers', 
            marker=dict(
                size=5, 
                color=selected_metric['time_pct'], # Gradient coloring for time
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title="% Stance", thickness=10, len=0.8)
            ),
            line=dict(color='black', width=1), # Thin black line connecting the colored dots
            name=f"Step {selected_metric['step_id']}",
            hovertemplate="ML: %{x:.2f} cm<br>AP: %{y:.2f} cm<extra></extra>"
        ))

    # 3. Layout Formatting
    fig.update_layout(
        title="COP Trajectory", 
        xaxis_title="Mediolateral (cm)", 
        yaxis_title="Anteroposterior (cm)", 
        yaxis=dict(scaleanchor="x", scaleratio=1), # Keep physical aspect ratio 1:1
        margin=dict(l=40, r=20, t=40, b=40),
        plot_bgcolor='#f9f9f9',
        showlegend=False
    )
    return fig

def create_heatmap_and_histogram(matrix, step_id, dynamic_scale=True):
    """
    Generates a synchronized Heatmap and Histogram for a single step.
    Uses numpy for explicit binning to ensure perfect color mapping.
    """
    if matrix is None:
        empty = go.Layout(title="No Data", xaxis={'visible': False}, yaxis={'visible': False})
        return go.Figure(layout=empty), go.Figure(layout=empty)

    #config
    THRESHOLD = 10  # kPa noise floor
    Z_MIN = 0
    
    #calculate true maximum of the current footstep
    current_max = np.max(matrix)
    
    #set upper bound based on dynamic or fixed requirement
    Z_MAX = current_max if dynamic_scale else 800 

    #1 HEATMAP
    heatmap_fig = go.Figure(data=go.Heatmap(
        z=matrix,
        colorscale='Jet',
        zmin=Z_MIN, zmax=Z_MAX,
        hovertemplate="X: %{x}<br>Y: %{y}<br>Pressure: %{z:.1f} kPa<extra></extra>",
    ))
    
    #10kPa Contour Outline
    heatmap_fig.add_trace(go.Contour(
        z=matrix,
        contours=dict(
            type='constraint',
            operation='>=',
            value=THRESHOLD,
            coloring='none',
        ),
        line=dict(color='white', width=2, dash='solid'),
        showlegend=False,
        hoverinfo='skip'
    ))

    heatmap_fig.update_layout(
        title=f"Pressure Map (Step {step_id}) - Peak: {current_max:.1f} kPa",
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis=dict(visible=False), 
        yaxis=dict(visible=False, scaleanchor='x'), 
        plot_bgcolor='black'
    )

    #2 HISTOGRAM (using explicit NumPy binning to fix color mapping)
    flat_data = matrix.flatten()
    active_pixels = flat_data[flat_data > THRESHOLD]

    #handle edge case where step is entirely noise
    if len(active_pixels) == 0:
        return heatmap_fig, go.Figure(layout=go.Layout(title="no pressure > 10 kPa"))

    #explicitly calculate bins (5 kPa increments up to the maximum)
    bins = np.arange(THRESHOLD, current_max + 5, 5)
    counts, bin_edges = np.histogram(active_pixels, bins=bins)
    
    #calculate the center of each bin for the X-axis
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

    #plot using go.Bar to enforce strict color mapping
    hist_fig = go.Figure(data=go.Bar(
        x=bin_centers,
        y=counts,
        width=5, #match the bin size
        marker=dict(
            color=bin_centers, #color strictly by the x-axis value
            cmin=Z_MIN, 
            cmax=Z_MAX, 
            colorscale='Jet',
            line=dict(width=0) #remove bar borders for cleaner look
        ),
        hovertemplate="Pressure: %{x} kPa<br>Sensors: %{y}<extra></extra>"
    ))

    hist_fig.update_layout(
        title=f"Load Distribution (> {THRESHOLD} kPa)",
        xaxis_title="Pressure (kPa)",
        yaxis_title="Count (Sensors)",
        margin=dict(l=40, r=20, t=40, b=40),
        showlegend=False,
        bargap=0
    )

    return heatmap_fig, hist_fig

# =====================================================================
# CROSS-TRIAL (PHASE 2) PLOTS
# =====================================================================

def create_box_plot(df, y_col, x_col, color_col):
    if df.empty:
        return go.Figure(layout=get_empty_physics_layout("Box Plot - No Data"))
    
    color_arg = color_col if color_col != 'none' else None

    safe_custom_data = [col for col in ['participant_id', 'footwear', 'speed'] if col in df.columns]
    dynamic_hover_data = generate_dynamic_hover_data(df)
    
    fig = px.box(
        df, 
        x=x_col, 
        y=y_col, 
        color=color_arg,
        points="all",
        title=f"Distribution of {y_col} by {x_col}",
        color_discrete_map=COLOR_MAP,
        custom_data=safe_custom_data,
        hover_data=dynamic_hover_data
    )
    
    fig.update_layout(
        margin=dict(l=20, r=20, t=30, b=20),
        plot_bgcolor='#f9f9f9',
        legend_title_text=color_col.capitalize() if color_col and color_col != 'none' else "",
        xaxis_title=x_col.replace('_', ' ').title() if x_col else "",
        yaxis_title=y_col.replace('_', ' ').title() if y_col else ""
    )
    return fig

def create_violin_plot(df, y_col, x_col, color_col):
    if df.empty:
        return go.Figure(layout=get_empty_physics_layout("Violin Plot - No Data"))
    
    color_arg = color_col if color_col != 'none' else None
    
    safe_custom_data = [col for col in ['participant_id', 'footwear', 'speed'] if col in df.columns]
    dynamic_hover_data = generate_dynamic_hover_data(df)
    
    fig = px.violin(
        df, 
        x=x_col, 
        y=y_col, 
        color=color_arg,
        box=True, 
        title=f"Density Shape of {y_col} by {x_col}",
        color_discrete_map=COLOR_MAP,
        custom_data=safe_custom_data,
        hover_data=dynamic_hover_data
    )
    
    fig.update_layout(
        margin=dict(l=20, r=20, t=30, b=20),
        plot_bgcolor='#f9f9f9',
        legend_title_text=color_col.capitalize() if color_col and color_col != 'none' else "",
        xaxis_title=x_col.replace('_', ' ').title() if x_col else "",
        yaxis_title=y_col.replace('_', ' ').title() if y_col else ""
    )
    return fig

def create_bivariate_scatter_plot(df, y_col, x_col, color_col):
    """
    Generates a Bivariate Scatter Plot to show correlations between two continuous metrics.
    Includes an OLS trendline for instant regression analysis.
    """
    if df.empty:
        return go.Figure(layout=get_empty_physics_layout("Scatter Plot - No Data"))
    
    color_arg = color_col if color_col != 'none' else None

    safe_custom_data = [col for col in ['participant_id', 'footwear', 'speed'] if col in df.columns]
    dynamic_hover_data = generate_dynamic_hover_data(df)
    
    fig = px.scatter(
        df, 
        x=x_col, 
        y=y_col, 
        color=color_arg,
        trendline="ols", #instantly draw the regression line for each colored group
        title=f"Correlation of {x_col.replace('_', ' ').title()} and {y_col.replace('_', ' ').title()}",
        color_discrete_map=COLOR_MAP,
        custom_data=safe_custom_data,
        hover_data=dynamic_hover_data
    )
    
    fig.update_layout(
        margin=dict(l=20, r=20, t=30, b=20),
        plot_bgcolor='#f9f9f9',
        legend_title_text=color_col.capitalize() if color_col and color_col != 'none' else "",
        xaxis_title=x_col.replace('_', ' ').title() if x_col else "",
        yaxis_title=y_col.replace('_', ' ').title() if y_col else ""
    )
    return fig

def create_aggregate_waveform_plot(time_pct, mean_grf, upper_bound, lower_bound):
    """
    Renders a continuous mean waveform surrounded by a shaded standard deviation band.
    """
    if time_pct is None:
        return go.Figure(layout=get_empty_physics_layout("Waveform - No Data"))

    fig = go.Figure()

    # 1 invisible Upper Bound
    fig.add_trace(go.Scatter(
        x=time_pct, y=upper_bound,
        mode='lines', line=dict(width=0), showlegend=False,
        hoverinfo='skip'
    ))
    
    # 2 lower Bound (Fills space up to the Upper Bound)
    fig.add_trace(go.Scatter(
        x=time_pct, y=lower_bound,
        mode='lines', line=dict(width=0),
        fill='tonexty', fillcolor='rgba(0, 123, 255, 0.2)', showlegend=False,
        hoverinfo='skip'
    ))
    
    # 3 Solid Mean Line
    fig.add_trace(go.Scatter(
        x=time_pct, y=mean_grf,
        mode='lines', line=dict(color='rgba(0, 123, 255, 1)', width=3),
        name='Mean GRF'
    ))

    fig.update_layout(
        title="Aggregate GRF Waveform (plus minus Std Dev)",
        xaxis_title="% Stance Phase",
        yaxis_title="Ground Reaction Force (N)",
        plot_bgcolor='#f9f9f9',
        margin=dict(l=40, r=20, t=40, b=40),
        showlegend=False
    )
    return fig