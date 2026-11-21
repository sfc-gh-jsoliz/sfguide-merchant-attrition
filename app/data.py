"""Data layer: one function per dataset, Sample (bundled CSVs) or Live (Snowflake).

Sample mode computes ATTRITION_MERCHANT_HEALTH's columns in pandas with the same
rules as sql/setup.sql; Live mode reads the views. Live never falls back to
Sample: a failed query raises, and the page shows the error.
"""
import os
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

DATABASE = "SNOWPACK_MERCHANT_ATTRITION"
SCHEMA = f"{DATABASE}.CORE"
WAREHOUSE = "SNOWPACK_MERCHANT_ATTRITION_WH"
ROLE = "MERCHANT_ATTRITION_ROLE"
SAMPLE_DIR = Path(__file__).parent / "sample"
LIVE_ENV = ("SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_PRIVATE_KEY_PATH")
BANDS = ["healthy", "watch", "at-risk", "churned"]
TENURES = ["New (<1yr)", "Established (1-3yr)", "Mature (3yr+)"]


def in_snowflake():
    """True when running as Streamlit in Snowflake (an active session exists)."""
    try:
        from snowflake.snowpark.context import get_active_session
        get_active_session()
        return True
    except Exception:
        return False


def live_configured():
    return in_snowflake() or all(os.environ.get(k) for k in LIVE_ENV)


@st.cache_resource(show_spinner=False)
def session():
    """Snowpark session: the app's own in Snowflake, key-pair auth when run locally."""
    if in_snowflake():
        from snowflake.snowpark.context import get_active_session
        return get_active_session()
    from snowflake.snowpark import Session
    return Session.builder.configs({
        "account": os.environ["SNOWFLAKE_ACCOUNT"],
        "user": os.environ["SNOWFLAKE_USER"],
        "authenticator": "SNOWFLAKE_JWT",
        "private_key_file": os.environ["SNOWFLAKE_PRIVATE_KEY_PATH"],
        "role": os.environ.get("SNOWFLAKE_ROLE", ROLE),
        "warehouse": os.environ.get("SNOWFLAKE_WAREHOUSE", WAREHOUSE),
        "database": DATABASE,
        "schema": "CORE",
    }).create()


def sql_df(q, params=None):
    df = session().sql(q, params=params or []).to_pandas()
    df.columns = [c.lower() for c in df.columns]
    return df


def _months_between(a, b):
    return (b.dt.year - a.dt.year) * 12 + (b.dt.month - a.dt.month)


def _health_from_csv():
    m = pd.read_csv(SAMPLE_DIR / "merchants.csv")
    mm = pd.read_csv(SAMPLE_DIR / "merchant_monthly.csv")
    df = mm.merge(m[["merchant_id", "merchant_name", "category_code", "category_name", "onboarded_date",
                     "baseline_monthly_volume"]], on="merchant_id")
    ratio = df.monthly_volume_usd / df.baseline_monthly_volume
    df["vol_ratio"] = ratio.round(4)
    df["volume_decline_pct"] = ((df.baseline_monthly_volume - df.monthly_volume_usd) / df.baseline_monthly_volume * 100).round(2)
    df["tenure_months"] = _months_between(pd.to_datetime(df.onboarded_date), pd.to_datetime(df.month_end))
    df["risk_band"] = np.select(
        [df.churned_flag, (df.days_since_last_txn > 45) | (ratio < 0.60), (df.days_since_last_txn > 20) | (ratio < 0.85)],
        ["churned", "at-risk", "watch"], "healthy")
    df["tenure_band"] = np.select([df.tenure_months < 12, df.tenure_months < 36], TENURES[:2], TENURES[2])
    return df


NUMERIC = ("baseline_monthly_volume", "monthly_volume_usd", "txn_count", "days_since_last_txn", "support_tickets",
           "vol_ratio", "volume_decline_pct", "tenure_months")


@st.cache_data(show_spinner=False, ttl=600)
def health(mode):
    """One row per merchant and month (ATTRITION_MERCHANT_HEALTH in Live)."""
    if mode == "Live":
        df = sql_df(f"""SELECT merchant_id, merchant_name, category_code, category_name, month_end::string AS month_end,
                               onboarded_date::string AS onboarded_date, baseline_monthly_volume, monthly_volume_usd,
                               txn_count, days_since_last_txn, support_tickets, churned_flag, vol_ratio,
                               volume_decline_pct, tenure_months, risk_band, tenure_band
                        FROM {SCHEMA}.ATTRITION_MERCHANT_HEALTH ORDER BY merchant_id, month_end""")
        for c in NUMERIC:
            df[c] = pd.to_numeric(df[c])
        df["churned_flag"] = df["churned_flag"].astype(bool)
    else:
        df = _health_from_csv().sort_values(["merchant_id", "month_end"])
    df["month"] = pd.to_datetime(df["month_end"])
    return df.reset_index(drop=True)


@st.cache_data(show_spinner=False, ttl=600)
def demand(mode):
    """Category demand backdrop, 36 months (ATTRITION_CATEGORY_HEALTH in Live)."""
    if mode == "Live":
        df = sql_df(f"""SELECT category_code, category_name, month_end::string AS month_end, market_sales_usd,
                               mom_growth_pct, yoy_growth_pct
                        FROM {SCHEMA}.ATTRITION_CATEGORY_HEALTH ORDER BY category_code, month_end""")
        for c in ("market_sales_usd", "mom_growth_pct", "yoy_growth_pct"):
            df[c] = pd.to_numeric(df[c])
    else:
        df = pd.read_csv(SAMPLE_DIR / "category_demand.csv")
    df["month"] = pd.to_datetime(df["month_end"])
    return df.reset_index(drop=True)


@st.cache_data(show_spinner=False, ttl=600)
def data_note(mode):
    if mode != "Live":
        return "synthetic", "Synthetic merchant book and synthetic category demand backdrop."
    r = sql_df(f"SELECT mode, note FROM {SCHEMA}.ATTRITION_DATA_SOURCE_INFO").iloc[0]
    return r["mode"], r["note"]


def diagnose(book_yoy, demand_yoy):
    """Merchant problem or market slowdown? Compares the book's YoY volume with category demand YoY."""
    gap = book_yoy - demand_yoy
    if gap <= -10:
        return "Retention problem"
    if demand_yoy < 0 and book_yoy < 0:
        return "Market slowdown"
    if book_yoy >= 0:
        return "Healthy"
    return "Watch"


def monthly(h):
    """Book-level series per month: counts per band, volume, baseline, NRR."""
    g = h.groupby("month")
    out = g.agg(volume=("monthly_volume_usd", "sum"), baseline=("baseline_monthly_volume", "sum"),
                tickets=("support_tickets", "sum")).reset_index()
    bands = pd.crosstab(h.month, h.risk_band).reindex(columns=BANDS, fill_value=0).reset_index()
    out = out.merge(bands, on="month")
    out["active"] = out[["healthy", "watch", "at-risk"]].sum(axis=1)
    out["nrr"] = out.volume / out.baseline * 100
    return out


def category_summary(h, d):
    """One row per category for the latest month, with book vs demand YoY and a diagnosis."""
    last = h.month.max()
    yago = last - pd.DateOffset(months=12)
    L, Y = h[h.month == last], h[h.month == yago]
    dl = d[d.month == last].set_index("category_code")
    rows = []
    for code, g in L.groupby("category_code"):
        vol, base = g.monthly_volume_usd.sum(), g.baseline_monthly_volume.sum()
        vol_y = Y[Y.category_code == code].monthly_volume_usd.sum()
        book_yoy = (vol / vol_y - 1) * 100
        dem_yoy = float(dl.loc[code, "yoy_growth_pct"])
        counts = g.risk_band.value_counts()
        series = h[h.category_code == code].groupby("month").monthly_volume_usd.sum()
        rows.append({
            "category_code": code, "category": g.category_name.iloc[0], "merchants": len(g),
            "healthy": int(counts.get("healthy", 0)), "watch": int(counts.get("watch", 0)),
            "at_risk": int(counts.get("at-risk", 0)), "churned": int(counts.get("churned", 0)),
            "active": int(len(g) - counts.get("churned", 0)),
            "churn_rate": counts.get("churned", 0) / len(g) * 100,
            "nrr": vol / base * 100, "volume": vol, "book_yoy": book_yoy, "demand_yoy": dem_yoy,
            "gap": book_yoy - dem_yoy, "diagnosis": diagnose(book_yoy, dem_yoy),
            "trend": [round(x / 1e6, 3) for x in series],
        })
    return pd.DataFrame(rows).sort_values("gap").reset_index(drop=True)


SEVERITY = {"at-risk": 0, "watch": 1, "churned": 2, "healthy": 3}


def save_list(h):
    """Latest-month merchants with signals, most urgent first."""
    last = h.month.max()
    h = h.sort_values(["merchant_id", "month"])
    prev3 = h.groupby("merchant_id").monthly_volume_usd.shift(3)
    h = h.assign(vol_3m_change=(h.monthly_volume_usd / prev3 - 1) * 100)
    # months in a row below 85% of baseline (how long the decline has run)
    below = (h.vol_ratio < 0.85).astype(int)
    block = ((below != below.shift()) | (h.merchant_id != h.merchant_id.shift())).cumsum()
    run = below.groupby(block).cumsum() * below
    h = h.assign(months_declining=run)
    first_churn = h[h.churned_flag].groupby("merchant_id").month.min()
    L = h[h.month == last].copy()
    L["churned_since"] = L.merchant_id.map(first_churn)
    L["severity"] = L.risk_band.map(SEVERITY)
    return L.sort_values(["severity", "vol_ratio"]).reset_index(drop=True)


@st.cache_data(show_spinner=False, ttl=30)
def saved_notes(mode):
    if mode != "Live":
        return None
    return sql_df(f"""SELECT run_id, subject, status, edits_applied, residual_hedges, report_md, edits,
                             fact_pack, model, latency_ms, created_at::string AS created_at
                      FROM {SCHEMA}.ATTRITION_REPORTS ORDER BY created_at DESC LIMIT 24""")
