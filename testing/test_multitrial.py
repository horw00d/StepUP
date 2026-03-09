import time
from data import fetch_cross_trial_data

print("--- TESTING CROSS-TRIAL FETCH ENGINE ---")

# Test 1: Fetch absolutely everything in the database
start_time = time.time()
df_all = fetch_cross_trial_data()
end_time = time.time()

print(f"\n1. Full Database Fetch:")
print(f"   -> Retrieved {len(df_all)} footsteps in {end_time - start_time:.4f} seconds.")
if not df_all.empty:
    print(f"   -> Columns captured: {list(df_all.columns)}")

# Test 2: Fetch a specific experimental cohort
print("\n2. Targeted Cohort Fetch (e.g., All 'Fast' speeds in 'Sneakers'):")
start_time = time.time()
df_cohort = fetch_cross_trial_data(shoes=['P1'], speeds=['W3'])
end_time = time.time()

print(f"   -> Retrieved {len(df_cohort)} footsteps in {end_time - start_time:.4f} seconds.")

# Test 3: Verify grouping capabilities for Plotly Express
if not df_cohort.empty:
    print("\n3. Testing Pandas GroupBy capability:")
    # Calculate the average peak GRF for males vs females in this specific cohort
    summary = df_cohort.groupby('sex')['peak_grf'].mean()
    print(summary)