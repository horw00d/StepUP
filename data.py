import os
import pandas as pd
import numpy as np
from sqlalchemy import select, distinct
from types import SimpleNamespace
from database import Session, engine
from models import Trial, Footstep, Participant
from config import SENSOR_SIZE, TILE_SIZE
from functools import lru_cache

def get_dropdown_options(model_col):
    """Reusable helper for populating dropdowns."""
    with Session(engine) as session:
        results = session.scalars(select(distinct(model_col)).order_by(model_col)).all()
        return [{'label': str(x), 'value': str(x)} for x in results]

@lru_cache(maxsize=32)
def fetch_trial_data(part, shoe, speed):
    """
    Fetches the Trial and Footsteps, returning a processed DataFrame and the raw steps list.
    """
    with Session(engine) as session:
        # 1. Fetch trial
        stmt = select(Trial).where(Trial.participant_id == part, Trial.footwear == shoe, Trial.speed == speed)
        trial = session.scalar(stmt)
        
        if not trial:
            return None, [], pd.DataFrame() 

        # 2. Get specific columns (Now including new physics scalars)
        stmt = select(
            Footstep.id,
            Footstep.footstep_index,
            Footstep.start_frame,
            Footstep.mean_grf,
            Footstep.r_score,
            Footstep.foot_length,
            Footstep.foot_width,
            Footstep.rotation_angle,
            Footstep.side,
            Footstep.is_outlier,
            Footstep.pass_id,
            Footstep.box_xmin,
            Footstep.box_xmax,
            Footstep.box_ymin,
            Footstep.box_ymax,
            Footstep.peak_grf,
            Footstep.stance_duration_frames
        ).where(Footstep.trial_id == trial.id).order_by(Footstep.footstep_index)
        
        results = session.execute(stmt).all()
        
        # 3. Build dataframe (Keep your existing tile logic exactly the same)
        data_list = []
        steps_list_for_grid = []
        
        for row in results:
            row_dict = dict(row._mapping)
            
            if row.box_xmin is not None:
                x_center = ((row.box_xmin + row.box_xmax) / 2) * SENSOR_SIZE
                y_center = ((row.box_ymin + row.box_ymax) / 2) * SENSOR_SIZE
                
                col = min(1, int(x_center // TILE_SIZE))
                row_idx = min(5, int(y_center // TILE_SIZE))
                tile_id = (row_idx * 2) + col + 1
                
                row_dict['tile_id'] = tile_id
                
                step_obj = SimpleNamespace(**row_dict)
                steps_list_for_grid.append(step_obj)
            else:
                row_dict['tile_id'] = -1 
                steps_list_for_grid.append(SimpleNamespace(**row_dict))

            row_dict['is_outlier'] = "Outlier" if row_dict['is_outlier'] else "Normal"
            data_list.append(row_dict)

        df = pd.DataFrame(data_list)
        return trial, steps_list_for_grid, df

def fetch_physics_arrays(step_ids):
    """
    Fetches the pre-computed JSON physics arrays directly from the database.
    """
    if not step_ids: return []
    
    with Session(engine) as session:
        stmt = select(
            Footstep.id,
            Footstep.time_pct_array,
            Footstep.grf_array,
            Footstep.cop_ml_array,
            Footstep.cop_ap_array
        ).where(Footstep.id.in_(step_ids))
        
        results = session.execute(stmt).all()
        
        metrics = []
        for row in results:
            metrics.append({
                "step_id": row.id,
                "time_pct": row.time_pct_array or [],
                "grf": row.grf_array or [],
                "cop_ml": row.cop_ml_array or [],
                "cop_ap": row.cop_ap_array or []
            })
        return metrics

def fetch_step_by_id(step_id):
    """Fetches a single footstep by ID."""
    with Session(engine) as session:
        return session.get(Footstep, step_id)

def fetch_footstep_matrix(step_id):
    """
    Loads the pre-sharded raw pressure matrix for a specific step.
    Returns: numpy array or None
    """
    try:
        # construct path to sharded data file
        file_path = f"./assets/data/step_{step_id}.npy"
        
        if os.path.exists(file_path):
            return np.load(file_path)
        return None
    except Exception as e:
        print(f"Error loading matrix for step {step_id}: {e}")
        return None

def fetch_pass_options(part, shoe, speed):
    """Fetches unique Pass IDs."""
    trial, steps, _ = fetch_trial_data(part, shoe, speed)
    if not trial: return [], []
    unique_passes = sorted(list(set([s.pass_id for s in steps if s.pass_id is not None])))
    options = [{'label': f"Pass {p}", 'value': p} for p in unique_passes]
    return options, unique_passes