"""Save list: merchants on watch or at risk this month, with a detail panel and an outreach action."""
import altair as alt
import pandas as pd
import streamlit as st

import brand
import data
from views.common import cap, load, theme

ACTIONS = ["Relationship call", "Pricing review", "Service recovery", "Monitor only"]


def why(r):
    out = []
    if r.vol_ratio < 0.60:
        out.append(f"Volume is {r.vol_ratio * 100:.0f}% of baseline (at-risk line: 60%).")
    elif r.vol_ratio < 0.85:
        out.append(f"Volume is {r.vol_ratio * 100:.0f}% of baseline (watch line: 85%).")
    if r.days_since_last_txn > 45:
        out.append(f"{int(r.days_since_last_txn)} days since the last transaction (at-risk line: 45).")
    elif r.days_since_last_txn > 20:
        out.append(f"{int(r.days_since_last_txn)} days since the last transaction (watch line: 20).")
    if r.support_tickets >= 2:
        out.append(f"{int(r.support_tickets)} support tickets this month.")
    if r.months_declining >= 2:
        out.append(f"Below 85% of baseline for {int(r.months_declining)} months in a row.")
    if r.risk_band == "churned":
        out.append(f"Churned since {pd.Timestamp(r.churned_since):%B %Y}.")
    return out or ["Inside every threshold this month."]


def save_outreach(mode, r, action, owner, note):
    if mode == "Live":
        data.session().sql(
            f"INSERT INTO {data.SCHEMA}.ATTRITION_OUTREACH (merchant_id, risk_band, action, owner, note) SELECT ?, ?, ?, ?, ?",
            params=[r.merchant_id, r.risk_band, action, owner, note]).collect()
    st.session_state.setdefault("outreach", []).insert(0, {"merchant_id": r.merchant_id, "action": action, "owner": owner})


def detail(mode, r, h, d):
    st.markdown(f'<div style="display:flex;gap:.6rem;align-items:center;flex-wrap:wrap"><p class="mw-card-h" style="margin:0">'
                f'{brand.esc(r.merchant_id)}</p>{brand.pill(r.risk_band)}<span class="mw-card-s" style="margin:0">'
                f'{brand.esc(r.category_name)} · {brand.esc(r.tenure_band)}</span></div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="mw-facts">'
        f'<div><small>Volume, {r.month:%b %Y}</small><b>{brand.usd(r.monthly_volume_usd)}</b></div>'
        f'<div><small>Baseline / month</small><b>{brand.usd(r.baseline_monthly_volume)}</b></div>'
        f'<div><small>Days idle</small><b>{int(r.days_since_last_txn)}</b></div>'
        f'<div><small>Support tickets</small><b>{int(r.support_tickets)}</b></div></div>', unsafe_allow_html=True)
    st.markdown('<ul class="mw-why">' + "".join(f"<li>{brand.esc(w)}</li>" for w in why(r)) + "</ul>", unsafe_allow_html=True)

    g = h[h.merchant_id == r.merchant_id].sort_values("month")
    dem = d[(d.category_code == r.category_code) & (d.month >= g.month.min())].sort_values("month")
    vol = pd.DataFrame({"month": g.month, "value": g.vol_ratio * 100, "series": "Merchant volume, % of baseline"})
    dmd = pd.DataFrame({"month": dem.month, "value": dem.market_sales_usd.values / dem.market_sales_usd.iloc[0] * 100,
                        "series": "Category demand, indexed"})
    both = pd.concat([vol, dmd])
    dom = ["Merchant volume, % of baseline", "Category demand, indexed"]
    base = alt.Chart(both).encode(x=alt.X("month:T", title=None, axis=alt.Axis(format="%b %y", labelAngle=0, tickCount=6)))
    lines = base.mark_line(strokeWidth=2.2, interpolate="monotone").encode(
        y=alt.Y("value:Q", title="% (Jul 2024 = 100 for demand)"),
        color=alt.Color("series:N", title=None, scale=alt.Scale(domain=dom, range=[brand.T["plum500"], brand.T["demand"]])),
        strokeDash=alt.StrokeDash("series:N", legend=None, scale=alt.Scale(domain=dom, range=[[1, 0], [6, 4]])),
        tooltip=[alt.Tooltip("month:T", title="Month-end", format="%B %Y"), alt.Tooltip("series:N", title="Series"),
                 alt.Tooltip("value:Q", title="Value", format=".1f")])
    rules = alt.Chart(pd.DataFrame({"y": [85, 60], "t": ["watch 85%", "at risk 60%"]})).mark_rule(
        strokeDash=[2, 3], color=brand.BAND["at-risk"][2], opacity=.7).encode(y="y:Q", tooltip=alt.Tooltip("t:N", title="Threshold"))
    st.altair_chart((lines + rules).properties(height=220), use_container_width=True, theme=None)

    if r.risk_band in ("watch", "at-risk"):
        with st.form(key=f"outreach_{r.merchant_id}", border=False):
            c1, c2 = st.columns(2)
            action = c1.selectbox("Next step", ACTIONS)
            owner = c2.text_input("Owner", value="Retention desk")
            note = st.text_input("Note", placeholder="Optional")
            if st.form_submit_button("Add to outreach queue", type="primary", width="stretch"):
                try:
                    save_outreach(mode, r, action, owner[:60], note[:300])
                    st.success(f"{r.merchant_id} added: {action}, owner {owner}. "
                               + ("Saved to ATTRITION_OUTREACH." if mode == "Live" else "Sample mode: kept in this session only."))
                except Exception as e:
                    st.error(f"Could not save to ATTRITION_OUTREACH: {e}")


def render(mode):
    theme()
    h, d = load(mode)
    sl = data.save_list(h)
    last = h.month.max()
    st.markdown(brand.header(
        "Save list", f"Merchants to call this month ({last:%B %Y}), most urgent first. Select a row for the merchant's signals and to queue outreach.",
        cap(mode, "ATTRITION_MERCHANT_HEALTH view"), mode != "Live"), unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1.3, 1.3, 1])
    bands = c1.multiselect("Risk band", data.BANDS, default=["at-risk", "watch"], format_func=brand.BAND_LABEL.get, key="sl_bands")
    cats = c2.multiselect("Category", sorted(sl.category_name.unique()), key="sl_cats", placeholder="All categories")
    q = c3.text_input("Search merchant ID", key="sl_q", placeholder="e.g. ELECTRONICS-0")
    f = sl[sl.risk_band.isin(bands or data.BANDS)]
    if cats:
        f = f[f.category_name.isin(cats)]
    if q:
        f = f[f.merchant_id.str.contains(q.strip(), case=False, regex=False)]

    counts = sl.risk_band.value_counts()
    st.markdown(" ".join(f'{brand.pill(b)} <span style="font-family:var(--mono);margin-right:.9rem">{counts.get(b, 0)}</span>'
                         for b in data.BANDS), unsafe_allow_html=True)

    if f.empty:
        st.markdown('<div class="mw-card mw-empty"><b>No merchants match</b>Clear a filter or add the Healthy band.</div>', unsafe_allow_html=True)
        return

    trends = h.groupby("merchant_id").vol_ratio.apply(lambda s: [round(x * 100, 1) for x in s])
    t = pd.DataFrame({
        "Merchant": f.merchant_id, "Category": f.category_name, "Band": f.risk_band.map(brand.BAND_LABEL),
        "Volume % of baseline": (f.vol_ratio * 100).round(1), "3-mo change %": f.vol_3m_change.round(1),
        "Days idle": f.days_since_last_txn.astype(int), "Tickets": f.support_tickets.astype(int),
        "Months declining": f.months_declining.astype(int), "Tenure": f.tenure_band,
        "24-month volume": f.merchant_id.map(trends),
    }).reset_index(drop=True)
    soft = {brand.BAND_LABEL[b]: brand.BAND[b] for b in data.BANDS}
    styled = t.style.map(lambda v: f"background-color:{soft[v][1]};color:{soft[v][0]};font-weight:700", subset=["Band"])
    with st.container(key="card_table"):
        ev = st.dataframe(styled, hide_index=True, width="stretch", on_select="rerun", selection_mode="single-row",
                          key="sl_table", height=min(420, 38 + 35 * len(t)),
                          column_config={
                              "24-month volume": st.column_config.LineChartColumn("24-month volume", y_min=0, y_max=130),
                              "Volume % of baseline": st.column_config.NumberColumn(format="%.1f%%"),
                              "3-mo change %": st.column_config.NumberColumn(format="%+.1f%%"),
                          })
        st.caption(f"{len(t)} merchants · sort by any column header · thresholds: watch under 85% of baseline or 20+ idle days, at risk under 60% or 45+ idle days.")
    rows = ev.selection.rows if ev and ev.selection else []
    pick = t.Merchant.iloc[rows[0]] if rows else t.Merchant.iloc[0]
    r = f[f.merchant_id == pick].iloc[0]
    with st.container(key="card_detail"):
        if not rows:
            st.markdown('<p class="mw-card-s">Showing the most urgent merchant. Select a row to switch.</p>', unsafe_allow_html=True)
        detail(mode, r, h, d)
    q = st.session_state.get("outreach") or []
    if q:
        st.markdown('<p class="mw-card-h" style="margin-top:1rem">Outreach queued this session</p>' +
                    "".join(f'<div class="mw-cat"><div class="n">{brand.esc(x["merchant_id"])}</div><div>{brand.esc(x["action"])}</div>'
                            f'<div style="color:var(--muted);font-size:.8rem">{brand.esc(x["owner"])}</div></div>' for x in q[:8]),
                    unsafe_allow_html=True)
