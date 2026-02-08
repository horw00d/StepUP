import os
import pandas as pd
import numpy as np
from sqlalchemy import select, distinct
from types import SimpleNamespace
from database import Session, engine
from models import Trial, Footstep, Participant

SENSOR_SIZE = 0.005
TILE_SIZE = 0.6

def get_dropdown_options(model_col):
    """Reusable helper for populating dropdowns."""
    with Session(engine) as session:
        results = session.scalars(select(distinct(model_col)).order_by(model_col)).all()
        return [{'label': str(x), 'value': str(x)} for x in results]

def fetch_trial_data(part, shoe, speed):
    """
    Fetches the Trial and Footsteps, returning a processed DataFrame and the raw steps list.
    """
    with Session(engine) as session:
        #1 fetch trial
        stmt = select(Trial).where(Trial.participant_id == part, Trial.footwear == shoe, Trial.speed == speed)
        trial = session.scalar(stmt)
        
        if not trial:
            return None, [], pd.DataFrame() # Return empty DF

        #2 get specific columns as tuples
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
            Footstep.box_ymax
        ).where(Footstep.trial_id == trial.id).order_by(Footstep.footstep_index)
        
        results = session.execute(stmt).all()
        
        #3 build dataframe
        data_list = []
        steps_list_for_grid = []
        
        for row in results:
            row_dict = row._mapping
            
            # DataFrame Dict
            clean_dict = dict(row_dict)
            if row.box_xmin is not None:
                # Convert sensor units to meters
                x_center = ((row.box_xmin + row.box_xmax) / 2) * SENSOR_SIZE
                y_center = ((row.box_ymin + row.box_ymax) / 2) * SENSOR_SIZE
                
                # Determine Row (0-5) and Col (0-1)
                # Clamp to max indices to prevent edge case errors
                col = min(1, int(x_center // TILE_SIZE))
                row_idx = min(5, int(y_center // TILE_SIZE))
                
                # 1-based Tile ID (1-12)
                tile_id = (row_idx * 2) + col + 1
                clean_dict['tile_id'] = tile_id
                
                # Add to the simple namespace object too (for the walkway/grid)
                # We create a new SimpleNamespace to avoid mutating the read-only row
                step_obj = SimpleNamespace(**row_dict)
                step_obj.tile_id = tile_id
                steps_list_for_grid.append(step_obj)
            else:
                clean_dict['tile_id'] = -1 # Unknown
                steps_list_for_grid.append(SimpleNamespace(**row_dict))

            clean_dict['is_outlier'] = "Outlier" if row_dict['is_outlier'] else "Normal"
            data_list.append(clean_dict)

        df = pd.DataFrame(data_list)
        
        return trial, steps_list_for_grid, df

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