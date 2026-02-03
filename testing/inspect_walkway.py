import plotly.graph_objects as go
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from models import Trial, Footstep

# 1. SETUP
DATABASE_URL = "sqlite:///stepup.db"
engine = create_engine(DATABASE_URL)

def create_walkway_plot(footsteps):
    """(Exact copy of your plotting logic for testing)"""
    SENSOR_SIZE_M = 0.005
    TILE_WIDTH_M = 0.6
    TOTAL_WIDTH_M = 1.2
    TOTAL_LENGTH_M = 3.6
    
    fig = go.Figure()

    # Draw Tiles
    tiles = []
    for x in [0, TILE_WIDTH_M]:
        for y in [i * TILE_WIDTH_M for i in range(6)]:
            tiles.append(dict(
                type="rect", x0=x, x1=x + TILE_WIDTH_M, y0=y, y1=y + TILE_WIDTH_M,
                line=dict(color="#dddddd", width=1), fillcolor="white", layer="below"
            ))
    fig.update_layout(shapes=tiles)

    # Draw Boxes
    box_shapes = []
    count = 0
    for step in footsteps:
        # --- CRITICAL CHECK ---
        if step.box_xmin is None:
            continue
        
        count += 1
        x0 = step.box_xmin * SENSOR_SIZE_M
        x1 = step.box_xmax * SENSOR_SIZE_M
        y0 = step.box_ymin * SENSOR_SIZE_M
        y1 = step.box_ymax * SENSOR_SIZE_M
        
        box_shapes.append(dict(
            type="rect", x0=x0, x1=x1, y0=y0, y1=y1,
            line=dict(color="blue", width=1), fillcolor="blue", opacity=0.3
        ))

    print(f"Plotting {count} valid boxes found in data.")
    fig.update_layout(shapes=tiles + box_shapes)
    fig.update_layout(
        title=f"Debug Walkway ({count} steps)", 
        xaxis=dict(range=[-0.1, 1.3], scaleanchor="y"), 
        yaxis=dict(range=[-0.1, 3.7]),
        height=800
    )
    return fig

def run_diagnostic():
    print("--- DIAGNOSTIC START ---")
    with Session(engine) as session:
        # Get the first trial
        trial = session.scalars(select(Trial).limit(1)).first()
        if not trial:
            print("ERROR: Database is empty!")
            return

        print(f"Inspecting Trial ID: {trial.id} ({trial.footwear})")
        
        # Get footsteps
        steps = session.scalars(select(Footstep).where(Footstep.trial_id == trial.id)).all()
        print(f"Found {len(steps)} footsteps.")
        
        # Check Data Integrity
        valid_boxes = [s for s in steps if s.box_xmin is not None]
        
        if len(valid_boxes) == 0:
            print("\n❌ CRITICAL ISSUE: No Bounding Box Data Found!")
            print("   The columns 'box_xmin' etc. are NULL in the database.")
            print("   SOLUTION: You must delete 'stepup.db' and run 'python ingest.py' again.")
        else:
            print(f"\n✅ SUCCESS: Found {len(valid_boxes)} steps with coordinate data.")
            print(f"   Sample Box (Step {valid_boxes[0].id}): "
                  f"x[{valid_boxes[0].box_xmin}-{valid_boxes[0].box_xmax}] "
                  f"y[{valid_boxes[0].box_ymin}-{valid_boxes[0].box_ymax}]")
            
            # Generate and open plot
            fig = create_walkway_plot(steps)
            fig.show()

if __name__ == "__main__":
    run_diagnostic()