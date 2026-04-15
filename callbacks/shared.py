from dash import Input, Output, MATCH


def register_shared_callbacks(app):
    # H. CLEAR QUERY
    @app.callback(
        Output({"type": "query-input", "tab": MATCH}, "value"),
        Input({"type": "clear-query-btn", "tab": MATCH}, "n_clicks"),
        prevent_initial_call=True,
    )
    def clear_query(n_clicks):
        return ""
