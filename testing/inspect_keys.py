import numpy as np
import os

# Path to one of the failing files you listed
broken_file = "/home/cameron/StepUP-P150/141/BF/W1/pipeline_1.npz"

if os.path.exists(broken_file):
    try:
        # Load the file
        with np.load(broken_file) as data:
            # Print all keys (variable names) inside the file
            print(f"Keys found in {os.path.basename(broken_file)}:")
            print(data.files)

            # Optional: Print shape of the first key found to confirm it's the right data
            if len(data.files) > 0:
                first_key = data.files[0]
                print(f"Shape of '{first_key}': {data[first_key].shape}")
    except Exception as e:
        print(f"Could not open file: {e}")
else:
    print("File not found. Check the path.")
