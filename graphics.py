import plotly.graph_objects as go

def create_walkway_plot(footsteps, selected_step_id=None):
    
    SENSOR_SIZE_M = 0.005
    TILE_WIDTH_M = 0.6
    
    fig = go.Figure()

    #draw tiles
    tiles = []
    for x in [0, TILE_WIDTH_M]:
        for y in [i * TILE_WIDTH_M for i in range(6)]:
            tiles.append(dict(
                type="rect", x0=x, x1=x + TILE_WIDTH_M, y0=y, y1=y + TILE_WIDTH_M,
                line=dict(color="#dddddd", width=1), fillcolor="white", layer="below"
            ))
    fig.update_layout(shapes=tiles)

    #draw footsteps
    box_shapes = []
    valid_box_count = 0
    
    for step in footsteps:
        if step.box_xmin is None: 
            continue
        
        valid_box_count += 1
        
        x0, x1 = step.box_xmin * SENSOR_SIZE_M, step.box_xmax * SENSOR_SIZE_M
        y0, y1 = step.box_ymin * SENSOR_SIZE_M, step.box_ymax * SENSOR_SIZE_M
        
        is_selected = (step.id == selected_step_id)
        
        #highlighting selected step red
        if is_selected:
            color = "#FF0000"
            opacity = 0.8
            line_width = 3
        else:
            #currently hardcoding left/right foot colors, could be made enforced by main selection menu
            color = "#1f77b4" if step.side == 'Left' else "#2ca02c"
            opacity = 0.4
            line_width = 1

        box_shapes.append(dict(
            type="rect", x0=x0, x1=x1, y0=y0, y1=y1,
            line=dict(color=color, width=line_width),
            fillcolor=color, opacity=opacity, layer="above"
        ))

        #invisible scatter point for clicks
        fig.add_trace(go.Scatter(
            x=[(x0+x1)/2], y=[(y0+y1)/2],
            mode='markers', marker=dict(opacity=0),
            customdata=[[step.id, step.pass_id, step.footstep_index]], 
            
            #hover info
            hovertemplate="<b>Step %{customdata[2]}</b><br>Pass: %{customdata[1]}<br>ID: %{customdata[0]}<extra></extra>",
            showlegend=False
        ))
    
    fig.update_layout(shapes=tiles + box_shapes)
    fig.update_layout(
        title=f"Spatial Footstep Map ({valid_box_count} steps)",
        xaxis=dict(title="Width (m)", range=[-0.1, 1.3], scaleanchor="y", scaleratio=1),
        yaxis=dict(title="Length (m)", range=[-0.1, 3.7]),
        margin=dict(l=20, r=20, t=40, b=20),
        plot_bgcolor="#f9f9f9",
        clickmode='event+select'
    )
    return fig