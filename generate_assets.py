import os
import numpy as np
import matplotlib.pyplot as plt
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from models import Trial, Footstep

# SETUP
ASSETS_DIR = "./assets/footsteps"
DATABASE_URL = "sqlite:///stepup.db"
os.makedirs(ASSETS_DIR, exist_ok=True)

def generate_assets():
    engine = create_engine(DATABASE_URL)
    session = Session(engine)

    # Fetch all trials
    stmt = select(Trial).where(Trial.file_path.is_not(None))
    trials = session.scalars(stmt).all()
    
    print(f"Found {len(trials)} trials to process...")

    for trial in trials:
        if not os.path.exists(trial.file_path):
            continue

        try:
            # Load the NPZ file context manager style to ensure it closes
            with np.load(trial.file_path) as data:
                
                #check file format
                keys = data.files
                is_batch_format = 'arr_0' in keys
                
                # if batch format, load the big tensor once to save memory
                if is_batch_format:
                    footsteps_tensor = data['arr_0']
                
                #fetch DB records for trial
                db_steps = session.scalars(
                    select(Footstep).where(Footstep.trial_id == trial.id)
                ).all()

                for step in db_steps:
                    idx = step.footstep_index
                    
                    try:
                        step_data = None
                        
                        #format A: single large tensor
                        if is_batch_format:
                            if idx < len(footsteps_tensor):
                                step_data = footsteps_tensor[idx]
                        
                        #format B: Individual keys '0', '1', '2'
                        else:
                            str_idx = str(idx)
                            if str_idx in data:
                                step_data = data[str_idx]

                        #found data, save the image
                        if step_data is not None:
                            #collapse time (axis 0) to get Peak Pressure
                            peak_pressure = np.max(step_data, axis=0)
                            
                            # Save to assets
                            output_path = os.path.join(ASSETS_DIR, f"step_{step.id}.png")
                            plt.imsave(output_path, peak_pressure, cmap='jet', origin='lower')
                    
                    except Exception as step_error:
                        print(f"Error processing step {step.id} in trial {trial.id}: {step_error}")
                        continue
                        
            print(f"Processed Trial {trial.id}")
            
        except Exception as e:
            print(f"CRITICAL ERROR loading {trial.file_path}: {e}")
            continue

    print("Asset generation complete!")

if __name__ == "__main__":
    generate_assets()