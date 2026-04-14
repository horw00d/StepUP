import os
import logging
import numpy as np
import matplotlib.pyplot as plt
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from models import Trial, Footstep

# SETUP
ASSETS_DIR = "./assets/footsteps"
DATA_DIR = "./assets/data"
DATABASE_URL = "sqlite:///stepup.db"

os.makedirs(ASSETS_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

def run_generate_assets():
    engine = create_engine(DATABASE_URL)
    session = Session(engine)

    stmt = select(Trial).where(Trial.file_path.is_not(None))
    trials = session.scalars(stmt).all()
    
    logging.info(f"Processing {len(trials)} trials...")

    for trial in trials:
        if not os.path.exists(trial.file_path): continue

        try:
            with np.load(trial.file_path) as data:
                keys = data.files
                is_batch_format = 'arr_0' in keys
                
                if is_batch_format:
                    footsteps_tensor = data['arr_0']
                
                db_steps = session.scalars(
                    select(Footstep).where(Footstep.trial_id == trial.id)
                ).all()

                for step in db_steps:
                    idx = step.footstep_index
                    step_data = None
                    
                    try:
                        if is_batch_format:
                            if idx < len(footsteps_tensor):
                                step_data = footsteps_tensor[idx]
                        else:
                            if str(idx) in data:
                                step_data = data[str(idx)]

                        if step_data is not None:
                            #1 collapse to Peak Pressure (Max over time)
                            peak_pressure = np.max(step_data, axis=0)
                            
                            #2 orientation fix
                            aligned_matrix = np.flipud(peak_pressure)

                            #3 save PNG (Visual Asset)
                            img_path = os.path.join(ASSETS_DIR, f"step_{step.id}.png")
                            plt.imsave(img_path, peak_pressure, cmap='jet', origin='upper')

                            #save RAW DATA (Analytical Asset)
                            npy_path = os.path.join(DATA_DIR, f"step_{step.id}.npy")
                            np.save(npy_path, aligned_matrix)
                    
                    except Exception as step_error:
                        logging.error(f"Error step {step.id}: {step_error}")
                        continue
                        
            logging.info(f"Processed Trial {trial.id}")
            
        except Exception as e:
            logging.error(f"Error Trial {trial.id}: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
    run_generate_assets()