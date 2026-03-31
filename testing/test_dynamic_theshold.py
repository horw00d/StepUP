import sys
import os
import time
import pandas as pd
import numpy as np
from sqlalchemy import select

# Append parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import engine
from models import Footstep

def run_threshold_test():
    print("==================================================")
    print("🚀 STARTING DYNAMIC THRESHOLD PERFORMANCE TEST")
    print("==================================================\n")

    with engine.connect() as conn:
        print("⏳ Fetching ALL r_score data from SQLite...")
        t0 = time.time()
        # Fetching only what we need to simulate the dataframe state
        stmt = select(Footstep.id, Footstep.r_score, Footstep.is_outlier)
        df = pd.read_sql(stmt, conn)
        t1 = time.time()
        print(f"✅ Fetched {len(df)} rows in {t1 - t0:.4f} seconds.\n")

        # --- THE TEST ---
        thresholds_to_test = [0.95, 0.80, 0.50]
        
        for thresh in thresholds_to_test:
            print(f"🧪 Testing dynamic reclassification (Threshold = {thresh})...")
            t_start = time.time()
            
            # This is the exact code we will put in helpers.py
            # If r_score is missing (NaN), we default to 'Normal' or 'Outlier' based on your preference
            df['dynamic_outlier'] = np.where(df['r_score'] < thresh, 'Outlier', 'Normal')
            
            t_end = time.time()
            
            outlier_count = len(df[df['dynamic_outlier'] == 'Outlier'])
            print(f"   ⏱️ Vectorized operation took: {(t_end - t_start) * 1000:.2f} milliseconds")
            print(f"   📊 Result: {outlier_count} Outliers found.\n")

if __name__ == '__main__':
    run_threshold_test()