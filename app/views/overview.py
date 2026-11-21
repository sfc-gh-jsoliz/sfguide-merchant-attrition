"""Overview: the month-end early-warning picture for the merchant-retention team."""
import altair as alt
import pandas as pd
import streamlit as st

import brand
import data
from views.common import cap, load, theme


def render(mode):
    theme()
    h, d = load(mode)
    m = data.monthly(h)
    last, yago = m.month.iloc[-1], m.month.iloc[-13]
    cur, ya = m.iloc[-1], m.iloc[-13]
    first_churn = h[h.churned_flag].groupby("merchant_id").month.min()
    churned_12m = int(((first_churn > yago) & (first_churn <= last)).sum())
    churned_prev = int(((first_churn > yago - pd.DateOffset(months=12)) & (first_churn <= yago)).sum())
    trail = m.tail(12)

    st.markdown(brand.header(
        "Merchant health overview",
        f"Month-end {last:%B %Y} across {h.merchant_id.nunique()} merchants in 6 categories. Every figure comes from ATTRITION_MERCHANT_HEALTH.",
        cap(mode, "ATTRITION_MERCHANT_HEALTH view"), mode != "Live"), unsafe_allow_html=True)

    flagged, flagged_y = int(cur.watch + cur["at-risk"]), int(ya.watch + ya["at-risk"])
    tiles = [
        brand.kpi("Active merchants", brand.counter("", cur.active),
                  brand.delta(cur.active - ya.active, f"{int(cur.active - ya.active):+d} vs {yago:%b %Y}"),
                  list(trail.active), swatch=brand.BAND["healthy"][2]),
        brand.kpi("On the save list (watch + at risk)", brand.counter("", flagged),
                  brand.delta(flagged - flagged_y, f"{flagged - flagged_y:+d} vs {yago:%b %Y}", good_up=False),
                  list(trail.watch + trail["at-risk"]), color=brand.BAND["at-risk"][2], swatch=brand.BAND["at-risk"][2]),
        brand.kpi("Churned in the last 12 months", brand.counter("", churned_12m),
                  brand.delta(churned_12m - churned_prev, f"{churned_12m - churned_prev:+d} vs prior 12 months", good_up=False),
                  list(trail.churned), color=brand.BAND["churned"][2], swatch=brand.BAND["churned"][2]),
        brand.kpi("Net revenue retention", brand.counter("", int(cur.nrr), f"{cur.nrr % 1:.1f}%"[1:]),
                  brand.delta(cur.nrr - ya.nrr, f"{cur.nrr - ya.nrr:+.1f} pts vs {yago:%b %Y}"), list(trail.nrr)),
    ]
    st.markdown(f'<div class="mw-kpis">{"".join(tiles)}</div>', unsafe_allow_html=True)

    cs = data.category_summary(h, d)
    worst = cs.iloc[0]
    slow = cs[cs.diagnosis == "Market slowdown"].sort_values("demand_yoy")
    msg = (f'<b>Early warning.</b> {brand.esc(worst.category)}: the book is {brand.pct(worst.book_yoy)} year on year while '
           f'category demand is {brand.pct(worst.demand_yoy)}, a gap of {abs(worst.gap):.1f} points. That is a retention problem, not the market. ')
    if len(slow):
        s = slow.iloc[0]
        msg += (f'{brand.esc(s.category)} is shrinking too ({brand.pct(s.book_yoy)}), but its demand is also down '
                f'({brand.pct(s.demand_yoy)}): mostly a market slowdown. ')
    msg += 'Open <b>Save list</b> to work the merchants, or <b>Attrition notes</b> for a verified write-up.'
    st.markdown(f'<div class="mw-insight">{msg}</div>', unsafe_allow_html=True)

    left, right = st.columns([1.6, 1], gap="medium")
    with left.container(key="card_bands"):
        st.markdown(f'<p class="mw-card-h">Merchants off healthy, by band</p><p class="mw-card-s">Watch, at-risk and churned merchants per month-end, stacked; '
                    f'the other {int(cur.healthy)} of {int(cur.active + cur.churned)} are healthy in {last:%B %Y}. Hover for the band and month.</p>', unsafe_allow_html=True)
        long = m.melt(id_vars="month", value_vars=data.BANDS[1:], var_name="band", value_name="merchants")
        long["band_label"] = long.band.map(brand.BAND_LABEL)
        long["order"] = long.band.map({b: i for i, b in enumerate(data.BANDS)})
        chart = alt.Chart(long).mark_bar(opacity=.95, cornerRadiusTopLeft=2, cornerRadiusTopRight=2).encode(
            x=alt.X("yearmonth(month):O", title=None, axis=alt.Axis(labelExpr="timeFormat(datum.value, '%b %y')", labelAngle=-40)),
            y=alt.Y("merchants:Q", title="Merchants", stack="zero"),
            color=alt.Color("band_label:N", title=None, sort=[brand.BAND_LABEL[b] for b in data.BANDS[1:]],
                            scale=alt.Scale(domain=[brand.BAND_LABEL[b] for b in data.BANDS[1:]], range=[brand.BAND[b][2] for b in data.BANDS[1:]])),
            order=alt.Order("order:Q"),
            tooltip=[alt.Tooltip("month:T", title="Month-end", format="%B %Y"), alt.Tooltip("band_label:N", title="Band"),
                     alt.Tooltip("merchants:Q", title="Merchants")],
        ).properties(height=320)
        st.altair_chart(chart, use_container_width=True, theme=None)
    with right.container(key="card_vs"):
        st.markdown('<p class="mw-card-h">Book vs market, year on year</p><p class="mw-card-s">Merchant book volume change against category demand change. Widest gap first.</p>', unsafe_allow_html=True)
        rows = "".join(
            f'<div class="mw-cat"><div><div style="font-weight:600">{brand.esc(r.category)}</div>{brand.bandbar({"healthy": r.healthy, "watch": r.watch, "at-risk": r.at_risk, "churned": r.churned})}</div>'
            f'<div class="mw-vs">book <span class="{"up" if r.book_yoy >= 0 else "down"}">{brand.pct(r.book_yoy)}</span><br>'
            f'demand <span style="color:var(--demand);font-weight:700">{brand.pct(r.demand_yoy)}</span></div>'
            f'<div>{brand.diag_pill(r.diagnosis)}</div></div>' for r in cs.itertuples())
        st.markdown(rows + brand.legend(), unsafe_allow_html=True)

    with st.container(key="card_index"):
        st.markdown('<p class="mw-card-h">Processed volume vs category demand</p><p class="mw-card-s">Both indexed to July 2024 = 100. Solid: the merchant book. Dashed: category demand. A solid line falling under its dashed line is attrition the market does not explain.</p>', unsafe_allow_html=True)
        pick = st.selectbox("Category", ["All categories"] + list(cs.category), key="ov_cat", label_visibility="collapsed")
        hh, dd = (h, d) if pick == "All categories" else (h[h.category_name == pick], d[d.category_name == pick])
        book = hh.groupby("month").monthly_volume_usd.sum()
        dem = dd[dd.month >= h.month.min()].groupby("month").market_sales_usd.sum()
        idx = pd.concat([
            pd.DataFrame({"month": book.index, "index": book.values / book.iloc[0] * 100, "series": "Merchant book"}),
            pd.DataFrame({"month": dem.index, "index": dem.values / dem.iloc[0] * 100, "series": "Category demand"})])
        line = alt.Chart(idx).mark_line(strokeWidth=2.4, interpolate="monotone").encode(
            x=alt.X("month:T", title=None, axis=alt.Axis(format="%b %y", labelAngle=0, tickCount=8)),
            y=alt.Y("index:Q", title="Index (Jul 2024 = 100)", scale=alt.Scale(zero=False)),
            color=alt.Color("series:N", title=None, scale=alt.Scale(domain=["Merchant book", "Category demand"],
                                                                    range=[brand.T["plum500"], brand.T["demand"]])),
            strokeDash=alt.StrokeDash("series:N", legend=None, scale=alt.Scale(domain=["Merchant book", "Category demand"],
                                                                               range=[[1, 0], [6, 4]])),
            tooltip=[alt.Tooltip("month:T", title="Month-end", format="%B %Y"), alt.Tooltip("series:N", title="Series"),
                     alt.Tooltip("index:Q", title="Index", format=".1f")],
        ).properties(height=250)
        st.altair_chart(line, use_container_width=True, theme=None)
