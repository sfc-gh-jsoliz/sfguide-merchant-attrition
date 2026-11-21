"""Seeded, deterministic generator for the Merchant Attrition Early-Warning book.

Run:  python3 data/generate.py
Writes the CSVs in data/ and app/sample/ and the INSERT block between the
GENERATED DATA markers in sql/setup.sql. Same seed, same output, byte for byte.
Standard library only.

The model is the original pack's: six MCC-aligned categories x 20 merchants,
24 month-ends (Jul 2024 - Jun 2026), a fixed number of churners per category decaying linearly to ~2% of
baseline over 3-8 months and then staying churned, days-idle and support
tickets rising during the decay, and a 36-month category demand series with
MoM / YoY growth. What changed: a fixed-seed Python RNG replaces HASH() noise,
and the planted stories in data/README.md are set on purpose (per-category
churn odds, demand drift, and healthy merchants tracking their category).
"""
import calendar
import csv
import random
import re
from datetime import date
from pathlib import Path

SEED = 20260630
ROOT = Path(__file__).resolve().parent.parent
MONTHS = 24          # merchant window: Jul 2024 - Jun 2026
DEMAND_MONTHS = 36   # demand window starts 12 months earlier so YoY has an anchor
PER_CATEGORY = 20

# code, name, MCC, Census variable (seasonally adjusted advance retail sales)
CATEGORIES = [
    ("RESTAURANTS", "Restaurants & Food Service", "5812", "ADV_722SM_SA"),
    ("APPAREL", "Clothing & Accessories", "5651", "ADV_448SM_SA"),
    ("ELECTRONICS", "Electronics & Appliances", "5732", "ADV_443SM_SA"),
    ("GROCERY", "Food & Beverage Stores", "5411", "ADV_445SM_SA"),
    ("FURNITURE", "Furniture & Home Furnishings", "5712", "ADV_442SM_SA"),
    ("HEALTH", "Health & Personal Care", "5912", "ADV_446SM_SA"),
]
# code: (volume scale, churners out of 20, monthly demand drift, earliest decay start)
# Planted stories (data/README.md):
#   ELECTRONICS  demand grows fastest but the book churns most, mostly late: a retention problem.
#   APPAREL      demand shrinks and healthy merchants shrink with it: a market slowdown.
#   GROCERY      low churn, steady demand: the healthy benchmark.
DRIVERS = {
    "RESTAURANTS": (1.30, 5, 0.0035, 6),
    "APPAREL": (0.80, 3, -0.0045, 6),
    "ELECTRONICS": (0.90, 8, 0.0055, 13),
    "GROCERY": (1.20, 1, 0.0030, 6),
    "FURNITURE": (0.70, 5, -0.0010, 6),
    "HEALTH": (1.00, 4, 0.0040, 6),
}


def month_end(y, m):
    return date(y, m, calendar.monthrange(y, m)[1])


def months_from(y, m, n):
    out = []
    for _ in range(n):
        out.append(month_end(y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def add_months(d, k):
    y, m = d.year, d.month + k
    while m <= 0:
        y, m = y - 1, m + 12
    while m > 12:
        y, m = y + 1, m - 12
    return date(y, m, 1)


def build():
    rng = random.Random(SEED)
    months = months_from(2024, 7, MONTHS)
    dmonths = months_from(2023, 7, DEMAND_MONTHS)
    cats = [dict(category_code=c, category_name=n, mcc=mcc, census_variable=v) for c, n, mcc, v in CATEGORIES]

    merchants, monthly = [], []
    for c in cats:
        code = c["category_code"]
        scale, n_churn, drift, earliest = DRIVERS[code]
        churners = set(rng.sample(range(1, PER_CATEGORY + 1), n_churn))
        for k in range(1, PER_CATEGORY + 1):
            mid = f"{code}-{k:03d}"
            onboarded = add_months(date(2024, 7, 1), -rng.randrange(48))
            baseline = round((rng.randrange(480001) + 20000) * scale)
            is_churner = k in churners
            decay_start = rng.randrange(earliest, 22)
            decay_len = 3 + rng.randrange(6)
            merchants.append(dict(merchant_id=mid, merchant_name=f"Merchant {mid}", mcc=c["mcc"],
                                  category_code=code, category_name=c["category_name"],
                                  onboarded_date=onboarded.isoformat(), baseline_monthly_volume=baseline,
                                  is_churner=str(is_churner).upper(), decay_start_idx=decay_start,
                                  decay_len=decay_len))
            done = decay_start + decay_len
            for i, me in enumerate(months):
                noise = (rng.randrange(11) - 5) / 100.0
                if not is_churner or i < decay_start:
                    decay = 1.0
                elif i >= done:
                    decay = 0.02
                else:
                    decay = 1.0 - (i - decay_start) / decay_len * 0.95
                churned = is_churner and i >= done
                # healthy merchants follow their category's demand trend (original: +0.4%/month for all)
                vol = max(round(baseline * (1 + (drift + 0.0005) * i) * decay * (1 + noise)), 0)
                if churned:
                    idle = 60 + (i - done) * 30
                    tickets = 0
                elif decay < 1.0:
                    idle = round(5 + (1 - decay) * 50)
                    tickets = round(2 + (1 - decay) * 4)
                else:
                    idle = rng.randrange(11)
                    tickets = rng.randrange(2)
                monthly.append(dict(merchant_id=mid, month_end=me.isoformat(), monthly_volume_usd=vol,
                                    txn_count=round(vol / 85.0), days_since_last_txn=idle,
                                    support_tickets=tickets, churned_flag=str(churned).upper()))

    demand = []
    for c in cats:
        scale, _, drift, _ = DRIVERS[c["category_code"]]
        series = [round(scale * 6.0e10 * (1 + drift * g) * (1 + (rng.randrange(7) - 3) / 100.0))
                  for g in range(DEMAND_MONTHS)]
        for g, me in enumerate(dmonths):
            mom = round((series[g] / series[g - 1] - 1) * 100, 2) if g >= 1 else ""
            yoy = round((series[g] / series[g - 12] - 1) * 100, 2) if g >= 12 else ""
            demand.append(dict(category_code=c["category_code"], category_name=c["category_name"],
                               month_end=me.isoformat(), market_sales_usd=series[g],
                               mom_growth_pct=mom, yoy_growth_pct=yoy))
    return cats, merchants, monthly, demand


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def sql_value(v):
    if v == "":
        return "NULL"
    if isinstance(v, (int, float)):
        return repr(v)
    if v in ("TRUE", "FALSE"):
        return v
    return "'" + str(v).replace("'", "''") + "'"


def inserts(table, rows, chunk=500):
    cols = list(rows[0])
    out = []
    for s in range(0, len(rows), chunk):
        vals = ",\n".join("  (" + ", ".join(sql_value(r[c]) for c in cols) + ")" for r in rows[s:s + chunk])
        out.append(f"INSERT INTO {table} ({', '.join(cols)}) VALUES\n{vals};")
    return "\n\n".join(out)


def main():
    cats, merchants, monthly, demand = build()
    files = {"categories.csv": cats, "merchants.csv": merchants, "merchant_monthly.csv": monthly,
             "category_demand.csv": demand}
    for name, rows in files.items():
        write_csv(ROOT / "data" / name, rows)
        write_csv(ROOT / "app" / "sample" / name, rows)
    block = "\n\n".join([
        f"-- Generated by data/generate.py (seed {SEED}). Do not edit by hand.",
        inserts("ATTRITION_MERCHANT_CATEGORY", cats),
        inserts("ATTRITION_MERCHANT", merchants),
        inserts("ATTRITION_MERCHANT_MONTHLY", monthly),
        inserts("ATTRITION_CATEGORY_DEMAND", demand),
    ])
    setup = ROOT / "sql" / "setup.sql"
    text = setup.read_text()
    new = re.sub(r"(-- BEGIN GENERATED DATA\n).*?(-- END GENERATED DATA)",
                 lambda m: m.group(1) + block + "\n" + m.group(2), text, flags=re.S)
    setup.write_text(new)
    print(f"{len(cats)} categories, {len(merchants)} merchants, {len(monthly)} merchant-months, "
          f"{len(demand)} demand rows; churners {sum(m['is_churner'] == 'TRUE' for m in merchants)}")


if __name__ == "__main__":
    main()
