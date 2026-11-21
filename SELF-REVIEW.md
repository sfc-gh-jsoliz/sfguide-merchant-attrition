# Self-review (v2 rebuild, 2026-11-21)

Every item from the build standard's "Before you call it done" list and every CONTRIBUTING Must and Should, checked on the `v2-rebuild` branch. All results are from this build session.

## Build standard: before you call it done

| Item | Result | Evidence |
|---|---|---|
| App runs from a fresh clone in mock (Sample) mode | pass | Fresh `git clone` of `v2-rebuild`, no Snowflake env vars: all five views render in Sample mode with no exceptions |
| Setup → Live mode → cleanup in a clean role | pass | `sql/setup.sql` run with key-pair auth (13-17 s, also twice in a row); every view, the note, the agent and the outreach action exercised in Live in a browser as `MERCHANT_ATTRITION_ROLE`; `sql/cleanup.sql` then `SHOW DATABASES/WAREHOUSES/ROLES/STREAMLITS/AGENTS` all empty |
| Grep files and git history for secrets, account identifiers, user names | pass | No account locators, account names, user names, local paths, key material or `.pyc` files in HEAD or pushed history; only public example-pack links in `COCO-V2-INSTRUCTIONS.md` |
| Pages URL and `/try/` signed out; phone width; dark mode | pass | Fork preview (`v2-rebuild` `/docs`): guide and `/try/` 200, every referenced CSS/JS/font/image 200, no console errors or sideways scroll at 390 px and 1440 px. Guide has a dark mode; the app is light-only by design (see DESIGN.md) |
| Story beats visible in a screenshot | pass | Overview and Categories screenshots show Electronics & Appliances as a retention problem (book −26.4% vs demand +12.4%) and Clothing & Accessories as a market slowdown; Save list shows the at-risk merchants |

## CONTRIBUTING Musts

| Must | Result | Notes |
|---|---|---|
| Business problem first; one industry and function | pass | Payments · merchant retention (Operations) |
| Public repo `sfguide-<topic>`, Apache 2.0 LICENSE | pass | Unchanged |
| GitHub Pages enabled (`.nojekyll` if needed) | pass on fork / pending on owner repo | `docs/.nojekyll` included; owner switches Pages to `main` `/docs` after merge (V2-CHANGES.md) |
| Landing: problem and outcome on first screen | pass | Problem-first headline and scenario |
| Screenshots of the running app with captions naming the capability, and alt text | pass | Five screenshots from the Streamlit app; alt text describes each image |
| Name the capability behind each step; claim only what was used and tested | pass | AI_COMPLETE, Cortex Agents, Cortex Analyst, semantic views, Streamlit in Snowflake, SQL views, all run live |
| Visible disclaimer; repo and docs links | pass | Disclaimer band; all docs links return 200 |
| No Snowflake logo files; no internal sales motions | pass | Own SVG mark |
| End-user app with navigation, drill-downs and an action | pass | Five views, row drill-downs, outreach action |
| No-account mode | pass | Sample mode and hosted `/try/` |
| Simulated AI labeled "Sample AI response" | pass | App and `/try/` |
| Live mode on Snowflake, same app | pass | Live equals Sample row for row (merchant health and demand compared column by column) |
| Synthetic data only | pass | Seeded generator; AI text scanned for company names: none |
| Self-contained setup (own DB, XSMALL warehouse, 60 s suspend) | pass | |
| Cleanup removes everything | pass | Confirmed with SHOW |
| No credentials, account IDs, internal hostnames in code, screenshots, history | pass | See leak scan |
| User names redacted | pass | `<YOUR_USER>` placeholders |
| No customer data or internal references | pass | |
| GA features or labeled preview | pass | No preview features used |
| README: prerequisites, run steps, objects table, cost and time, limitations, Customize with Cortex Code, owner and review date, license and as-is disclaimer | pass | |
| Outcomes as possibilities; synthetic results qualified | pass | "on this synthetic data set" |

## CONTRIBUTING Shoulds

| Should | Result | Notes |
|---|---|---|
| Template repository, description and topics | skipped | Repository settings belong to the owner; listed in V2-CHANGES.md "after merging" |
| Several screenshots, overview first | pass | |
| Prerequisites, time and cost near the top of the landing page | pass | Hero facts |
| Phone width and dark mode on the landing page | pass | |
| No trackers or CDN scripts | pass | Fonts bundled |
| Sample/Live switch in the header; Live default when connected; setup steps when not; no silent fallback | pass | Rail switch; Live query errors are shown, not replaced |
| Realistic 4-8 s staged AI wait in Sample; same truthful steps in Live with measured latency | pass | |
| Capability badges in the UI | pass | "Powered by" chips and Live/Sample caption on every view |
| Polish, no empty or error screens in the main flow | pass | Empty states only when filters exclude everything |
| Hosted example usable at 390 px | pass | |
| Least-privilege role | pass | `MERCHANT_ATTRITION_ROLE` |
| Edition notes | pass | Enterprise noted in README |
| Setup runs top to bottom with no find-and-replace | pass | |
| "Example" not "demo" on customer-facing pages | pass | |

## v2 bar (00c)

| Item | Result | Notes |
|---|---|---|
| `docs/DESIGN.md`: brand, palette, type, layout, distinct from 5+ live packs | pass | Compared with 11 packs |
| No coined product name; plain pack name as the title | pass | "Merchant Attrition Early-Warning" |
| Branded shell, KPI tiles with trends, charts with tooltips and legends, sortable/filterable tables, status pills, detail panels, empty/loading/error states | pass | Skeleton while Live loads |
| Motion: transitions, skeletons, hover, count-up | pass | Reduced-motion respected |
| Contrast WCAG AA | pass | `scripts/check_contrast.py`: every pair ≥ 4.5:1 |
| Seeded deterministic generator; planted stories documented | pass | Two runs byte-identical; `data/README.md` |
| `build:example` writes `docs/.nojekyll`; `/try/` JS and CSS return 200 | pass | On the fork's Pages preview |

## Not re-verified

- `sql/census_backdrop.sql` (optional real US Census demand) is the original pack's query and was not re-run: the Financial Data Package listing was not available in the test account. Stated in README and V2-CHANGES.md.
- `CREATE STREAMLIT` from `APP_STAGE` succeeded, but the deployed app was not opened in Snowsight (no interactive sign-in used). The same code ran Live locally through key-pair auth.
