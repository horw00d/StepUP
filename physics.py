import numpy as np
import traceback
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from models import Footstep, Trial
from database import engine, Session

# --- CONSTANTS ---
SENSOR_AREA_M2 = 2.5e-5  # (0.5cm * 0.5cm)
SENSOR_SIDE_CM = 0.5     # 5mm

def get_footstep_physics(footstep_id):
    
    with Session(engine) as session:
        # 1. Fetch Metadata
        step = session.get(Footstep, footstep_id)
        if not step:
            print("ERROR: Footstep not found in DB")
            return None
        
        # 2. Get File Path
        # We access this OUTSIDE the try block to ensure the DB relationship works
        try:
            file_path = step.trial.file_path
            idx = step.footstep_index
        except Exception as e:
            print("ERROR accessing Trial relationship:")
            print(traceback.format_exc())
            return None

        # 3. Load Raw Tensor
        try:
            with np.load(file_path) as data:
                tensor = None
                
                # Format A: Batch
                if 'arr_0' in data:
                    tensor = data['arr_0'][idx]
                
                # Format B: Fragmented
                else:
                    str_idx = str(idx)
                    
                    if str_idx in data:
                        tensor = data[str_idx]
                    else:
                        print(f"ERROR: Key '{str_idx}' not found in file.")
                        return None

                # 4. Calculate GRF (Equation 1)
                # Sum across spatial axes (1, 2)
                sum_pressure_kpa = np.sum(tensor, axis=(1, 2))
                grf_curve = 1000 * SENSOR_AREA_M2 * sum_pressure_kpa

                # 5. Calculate COP (Equation 2)
                frames, height, width = tensor.shape
                x_coords, y_coords = np.meshgrid(np.arange(width), np.arange(height))
                
                cop_ml = [] 
                cop_ap = [] 

                for t in range(frames):
                    frame_pressure = tensor[t]
                    total_p = np.sum(frame_pressure)
                    
                    if total_p == 0:
                        cop_ml.append(np.nan)
                        cop_ap.append(np.nan)
                    else:
                        # Center of Mass Calculation
                        c_x = (np.sum(x_coords * frame_pressure) / total_p) * SENSOR_SIDE_CM
                        c_y = (np.sum(y_coords * frame_pressure) / total_p) * SENSOR_SIDE_CM
                        
                        cop_ml.append(c_x)
                        cop_ap.append(c_y)

                return {
                    "time_pct": np.linspace(0, 100, len(grf_curve)),
                    "grf": grf_curve,
                    "cop_ml": cop_ml,
                    "cop_ap": cop_ap,
                    "step_id": step.footstep_index
                }

        except Exception:
            print("CRITICAL EXCEPTION IN PHYSICS MODULE:")
            print(traceback.format_exc())
            return None