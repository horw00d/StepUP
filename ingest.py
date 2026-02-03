import os
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from models import Base, Participant, Trial, Footstep

DATABASE_URL = "sqlite:///stepup.db"
DATA_ROOT = "/home/cameron/StepUP-P150/"

def init_db():
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(engine)
    return engine

def ingest_data():
    engine = init_db()
    session = Session(engine)
    
    print("Starting ingestion...")

    meta_path = "/home/cameron/StepUP-P150/participant_metadata.csv" 
    if os.path.exists(meta_path):
        df_meta = pd.read_csv(meta_path)
        
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
        print(f"Ingested {len(participants)} participants.")
    else:
        print(f"Warning: Could not find {meta_path}")

    # 2. CRAWL TRIALS AND FOOTSTEPS
    # walk the dir structure: /ParticipantID/Footwear/Speed/
    
    # Walk the dir
    for root, dirs, files in os.walk(DATA_ROOT):
        if "metadata.csv" in files:
            # Parse path to get context (like ./001/BF/W1)
            parts = os.path.normpath(root).split(os.sep)
            
            # Assuming structure ends in .../ParticipantID/Footwear/Speed
            speed_cond = parts[-1]
            footwear_cond = parts[-2]
            participant_id = parts[-3]
            
            # Create the Trial record
            trial = Trial(
                participant_id=participant_id,
                footwear=footwear_cond,
                speed=speed_cond,
                file_path=os.path.join(root, "pipeline_1.npz") # Storing path
            )
            session.add(trial)
            session.flush() # Flush to assign trial.id
            
            # Load Footstep Metadata CSV
            csv_path = os.path.join(root, "metadata.csv")
            df_steps = pd.read_csv(csv_path)
            
            # Bulk create footsteps
            footsteps_batch = []
            for _, row in df_steps.iterrows():
                step = Footstep(
                    trial_id=trial.id,
                    footstep_index=row['FootstepID'],
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
                    mean_grf=row['MeanGRF'],
                    is_outlier=bool(row['Outlier']),
                    is_incomplete=bool(row['Incomplete']),
                    exclude=bool(row['Exclude'])
                )
                footsteps_batch.append(step)
            
            session.add_all(footsteps_batch)
            print(f"Processed Trial: {participant_id} - {footwear_cond} - {speed_cond} ({len(footsteps_batch)} steps)")
            
    session.commit()
    print("Ingestion complete.")

if __name__ == "__main__":
    ingest_data()