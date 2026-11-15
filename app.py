"""FarmFit · Hurricane to Harvest (NASA Space Apps 2026, Field Shift).

Run: streamlit run app.py
The original FarmFit crop-check app lives on in legacy_app.py.
"""

import streamlit as st

st.set_page_config(
    page_title="Hurricane to Harvest · FarmFit",
    page_icon="🌀",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from fieldshift import ui  # noqa: E402

ui.render()
