import re
import pandas as pd
import numpy as np
from config import (
    ALLOWED_COLUMNS,
    ALLOWED_KEYWORDS,
    TRIAL_GROUP_KEYS,
    PARTICIPANT_GROUP_KEYS,
)


def apply_advanced_query(df, query_string):
    """
    Executes a free-form Boolean query string against a DataFrame securely.
    Returns: (filtered_df: pd.DataFrame, error_message: str)
    """
    if df.empty or not query_string:
        return df, ""

    is_valid, validation_msg = validate_query_string(query_string)
    if not is_valid:
        return df, validation_msg

    try:
        # Executes the string logic in-memory
        filtered_df = df.query(query_string)
        return filtered_df, ""
    except Exception as e:
        # Catches syntax or Pandas evaluation errors
        return df, f"Execution Error: {e}"


# helper function to apply all filters in one place
def filter_dataframe(df, sides, outliers, tiles, passes, query_string=None):
    """
    (Phase 1 Legacy) Applies standard UI filters and advanced queries.
    """
    error_msg = ""
    if df.empty:
        return df, error_msg

    # 1. Standard UI Filters
    if sides:
        df = df[df["side"].isin(sides)]
    if outliers:
        df = df[df["is_outlier"].isin(outliers)]
    if tiles:
        df = df[df["tile_id"].isin(tiles)]
    if passes:
        df = df[df["pass_id"].isin(passes)]

    # 2. Advanced Query Builder Execution (Refactored)
    if query_string:
        df, error_msg = apply_advanced_query(df, query_string)

    return df, error_msg


def validate_query_string(query_string):
    """
    Validates a free-form query string against a strict allowlist.
    Returns: (is_valid: bool, error_message: str)
    """
    # 1. Handle empty queries gracefully
    if not query_string or not query_string.strip():
        return True, ""

    # 2. Check for illegal characters
    # We only allow alphanumeric, spaces, quotes, standard math/logic operators, and brackets.
    # Anything else (like ;, @, $, or system path slashes) triggers an immediate failure.
    if re.search(r'[^a-zA-Z0-9_\s><=!()[\]\'".,-]', query_string):
        return False, "Query contains illegal characters."

    # 3. Isolate variables from string literals
    # We temporarily remove text inside quotes (e.g., 'Left', "Right")
    # so the validator doesn't flag user-inputted strings as invalid column names.
    query_no_strings = re.sub(r'["\'].*?["\']', "", query_string)

    # 4. Extract all mathematical variables/words
    # Regex \b[a-zA-Z_]\w*\b grabs anything that looks like a variable name
    words = re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", query_no_strings)

    # 5. Verify against the Allowlist
    for word in words:
        if word not in ALLOWED_COLUMNS and word not in ALLOWED_KEYWORDS:
            return (
                False,
                f"Invalid term: '{word}'. Only approved columns and operators are allowed.",
            )

    # 6. Passed all security checks
    return True, ""


# Architectural constants: defines the exact grouping identity for each granularity level.
# These are the columns that define "one row" at that level of analysis.
# IMPORTANT: 'side' is intentionally excluded from PARTICIPANT_GROUP_KEYS.
# At participant granularity, the unit of analysis is the person, not the foot.
# Left and Right steps are averaged together into a single bilateral mean per participant.
# This is a conscious biomechanical decision: symmetric metrics (GRF, stance duration,
# foot dimensions) are valid to average across sides. Laterality analysis belongs
# at footstep or trial granularity where side remains a grouping key.


def apply_data_granularity(df, granularity):
    """
    Aggregates cross-trial DataFrames to prevent statistical pseudoreplication.

    Granularity levels and their units of analysis:
    - 'footstep':    No aggregation. 1 row = 1 footstep. Side is preserved.
    - 'trial':       1 row = 1 walking condition per participant per side.
                     (participant x footwear x speed x side)
    - 'participant': 1 row = 1 person. Left and Right steps are averaged together.
                     Side is not a grouping key at this level by design — see
                     PARTICIPANT_GROUP_KEYS for the architectural rationale.

    All aggregated rows include an 'n_footsteps' column indicating how many
    raw footsteps were averaged to produce that row.

    Args:
        df:          Raw cross-trial DataFrame from fetch_cross_trial_data.
        granularity: One of 'footstep', 'trial', 'participant'.

    Returns:
        Aggregated DataFrame with 'n_footsteps' column always present.
    """
    if df.empty or granularity == "footstep":
        df_out = df.copy()
        # n_footsteps = 1 per row at footstep granularity; column exists at all
        # granularity levels so downstream hover and display logic is unified.
        df_out["n_footsteps"] = 1
        return df_out

    if granularity == "trial":
        group_keys = TRIAL_GROUP_KEYS
    elif granularity == "participant":
        group_keys = PARTICIPANT_GROUP_KEYS
    else:
        print(
            f"Warning: Unknown granularity '{granularity}'. Returning unaggregated data."
        )
        return df

    missing = [col for col in group_keys if col not in df.columns]
    if missing:
        print(
            f"Warning: apply_data_granularity missing expected columns for "
            f"'{granularity}' granularity: {missing}. Returning unaggregated data."
        )
        return df

    try:
        step_counts = df.groupby(group_keys).size().reset_index(name="n_footsteps")
        aggregated_df = df.groupby(group_keys).mean(numeric_only=True).reset_index()
        return pd.merge(aggregated_df, step_counts, on=group_keys)

    except Exception as e:
        print(f"Warning: Granularity aggregation failed for '{granularity}': {e}")
        return df


def apply_dynamic_outliers(df, metric, operator, threshold):
    """
    Dynamically reclassifies the 'is_outlier' column using vectorized NumPy math.
    Extensible design allows checking any metric with any standard operator.
    """
    # Safety checks: if inputs are missing or invalid, return the unmodified DataFrame
    if df.empty or not metric or threshold is None or operator not in ["<", ">"]:
        return df

    # Ensure the requested metric actually exists in the current DataFrame
    if metric not in df.columns:
        return df

    # Build the vectorized boolean mask based on the selected operator
    if operator == "<":
        condition = df[metric] < threshold
    else:
        condition = df[metric] > threshold

    # Overwrite the static database flags with the new dynamic classification
    df["is_outlier"] = np.where(condition, "Outlier", "Normal")

    return df
