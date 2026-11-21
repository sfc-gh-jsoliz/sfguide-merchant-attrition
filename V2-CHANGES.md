# Merchant Attrition Early-Warning: v2 changes

This branch (`v2-rebuild`) rebuilds the pack to the Snow Packs v2 bar (see [`COCO-V2-INSTRUCTIONS.md`](COCO-V2-INSTRUCTIONS.md)). What stays the same: the use case (a processor's merchant-retention team spotting merchants decaying toward churn, and telling merchant problems from category slowdowns), the six MCC categories and the decay model, the risk-band rules, the grounded-note loop (fact pack → `AI_COMPLETE` draft → `AI_COMPLETE` verifier), the Snowflake features (`AI_COMPLETE`, the `ATTRITION_SV` semantic view, the `ATTRITION_AGENT` Cortex Agent, Streamlit in Snowflake), the optional real US Census demand backdrop, the Streamlit stack, the database, warehouse and `ATTRITION_*` object names, the notebook and the owner line. The app is titled with the pack's plain name; there is no product name.

## Screen by screen

### App shell (new)
- **Before:** a Streamlit title, a mode banner and a sidebar button; the app needed a Snowflake session to start.
- **After:** a plum left rail with the logo, a Sample/Live switch, five views, an environment badge and a role chip. Tokens, fonts (Manrope, DM Mono, bundled) and motion follow [`docs/DESIGN.md`](docs/DESIGN.md). With no connection, Live shows setup steps instead of falling back to sample data.

### Overview (new)
- KPI tiles (active merchants, save list, churned in the last 12 months, NRR) with year-on-year deltas, sparklines and count-up; an early-warning note computed from the data; watch/at-risk/churned merchants by month; a book-vs-market list with a diagnosis pill per category; and book volume vs category demand, indexed, per category.
- **Why:** the old app opened on a list of saved notes, so a first-time reader saw no numbers until they ran the AI.

### Save list (new)
- A sortable, filterable table of this month's merchants (band, category, search) with band pills and 24-month sparklines. Selecting a row shows why the merchant was flagged, its volume against baseline and its category's demand, and an **Add to outreach queue** form that writes to a new `ATTRITION_OUTREACH` table in Live mode.
- **Why:** the old app only had a category-level note; v2 asks for a drill-down and a decision.

### Categories (new)
- Each category's book YoY vs demand YoY, the gap, NRR, churn rate and band counts, with a diagnosis (retention problem, market slowdown, healthy, watch). Drill-down: YoY lines, risk bands by tenure, NRR by category.
- **Why:** makes the pack's core story ("is it the merchant or the market?") visible without reading a note.

### Attrition notes (was the whole app)
- Same loop and prompts, plus: a scope picker (all categories or one), staged steps, a streaming reveal, the verifier's flags above the note, sources (fact-pack categories, month, model, latency) under it, and a note library.
- **Fixes and changes:**
  - `AI_COMPLETE` returns its text JSON-encoded through Snowpark (`"..."` with escaped quotes); the old verifier never decoded it. The app and notebook now decode it first, and keep the last JSON object if the verifier emits several.
  - The fact pack adds the same month a year earlier, so notes can state the book's YoY change next to category demand YoY (the original contrast compared demand YoY with a baseline-based decline).
  - The verifier prompt now accepts rounding, thousands separators, correct point differences and the "retention problem / market slowdown" labels the draft is told to use; it still flags wrong numbers, invented facts, hedges and non-English text.
  - `ATTRITION_REPORTS` also stores the flags, fact pack, model and latency.
- On the synthetic data, 5 of 7 captured notes verify; the 2 flags are real (a wrong "13×" ratio and a hedged recommendation).

### Ask the agent (new in the app)
- The agent existed before but only in Snowsight. The app now calls it with `SNOWFLAKE.CORTEX.DATA_AGENT_RUN` and shows staged steps, the answer, the result table and the SQL Cortex Analyst wrote.
- The agent spec gains an `execution_environment` warehouse, a "filter to one month for merchant counts" hint and a "do not name real companies" instruction.

### Landing page (`docs/index.html`, replaces the root `index.html`)
- Its own identity: a plum-night hero with a volume "pulse" that flattens into churn, the four risk bands, a problem-first headline, five captioned screenshots with alt text, a "how Snowflake does each step" strip, run options, prerequisites, a disclaimer and doc links. Dark mode, phone width, no CDN scripts.

### Hosted example (`docs/try/`, replaces the root `try/`)
- A dependency-free static copy of all five screens. Its numbers are produced by the app's own `app/data.py` (Sample mode) through `scripts/build_example.py`, so they match the app exactly. SVG charts with tooltips, sortable table, merchant drawer with the outreach form, staged AI with the "Sample AI response" label. The Live button explains how to run Live.

## Data, SQL and repo

- **Seeded generator:** `data/generate.py` (seed `20260630`) replaces `HASH()` noise in SQL. It keeps the original decay model and writes `data/*.csv`, `app/sample/*.csv` and the INSERT block in `sql/setup.sql`. The planted stories are set on purpose (fixed churner counts per category, category demand drift, healthy merchants tracking their category) and documented in [`data/README.md`](data/README.md).
- **SQL:** `app/setup_synthetic.sql`, `app/setup.sql` and `app/teardown.sql` become `sql/setup.sql`, `sql/census_backdrop.sql` and `sql/cleanup.sql`.
  - Setup adds a least-privilege `MERCHANT_ATTRITION_ROLE` that owns everything, the synthetic demand series as a table (`ATTRITION_CATEGORY_DEMAND`) under the `ATTRITION_CATEGORY_HEALTH` view (no more TABLE/VIEW type switching), a per-merchant `ATTRITION_MERCHANT_HEALTH` view (the benchmark now reads it), `ATTRITION_OUTREACH`, extra `ATTRITION_REPORTS` columns, and an `APP_STAGE` stage.
  - `census_backdrop.sql` is the original real-data view, run after setup instead of a second full setup.
  - Cleanup drops the objects as the pack role, then drops the role.
- **Removed:** root `index.html`, `styles.css`, `try/` and `assets/` (replaced under `docs/`); short redirect stubs stay at `index.html` and `try/index.html` so your current links keep working until Pages points at `/docs`.
- **Added:** `app/` modules (`data.py`, `ai.py`, `brand.py`, `views/`), `requirements.txt` and `environment.yml` pinned to Streamlit 1.50.0, bundled fonts with their OFL licenses, `scripts/` (build, capture, contrast check), `package.json` with `npm run build:example`, and `.gitignore`.
- **Notebook:** prerequisites, fact pack, DATA RULES and verifier now match the app.
- **Self-review:** [`SELF-REVIEW.md`](SELF-REVIEW.md).
- **Verified live** on 2026-11-21 in a Snowflake demo account with key-pair auth: setup ran in 13-17 s and twice in a row; every screen ran in Live mode; Live and Sample data are identical row for row; notes took 7-13 s and agent answers 13-29 s; an outreach row was written; `CREATE STREAMLIT` from the stage succeeded (the deployed app was not opened in Snowsight); every notebook cell ran; cleanup left nothing behind (checked with SHOW).

## What to do after merging

1. **Pull:** merge `v2-rebuild` into your `main` (fast-forward), then `git pull` in your local clone.
2. **Pages:** Settings → Pages → Build and deployment → *Deploy from a branch*, branch `main`, folder **`/docs`** (it was `/ (root)`). `docs/.nojekyll` is included. The root redirect stubs can be deleted once Pages serves `/docs`.
3. After Pages redeploys, open `https://sfc-gh-jsoliz.github.io/sfguide-merchant-attrition/` and `/try/`, and check that every CSS and JS file referenced from `/try/index.html` returns 200 (`../assets/tokens.css`, `app.css`, `data.js`, `app.js`).
4. Optional: Settings → *Template repository*, and add topics (`snowflake`, `financial-services`, `payments`, `cortex`, `streamlit`).
5. Rebuild commands, if you change the data or the AI samples:

   ```bash
   python3 data/generate.py                    # regenerate data and the setup.sql data block
   # run sql/setup.sql, then with Live env vars set:
   python3 scripts/capture_sample.py           # recapture Sample AI responses from Live
   npm run build:example                        # or: python3 scripts/build_example.py
   python3 scripts/check_contrast.py           # WCAG AA check of the palette
   ```

6. The catalog card needs the new screenshots: `docs/catalog/merchant-attrition-1.jpg` … `-5.jpg` (960×600, under 100 KB each, overview first) are ready for the catalog PR.
7. To bring your other packs to v2 with your own CoCo, give it [`COCO-V2-INSTRUCTIONS.md`](COCO-V2-INSTRUCTIONS.md) together with the catalog's CONTRIBUTING.md.
