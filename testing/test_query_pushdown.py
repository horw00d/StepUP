import sys
import os
import time
import pandas as pd
from sqlalchemy import select, text

# Append parent directory to path so we can import from the main app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import engine
from models import Footstep, Trial, Participant

def get_base_stmt():
    """Returns the exact 3-table join used in the Cross-Trial tab."""
    return select(
        Footstep.id.label('footstep_id'),
        Footstep.footstep_index,
        Footstep.start_frame,
        Footstep.r_score,
        Footstep.side,
        Footstep.is_outlier,
        Footstep.mean_grf,
        Footstep.peak_grf,
        Footstep.stance_duration_frames,
        Footstep.foot_length,
        Footstep.foot_width,
        Footstep.rotation_angle,
        Trial.id.label('trial_id'),
        Trial.footwear,
        Trial.speed,
        Participant.id.label('participant_id'),
        Participant.sex,
        Participant.age,
        Participant.weight_kg
    ).join(Trial, Footstep.trial_id == Trial.id)\
     .join(Participant, Trial.participant_id == Participant.id)

def run_performance_race():
    print("==================================================")
    print("🏎️  STARTING SQLITE QUERY PUSHDOWN RACE")
    print("==================================================\n")

    query_string = "age >= 90"
    
    with engine.connect() as conn:
        # ---------------------------------------------------------
        # TEST 1: CLIENT-SIDE FILTERING (The Current Architecture)
        # ---------------------------------------------------------
        print("▶️ TEST 1: Client-Side (Pandas) Filtering")
        stmt_unfiltered = get_base_stmt()
        
        t0 = time.time()
        print("   ⏳ Fetching ALL data over connection...")
        df_all = pd.read_sql(stmt_unfiltered, conn)
        t1 = time.time()
        print(f"   ✅ Fetched {len(df_all)} rows in {t1 - t0:.4f} seconds.")
        
        print(f"   ⏳ Applying Pandas filter: '{query_string}'...")
        df_filtered = df_all.query(query_string)
        t2 = time.time()
        print(f"   ✅ Filtered down to {len(df_filtered)} rows in {t2 - t1:.4f} seconds.")
        
        test1_total = t2 - t0
        print(f"🏁 TEST 1 TOTAL TIME: {test1_total:.4f} seconds\n")

        # ---------------------------------------------------------
        # TEST 2: SERVER-SIDE FILTERING (The Pushdown Hypothesis)
        # ---------------------------------------------------------
        print("▶️ TEST 2: Server-Side (SQLite) Filtering")
        # We inject the WHERE clause natively into the SQL statement
        stmt_filtered = get_base_stmt().where(text(query_string))
        
        t3 = time.time()
        print(f"   ⏳ Fetching strictly filtered data over connection...")
        df_pushdown = pd.read_sql(stmt_filtered, conn)
        t4 = time.time()
        print(f"   ✅ Fetched {len(df_pushdown)} rows in {t4 - t3:.4f} seconds.")
        
        test2_total = t4 - t3
        print(f"🏁 TEST 2 TOTAL TIME: {test2_total:.4f} seconds\n")

        # ---------------------------------------------------------
        # RESULTS
        # ---------------------------------------------------------
        print("==================================================")
        print("🏆 RESULTS")
        if test2_total < test1_total:
            multiplier = test1_total / test2_total if test2_total > 0 else float('inf')
            print(f"Query Pushdown was {multiplier:.1f}x faster!")
        else:
            print("Query Pushdown was slower (Hypothesis invalidated).")
        print("==================================================")

if __name__ == '__main__':
    run_performance_race()