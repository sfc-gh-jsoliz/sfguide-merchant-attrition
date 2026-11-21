"""Categories: is it the merchants or the market? Book vs demand per MCC category, with a drill-down."""
import altair as alt
import pandas as pd
import streamlit as st

import brand
import data
from views.common import band_scale, cap, load, theme


def yoy_series(h, d, code):
    g = h[h.category_code == code].groupby("month").monthly_volume_usd.sum()
    book = (g / g.shift(12) - 1) * 100
    dem = d[d.category_code == code].set_index("month").yoy_growth_pct
    out = pd.concat([
        pd.DataFrame({"month": book.index, "yoy": book.values, "series": "Merchant book"}),
        pd.DataFrame({"month": dem.index, "yoy": dem.values, "series": "Category demand"})]).dropna()
    return out[out.month >= h.month.max() - pd.DateOffset(months=11)]


def render(mode):
    theme()
    h, d = load(mode)
    cs = data.category_summary(h, d)
    last = h.month.max()
    st.markdown(brand.header(
        "Categories", f"Each MCC category's book against its demand backdrop, {last:%B %Y} vs a year earlier. "
                      "A book shrinking 10+ points faster than demand is a retention problem; a book shrinking with its market is a slowdown.",
        cap(mode, "ATTRITION_MERCHANT_HEALTH + ATTRITION_CATEGORY_HEALTH"), mode != "Live"), unsafe_allow_html=True)

    t = pd.DataFrame({
        "Category": cs.category, "Diagnosis": cs.diagnosis, "Book YoY %": cs.book_yoy.round(1),
        "Demand YoY %": cs.demand_yoy.round(1), "Gap (pts)": cs.gap.round(1), "NRR %": cs.nrr.round(1),
        "Churn rate %": cs.churn_rate.round(1), "Active": cs.active, "Watch": cs.watch, "At risk": cs.at_risk,
        "Churned": cs.churned, "Volume trend ($M)": cs.trend,
    })
    tone = {k: brand.BAND[v] for k, v in brand.DIAG.items()}
    styled = t.style.map(lambda v: f"background-color:{tone[v][1]};color:{tone[v][0]};font-weight:700", subset=["Diagnosis"])
    with st.container(key="card_cats"):
        ev = st.dataframe(styled, hide_index=True, width="stretch", on_select="rerun", selection_mode="single-row",
                          key="cat_table", column_config={
                              "Volume trend ($M)": st.column_config.AreaChartColumn("Volume trend ($M)"),
                              "Book YoY %": st.column_config.NumberColumn(format="%+.1f%%"),
                              "Demand YoY %": st.column_config.NumberColumn(format="%+.1f%%"),
                              "Gap (pts)": st.column_config.NumberColumn(format="%+.1f"),
                              "NRR %": st.column_config.NumberColumn(format="%.1f%%"),
                              "Churn rate %": st.column_config.NumberColumn(format="%.1f%%"),
                          })
        st.caption("Gap = book YoY minus demand YoY. Churn rate = churned merchants / all 20 merchants in the category. Select a row to drill in.")
    rows = ev.selection.rows if ev and ev.selection else []
    r = cs.iloc[rows[0] if rows else 0]
    code = r.category_code

    st.markdown(f'<div style="display:flex;gap:.6rem;align-items:center;flex-wrap:wrap;margin:.4rem 0 .6rem">'
                f'<p class="mw-card-h" style="margin:0;font-size:1.1rem">{brand.esc(r.category)}</p>{brand.diag_pill(r.diagnosis)}'
                f'<span class="mw-card-s" style="margin:0">book {brand.pct(r.book_yoy)} · demand {brand.pct(r.demand_yoy)} · NRR {r.nrr:.1f}%</span></div>',
                unsafe_allow_html=True)
    left, right = st.columns(2, gap="medium")
    with left.container(key="card_yoy"):
        st.markdown('<p class="mw-card-h">Year-on-year change, last 12 months</p><p class="mw-card-s">Solid: merchant book volume. Dashed: category demand.</p>', unsafe_allow_html=True)
        dom = ["Merchant book", "Category demand"]
        chart = alt.Chart(yoy_series(h, d, code)).mark_line(strokeWidth=2.4, point=True, interpolate="monotone").encode(
            x=alt.X("month:T", title=None, axis=alt.Axis(format="%b %y", labelAngle=0)),
            y=alt.Y("yoy:Q", title="YoY change (%)"),
            color=alt.Color("series:N", title=None, scale=alt.Scale(domain=dom, range=[brand.T["plum500"], brand.T["demand"]])),
            strokeDash=alt.StrokeDash("series:N", legend=None, scale=alt.Scale(domain=dom, range=[[1, 0], [6, 4]])),
            tooltip=[alt.Tooltip("month:T", title="Month-end", format="%B %Y"), alt.Tooltip("series:N", title="Series"),
                     alt.Tooltip("yoy:Q", title="YoY %", format="+.1f")])
        zero = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color=brand.T["line"]).encode(y="y:Q")
        st.altair_chart((zero + chart).properties(height=240), use_container_width=True, theme=None)
    with right.container(key="card_tenure"):
        st.markdown('<p class="mw-card-h">Risk bands by tenure, this month</p><p class="mw-card-s">Merchants per tenure band. Hover for counts.</p>', unsafe_allow_html=True)
        L = h[(h.category_code == code) & (h.month == last)]
        tb = L.groupby(["tenure_band", "risk_band"]).size().reset_index(name="merchants")
        tb["band_label"] = tb.risk_band.map(brand.BAND_LABEL)
        tb["order"] = tb.risk_band.map({b: i for i, b in enumerate(data.BANDS)})
        bars = alt.Chart(tb).mark_bar(cornerRadius=3).encode(
            y=alt.Y("tenure_band:N", title=None, sort=data.TENURES),
            x=alt.X("merchants:Q", title="Merchants", stack="zero"),
            color=alt.Color("band_label:N", title=None, scale=band_scale(), sort=[brand.BAND_LABEL[b] for b in data.BANDS]),
            order=alt.Order("order:Q"),
            tooltip=[alt.Tooltip("tenure_band:N", title="Tenure"), alt.Tooltip("band_label:N", title="Band"),
                     alt.Tooltip("merchants:Q", title="Merchants")])
        st.altair_chart(bars.properties(height=240), use_container_width=True, theme=None)

    with st.container(key="card_nrr"):
        st.markdown('<p class="mw-card-h">Net revenue retention by category</p><p class="mw-card-s">Processed volume as % of baseline, per month-end. The selected category is drawn bold.</p>', unsafe_allow_html=True)
        n = h.groupby(["month", "category_name"]).agg(v=("monthly_volume_usd", "sum"), b=("baseline_monthly_volume", "sum")).reset_index()
        n["nrr"] = n.v / n.b * 100
        n["sel"] = n.category_name == r.category
        lines = alt.Chart(n).mark_line(interpolate="monotone").encode(
            x=alt.X("month:T", title=None, axis=alt.Axis(format="%b %y", labelAngle=0, tickCount=8)),
            y=alt.Y("nrr:Q", title="NRR (%)", scale=alt.Scale(zero=False)),
            detail="category_name:N",
            color=alt.condition("datum.sel", alt.value(brand.T["plum500"]), alt.value("#CDBFD8")),
            strokeWidth=alt.condition("datum.sel", alt.value(3), alt.value(1.4)),
            tooltip=[alt.Tooltip("month:T", title="Month-end", format="%B %Y"), alt.Tooltip("category_name:N", title="Category"),
                     alt.Tooltip("nrr:Q", title="NRR %", format=".1f")])
        st.altair_chart(lines.properties(height=240), use_container_width=True, theme=None)
