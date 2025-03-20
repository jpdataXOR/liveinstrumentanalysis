import streamlit as st

def apply_theme(theme):
    if theme == "Light":
        st.session_state.theme = {
            "background_color": "#FFFFFF",
            "text_color": "#000000",
            "line_color": "#000000",
            "marker_color": "#000000",
            "projection_color": "rgba(150,150,150,0.6)",
            "latest_projection_color": "rgba(34,139,34,0.8)",    # Forest green
            "avg_projection_color": "rgba(135,206,235,0.8)",     # Light blue
            "avg_latest_projection_color": "rgba(0,105,148,0.8)" # Dark blue
        }
    else:
        st.session_state.theme = {
            "background_color": "#000000",
            "text_color": "#FFFFFF",
            "line_color": "#FFFFFF",
            "marker_color": "#FFFFFF",
            "projection_color": "rgba(150,150,150,0.6)",
            "latest_projection_color": "rgba(144,238,144,0.8)",  # Light green
            "avg_projection_color": "rgba(135,206,235,0.8)",     # Light blue
            "avg_latest_projection_color": "rgba(0,105,148,0.8)" # Dark blue
        }

def get_theme():
    return st.session_state.theme