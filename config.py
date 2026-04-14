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
    # Kinetic Metrics
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
