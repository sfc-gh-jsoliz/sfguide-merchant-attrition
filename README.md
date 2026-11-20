# Merchant Attrition Early-Warning — a Snow Pack

Flag the merchants whose processed volume is quietly decaying toward churn — and tell whether it's the merchant or the whole category slowing — before they leave, built on Snowflake.

Owner: Javier Soliz · Last reviewed: November 2026

## What it shows

A payments processor / acquirer merchant-retention team rolls up merchant health by category and surfaces an early-warning, save-list view:

- A **gallery** of attrition notes, each badged **Verified** or **Needs review**.
- A **sidebar** that rolls up merchant health per category (active, churned, at-risk, churn rate %, net revenue retention %) and writes a one-page note.
- Each note contrasts a category's merchant decline against its **retail-sales demand backdrop**, so a merchant book shrinking while its category is *growing* stands out as a fixable retention problem rather than a market-wide slowdown.

Capabilities shown: Cortex `AI_COMPLETE`, Cortex Agents, Cortex Analyst, Semantic Views, Streamlit in Snowflake, Snowflake SQL.

## How it works

1. **Semantic view** (`ATTRITION_SV`) gives governed business meaning over merchant health by category, month, risk band and tenure.
2. **Fact pack** — the app queries the benchmark view for the rolled-up latest-month facts per category; this is the agent's entire allowed universe of numbers.
3. **Grounded draft** — the app calls Cortex `AI_COMPLETE` to write the save-list note under strict DATA RULES: copy figures exactly, contrast decline against category demand, no estimates or outside benchmarks.
4. **Verifier** — a second `AI_COMPLETE` pass checks every claim against the fact pack and flags the note Verified or Needs review.

Setup also creates a **Cortex Agent** (`ATTRITION_AGENT`) and the **Cortex Analyst semantic view** it sits on. These are explorable in Snowsight (AI & ML → Agents) for natural-language Q&A — they are **not** called by the Streamlit app, which uses `AI_COMPLETE` directly.

The pack contrasts synthetic merchant decline against a real demand backdrop: the free, public **US Census Advance Retail Sales** series by category. In sample mode that backdrop is synthetic too, so nothing external is needed.

## Prerequisites

- Snowflake Enterprise Edition or higher, in a region where Cortex AISQL and Cortex Agents are available.
- A Snowflake account with Cortex AI functions available in your region (`AI_COMPLETE`; defaults to `claude-sonnet-4-5` — change the `MODEL` parameter in the app if your account differs).
- A role that can `CREATE DATABASE` and `CREATE WAREHOUSE` (the setup scripts create their own dedicated database, schema, and warehouse).
- Streamlit in Snowflake enabled.
- **Sample mode** is fully synthetic — no Marketplace listing required.
- **Real-data mode** mounts the free, public **Financial Data Package** listing (`SNOWFLAKE_PUBLIC_DATA_FINANCIAL_PACKAGE`, US Census retail sales).

## Setup

1. **Sample (synthetic) mode:** run [`app/setup_synthetic.sql`](app/setup_synthetic.sql). Creates everything on synthetic merchant data with a synthetic category backdrop — no listing required.
2. **Real-data mode:** in Snowsight → Marketplace, get the free **Financial Data Package** (`SNOWFLAKE_PUBLIC_DATA_FINANCIAL_PACKAGE`), then run [`app/setup.sql`](app/setup.sql). The merchant book stays synthetic; the category demand backdrop becomes real US Census retail sales.
3. **Deploy the app:** create a Streamlit in Snowflake over [`app/streamlit_app.py`](app/streamlit_app.py) **inside `SNOWPACK_MERCHANT_ATTRITION.CORE`** — create the stage and the `STREAMLIT` object in that schema (upload to a stage and `CREATE STREAMLIT`, or paste it into a new Streamlit in Snowsight) so `teardown.sql` removes them with the database. Run it with a role that can read the `CORE` schema.
4. **(Optional) Explore the agent:** Snowsight → AI & ML → Agents → **Merchant Attrition Agent**.

Both scripts build the identical objects, so the app, semantic view, and agent are unchanged between modes. `ATTRITION_CATEGORY_HEALTH` is a TABLE in sample mode and a VIEW in real-data mode, so each script drops the other type first (only one mode is deployed at a time in the shared schema).

[`notebook/lab-merchant-attrition.ipynb`](notebook/) is a step-by-step lab that builds the whole pattern (semantic view → fact pack → grounded draft → verifier → persist) cell by cell.

## Customize with Cortex Code

Open this pack in Cortex Code and adapt it to your own retention model with prompts like:

- "Add a 90-day attrition-probability score per merchant to `ATTRITION_MERCHANT_MONTHLY` and surface it in the save-list, so churn risk is ranked instead of a flat at-risk flag."
- "Redefine net revenue retention (NRR) to use trailing-12-month processed volume instead of month-over-month, and update `ATTRITION_SV` and the fact pack so the note's NRR % matches."
- "Swap the US Census Advance Retail Sales backdrop for a finer category demand series and re-map the MCC → Census variable crosswalk in `ATTRITION_MERCHANT_CATEGORY`, so the demand contrast lines up with my merchant categories."

## Objects created

| Object | Type | Purpose |
|---|---|---|
| `SNOWPACK_MERCHANT_ATTRITION` | Database | Dedicated, isolated home for this pack |
| `SNOWPACK_MERCHANT_ATTRITION.CORE` | Schema | Holds all objects below |
| `SNOWPACK_MERCHANT_ATTRITION_WH` | Warehouse (XSMALL) | Dedicated compute; auto-suspend 60s |
| `ATTRITION_MERCHANT_CATEGORY` | Table | Category dimension (MCC → Census variable mapping) |
| `ATTRITION_MERCHANT` | Table | Synthetic merchant master (MID, MCC, onboarding, baseline volume) |
| `ATTRITION_MERCHANT_MONTHLY` | Table | Synthetic monthly processed volume + health signals |
| `ATTRITION_CATEGORY_HEALTH` | Table (sample) / View (real) | Category demand backdrop with MoM / YoY growth |
| `ATTRITION_BENCHMARK` | View | Wide pre-joined grain (category/month/risk/tenure) for the semantic view |
| `ATTRITION_DATA_SOURCE_INFO` | View | Marker exposing the active data mode to the app |
| `ATTRITION_SV` | Semantic view | Governed model for Cortex Analyst |
| `ATTRITION_REPORTS` | Table | Persisted generated notes (draft, status, hedge counts) |
| `ATTRITION_AGENT` | Cortex Agent | Cortex Analyst agent over `ATTRITION_SV` (explorable in Snowsight) |
| Streamlit app | Streamlit in Snowflake | The gallery + note-generation UI (deployed in step 3) |

## Cost & time

Setup runs in a few minutes on the XSMALL warehouse. Ongoing cost is minimal: the warehouse auto-suspends after 60 seconds, and the main variable cost is Cortex `AI_COMPLETE` token usage each time a note is generated and verified (two model calls per note). Review Cortex pricing and regional feature availability for your account.

## Known limitations

- The merchant book (`ATTRITION_MERCHANT`, `ATTRITION_MERCHANT_MONTHLY`) is **synthetic** in both modes — a specific acquirer's merchant-level volume has no public source.
- The category demand benchmark is at category/month granularity (US Census Advance Retail Sales), not merchant level.
- The hosted Try page uses **mocked** AI responses for illustration — it is not live inference.
- This is an illustrative example, not a production system. Validate AI output and involve the relevant business owner before relying on it.

## Cleanup

Run [`app/teardown.sql`](app/teardown.sql) to drop the dedicated database (all objects) and the dedicated warehouse.

## Learn more

- [Cortex AISQL (`AI_COMPLETE` and related functions)](https://docs.snowflake.com/en/user-guide/snowflake-cortex/aisql)
- [Cortex Agents](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-agents)
- [Cortex Analyst](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst)
- [Streamlit in Snowflake](https://docs.snowflake.com/en/developer-guide/streamlit/about-streamlit)

## License

Apache 2.0 (see [`LICENSE`](LICENSE)). Illustrative example, as-is, not supported by Snowflake Support. This is not an official Snowflake product. Contains no customer data. Review and test before any production use.
