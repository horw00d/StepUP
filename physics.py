import numpy as np
from scipy.signal import butter, filtfilt
from sqlalchemy import select
from models import Footstep
from database import engine, Session
from config import SENSOR_AREA_M2, SENSOR_SIDE_CM, SAMPLING_FREQ


def safe_filtfilt(b, a, signal):
    """applies filtfilt, bypassing if the array is too short."""
    padlen = 3 * max(len(a), len(b))
    if len(signal) <= padlen:
        return signal
    return filtfilt(b, a, signal)


def get_batch_physics(step_ids):
    """
    reads DB once, opens the .npz file once,
    and uses pure NumPy Vectorization to process
    """
    if not step_ids:
        return []

    all_metrics = []

    # 1 fetch all steps in a single DB query
    with Session(engine) as session:
        stmt = select(Footstep).where(Footstep.id.in_(step_ids))
        steps = session.scalars(stmt).all()

        if not steps:
            return []

        steps_by_file = {}
        for s in steps:
            fp = s.trial.file_path
            if fp not in steps_by_file:
                steps_by_file[fp] = []
            steps_by_file[fp].append(s)

    # 2 open each file once
    for file_path, file_steps in steps_by_file.items():
        try:
            with np.load(file_path) as data:
                main_tensor = data["arr_0"] if "arr_0" in data else None

                # 3 process each step
                for step in file_steps:
                    idx = step.footstep_index
                    tensor = (
                        main_tensor[idx] if main_tensor is not None else data[str(idx)]
                    )

                    # 1 calculate GRF for all frames at once
                    raw_grf = np.sum(tensor, axis=(1, 2))
                    frames, height, width = tensor.shape

                    # 2 create coordinate grids
                    x_coords, y_coords = np.meshgrid(
                        np.arange(width), np.arange(height)
                    )

                    # 3 multiply the entire 3D tensor by the 2D grids instantly
                    weighted_x_sum = np.sum(tensor * x_coords, axis=(1, 2))
                    weighted_y_sum = np.sum(tensor * y_coords, axis=(1, 2))

                    # 4 divide by GRF safely (ignore division by zero warnings)
                    with np.errstate(divide="ignore", invalid="ignore"):
                        cop_ml = np.where(raw_grf > 0, weighted_x_sum / raw_grf, 0.0)
                        cop_ap = np.where(raw_grf > 0, weighted_y_sum / raw_grf, 0.0)

                    # data cleaning
                    mask = raw_grf > 0
                    if np.any(mask):
                        cop_ml = cop_ml - np.mean(cop_ml[mask])
                        cop_ap = cop_ap - np.mean(cop_ap[mask])

                    # data filtering
                    order = 2
                    cutoff = 20
                    nyquist = 0.5 * SAMPLING_FREQ
                    normal_cutoff = cutoff / nyquist
                    b, a = butter(order, normal_cutoff, btype="low", analog=False)

                    grf_filtered = safe_filtfilt(b, a, raw_grf)
                    cop_ml_filtered = safe_filtfilt(b, a, cop_ml)
                    cop_ap_filtered = safe_filtfilt(b, a, cop_ap)

                    # unit conversion-
                    grf_final = grf_filtered * 1000 * SENSOR_AREA_M2
                    cop_ml_final = cop_ml_filtered * SENSOR_SIDE_CM
                    cop_ap_final = cop_ap_filtered * SENSOR_SIDE_CM

                    all_metrics.append(
                        {
                            "time_pct": np.linspace(0, 100, len(grf_final)),
                            "grf": grf_final,
                            "cop_ml": cop_ml_final,
                            "cop_ap": cop_ap_final,
                            "step_id": step.id,
                        }
                    )

        except Exception as e:
            print(f"CRITICAL ERROR processing file {file_path}: {e}")

    return all_metrics


def get_footstep_physics(footstep_id):
    """Fallback single-step wrapper referencing the new optimized batch function"""
    result = get_batch_physics([footstep_id])
    return result[0] if result else None


def compute_tensor_physics(tensor):
    """
    PURE FUNCTION: Takes a raw 3D numpy tensor (Frames, Height, Width)
    and returns a dictionary of computed scalar metrics and 1D arrays.
    """
    try:
        raw_grf = np.sum(tensor, axis=(1, 2))
        frames, height, width = tensor.shape

        # Coordinate grids
        x_coords, y_coords = np.meshgrid(np.arange(width), np.arange(height))

        # Vectorized COP calculation
        weighted_x_sum = np.sum(tensor * x_coords, axis=(1, 2))
        weighted_y_sum = np.sum(tensor * y_coords, axis=(1, 2))

        with np.errstate(divide="ignore", invalid="ignore"):
            cop_ml = np.where(raw_grf > 0, weighted_x_sum / raw_grf, 0.0)
            cop_ap = np.where(raw_grf > 0, weighted_y_sum / raw_grf, 0.0)

        # Data Cleaning
        mask = raw_grf > 0
        if np.any(mask):
            cop_ml = cop_ml - np.mean(cop_ml[mask])
            cop_ap = cop_ap - np.mean(cop_ap[mask])

        # Filtering
        order = 2
        cutoff = 20
        nyquist = 0.5 * SAMPLING_FREQ
        normal_cutoff = cutoff / nyquist
        b, a = butter(order, normal_cutoff, btype="low", analog=False)

        grf_filtered = safe_filtfilt(b, a, raw_grf)
        cop_ml_filtered = safe_filtfilt(b, a, cop_ml)
        cop_ap_filtered = safe_filtfilt(b, a, cop_ap)

        # Unit Conversion
        grf_final = grf_filtered * 1000 * SENSOR_AREA_M2
        cop_ml_final = cop_ml_filtered * SENSOR_SIDE_CM
        cop_ap_final = cop_ap_filtered * SENSOR_SIDE_CM

        # Generate time percentage array
        time_pct = np.linspace(0, 100, len(grf_final))

        return {
            "peak_grf": float(np.max(grf_final)) if len(grf_final) > 0 else 0.0,
            "stance_duration_frames": int(frames),
            "time_pct_array": time_pct.tolist(),  # Python lists for JSON serialization
            "grf_array": grf_final.tolist(),
            "cop_ml_array": cop_ml_final.tolist(),
            "cop_ap_array": cop_ap_final.tolist(),
        }
    except Exception as e:
        print(f"      -> Math Error on tensor: {e}")
        return None
