from sqlalchemy import select, distinct
import pandas as pd
from database import Session, engine
from models import Trial, Footstep, Participant

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
        # 1. Fetch Trial
        stmt = select(Trial).where(Trial.participant_id == part, Trial.footwear == shoe, Trial.speed == speed)
        trial = session.scalar(stmt)
        
        if not trial:
            return None, [], "Status: No Trial Found"

        # 2. Fetch Steps
        steps = session.scalars(
            select(Footstep).where(Footstep.trial_id == trial.id).order_by(Footstep.footstep_index)
        ).all()
        
        # 3. Build DataFrame (Centralized logic)
        data = [{
            'id': s.id,
            'footstep_index': s.footstep_index,
            'start_frame': s.start_frame,
            'mean_grf': s.mean_grf,
            'r_score': s.r_score,
            'foot_length': s.foot_length,
            'foot_width': s.foot_width,
            'rotation_angle': s.rotation_angle,
            'side': s.side,
            'is_outlier': "Outlier" if s.is_outlier else "Normal"
        } for s in steps]
        
        df = pd.DataFrame(data)
        
        return trial, steps, df

def fetch_step_by_id(step_id):
    """Fetches a single footstep by ID (for physics/highlighting)."""
    with Session(engine) as session:
        return session.get(Footstep, step_id)

def fetch_pass_options(part, shoe, speed):
    """
    Fetches unique Pass IDs for a trial to populate the dropdown.
    """
    trial, steps, _ = fetch_trial_data(part, shoe, speed)
    
    if not trial:
        return [], []
        
    # Extract unique passes
    unique_passes = sorted(list(set([s.pass_id for s in steps if s.pass_id is not None])))
    options = [{'label': f"Pass {p}", 'value': p} for p in unique_passes]
    
    return options, unique_passes