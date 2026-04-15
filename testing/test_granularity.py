import sys
import os

# Ensure we can import from the parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import data
from helpers import apply_data_granularity


def run_test():
    # 1. Simulate your exact UI selection
    test_participants = [
        "001",
        "002",
        "003",
        "004",
        "005",
    ]  # Replace with your actual 5 selected IDs
    test_shoes = ["BF"]  # e.g., Canvas Shoes
    test_speeds = ["W1"]  # e.g., Preferred Speed

    print(f"Fetching data for Participants: {test_participants}")
    df_raw = data.fetch_cross_trial_data(
        part_ids=test_participants, shoes=test_shoes, speeds=test_speeds
    )

    print(f"\nRaw Footsteps Extracted: {len(df_raw)}")

    # 2. Apply the aggregation
    df_agg = apply_data_granularity(df_raw, granularity="participant")

    # 3. Print the results
    print(f"\nAggregated Data Points: {len(df_agg)}")
    print("\nData Shape Breakdown:")
    # Print just the identifying columns to see the Left/Right split
    if not df_agg.empty:
        print(df_agg[["participant_id", "side", "peak_grf"]].to_string(index=False))


if __name__ == "__main__":
    run_test()
