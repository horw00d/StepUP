import os
import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from models import Footstep

# Connect to your database
DATABASE_URL = "sqlite:///stepup.db"
engine = create_engine(DATABASE_URL)


def inspect_specific_step(step_id):
    print(f"--- INSPECTING FOOTSTEP ID: {step_id} ---")

    with Session(engine) as session:
        # 1. Fetch the Step
        step = session.get(Footstep, step_id)

        if not step:
            print("ERROR: Footstep not found in database!")
            return

        # 2. Inspect the Path
        file_path = step.trial.file_path
        print(f"Trial ID: {step.trial.id}")
        print(f"Expected File Path: {file_path}")

        # 3. Check if File Exists
        if os.path.exists(file_path):
            print("STATUS: File exists on disk ✅")
        else:
            print("STATUS: FILE NOT FOUND ❌")
            print(
                "   -> Check if the path in the DB matches your actual folder structure."
            )
            return

        # 4. Try Loading the Data (Replicating physics.py logic)
        try:
            print(f"Attempting to load index {step.footstep_index}...")
            with np.load(file_path) as data:
                print(f"Keys in file: {list(data.keys())}")

                # Logic from physics.py
                if "arr_0" in data:
                    print("Format: Batch (arr_0)")
                    tensor = data["arr_0"][step.footstep_index]
                    print(f"Success! Loaded tensor with shape: {tensor.shape}")
                else:
                    print("Format: Fragmented (0, 1, 2...)")
                    str_idx = str(step.footstep_index)
                    if str_idx in data:
                        tensor = data[str_idx]
                        print(f"Success! Loaded tensor with shape: {tensor.shape}")
                    else:
                        print(f"FAILURE: Key '{str_idx}' not found in file.")

        except Exception as e:
            print(f"CRITICAL EXCEPTION during loading: {e}")


if __name__ == "__main__":
    inspect_specific_step(145351)
