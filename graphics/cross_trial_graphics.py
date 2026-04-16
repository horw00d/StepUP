import plotly.graph_objects as go
import plotly.express as px
from config import COLOUR_MAP
from graphics.cross_trial_helpers import (
    apply_cross_trial_layout,
    generate_dynamic_hover_data,
    get_custom_data,
    resolve_color_arg,
)
from graphics.single_trial_graphics import get_empty_physics_layout


def create_box_plot(df, y_col, x_col, color_col):
    if df.empty:
        return go.Figure(layout=get_empty_physics_layout("Box Plot - No Data"))

    fig = px.box(
        df,
        x=x_col,
        y=y_col,
        color=resolve_color_arg(color_col),
        points="all",
        title=f"Distribution of {y_col} by {x_col}",
        color_discrete_map=COLOUR_MAP,
        custom_data=get_custom_data(df),
        hover_data=generate_dynamic_hover_data(df),
    )

    return apply_cross_trial_layout(fig, x_col, y_col, color_col)


def create_violin_plot(df, y_col, x_col, color_col):
    if df.empty:
        return go.Figure(layout=get_empty_physics_layout("Violin Plot - No Data"))

    fig = px.violin(
        df,
        x=x_col,
        y=y_col,
        color=resolve_color_arg(color_col),
        box=True,
        title=f"Density Shape of {y_col} by {x_col}",
        color_discrete_map=COLOUR_MAP,
        custom_data=get_custom_data(df),
        hover_data=generate_dynamic_hover_data(df),
    )

    return apply_cross_trial_layout(fig, x_col, y_col, color_col)


def create_bivariate_scatter_plot(df, y_col, x_col, color_col):
    """
    Generates a Bivariate Scatter Plot to show correlations for twometrics.
    Includes an OLS trendline for instant regression analysis.
    """
    if df.empty:
        return go.Figure(layout=get_empty_physics_layout("Scatter Plot - No Data"))

    fig = px.scatter(
        df,
        x=x_col,
        y=y_col,
        color=resolve_color_arg(color_col),
        trendline="ols",
        title=f"Correlation of {x_col.replace('_', ' ').title()} and {y_col.replace('_', ' ').title()}",
        color_discrete_map=COLOUR_MAP,
        custom_data=get_custom_data(df),
        hover_data=generate_dynamic_hover_data(df),
    )

    return apply_cross_trial_layout(fig, x_col, y_col, color_col)


def create_aggregate_waveform_plot(time_pct, mean_grf, upper_bound, lower_bound):
    """
    Renders a continuous mean waveform surrounded by a shaded standard deviation band.
    """
    if time_pct is None:
        return go.Figure(layout=get_empty_physics_layout("Waveform - No Data"))

    fig = go.Figure()

    # 1 invisible Upper Bound
    fig.add_trace(
        go.Scatter(
            x=time_pct,
            y=upper_bound,
            mode="lines",
            line=dict(width=0),
            showlegend=False,
            hoverinfo="skip",
        )
    )

    # 2 lower Bound (Fills space up to the Upper Bound)
    fig.add_trace(
        go.Scatter(
            x=time_pct,
            y=lower_bound,
            mode="lines",
            line=dict(width=0),
            fill="tonexty",
            fillcolor="rgba(0, 123, 255, 0.2)",
            showlegend=False,
            hoverinfo="skip",
        )
    )

    # 3 Solid Mean Line
    fig.add_trace(
        go.Scatter(
            x=time_pct,
            y=mean_grf,
            mode="lines",
            line=dict(color="rgba(0, 123, 255, 1)", width=3),
            name="Mean GRF",
        )
    )

    fig.update_layout(
        title="Aggregate GRF Waveform (plus minus Std Dev)",
        xaxis_title="% Stance Phase",
        yaxis_title="Ground Reaction Force (N)",
        plot_bgcolor="#f9f9f9",
        margin=dict(l=40, r=20, t=40, b=40),
        showlegend=False,
    )
    return fig
