"""Shared view helpers: load data with a skeleton, show Live errors (never fall back)."""
import altair as alt
import streamlit as st

import brand
import data


def load(mode):
    ph = st.empty()
    if mode == "Live" and not st.session_state.get("_live_loaded"):
        ph.markdown(brand.skeleton(), unsafe_allow_html=True)
    try:
        h, d = data.health(mode), data.demand(mode)
    except Exception as e:  # Live failure: show it, do not substitute sample data
        ph.empty()
        st.error(f"Live query failed: {e}")
        st.caption(f"Check that sql/setup.sql ran and your role is {data.ROLE}, or switch to Sample.")
        st.stop()
    if mode == "Live":
        st.session_state["_live_loaded"] = True
    ph.empty()
    return h, d


def cap(mode, text):
    return f"Live · {text}" if mode == "Live" else f"Sample data · {text}"


def theme():
    def _t():
        return {"config": {
            "font": "Manrope",
            "view": {"stroke": None},
            "axis": {"labelColor": brand.T["muted"], "titleColor": brand.T["ink2"], "gridColor": "#ECE5F0",
                     "domainColor": brand.T["line"], "tickColor": brand.T["line"], "labelFontSize": 11,
                     "titleFontSize": 11, "titleFontWeight": 600},
            "axisX": {"grid": False},
            "legend": {"labelColor": brand.T["ink2"], "titleColor": brand.T["muted"], "labelFontSize": 11,
                       "titleFontSize": 11, "orient": "bottom", "symbolType": "square"},
            "background": "transparent",
        }}
    alt.themes.register("attrition", _t)
    alt.themes.enable("attrition")


def band_scale():
    return alt.Scale(domain=[brand.BAND_LABEL[b] for b in data.BANDS], range=[brand.BAND[b][2] for b in data.BANDS])
