ALLOWED_COLUMNS = [
    # Demographic Data
    "participant_id",
    "sex",
    "age",
    "weight_kg",
    "height_cm",
    # Trial Context
    "trial_id",
    "footwear",
    "speed",
    "side",
    "is_outlier",
    # Footstep Context
    "footstep_id",
    "footstep_index",
    "start_frame",
    "r_score",
    # Kinematic Metrics
    "mean_grf",
    "peak_grf",
    "stance_duration_frames",
    "foot_length",
    "foot_width",
    "rotation_angle",
]

# The strict allowlist of logical Python/Pandas operators
ALLOWED_KEYWORDS = {"and", "or", "not", "in"}

# Physics Module
SENSOR_AREA_M2 = 2.5e-5
SENSOR_SIDE_CM = 0.5
SAMPLING_FREQ = 100

# Data Module
SENSOR_SIZE = 0.005
TILE_SIZE = 0.6

# define standard colors for consistency across app
COLOUR_MAP = {
    "Left": "#1f77b4",  # Muted Blue
    "Right": "#2ca02c",  # Muted Green
    "Normal": "#7f7f7f",  # Gray
    "Outlier": "#d62728",  # Red
}

NO_COLOR_SENTINEL = "none"


class Granularity:
    FOOTSTEP = "footstep"
    TRIAL = "trial"
    PARTICIPANT = "participant"


# config.py
GRANULARITY_COMPATIBLE_GROUPS = {
    "footstep": {"footwear", "speed", "sex", "side", "participant_id", "is_outlier"},
    "trial": {"footwear", "speed", "sex", "side", "participant_id", "is_outlier"},
    "participant": {"sex", "side", "participant_id", "is_outlier"},
}

TRIAL_GROUP_KEYS = ["participant_id", "footwear", "speed", "sex", "side", "is_outlier"]
PARTICIPANT_GROUP_KEYS = ["participant_id", "sex", "side", "is_outlier"]

DESIRED_HOVER_COLS = [
    "participant_id",
    "side",
    "footwear",
    "speed",
    "is_outlier",
    "n_footsteps",
]

EXTERNAL_STYLESHEETS = ["https://codepen.io/chriddyp/pen/bWLwgP.css"]

FEATURE_OPTIONS = [
    {"label": "Footstep Sequence ID", "value": "footstep_index"},
    {"label": "Start Frame (Time)", "value": "start_frame"},
    {"label": "R-Score (Quality)", "value": "r_score"},
    {"label": "Mean GRF (Pressure)", "value": "mean_grf"},
    {"label": "Peak GRF (Pressure)", "value": "peak_grf"},
    {"label": "Stance Duration", "value": "stance_duration_frames"},
    {"label": "Foot Length", "value": "foot_length"},
    {"label": "Foot Width", "value": "foot_width"},
    {"label": "Rotation Angle", "value": "rotation_angle"},
]

CT_GROUP_OPTIONS = [
    {"label": "Footwear Type", "value": "footwear"},
    {"label": "Walking Speed", "value": "speed"},
    {"label": "Biological Sex", "value": "sex"},
    {"label": "Participant ID", "value": "participant_id"},
]

CT_COLOR_OPTIONS = [
    {"label": "None", "value": NO_COLOR_SENTINEL},
    {"label": "Footwear Type", "value": "footwear"},
    {"label": "Walking Speed", "value": "speed"},
    {"label": "Biological Sex", "value": "sex"},
    {"label": "Side (Left/Right)", "value": "side"},
    {"label": "Outlier Status", "value": "is_outlier"},
]

# LAYOUT CONSTANTS

# Options for the single-trial Color By dropdown.
ST_COLOR_OPTIONS = [
    {"label": "Side (L/R)", "value": "side"},
    {"label": "Outlier Status", "value": "is_outlier"},
    {"label": "Tile ID", "value": "tile_id"},
    {"label": "Pass ID", "value": "pass_id"},
]

# ── Internal constants ─────────────────────────────────────────────────────────
_VALID_TAB_NAMES = frozenset({"single", "cross"})

# Maps tab_name to the string prefix used in non-pattern-matched component IDs.
_TAB_PREFIX = {"single": "st", "cross": "ct"}

_QUERY_PLACEHOLDER = {
    "single": "e.g., peak_grf > 800 and is_outlier == 'Normal'",
    "cross": "e.g., age >= 60 and peak_grf < 600",
}

_APPLY_BTN_ID = {
    "single": "st-apply-query-btn",
    "cross": "ct-apply-query-btn",
}

# GRAPHICS CONSTANTS

_GHOST_LINE_COLOR = "lightgrey"
_GHOST_LINE_WIDTH = 1
_GHOST_LINE_OPACITY = 0.3

_SELECTED_GRF_COLOR = "#007BFF"
_SELECTED_GRF_WIDTH = 3

_HEATMAP_NOISE_FLOOR_KPA = 10
_HEATMAP_FIXED_MAX_KPA = 800

_LEGEND_OVERFLOW_THRESHOLD = 5  # categories above this move the legend to the right

_STANDARD_MARGIN_SM = dict(l=20, r=20, t=30, b=20)
_STANDARD_MARGIN_LG = dict(l=40, r=20, t=40, b=40)
_STANDARD_BGCOLOR = "#f9f9f9"
