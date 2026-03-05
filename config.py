ALLOWED_COLUMNS = {
    'footstep_index', 'start_frame', 'r_score', 'mean_grf', 
    'foot_length', 'foot_width', 'rotation_angle', 
    'side', 'is_outlier', 'tile_id', 'pass_id'
}

# The strict allowlist of logical Python/Pandas operators
ALLOWED_KEYWORDS = {'and', 'or', 'not', 'in'}

#Physics Module
SENSOR_AREA_M2 = 2.5e-5 
SENSOR_SIDE_CM = 0.5 
SAMPLING_FREQ = 100 

#Data Module
SENSOR_SIZE = 0.005
TILE_SIZE = 0.6