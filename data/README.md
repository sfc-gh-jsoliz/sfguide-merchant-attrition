# Synthetic data: Merchant Attrition Early-Warning

Everything here is synthetic. `data/generate.py` (standard library only, seed `20260630`) writes these CSVs, the same CSVs in `app/sample/` (Sample mode) and the INSERT block in `sql/setup.sql`, so Sample mode and Snowflake hold identical rows. Re-running the generator gives byte-identical output.

```bash
python3 data/generate.py
```

| File | Rows | What it is |
|---|---|---|
| `categories.csv` | 6 | MCC-aligned categories and the US Census retail-sales variable each maps to |
| `merchants.csv` | 120 | 20 merchants per category: MID, MCC, onboarding date, baseline monthly volume, and the generator's ground truth (`is_churner`, `decay_start_idx`, `decay_len`), which the app never reads |
| `merchant_monthly.csv` | 2,880 | Monthly processed volume, transactions, days since last transaction, support tickets and churned flag, July 2024 to June 2026 |
| `category_demand.csv` | 216 | Category market sales with MoM and YoY growth, July 2023 to June 2026 (12 extra months so YoY has an anchor) |

## Model (the original pack's, with a seeded RNG)

- Healthy merchants follow their category's demand trend with ±5% monthly noise.
- A churner starts decaying at a month index from its category's earliest start to 21, falls linearly to about 2% of baseline over 3-8 months, then stays churned. While it decays, idle days and support tickets rise.
- Risk bands, in `ATTRITION_MERCHANT_HEALTH` (and the same rules in `app/data.py`): churned; at risk below 60% of baseline or more than 45 idle days; watch below 85% or more than 20 idle days; healthy otherwise.

## Planted stories (June 2026 vs June 2025, on this synthetic data)

| Category | Book YoY | Demand YoY | What it shows |
|---|---|---|---|
| Electronics & Appliances | −26.4% | +12.4% | **Retention problem.** 8 of 20 merchants are churners and their decay starts late (from month 13), so the book collapses while demand grows fastest. 5 churned, 1 at risk, 2 on watch. |
| Restaurants & Food Service | −15.0% | −1.2% | Also a retention problem: the book falls 13.8 points more than its market. |
| Clothing & Accessories | −15.9% | −10.6% | **Market slowdown.** Demand drifts down and healthy merchants shrink with it; only 3 churners. |
| Furniture & Home Furnishings | −8.4% | −2.2% | Market slowdown, milder. |
| Food & Beverage Stores | +5.4% | +4.4% | **Healthy benchmark.** One churner, steady demand. |
| Health & Personal Care | +2.6% | +1.3% | Healthy. |

Diagnosis rule (`app/data.py`, `diagnose`): gap = book YoY − demand YoY; a gap of −10 points or worse is a retention problem; otherwise a shrinking book in a shrinking market is a market slowdown; a growing book is healthy.

The save list in June 2026 holds 7 merchants (3 at risk, 4 on watch); 18 merchants have churned, 16 of them in the last 12 months.
