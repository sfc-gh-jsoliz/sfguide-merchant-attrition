import json
import streamlit as st
from snowflake.snowpark.context import get_active_session

st.set_page_config(page_title="Merchant Attrition Early-Warning", layout="wide")

SCHEMA = "SNOWPACK_MERCHANT_ATTRITION.CORE"
MODEL = "claude-sonnet-4-5"
session = get_active_session()
_rerun = getattr(st, "rerun", getattr(st, "experimental_rerun", lambda: None))
BADGE = {"verified": "✅ Verified", "needs_review": "⚠️ Needs review"}


def sql_df(q, p=None):
    df = session.sql(q, params=p or []).to_pandas()
    df.columns = [c.lower() for c in df.columns]
    return df


def data_mode():
    try:
        r = session.sql(f"SELECT mode, note FROM {SCHEMA}.ATTRITION_DATA_SOURCE_INFO").collect()[0]
        return r[0], r[1]
    except Exception:
        return "unknown", ""


def load_reports():
    return sql_df(f"SELECT run_id, subject, status, edits_applied, residual_hedges, report_md, created_at FROM {SCHEMA}.ATTRITION_REPORTS ORDER BY created_at DESC")


def fact_pack():
    return session.sql(f"""
        WITH latest AS (SELECT MAX(month_end) z FROM {SCHEMA}.ATTRITION_BENCHMARK)
        SELECT ARRAY_AGG(OBJECT_CONSTRUCT(
          'category', g.category_name, 'month', g.month_end::string,
          'total_merchants', g.total_merchants, 'active_merchants', g.active_merchants,
          'churned_merchants', g.churned_merchants, 'at_risk_merchants', g.at_risk_merchants,
          'churn_rate_pct', g.churn_rate_pct, 'net_revenue_retention_pct', g.nrr_pct,
          'avg_volume_decline_pct', g.avg_vol_decline, 'category_yoy_growth_pct', g.cat_yoy))
        FROM (
          SELECT b.category_name, b.month_end,
                 SUM(b.merchant_count)        AS total_merchants,
                 SUM(b.active_merchant_count) AS active_merchants,
                 SUM(b.churned_count)         AS churned_merchants,
                 SUM(b.at_risk_count)         AS at_risk_merchants,
                 ROUND(SUM(b.churned_count)*100.0/NULLIF(SUM(b.merchant_count),0),1)        AS churn_rate_pct,
                 ROUND(SUM(b.monthly_volume_usd)*100.0/NULLIF(SUM(b.baseline_volume_usd),0),1) AS nrr_pct,
                 ROUND(AVG(b.avg_volume_decline_pct),1) AS avg_vol_decline,
                 ROUND(AVG(b.category_yoy_growth_pct),1) AS cat_yoy
          FROM {SCHEMA}.ATTRITION_BENCHMARK b JOIN latest ON b.month_end = latest.z
          GROUP BY b.category_name, b.month_end
        ) g
    """).collect()[0][0]


def draft_note(fp):
    rules = (
        "You are a payments merchant-retention analyst. Write a concise attrition early-warning note using ONLY the FACTS JSON.\n"
        "DATA RULES: use only numbers in FACTS, copy exactly; churn_rate_pct and net_revenue_retention_pct are percentages; "
        "avg_volume_decline_pct positive = below baseline; category_yoy_growth_pct is the category demand backdrop — contrast merchant attrition against it; "
        "dollars are USD; no estimates, no hedging, no outside benchmarks; missing = n/d.\n"
        "OUTPUT markdown starting with '# ', a one-line takeaway (where attrition is worst), a table "
        "(category | active | churned | at-risk | churn rate % | NRR % | category YoY %), 3 bullets prioritizing a save-list, ending with '## Data Coverage'."
    )
    return session.sql("SELECT AI_COMPLETE(?, ?)", params=[MODEL, rules + f"\n\nFACTS: {fp}"]).collect()[0][0]


def verify(fp, draft):
    vp = (
        "You are a fact-checker. Compare the DRAFT against the FACTS JSON (only allowed source). Return ONLY a JSON object with keys "
        "status ('verified' if every number/claim is supported and no hedge words like likely/approximately/around/could, else 'needs_review'), "
        "residual_hedges (int), edits (array of strings).\n\n" + f"FACTS: {fp}\n\nDRAFT:\n{draft}"
    )
    raw = session.sql("SELECT AI_COMPLETE(?, ?)", params=[MODEL, vp]).collect()[0][0]
    s, e = raw.find("{"), raw.rfind("}")
    try:
        return json.loads(raw[s:e + 1])
    except Exception:
        return {"status": "needs_review", "residual_hedges": None, "edits": ["unparseable verifier output"]}


st.title("Merchant Attrition Early-Warning")
st.caption("A payments processor's merchant book decaying toward churn, contextualized against category demand (US Census retail sales).")
_mode, _note = data_mode()
if _mode == "synthetic":
    st.warning("Sample mode — synthetic category backdrop. " + _note)
elif _mode == "marketplace":
    st.info("Live category demand — " + _note)

if "view" not in st.session_state:
    st.session_state["view"] = "gallery"

with st.sidebar:
    st.subheader("Generate a note")
    st.caption("Rolls up merchant health by category and writes a verified attrition save-list note.")
    if st.button("Run attrition analysis", type="primary", use_container_width=True):
        with st.spinner("Fact pack → grounded draft → verify (~20-40s)..."):
            fp = fact_pack()
            draft = draft_note(fp)
            v = verify(fp, draft)
            status = "verified" if v.get("status") == "verified" else "needs_review"
            session.sql(
                f"INSERT INTO {SCHEMA}.ATTRITION_REPORTS (subject, draft_md, report_md, status, edits_applied, residual_hedges) SELECT ?, ?, ?, ?, ?, ?",
                params=["Merchant attrition early-warning", draft, draft, status, len(v.get("edits", [])), v.get("residual_hedges")],
            ).collect()
        st.success(f"Done — {BADGE[status]}")
        st.session_state["view"] = "gallery"
        _rerun()

if st.session_state["view"].startswith("report:"):
    run_id = st.session_state["view"].split(":", 1)[1]
    rpt = load_reports()
    row = rpt[rpt["run_id"] == run_id]
    if st.button("← Back to gallery"):
        st.session_state["view"] = "gallery"
        _rerun()
    if not row.empty:
        r = row.iloc[0]
        st.markdown(f"**{BADGE.get(r['status'], r['status'])}**  &nbsp; residual hedges: {r['residual_hedges']}  |  flagged: {r['edits_applied']}")
        st.divider()
        st.markdown(r["report_md"])
else:
    reports = load_reports()
    if reports.empty:
        st.info("No notes yet. Use the sidebar to generate one.")
    else:
        cols = st.columns(3)
        for i, (_, r) in enumerate(reports.iterrows()):
            with cols[i % 3]:
                c = st.container()
                c.markdown(f"**{BADGE.get(r['status'], r['status'])}**")
                c.markdown(f"**{r['subject']}**")
                c.caption(f"{str(r['created_at'])[:16]} · {r['edits_applied']} flagged")
                if c.button("Open report", key=f"open_{r['run_id']}", use_container_width=True):
                    st.session_state["view"] = f"report:{r['run_id']}"
                    _rerun()
                c.markdown("---")
