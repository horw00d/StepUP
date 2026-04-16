import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from config import (
    _HEATMAP_FIXED_MAX_KPA,
    _HEATMAP_NOISE_FLOOR_KPA,
    _LEGEND_OVERFLOW_THRESHOLD,
    _SELECTED_GRF_COLOR,
    _SELECTED_GRF_WIDTH,
    _STANDARD_BGCOLOR,
    _STANDARD_MARGIN_LG,
    _STANDARD_MARGIN_SM,
    COLOUR_MAP,
)
from graphics.single_trial_helpers import (
    compute_pressure_histogram_data,
    render_ghost_traces,
)


# WALKWAY PLOT
def create_walkway_plot(footsteps, selected_step_id=None):
    SENSOR_SIZE_M = 0.005
    TILE_WIDTH_M = 0.6

    fig = go.Figure()

    # 1. Build tile background shapes
    tiles = []
    for x in [0, TILE_WIDTH_M]:
        for y in [i * TILE_WIDTH_M for i in range(6)]:
            tiles.append(
                dict(
                    type="rect",
                    x0=x,
                    x1=x + TILE_WIDTH_M,
                    y0=y,
                    y1=y + TILE_WIDTH_M,
                    line=dict(color="#dddddd", width=1),
                    fillcolor="white",
                    layer="below",
                )
            )

    # 2. Build footstep box shapes and invisible hover traces
    box_shapes = []
    for step in footsteps:
        if step.box_xmin is None:
            continue

        x0, x1 = step.box_xmin * SENSOR_SIZE_M, step.box_xmax * SENSOR_SIZE_M
        y0, y1 = step.box_ymin * SENSOR_SIZE_M, step.box_ymax * SENSOR_SIZE_M
        is_selected = step.id == selected_step_id

        if is_selected:
            color, opacity, line_width = "#FF0000", 0.8, 3
        else:
            color = "#1f77b4" if step.side == "Left" else "#2ca02c"
            opacity, line_width = 0.4, 1

        box_shapes.append(
            dict(
                type="rect",
                x0=x0,
                x1=x1,
                y0=y0,
                y1=y1,
                line=dict(color=color, width=line_width),
                fillcolor=color,
                opacity=opacity,
                layer="above",
            )
        )

        fig.add_trace(
            go.Scatter(
                x=[(x0 + x1) / 2],
                y=[(y0 + y1) / 2],
                mode="markers",
                marker=dict(opacity=0),
                customdata=[[step.id, step.tile_id, step.pass_id, step.footstep_index]],
                hovertemplate=(
                    "<b>Step %{customdata[3]}</b><br>"
                    "TileID: %{customdata[1]}<br>"
                    "Pass: %{customdata[2]}<br>"
                    "ID: %{customdata[0]}<extra></extra>"
                ),
                showlegend=False,
            )
        )

    # 3. Single layout call with all shapes combined
    fig.update_layout(
        shapes=tiles + box_shapes,
        title="Spatial Footstep Map",
        xaxis=dict(title="Width (m)", range=[-0.1, 1.3], scaleanchor="y", scaleratio=1),
        yaxis=dict(title="Length (m)", range=[-0.1, 3.7]),
        margin=dict(l=20, r=20, t=40, b=20),
        plot_bgcolor=_STANDARD_BGCOLOR,
        clickmode="event+select",
    )
    return fig


# SCATTER PLOT
def create_scatter_plot(df, x_col, y_col, color_col, selected_step_id=None):
    fig = go.Figure()

    if df.empty:
        fig.update_layout(title="No Data")
        return fig

    # Guard: surface configuration errors clearly rather than raising KeyError
    for col in (x_col, y_col, color_col):
        if col not in df.columns:
            fig.update_layout(title=f"Configuration Error: column '{col}' not found")
            return fig

    groups = df.groupby(color_col)

    for name, group in groups:
        preset_color = COLOUR_MAP.get(name, None)
        marker_settings = dict(size=10, opacity=0.7)
        if preset_color:
            marker_settings["color"] = preset_color

        group = group.reset_index(drop=True)
        fig.add_trace(
            go.Scatter(
                x=group[x_col],
                y=group[y_col],
                mode="markers",
                name=str(name),
                marker=marker_settings,
                customdata=group[["id", "footstep_index"]].values.tolist(),
                hovertemplate=f"{x_col}: %{{x}}<br>{y_col}: %{{y}}<br>Step: %{{customdata[1]}}<extra></extra>",
            )
        )

    if selected_step_id:
        row = df[df["id"] == selected_step_id]
        if not row.empty:
            fig.add_trace(
                go.Scatter(
                    x=row[x_col],
                    y=row[y_col],
                    mode="markers",
                    marker=dict(
                        color="red", size=15, line=dict(width=2, color="black")
                    ),
                    name="Selected",
                    hoverinfo="skip",
                )
            )

    legend_config = (
        dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02)
        if len(groups) > _LEGEND_OVERFLOW_THRESHOLD
        else dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    fig.update_layout(
        title=f"2D Feature Analysis: {x_col} vs {y_col}",
        clickmode="event+select",
        margin=_STANDARD_MARGIN_SM,
        legend=legend_config,
    )
    return fig


# RUG PLOT
def create_rug_plot(df, rug_col, color_col, selected_step_id=None):
    fig = go.Figure()

    if df.empty:
        fig.update_layout(title="No Data")
        return fig

    # Guard: surface configuration errors clearly rather than raising KeyError
    for col in (rug_col, color_col):
        if col not in df.columns:
            fig.update_layout(title=f"Configuration Error: column '{col}' not found")
            return fig

    groups = df.groupby(color_col)

    for name, group in groups:
        marker_color = COLOUR_MAP.get(name, None)
        group = group.reset_index(drop=True)
        fig.add_trace(
            go.Scatter(
                x=group[rug_col],
                y=[0] * len(group),
                mode="markers",
                name=str(name),
                marker=dict(
                    symbol="line-ns-open",
                    size=10,
                    line=dict(width=2),
                    color=marker_color,
                ),
                customdata=group[["id", "footstep_index"]].values.tolist(),
                hovertemplate=f"{rug_col}: %{{x}}<br>Step: %{{customdata[1]}}<extra></extra>",
            )
        )

    if selected_step_id:
        row = df[df["id"] == selected_step_id]
        if not row.empty:
            fig.add_trace(
                go.Scatter(
                    x=row[rug_col],
                    y=[0] * len(row),
                    mode="markers",
                    marker=dict(
                        color="red",
                        size=14,
                        symbol="line-ns-open",
                        line=dict(width=4),
                    ),
                    name="Selected",
                    hoverinfo="skip",
                )
            )

    fig.update_layout(
        title=f"1D Distribution: {rug_col}",
        clickmode="event+select",
        margin=_STANDARD_MARGIN_SM,
        yaxis=dict(visible=False, range=[-0.5, 0.5]),
        height=150,
        showlegend=False,
    )
    return fig


def get_empty_physics_layout(title="No Data"):
    """Helper to return a clean empty state for physics plots."""
    return go.Layout(
        title=title,
        xaxis={"visible": False},
        yaxis={"visible": False},
        annotations=[{"text": "Select a step or enable Overlay", "showarrow": False}],
        plot_bgcolor="white",
    )


def create_grf_plot(all_metrics, selected_step_id=None, overlay_mode=False):
    """
    Generates the Vertical Ground Reaction Force (GRF) plot.
    Supports 'Ghost Line' overlay for contextual variance analysis.
    """
    if not all_metrics:
        return go.Figure(layout=get_empty_physics_layout("Vertical GRF"))

    fig = go.Figure()

    if overlay_mode:
        selected_metric = render_ghost_traces(
            fig, all_metrics, selected_step_id, x_key="time_pct", y_key="grf"
        )
    else:
        selected_metric = next(
            (m for m in all_metrics if m["step_id"] == selected_step_id), None
        )

    if selected_metric:
        fig.add_trace(
            go.Scatter(
                x=selected_metric["time_pct"],
                y=selected_metric["grf"],
                mode="lines",
                line=dict(color=_SELECTED_GRF_COLOR, width=_SELECTED_GRF_WIDTH),
                name=f"Step {selected_metric['step_id']}",
                hovertemplate="Stance: %{x:.1f}%<br>Force: %{y:.1f} N<extra></extra>",
            )
        )

    title_text = (
        f"Vertical GRF (Step {selected_step_id})"
        if selected_step_id
        else "Vertical GRF"
    )
    fig.update_layout(
        title=title_text,
        xaxis_title="% Stance",
        yaxis_title="Force (N)",
        margin=_STANDARD_MARGIN_LG,
        plot_bgcolor=_STANDARD_BGCOLOR,
        showlegend=False,
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

    if overlay_mode:
        selected_metric = render_ghost_traces(
            fig, all_metrics, selected_step_id, x_key="cop_ml", y_key="cop_ap"
        )
    else:
        selected_metric = next(
            (m for m in all_metrics if m["step_id"] == selected_step_id), None
        )

    if selected_metric:
        fig.add_trace(
            go.Scatter(
                x=selected_metric["cop_ml"],
                y=selected_metric["cop_ap"],
                mode="lines+markers",
                marker=dict(
                    size=5,
                    color=selected_metric["time_pct"],
                    colorscale="Viridis",
                    showscale=True,
                    colorbar=dict(title="% Stance", thickness=10, len=0.8),
                ),
                line=dict(color="black", width=1),
                name=f"Step {selected_metric['step_id']}",
                hovertemplate="ML: %{x:.2f} cm<br>AP: %{y:.2f} cm<extra></extra>",
            )
        )

    fig.update_layout(
        title="COP Trajectory",
        xaxis_title="Mediolateral (cm)",
        yaxis_title="Anteroposterior (cm)",
        yaxis=dict(scaleanchor="x", scaleratio=1),
        margin=_STANDARD_MARGIN_LG,
        plot_bgcolor=_STANDARD_BGCOLOR,
        showlegend=False,
    )
    return fig


def create_pressure_heatmap(matrix, step_id, z_min, z_max):
    """
    Builds the pressure heatmap figure for a single footstep.
    Separated from the histogram so each chart has a single responsibility.
    """
    heatmap_fig = go.Figure(
        data=go.Heatmap(
            z=matrix,
            colorscale="Jet",
            zmin=z_min,
            zmax=z_max,
            hovertemplate="X: %{x}<br>Y: %{y}<br>Pressure: %{z:.1f} kPa<extra></extra>",
        )
    )
    heatmap_fig.add_trace(
        go.Contour(
            z=matrix,
            contours=dict(
                type="constraint",
                operation=">=",
                value=_HEATMAP_NOISE_FLOOR_KPA,
                coloring="none",
            ),
            line=dict(color="white", width=2, dash="solid"),
            showlegend=False,
            hoverinfo="skip",
        )
    )
    heatmap_fig.update_layout(
        title=f"Pressure Map (Step {step_id}) - Peak: {z_max:.1f} kPa",
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False, scaleanchor="x"),
        plot_bgcolor="black",
    )
    return heatmap_fig


def create_pressure_histogram(bin_centers, counts, z_min, z_max):
    """
    Builds the load-distribution histogram figure from pre-computed bin data.
    Separated from the heatmap so each chart has a single responsibility.
    """
    hist_fig = go.Figure(
        data=go.Bar(
            x=bin_centers,
            y=counts,
            width=5,
            marker=dict(
                color=bin_centers,
                cmin=z_min,
                cmax=z_max,
                colorscale="Jet",
                line=dict(width=0),
            ),
            hovertemplate="Pressure: %{x} kPa<br>Sensors: %{y}<extra></extra>",
        )
    )
    hist_fig.update_layout(
        title=f"Load Distribution (> {_HEATMAP_NOISE_FLOOR_KPA} kPa)",
        xaxis_title="Pressure (kPa)",
        yaxis_title="Count (Sensors)",
        margin=_STANDARD_MARGIN_LG,
        showlegend=False,
        bargap=0,
    )
    return hist_fig


def create_heatmap_and_histogram(matrix, step_id, dynamic_scale=True):
    """
    Delegates to the focused helpers above. Callers that only need one of the
    two charts should call create_pressure_heatmap / create_pressure_histogram
    directly rather than discarding half of this tuple.
    """
    _empty_layout = go.Layout(
        title="No Data", xaxis={"visible": False}, yaxis={"visible": False}
    )
    if matrix is None:
        empty = go.Figure(layout=_empty_layout)
        return empty, empty

    z_min = 0
    current_max = float(np.max(matrix))
    z_max = current_max if dynamic_scale else _HEATMAP_FIXED_MAX_KPA

    heatmap_fig = create_pressure_heatmap(matrix, step_id, z_min, z_max)

    bin_centers, counts = compute_pressure_histogram_data(
        matrix, _HEATMAP_NOISE_FLOOR_KPA, current_max
    )
    if bin_centers is None:
        hist_fig = go.Figure(
            layout=go.Layout(title=f"No pressure > {_HEATMAP_NOISE_FLOOR_KPA} kPa")
        )
    else:
        hist_fig = create_pressure_histogram(bin_centers, counts, z_min, z_max)

    return heatmap_fig, hist_fig
