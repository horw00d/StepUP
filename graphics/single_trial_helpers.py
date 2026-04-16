import numpy as np
import plotly.graph_objects as go
from config import _GHOST_LINE_COLOR, _GHOST_LINE_OPACITY, _GHOST_LINE_WIDTH


def render_ghost_traces(fig, all_metrics, selected_step_id, x_key, y_key):
    """
    faded background ghost traces for every metric except the selected step.
    returns selected metric dict, or None if it was not found in the list.
    """
    selected_metric = None
    for m in all_metrics:
        if m["step_id"] == selected_step_id:
            selected_metric = m
            continue
        fig.add_trace(
            go.Scatter(
                x=m[x_key],
                y=m[y_key],
                mode="lines",
                line=dict(color=_GHOST_LINE_COLOR, width=_GHOST_LINE_WIDTH),
                opacity=_GHOST_LINE_OPACITY,
                hoverinfo="skip",
                showlegend=False,
            )
        )
    return selected_metric


def compute_pressure_histogram_data(matrix, noise_floor, z_max):
    """
    Pure data function: filters active pixels and computes histogram bins.

    Extracted from create_heatmap_and_histogram so that the numpy logic
    can be reasoned about and tested independently of any Plotly code.

    Returns (bin_centers, counts) or (None, None) if no active pixels exist.
    """
    flat_data = matrix.flatten()
    active_pixels = flat_data[flat_data > noise_floor]

    if len(active_pixels) == 0:
        return None, None

    bins = np.arange(noise_floor, z_max + 5, 5)
    counts, bin_edges = np.histogram(active_pixels, bins=bins)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    return bin_centers, counts
