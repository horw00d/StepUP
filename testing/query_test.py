from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session
from models import Participant, Trial, Footstep

# Connect to the DB we just populated
DATABASE_URL = "sqlite:///stepup.db"
engine = create_engine(DATABASE_URL)
session = Session(engine)

# ---------------------------------------------------------
# QUERY 1: The "Directory" View
# "Select participant 1 barefoot trial" (from your notes)
# ---------------------------------------------------------
print("--- QUERY 1: Finding P001 Barefoot Trials ---")

stmt = select(Trial).where(Trial.participant_id == "001").where(Trial.footwear == "BF")

trials = session.scalars(stmt).all()

for t in trials:
    print(f"Found Trial ID: {t.id} | Speed: {t.speed} | File: {t.file_path}")


# ---------------------------------------------------------
# QUERY 2: The "Outlier" Analysis
# Find how many footsteps are flagged as outliers in W2 (Slow-to-Stop)
# ---------------------------------------------------------
print("\n--- QUERY 2: Counting Outliers in W2 ---")

# We join Footstep -> Trial to filter by speed 'W2'
stmt = (
    select(func.count(Footstep.id))
    .join(Trial)
    .where(Trial.speed == "W2")
    .where(Footstep.is_outlier == True)
)

outlier_count = session.scalar(stmt)
print(f"Total outliers in Slow-to-Stop (W2) trials: {outlier_count}")


# ---------------------------------------------------------
# QUERY 3: Fetching Data for the Visualizer
# Get specific footstep details (e.g., for the detailed view)
# ---------------------------------------------------------
print("\n--- QUERY 3: Detailed Footstep Data ---")

# Get first 5 steps of the first trial found above
first_trial = trials[0]

stmt = select(Footstep).where(Footstep.trial_id == first_trial.id).limit(5)

steps = session.scalars(stmt).all()

for s in steps:
    print(
        f"Step {s.footstep_index}: Frame {s.start_frame}-{s.end_frame} (R-Score: {s.r_score})"
    )
