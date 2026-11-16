import streamlit as st

st.set_page_config(page_title="FarmFit · Hurricane to Harvest", page_icon="🌀", layout="wide", initial_sidebar_state="collapsed")

from fieldshift import pages  # noqa: E402

pages.render()
