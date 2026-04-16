from config import (
    _STANDARD_BGCOLOR,
    _STANDARD_MARGIN_SM,
    DESIRED_HOVER_COLS,
    NO_COLOR_SENTINEL,
)


def generate_dynamic_hover_data(df):
    """
    Dynamically generates Plotly hover_data dictionary.
    Includes keys that exist in the DataFrame, prevents Plotly validation errors.
    """
    # List all the columns you ever want to see in a tooltip, in the order you want them
    desired_hover_cols = DESIRED_HOVER_COLS

    # Build dictionary dynamically: only add the column if it survived the aggregation
    return {col: True for col in desired_hover_cols if col in df.columns}


def get_custom_data(df):
    """
    returns first 3 indices of Plotly's customdata array.
    guarantees index 0=participant, 1=footwear, 2=speed for the Bridge callback,
    padding with None if the column was removed during aggregation.
    """
    return [
        df["participant_id"] if "participant_id" in df.columns else [None] * len(df),
        df["footwear"] if "footwear" in df.columns else [None] * len(df),
        df["speed"] if "speed" in df.columns else [None] * len(df),
    ]


def resolve_color_arg(color_col: str) -> str | None:
    """
    Converts the UI's no-color sentinel value into a Python None,
    which Plotly interprets as 'do not color by any column'.
    """
    return None if color_col == NO_COLOR_SENTINEL else color_col


def apply_cross_trial_layout(fig, x_col: str, y_col: str, color_col: str):
    """
    Applies standard axis labels, margins, background, and legend formatting
    shared across all cross-trial distribution plots.
    """

    def _fmt(col):
        return col.replace("_", " ").title() if col else ""

    fig.update_layout(
        margin=_STANDARD_MARGIN_SM,
        plot_bgcolor=_STANDARD_BGCOLOR,
        legend_title_text=(
            color_col.capitalize()
            if color_col and color_col != NO_COLOR_SENTINEL
            else ""
        ),
        xaxis_title=_fmt(x_col),
        yaxis_title=_fmt(y_col),
    )
    return fig
