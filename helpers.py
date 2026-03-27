import re
from config import ALLOWED_COLUMNS, ALLOWED_KEYWORDS

#helper function to apply all filters in one place
def filter_dataframe(df, sides, outliers, tiles, passes, query_string=None):
    """
    Common logic to filter the dataframe based on UI inputs and free-form query.
    Returns the filtered DataFrame AND an error message string (if any).
    """
    error_msg = ""
    if df.empty: return df, error_msg
    
    #1. standard UI Filters
    if sides: df = df[df['side'].isin(sides)]
    if outliers: df = df[df['is_outlier'].isin(outliers)]
    if tiles: df = df[df['tile_id'].isin(tiles)]
    if passes: df = df[df['pass_id'].isin(passes)]
        
    #2. advanced Query Builder Execution
    if query_string:
        is_valid, validation_msg = validate_query_string(query_string)
        if is_valid:
            try:
                #executes the string logic in-memory
                df = df.query(query_string)
            except Exception as e:
                #catch syntax errors
                error_msg = f"Execution Error: {e}"
        else:
            error_msg = validation_msg
            
    return df, error_msg

def validate_query_string(query_string):
    """
    Validates a free-form query string against a strict allowlist.
    Returns: (is_valid: bool, error_message: str)
    """
    # 1. Handle empty queries gracefully
    if not query_string or not query_string.strip():
        return True, ""
        
    # 2. Check for illegal characters
    # We only allow alphanumeric, spaces, quotes, standard math/logic operators, and brackets.
    # Anything else (like ;, @, $, or system path slashes) triggers an immediate failure.
    if re.search(r'[^a-zA-Z0-9_\s><=!()[\]\'".,-]', query_string):
        return False, "Query contains illegal characters."

    # 3. Isolate variables from string literals
    # We temporarily remove text inside quotes (e.g., 'Left', "Right") 
    # so the validator doesn't flag user-inputted strings as invalid column names.
    query_no_strings = re.sub(r'["\'].*?["\']', '', query_string)

    # 4. Extract all mathematical variables/words
    # Regex \b[a-zA-Z_]\w*\b grabs anything that looks like a variable name
    words = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', query_no_strings)

    # 5. Verify against the Allowlist
    for word in words:
        if word not in ALLOWED_COLUMNS and word not in ALLOWED_KEYWORDS:
            return False, f"Invalid term: '{word}'. Only approved columns and operators are allowed."

    # 6. Passed all security checks
    return True, ""

def apply_data_granularity(df, granularity):
    """
    Aggregates cross-trial DataFrames to prevent statistical pseudoreplication.
    - 'footstep': No aggregation (1 row = 1 step).
    - 'trial': Averages footsteps per trial condition (1 row = 1 trial).
    - 'participant': Averages all footsteps per participant (1 row = 1 person).
    """
    if df.empty or granularity == 'footstep':
        # Add a dummy count for single footsteps so the hover logic is unified
        df_out = df.copy()
        df_out['n_footsteps'] = 1 
        return df_out

    if granularity == 'trial':
        group_keys = ['participant_id', 'footwear', 'speed', 'sex', 'side']
    elif granularity == 'participant':
        group_keys = ['participant_id', 'sex', 'side']
    else:
        return df

    valid_group_keys = [col for col in group_keys if col in df.columns]

    try:
        # 1. Count how many footsteps are in each group
        step_counts = df.groupby(valid_group_keys).size().reset_index(name='n_footsteps')
        
        # 2. Calculate the means
        aggregated_df = df.groupby(valid_group_keys).mean(numeric_only=True).reset_index()
        
        # 3. Merge the counts back into the aggregated dataframe
        import pandas as pd
        final_df = pd.merge(aggregated_df, step_counts, on=valid_group_keys)
        return final_df
        
    except Exception as e:
        print(f"Warning: Granularity aggregation failed - {e}")
        return df