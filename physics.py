import numpy as np
import traceback
from scipy.signal import butter, filtfilt # new import from aaron's notebook
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from models import Footstep, Trial
from database import engine, Session

SENSOR_AREA_M2 = 2.5e-5 # (0.5cm * 0.5cm) in m^2
SENSOR_SIDE_CM = 0.5 # 5mm
SAMPLING_FREQ = 100 # 100 Hz (from notebook)

def get_footstep_physics(footstep_id):
    
    with Session(engine) as session:
        step = session.get(Footstep, footstep_id)
        if not step:
            print("ERROR: Footstep not found in DB")
            return None
        
        try:
            file_path = step.trial.file_path
            idx = step.footstep_index
            
            with np.load(file_path) as data:
                # Load Tensor
                if 'arr_0' in data:
                    tensor = data['arr_0'][idx]
                else:
                    str_idx = str(idx)
                    if str_idx in data:
                        tensor = data[str_idx]
                    else:
                        print(f"ERROR: Key '{str_idx}' not found.")
                        return None

                # calculate raw time series
                # calculate in raw units first, then filter, then convert to physics units
                
                # GRF (sum of pressure)
                # shape: (frames,)
                raw_grf = np.sum(tensor, axis=(1, 2))

                # COP (weighted average of indices)
                frames, height, width = tensor.shape
                x_coords, y_coords = np.meshgrid(np.arange(width), np.arange(height))
                
                cop_ml_indices = [] 
                cop_ap_indices = []

                for t in range(frames):
                    frame_pressure = tensor[t]
                    total_p = raw_grf[t]
                    
                    if total_p == 0:
                        # swing phase (foot in air)
                        cop_ml_indices.append(np.nan)
                        cop_ap_indices.append(np.nan)
                    else:
                        # weighted average of pixel indicies
                        c_x = np.sum(x_coords * frame_pressure) / total_p
                        c_y = np.sum(y_coords * frame_pressure) / total_p
                        
                        cop_ml_indices.append(c_x)
                        cop_ap_indices.append(c_y)

                # convert lists to numpy arrays for processing
                cop_ml = np.array(cop_ml_indices)
                cop_ap = np.array(cop_ap_indices)

                # 2. Data Cleaning (Research Methodology)
                
                # A. handle NaNs (replace with 0 or mean to allow filtering)
                cop_ml[np.isnan(cop_ml)] = 0
                cop_ap[np.isnan(cop_ap)] = 0
                
                # B. Mean Centering (Crucial for COP Trajectory shape)
                # "Center the time series so COP is with respect to foot center"
                # We use nanmean to ignore the swing phase zeros if possible, 
                # but since we zeroed them, we just center the active part.
                # Ideally we center based on the non-zero parts.
                mask = raw_grf > 0
                if np.any(mask):
                    cop_ml_center = np.mean(cop_ml[mask])
                    cop_ap_center = np.mean(cop_ap[mask])
                    cop_ml = cop_ml - cop_ml_center
                    cop_ap = cop_ap - cop_ap_center

                # 3. Filtering (btterworth low-pass)
                # "2nd order low-pass butterworth filter with a cut-off frequency of 20Hz"
                order = 2
                cutoff = 20
                nyquist = 0.5 * SAMPLING_FREQ
                normal_cutoff = cutoff / nyquist
                b, a = butter(order, normal_cutoff, btype='low', analog=False)

                # Apply filter (filtfilt applies it forward and backward for zero phase shift)
                # we filter GRF and both COP axes
                grf_filtered = filtfilt(b, a, raw_grf)
                cop_ml_filtered = filtfilt(b, a, cop_ml)
                cop_ap_filtered = filtfilt(b, a, cop_ap)

                # 4. Unit Conversion
                
                # GRF: kPa -> Newtons
                # Formula: GRF(N) = 1000 * Area(m2) * Pressure(kPa)
                grf_final = grf_filtered * 1000 * SENSOR_AREA_M2

                # COP: Indices -> Centimeters
                # Formula: Index * 0.5 cm
                cop_ml_final = cop_ml_filtered * SENSOR_SIDE_CM
                cop_ap_final = cop_ap_filtered * SENSOR_SIDE_CM
                
                return {
                    "time_pct": np.linspace(0, 100, len(grf_final)),
                    "grf": grf_final,
                    "cop_ml": cop_ml_final,
                    "cop_ap": cop_ap_final,
                    "step_id": step.footstep_index
                }

        except Exception:
            print("Critical exception in physics module:")
            print(traceback.format_exc())
            return None