import dash
from callbacks import register_callbacks
from config import EXTERNAL_STYLESHEETS
from layout import create_layout

# 1. Setup
external_stylesheets = EXTERNAL_STYLESHEETS
app = dash.Dash(
    __name__, external_stylesheets=external_stylesheets, title="StepUP Analyst"
)

# 2. Inject Layout
app.layout = create_layout()

# 3. Register Callbacks
register_callbacks(app)

# 4. Run
if __name__ == "__main__":
    app.run(debug=True, port=8000)
    print("App is running on http://localhost:8000")
