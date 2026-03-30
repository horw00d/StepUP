ALLOWED_COLUMNS = [
    # Demographic Data
    'participant_id', 'sex', 'age', 'weight_kg', 'height_cm',
    # Trial Context
    'trial_id', 'footwear', 'speed', 'side', 'is_outlier', 
    # Footstep Context
    'footstep_id', 'footstep_index', 'start_frame', 'r_score',
    # Kinetic Metrics
    'mean_grf', 'peak_grf', 'stance_duration_frames', 
    'foot_length', 'foot_width', 'rotation_angle'
]

# The strict allowlist of logical Python/Pandas operators
ALLOWED_KEYWORDS = {'and', 'or', 'not', 'in'}

#Physics Module
SENSOR_AREA_M2 = 2.5e-5 
SENSOR_SIDE_CM = 0.5 
SAMPLING_FREQ = 100 

#Data Module
SENSOR_SIZE = 0.005
TILE_SIZE = 0.6

NO_COLOR_SENTINEL = 'none'

class Granularity:
    FOOTSTEP = 'footstep'
    TRIAL = 'trial'
    PARTICIPANT = 'participant'

# config.py
GRANULARITY_COMPATIBLE_GROUPS = {
    'footstep': {'footwear', 'speed', 'sex', 'participant_id', 'side'},
    'trial': {'footwear', 'speed', 'sex', 'participant_id', 'side'},
    'participant': {'sex'},
}