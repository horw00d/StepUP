import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def raw_footstep_df():
    """
    Cross-trial DataFrame at footstep granularity with multiple footsteps
    per trial group so that trial/participant aggregation actually collapses rows.

    Structure:
      - 2 participants (001, 002)
      - Each has 1 trial (one footwear × speed combination)
      - Each trial has 4 footsteps (2 Left, 2 Right)
      - 8 footstep rows total
      - trial granularity  = 4 rows  (participant × side × is_outlier groups)
      - participant granularity = 2 rows (one per participant, sides averaged)
    """
    return pd.DataFrame(
        {
            "footstep_id": [1, 2, 3, 4, 5, 6, 7, 8],
            "participant_id": ["001", "001", "001", "001", "002", "002", "002", "002"],
            "sex": ["M", "M", "M", "M", "F", "F", "F", "F"],
            "age": [25, 25, 25, 25, 30, 30, 30, 30],
            "weight_kg": [75.0, 75.0, 75.0, 75.0, 60.0, 60.0, 60.0, 60.0],
            "footwear": ["BF", "BF", "BF", "BF", "SH", "SH", "SH", "SH"],
            "speed": ["W1", "W1", "W1", "W1", "W2", "W2", "W2", "W2"],
            "side": [
                "Left",
                "Left",
                "Right",
                "Right",
                "Left",
                "Left",
                "Right",
                "Right",
            ],
            "is_outlier": [
                "Normal",
                "Normal",
                "Normal",
                "Normal",
                "Normal",
                "Normal",
                "Normal",
                "Normal",
            ],
            "mean_grf": [500.0, 505.0, 510.0, 515.0, 480.0, 485.0, 490.0, 495.0],
            "peak_grf": [800.0, 810.0, 820.0, 830.0, 760.0, 770.0, 780.0, 790.0],
            "stance_duration_frames": [50, 51, 52, 53, 48, 49, 50, 51],
            "foot_length": [26.0, 26.0, 26.0, 26.0, 24.0, 24.0, 24.0, 24.0],
            "foot_width": [10.0, 10.0, 10.0, 10.0, 9.0, 9.0, 9.0, 9.0],
            "rotation_angle": [5.0, 5.5, -5.0, -5.5, 3.0, 3.5, -3.0, -3.5],
            "r_score": [0.95, 0.93, 0.90, 0.92, 0.88, 0.85, 0.87, 0.89],
            "trial_id": [1, 1, 1, 1, 2, 2, 2, 2],
            "footstep_index": [0, 1, 2, 3, 0, 1, 2, 3],
            "start_frame": [10, 62, 114, 166, 10, 59, 108, 157],
        }
    )


@pytest.fixture
def single_trial_df():
    """
    Minimal single-trial DataFrame matching fetch_trial_data output.
    Includes the extra columns that the single-trial tab uses.
    """
    return pd.DataFrame(
        {
            "id": [10, 11, 12, 13, 14, 15],
            "footstep_index": [0, 1, 2, 3, 4, 5],
            "start_frame": [10, 62, 114, 166, 218, 270],
            "side": ["Left", "Right", "Left", "Right", "Left", "Right"],
            "is_outlier": [
                "Normal",
                "Normal",
                "Outlier",
                "Normal",
                "Normal",
                "Outlier",
            ],
            "tile_id": [3, 4, 3, 4, 5, 6],
            "pass_id": [1, 1, 2, 2, 3, 3],
            "mean_grf": [500.0, 510.0, 480.0, 490.0, 520.0, 530.0],
            "peak_grf": [800.0, 820.0, 760.0, 780.0, 850.0, 870.0],
            "stance_duration_frames": [50, 52, 48, 49, 55, 56],
            "foot_length": [26.0, 26.0, 24.0, 24.0, 27.0, 27.0],
            "foot_width": [10.0, 10.0, 9.0, 9.0, 11.0, 11.0],
            "rotation_angle": [5.0, -5.0, 3.0, -3.0, 6.0, -6.0],
            "r_score": [0.95, 0.90, 0.70, 0.88, 0.92, 0.60],
        }
    )


@pytest.fixture
def physics_metrics():
    """
    A list of physics metric dicts as returned by data.fetch_physics_arrays.
    Uses synthetic sinusoidal waveforms to keep the fixture self-contained.
    """
    t = np.linspace(0, 100, 101).tolist()

    def _sine_grf(scale=800):
        return (np.sin(np.linspace(0, np.pi, 101)) * scale).tolist()

    def _cop(amplitude=2):
        return (np.linspace(-amplitude, amplitude, 101)).tolist()

    return [
        {
            "step_id": 10,
            "time_pct": t,
            "grf": _sine_grf(800),
            "cop_ml": _cop(2),
            "cop_ap": _cop(5),
        },
        {
            "step_id": 11,
            "time_pct": t,
            "grf": _sine_grf(820),
            "cop_ml": _cop(2),
            "cop_ap": _cop(5),
        },
        {
            "step_id": 12,
            "time_pct": t,
            "grf": _sine_grf(760),
            "cop_ml": _cop(2),
            "cop_ap": _cop(5),
        },
    ]


@pytest.fixture
def small_pressure_matrix():
    """
    8×8 synthetic peak-pressure matrix in kPa.
    Contains values both below and above the noise floor (10 kPa).
    """
    rng = np.random.default_rng(42)
    mat = rng.uniform(0, 500, (8, 8))
    mat[0, 0] = 5.0
    mat[7, 7] = 2.0
    return mat
