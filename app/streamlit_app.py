"""Merchant Attrition Early-Warning - a Snow Pack app on Snowflake.

Run locally (Sample mode, no account):   streamlit run app/streamlit_app.py
Live mode locally: set SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER and SNOWFLAKE_PRIVATE_KEY_PATH
(key-pair auth) and restart. In Streamlit in Snowflake the app uses its own session.
"""
import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import brand  # noqa: E402
import data  # noqa: E402
from views import ask, categories, notes, overview, save_list  # noqa: E402

st.set_page_config(page_title="Merchant Attrition Early-Warning", page_icon="📉", layout="wide",
                   initial_sidebar_state="auto")
st.markdown(brand.CSS, unsafe_allow_html=True)

LIVE_OK = data.live_configured()
if "mode" not in st.session_state:
    st.session_state.mode = "Live" if LIVE_OK else "Sample"

VIEWS = {
    "Overview": overview.render,
    "Save list": save_list.render,
    "Categories": categories.render,
    "Attrition notes": notes.render,
    "Ask the agent": ask.render,
}

with st.sidebar:
    st.html(f'<div class="mw-brand">{brand.LOGO_IMG}<div><b>Merchant Attrition Early-Warning</b>'
            '<span>Merchant retention · payments processor</span></div></div>')
    st.html('<div class="mw-rail-h">Data mode</div>')
    st.segmented_control("Data mode", ["Sample", "Live"], key="mode", label_visibility="collapsed",
                         help="Sample: bundled synthetic data, no account. Live: the same app on Snowflake.")
    mode = st.session_state.mode or st.session_state.get("_last_mode", "Sample")
    st.session_state["_last_mode"] = mode
    st.html('<div class="mw-rail-h">Views</div>')
    view = st.radio("View", list(VIEWS), label_visibility="collapsed", key="view")
    env = ('<span class="mw-chip live"><span class="mw-dot"></span>Live · Snowflake</span>' if mode == "Live"
           else '<span class="mw-chip sample"><span class="mw-dot"></span>Sample data</span>')
    st.html(f'<div class="mw-rail-h">Environment</div>{env}<br><span class="mw-chip role">Retention analyst<code>{data.ROLE}</code></span>'
            '<div class="mw-rail-foot">Synthetic merchant book and illustrative logic only. Not production, financial or '
            'regulatory advice.</div>')

if mode == "Live" and not LIVE_OK:
    st.markdown(brand.header("Connect Live mode", "Live mode runs this same app on Snowflake. No connection is configured, so nothing is shown instead of falling back to sample data.", "Setup needed"), unsafe_allow_html=True)
    st.markdown("1. Run `sql/setup.sql` in a Snowsight worksheet (about 15 s on an XSMALL warehouse).\n"
                "2. Register a key pair on your Snowflake user, then set these variables and restart:")
    st.code("export SNOWFLAKE_ACCOUNT=<org-account>\nexport SNOWFLAKE_USER=<YOUR_USER>\n"
            "export SNOWFLAKE_PRIVATE_KEY_PATH=~/.snowflake/keys/<your_key>.p8\n"
            "streamlit run app/streamlit_app.py", language="bash")
    st.markdown("Or deploy the app as Streamlit in Snowflake (README, *Deploy the app in Snowflake*). "
                "Switch back to **Sample** to keep exploring.")
    st.stop()

VIEWS[view](mode)
