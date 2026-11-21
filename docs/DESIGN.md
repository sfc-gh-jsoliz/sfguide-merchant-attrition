# Design: Merchant Attrition Early-Warning

The v2 app, the hosted example and the guide share one look. This file is the source of truth for colors, type, layout and motion; the Streamlit theme (`app/.streamlit/config.toml`), `app/brand.py`, `docs/assets/tokens.css` and `docs/try/app.css` copy their tokens from here.

## Brand

- **Name:** the pack's plain name, **Merchant Attrition Early-Warning**. No coined product name. Short form in tight spots: "Attrition Early-Warning".
- **Audience:** the merchant-retention and portfolio team at a payments processor or acquirer: relationship managers who work a save list, and their head of merchant services who reports churn and net revenue retention (NRR) upward.
- **Voice:** calm and clinical, like a monitoring screen. Short labels, numbers first, one plain sentence of "what this means". Say "at risk", "watch", "churned"; never "doomed" or "lost cause". Outcomes are possibilities ("helps the team spot…"), and every figure is from the synthetic book.
- **Logo mark (inline SVG):** a plum rounded square carrying a processed-volume line that runs flat, dips, and ends in a coral dot: the moment the early warning fires.

```svg
<svg viewBox="0 0 32 32" width="30" height="30" xmlns="http://www.w3.org/2000/svg">
  <rect width="32" height="32" rx="9" fill="#2A1636"/>
  <path d="M5 13 H11 L13.5 9 L16.5 17 L19 14 H21.5 C23.5 14 24.5 19 26 21.5" fill="none" stroke="#F3E9F7" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="26" cy="22" r="2.6" fill="#F07A5E"/>
</svg>
```

## Design direction: "vital signs"

The product reads like a patient monitor for a merchant book: a dark plum rail on the left, a pale lilac-grey canvas, white cards, and four risk-band colors that mean the same thing everywhere (tiles, pills, chart series, legend, drawer).

### Palette

| Token | Hex | Use |
|---|---|---|
| `plum-950` | `#1E0F27` | Landing hero, sidebar bottom gradient |
| `plum-900` | `#2A1636` | Sidebar rail, logo square |
| `plum-700` | `#4B2761` | Hover on rail, chart series "book" |
| `plum-500` | `#6D3B8C` | Primary buttons, active nav marker, links, focus ring |
| `canvas` | `#F6F3F8` | App background |
| `surface` | `#FFFFFF` | Cards, tables, drawer |
| `surface-2` | `#EEE8F2` | Table header, skeleton base, chips |
| `line` | `#DDD3E4` | Borders, gridlines |
| `ink` | `#1D1424` | Primary text |
| `ink-2` | `#463A51` | Secondary text |
| `muted` | `#675B72` | Captions, axes (AA on canvas and surface) |
| `healthy` | `#196B57` text / `#DDF2EA` soft / `#3AA588` series | Healthy band |
| `watch` | `#7A5200` text / `#FBEFD1` soft / `#D9A21B` series | Watch band |
| `at-risk` | `#A63A20` text / `#FBE2DA` soft / `#F07A5E` series | At-risk band, the warning dot |
| `churned` | `#544D5E` text / `#ECE9EF` soft / `#8D8697` series | Churned band |
| `demand` | `#245F8C` | Category demand backdrop line (always dashed) |

Text colors were checked with `scripts/check_contrast.py`: every text/background pair the app uses meets WCAG AA (4.5:1). Series colors are only used for marks, never for text.

### Typography

- **Manrope** (400–800, OFL, self-hosted woff2) for UI and headings. Headings 700 with −0.02em tracking; body 400–500.
- **DM Mono** (400/500, OFL) for figures: KPI values, table numbers, merchant IDs. Tabular numerals.
- No CDN: fonts ship in `app/static/fonts/` (Streamlit static serving) and `docs/fonts/`.

### Layout model

- **Left rail** (Streamlit sidebar, 260 px, plum): logo and name, the Sample/Live switch, five views as a vertical list with a coral "beat" marker on the active one, then the environment badge and the role chip (`Retention analyst · MERCHANT_ATTRITION_ROLE`). On phones the rail collapses behind Streamlit's menu control.
- **Canvas:** max 1240 px. Each view opens with a title row (title, one-line purpose, a "Powered by …" capability chip), then KPI tiles, then two-column cards that stack under 760 px.
- **Density:** medium. 12 px card radius, 1 px borders, no heavy shadows; one soft shadow on the drawer only.

### Charts

- Altair (bundled with Streamlit) in the app; hand-written SVG in the hosted example. Same encodings in both.
- Risk bands always stacked in the order healthy → watch → at-risk → churned with the band colors above.
- The demand backdrop is always a dashed `demand` blue line, so "book vs market" reads at a glance.
- Tooltips on every mark; legend at the bottom; light gridlines on y only.

### Motion

- Cards fade up 6 px over 180 ms (`animation-fill-mode: backwards`, so no transform is left behind).
- KPI values count up (CSS `@property` integer counter).
- Skeleton shimmer while Live queries run.
- AI runs show staged steps with a spinning ring on the current step, then a word-by-word reveal.
- `prefers-reduced-motion` turns all of it off.

### Dark mode

Not in the app (Streamlit theme is light). The landing page follows `prefers-color-scheme` with a plum-night variant.

## What makes it distinct

Checked against the live catalog and the other v2 rebuilds:

| Pack | Its look | What this pack avoids |
|---|---|---|
| Auto Finance Portfolio Analytics | Light dashboard with its own odometer brand | Its gauge hero and palette |
| Workforce Intelligence | People-analytics cards | Its card grid and accent |
| Cross-Border & FX | Pine-green top bar, saffron accents, horizontal tabs | Top-bar + tab layout, green/gold |
| Dispute Intelligence | Teal masthead, fog canvas, docket cards with left rules | Teal, left-ruled cards |
| Macro Stress Testing | Oxide on sand, instrument panel | Warm sand canvas, oxide |
| Verified Bank Research | Brass accents | Brass/gold primary |
| Complaints Intelligence | Burgundy on stone | Burgundy primary |
| Continuous Control Testing | Paper grid, ink and vermilion | Grid paper, vermilion |
| Governed Context Layer | Graphite night with lime | Dark-first UI, lime |
| Loan File Review | Cobalt blueprint | Cobalt primary |
| Market Data Discovery | Harbor navy and raspberry, topographic lines | Navy rail, contour lines |

So: the only plum-rail layout, the only four-band "vital signs" color system, the only Manrope/DM Mono pairing, and a hero built around a volume pulse line that flattens into churn.
