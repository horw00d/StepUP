import os
import logging
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from models import Base, Participant, Trial, Footstep
from physics import compute_tensor_physics

DATABASE_URL = "sqlite:///stepup.db"
DATA_ROOT = "./StepUP-P150/"

def init_db():
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(engine)
    return engine

def run_ingest():
    db_path = "stepup.db"
    if os.path.exists(db_path):
        os.remove(db_path)
        logging.info("Removed existing stepup.db for a clean initialization.")

    engine = init_db()
    session = Session(engine)
    
    logging.info("Starting ingestion...")
    
    meta_path = "./StepUP-P150/participant_metadata.csv" 
    if os.path.exists(meta_path):
        df_meta = pd.read_csv(meta_path, skipinitialspace=True)
        df_meta.columns = df_meta.columns.str.strip()
        
        # Bulk create participant objs
        participants = []
        for _, row in df_meta.iterrows():
            p = Participant(
                id=str(row['ParticipantID']).zfill(3), # Ensure '1' becomes '001'
                sex=row.get('Sex'),
                age=row.get('Age'),
                weight_kg=row.get('Weight (Kg)')
            )
            participants.append(p)
        
        session.add_all(participants)
        session.commit()
        logging.info(f"Ingested {len(participants)} participants.")
    else:
        logging.warning(f"Could not find metadata at {meta_path}")

    # 2. CRAWL TRIALS AND FOOTSTEPS
    # walk the dir structure: /ParticipantID/Footwear/Speed/
    
    # Walk the dir
    for root, dirs, files in os.walk(DATA_ROOT):
        if "metadata.csv" in files:
            df_steps = pd.read_csv(os.path.join(root, 'metadata.csv'), skipinitialspace=True)
            df_steps.columns = df_steps.columns.str.strip()

            # Parse path to get context (like ./001/BF/W1)
            parts = os.path.normpath(root).split(os.sep)
            
            # Assuming structure ends in .../ParticipantID/Footwear/Speed
            speed_cond = parts[-1]
            footwear_cond = parts[-2]
            participant_id = parts[-3]
            
            # create the Trial record
            npz_path = os.path.join(root, "pipeline_1.npz")
                
            # Check if it exists before assigning to the Trial
            trial_path = npz_path if os.path.exists(npz_path) else None
                
            trial = Trial(
                participant_id=participant_id,
                footwear=footwear_cond,
                speed=speed_cond,
                file_path=trial_path # Safe, explicit assignment
            )
            session.add(trial)
            session.flush() 
            
            footsteps_batch = []
            
            # safely open .npz and process inside the context manager
            if os.path.exists(npz_path):
                with np.load(npz_path) as data:
                    main_tensor = data['arr_0'] if 'arr_0' in data else None
                    
                    for _, row in df_steps.iterrows():
                        idx = row['FootstepID']
                        physics_data = None
                        
                        try:
                            # Extract tensor depending on how the NPZ was saved
                            if main_tensor is not None:
                                step_tensor = main_tensor[idx]
                            else:
                                step_tensor = data[str(idx)]
                                
                            # Calculate math
                            physics_data = compute_tensor_physics(step_tensor)
                            
                        except Exception as e:
                            print(f"Warning: Could not process tensor {idx} in {npz_path}: {e}")

                        # Build the Footstep object
                        step = Footstep(
                            trial_id=trial.id,
                            footstep_index=idx,
                            pass_id=row['PassID'],
                            start_frame=row['StartFrame'],
                            end_frame=row['EndFrame'],
                            side=row['Side'],
                            orientation=row['Orientation'],
                            foot_length=row['FootLength'],
                            foot_width=row['FootWidth'],
                            rotation_angle=row['RotationAngle'],
                            box_xmin=row['Xmin'],
                            box_xmax=row['Xmax'],
                            box_ymin=row['Ymin'],
                            box_ymax=row['Ymax'],
                            r_score=row['Rscore'],
                            mean_grf=row['MeanPressure'],
                            is_outlier=bool(row['Outlier']),
                            is_incomplete=bool(row['Incomplete']),
                            exclude=bool(row['Exclude']),
                            
                            # Safely inject the computed data
                            peak_grf=physics_data['peak_grf'] if physics_data else None,
                            stance_duration_frames=physics_data['stance_duration_frames'] if physics_data else None,
                            time_pct_array=physics_data['time_pct_array'] if physics_data else None,
                            grf_array=physics_data['grf_array'] if physics_data else None,
                            cop_ml_array=physics_data['cop_ml_array'] if physics_data else None,
                            cop_ap_array=physics_data['cop_ap_array'] if physics_data else None
                        )
                        footsteps_batch.append(step)
                        
            # If no .npz exists, still ingest the metadata with None for physics
            else:
                for _, row in df_steps.iterrows():
                    step = Footstep(
                        trial_id=trial.id, footstep_index=row['FootstepID'], pass_id=row['PassID'],
                        start_frame=row['StartFrame'], end_frame=row['EndFrame'], side=row['Side'],
                        orientation=row['Orientation'], foot_length=row['FootLength'], foot_width=row['FootWidth'],
                        rotation_angle=row['RotationAngle'], box_xmin=row['Xmin'], box_xmax=row['Xmax'],
                        box_ymin=row['Ymin'], box_ymax=row['Ymax'], r_score=row['Rscore'],
                        mean_grf=row['MeanGRF'], is_outlier=bool(row['Outlier']), 
                        is_incomplete=bool(row['Incomplete']), exclude=bool(row['Exclude'])
                    )
                    footsteps_batch.append(step)
            
            session.add_all(footsteps_batch)
            logging.info(f"Processed Trial: {participant_id} - {footwear_cond} - {speed_cond} ({len(footsteps_batch)} steps)")
            
    session.commit()
    logging.info("Ingestion complete.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
    run_ingestion()