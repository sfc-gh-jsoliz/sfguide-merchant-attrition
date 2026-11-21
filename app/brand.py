"""Brand: tokens from docs/DESIGN.md, global CSS and small HTML helpers."""
import base64
import html

T = {
    "plum950": "#1E0F27", "plum900": "#2A1636", "plum700": "#4B2761", "plum500": "#6D3B8C",
    "canvas": "#F6F3F8", "surface": "#FFFFFF", "surface2": "#EEE8F2", "line": "#DDD3E4",
    "ink": "#1D1424", "ink2": "#463A51", "muted": "#675B72", "demand": "#245F8C", "coral": "#F07A5E",
}
# band: (text, soft background, chart series)
BAND = {
    "healthy": ("#196B57", "#DDF2EA", "#3AA588"),
    "watch": ("#7A5200", "#FBEFD1", "#D9A21B"),
    "at-risk": ("#A63A20", "#FBE2DA", "#F07A5E"),
    "churned": ("#544D5E", "#ECE9EF", "#8D8697"),
}
BAND_LABEL = {"healthy": "Healthy", "watch": "Watch", "at-risk": "At risk", "churned": "Churned"}
DIAG = {  # diagnosis -> band styling it borrows
    "Retention problem": "at-risk", "Market slowdown": "watch", "Watch": "churned", "Healthy": "healthy",
}

LOGO = ('<svg viewBox="0 0 32 32" width="30" height="30" xmlns="http://www.w3.org/2000/svg">'
        '<rect width="32" height="32" rx="9" fill="#2A1636" stroke="#5A3A70"/>'
        '<path d="M5 13 H11 L13.5 9 L16.5 17 L19 14 H21.5 C23.5 14 24.5 19 26 21.5" fill="none" stroke="#F3E9F7" '
        'stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>'
        '<circle cx="26" cy="22" r="2.6" fill="#F07A5E"/></svg>')
LOGO_IMG = ('<img alt="Merchant Attrition Early-Warning logo" width="30" height="30" src="data:image/svg+xml;base64,'
            + base64.b64encode(LOGO.encode()).decode() + '">')

_FONTS = "".join(
    f'@font-face{{font-family:"{fam}";src:url("app/static/fonts/{f}-latin-{w}-normal.woff2") format("woff2");font-weight:{w};font-display:swap}}'
    for fam, f, ws in (("Manrope", "manrope", (400, 500, 600, 700, 800)), ("DM Mono", "dm-mono", (400, 500)))
    for w in ws)

CSS = "<style>" + _FONTS + """
@property --n{syntax:"<integer>";initial-value:0;inherits:false}
:root{--plum950:#1E0F27;--plum900:#2A1636;--plum700:#4B2761;--plum500:#6D3B8C;--canvas:#F6F3F8;--surface:#fff;--surface2:#EEE8F2;--line:#DDD3E4;
 --ink:#1D1424;--ink2:#463A51;--muted:#675B72;--demand:#245F8C;--coral:#F07A5E;
 --h-t:#196B57;--h-s:#DDF2EA;--w-t:#7A5200;--w-s:#FBEFD1;--r-t:#A63A20;--r-s:#FBE2DA;--c-t:#544D5E;--c-s:#ECE9EF;
 --sans:"Manrope",ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;--mono:"DM Mono",ui-monospace,SFMono-Regular,Menlo,monospace}
html{overflow-x:clip}
html,body,[class*="st-"],.stMarkdown,button,input,textarea,select{font-family:var(--sans)}
[data-testid="stIconMaterial"],.material-symbols-rounded{font-family:"Material Symbols Rounded"!important}
[data-testid="stToolbarActions"],[data-testid="stMainMenu"],[data-testid="stDecoration"],#MainMenu,footer,[data-testid="stAppDeployButton"],[data-testid="stStatusWidget"]{display:none!important}
[data-testid="stExpandSidebarButton"]{background:var(--plum900);border-radius:9px;color:#F3E9F7}[data-testid="stExpandSidebarButton"] *{color:#F3E9F7}
[data-testid="stHeader"]{background:transparent;height:2.6rem}
.stApp{background:var(--canvas)}
.block-container,[data-testid="stMainBlockContainer"]{padding-top:1.4rem!important;max-width:1240px;padding-left:1.4rem;padding-right:1.4rem}
/* rail */
[data-testid="stSidebar"]{background:linear-gradient(180deg,var(--plum900) 0%,var(--plum950) 100%);border-right:1px solid #3B2149}
[data-testid="stSidebar"] *{color:#F3E9F7}
[data-testid="stSidebarHeader"]{height:1.2rem;padding-top:.4rem}
[data-testid="stSidebarCollapseButton"] svg,[data-testid="stSidebarHeader"] button svg{fill:#C9B5D6;color:#C9B5D6}
.mw-brand{display:flex;gap:.65rem;align-items:center;margin:.2rem 0 1.1rem}
.mw-brand b{font-size:1rem;font-weight:800;letter-spacing:-.02em;line-height:1.15;display:block}
.mw-brand span{display:block;font-size:.72rem;color:#C9B5D6!important;margin-top:.15rem}
.mw-rail-h{font-size:.68rem;letter-spacing:.09em;text-transform:uppercase;color:#C9B5D6!important;margin:.9rem 0 .35rem;font-weight:700}
[data-testid="stSidebar"] [role="radiogroup"]{gap:.15rem!important}
[data-testid="stSidebar"] label[data-baseweb="radio"]{margin:0!important;padding:.55rem .7rem;border-radius:9px;width:100%;cursor:pointer;transition:background .15s;position:relative}
[data-testid="stSidebar"] label[data-baseweb="radio"]>div:first-child{display:none}
[data-testid="stSidebar"] label[data-baseweb="radio"] p{font-weight:600;font-size:.92rem;color:#E4D6EC!important}
[data-testid="stSidebar"] label[data-baseweb="radio"]:hover{background:#3A2048}
[data-testid="stSidebar"] label[data-baseweb="radio"]:has(input:checked){background:#4B2761}
[data-testid="stSidebar"] label[data-baseweb="radio"]:has(input:checked)::before{content:"";position:absolute;left:-.15rem;top:50%;width:6px;height:6px;margin-top:-3px;border-radius:50%;background:var(--coral);box-shadow:0 0 0 4px rgba(240,122,94,.18)}
[data-testid="stSidebar"] label[data-baseweb="radio"]:has(input:checked) p{color:#fff!important}
[data-testid="stSidebar"] [data-testid="stButtonGroup"] button{background:transparent;border-color:#5A3A70;font-size:.8rem;min-height:2rem}
[data-testid="stSidebar"] [data-testid="stButtonGroup"] button p{color:#E4D6EC!important}
[data-testid="stSidebar"] [data-testid="stButtonGroup"] button[kind$="Active"]{background:#F3E9F7;border-color:#F3E9F7}
[data-testid="stSidebar"] [data-testid="stButtonGroup"] button[kind$="Active"] p{color:var(--plum900)!important}
.mw-chip{display:inline-flex;align-items:center;gap:.4rem;font-size:.74rem;border-radius:12px;padding:.24rem .65rem;border:1px solid #5A3A70;max-width:100%;margin:.15rem 0;font-weight:600;overflow-wrap:anywhere}
.mw-chip.sample{background:#FBEFD1;border-color:#E8C877;color:#7A5200!important}.mw-chip.sample *{color:#7A5200!important}
.mw-chip.live{background:#DDF2EA;border-color:#8CCBB6;color:#196B57!important}.mw-chip.live *{color:#196B57!important}
.mw-dot{width:7px;height:7px;border-radius:50%;background:currentColor;display:inline-block}
.mw-chip.live .mw-dot{animation:mwPulse 1.6s ease-in-out infinite}
@keyframes mwPulse{50%{opacity:.35}}
.mw-rail-foot{font-size:.72rem;color:#C9B5D6!important;margin-top:1.2rem;line-height:1.45}
/* headings */
.mw-h{display:flex;align-items:flex-end;justify-content:space-between;gap:1rem;flex-wrap:wrap;margin:0 0 1rem}
.mw-h h1{font-size:1.7rem;line-height:1.15;margin:0;color:var(--ink);font-weight:800;letter-spacing:-.025em;padding:0}
.mw-h p{margin:.3rem 0 0;color:var(--muted);font-size:.92rem;max-width:64ch}
.mw-cap{display:inline-flex;gap:.35rem;align-items:center;font-size:.72rem;color:var(--plum500);background:#F1E8F6;border:1px solid #DCC8E8;border-radius:999px;padding:.22rem .65rem;font-weight:700;max-width:100%;flex-wrap:wrap}
.mw-cap.sample{color:var(--w-t);background:var(--w-s);border-color:#E8C877}
/* cards */
.mw-card,[class*="st-key-card"]{background:var(--surface);border:1px solid var(--line);border-radius:12px;min-width:0}
[class*="st-key-card"]{padding:1rem 1.1rem .7rem;animation:mwIn .18s ease-out backwards}
[class*="st-key-card"]:hover{border-color:#C9B5D6}
.mw-card{padding:1rem 1.1rem}
[data-testid="stMarkdownContainer"] p.mw-card-h,.mw-card-h{font-weight:700;font-size:.98rem;color:var(--ink);margin:0 0 .15rem}
[data-testid="stMarkdownContainer"] p.mw-card-s,.mw-card-s{font-size:.8rem;color:var(--muted);margin:0 0 .6rem}
@keyframes mwIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
/* kpis */
.mw-kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.8rem;margin-bottom:1rem}
.mw-kpi{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:.9rem 1rem .85rem;position:relative;overflow:hidden;animation:mwIn .18s ease-out backwards;transition:transform .15s,border-color .15s}
.mw-kpi:hover{transform:translateY(-1px);border-color:#C9B5D6}
.mw-kpi:nth-child(2){animation-delay:.04s}.mw-kpi:nth-child(3){animation-delay:.08s}.mw-kpi:nth-child(4){animation-delay:.12s}
.mw-kpi .k{font-size:.76rem;color:var(--muted);font-weight:600;display:flex;align-items:center;gap:.4rem}
.mw-kpi .k i{width:8px;height:8px;border-radius:2px;display:inline-block}
.mw-kpi .v{font-family:var(--mono);font-size:1.75rem;font-weight:500;color:var(--ink);margin:.3rem 0 .1rem;font-variant-numeric:tabular-nums;letter-spacing:-.03em}
.mw-kpi .v .cnt{animation:mwCount .7s ease-out forwards;counter-reset:n var(--n)}
.mw-kpi .v .cnt::after{content:counter(n)}
@keyframes mwCount{from{--n:0}}
.mw-kpi .d{font-size:.76rem;color:var(--muted)}
.mw-kpi svg{position:absolute;right:.75rem;bottom:.75rem}
.up{color:var(--h-t);font-weight:700}.down{color:var(--r-t);font-weight:700}
/* pills */
.mw-pill{display:inline-flex;align-items:center;gap:.35rem;font-size:.72rem;font-weight:700;border-radius:999px;padding:.16rem .6rem;white-space:nowrap}
.mw-pill::before{content:"";width:6px;height:6px;border-radius:50%;background:currentColor}
.mw-pill.healthy{background:var(--h-s);color:var(--h-t)}.mw-pill.watch{background:var(--w-s);color:var(--w-t)}
.mw-pill.at-risk{background:var(--r-s);color:var(--r-t)}.mw-pill.churned{background:var(--c-s);color:var(--c-t)}
/* band bar */
.mw-bandbar{display:flex;height:10px;border-radius:5px;overflow:hidden;background:var(--surface2);margin:.35rem 0 .25rem}
.mw-bandbar i{display:block;height:100%}
.mw-legend{display:flex;gap:.9rem;flex-wrap:wrap;font-size:.75rem;color:var(--ink2)}
.mw-legend span{display:inline-flex;align-items:center;gap:.35rem}.mw-legend i{width:9px;height:9px;border-radius:2px;display:inline-block}
/* category rows */
.mw-cat{display:grid;grid-template-columns:minmax(0,1.4fr) minmax(0,1fr) auto;gap:.8rem;align-items:center;padding:.6rem 0;border-bottom:1px solid #EEE8F2;font-size:.86rem}
.mw-cat:last-child{border-bottom:0}
.mw-cat .n{font-family:var(--mono);font-variant-numeric:tabular-nums;font-size:.82rem}
.mw-vs{font-family:var(--mono);font-size:.8rem;color:var(--ink2)}
/* insight */
.mw-insight{border:1px solid var(--line);border-left:3px solid var(--coral);background:var(--surface);border-radius:0 10px 10px 0;padding:.75rem .95rem;font-size:.88rem;color:var(--ink2);margin:.1rem 0 1rem}
.mw-insight b{color:var(--ink)}
/* detail */
.mw-facts{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.6rem;margin:.4rem 0 .8rem}
.mw-facts div{background:var(--canvas);border-radius:9px;padding:.55rem .7rem}
.mw-facts small{display:block;font-size:.7rem;color:var(--muted);font-weight:600}
.mw-facts b{font-family:var(--mono);font-weight:500;font-size:1.05rem;color:var(--ink)}
.mw-why{margin:.2rem 0 .4rem;padding-left:1.1rem;font-size:.86rem;color:var(--ink2)}
/* skeleton */
.mw-skel{border-radius:10px;background:linear-gradient(90deg,#EEE8F2 25%,#F7F3F9 37%,#EEE8F2 63%);background-size:400% 100%;animation:mwSh 1.3s ease infinite}
@keyframes mwSh{0%{background-position:100% 50%}100%{background-position:0 50%}}
/* ai */
.mw-steps{list-style:none;padding:0;margin:.2rem 0 .6rem}
.mw-steps li{display:flex;gap:.55rem;align-items:flex-start;font-size:.85rem;padding:.3rem 0;color:var(--muted)}
.mw-steps li.done{color:var(--ink2)}.mw-steps li.now{color:var(--ink);font-weight:600}
.mw-steps .ic{width:16px;height:16px;border-radius:50%;flex:none;margin-top:2px;border:2px solid var(--line)}
.mw-steps li.done .ic{background:var(--plum500);border-color:var(--plum500);box-shadow:inset 0 0 0 3px #fff}
.mw-steps li.now .ic{border-color:var(--coral);border-top-color:transparent;animation:mwSpin .8s linear infinite}
@keyframes mwSpin{to{transform:rotate(360deg)}}
.mw-src{font-size:.78rem;color:var(--muted);border-top:1px dashed var(--line);margin-top:.6rem;padding-top:.5rem}
.mw-src code{font-family:var(--mono);font-size:.74rem;background:var(--surface2);border-radius:4px;padding:.05rem .3rem;color:var(--ink2)}
[class*="st-key-note_body"] h1,[class*="st-key-card_answer"] h1{font-size:1.3rem!important;line-height:1.3!important;padding:.4rem 0!important}
[class*="st-key-note_body"] h2,[class*="st-key-card_answer"] h2{font-size:1.05rem!important;padding:.6rem 0 .2rem!important}
[data-testid="stMarkdownContainer"] table{font-size:.84rem;display:block;overflow-x:auto;max-width:100%}
[data-testid="stMarkdownContainer"] th{background:var(--surface2)}
.mw-empty{text-align:center;padding:2.2rem 1rem;color:var(--muted);font-size:.9rem}
.mw-empty b{display:block;color:var(--ink);font-size:1rem;margin-bottom:.25rem}
.stButton>button[kind="primary"]{background:var(--plum500);border-color:var(--plum500);color:#fff;font-weight:700}
.stButton>button[kind="primary"]:hover{background:var(--plum700);border-color:var(--plum700)}
.stButton>button{border-radius:9px}
[data-testid="stDataFrame"]{border-radius:10px}
@media (max-width:760px){
 .mw-kpis,.mw-facts{grid-template-columns:repeat(2,minmax(0,1fr))}
 .mw-kpi .v{font-size:1.3rem}.mw-kpi svg{display:none}
 .mw-h h1{font-size:1.35rem}
 .mw-cat{grid-template-columns:minmax(0,1fr) auto}.mw-cat .mw-vs{display:none}
 .block-container,[data-testid="stMainBlockContainer"]{padding-left:.8rem;padding-right:.8rem;padding-top:3.2rem!important}
}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
</style>
"""


def esc(s):
    return html.escape(str(s))


def usd(x, d=1):
    x = float(x)
    if abs(x) >= 1e9:
        return f"${x / 1e9:.{d + 1}f}B"
    if abs(x) >= 1e6:
        return f"${x / 1e6:.{d + 1}f}M"
    if abs(x) >= 1e3:
        return f"${x / 1e3:.0f}K"
    return f"${x:,.0f}"


def pct(x, d=1, sign=True):
    """x is already in percent units."""
    return f"{x:+.{d}f}%" if sign else f"{x:.{d}f}%"


def delta(x, text, good_up=True):
    good = (x >= 0) == good_up
    arrow = "▲" if x >= 0 else "▼"
    return f'<span class="{"up" if good else "down"}">{arrow} {esc(text)}</span>'


def spark(values, color="#6D3B8C", w=86, h=28, dash=None):
    lo, hi = min(values), max(values)
    rng = (hi - lo) or 1
    pts = " ".join(f"{i * w / (len(values) - 1):.1f},{h - 2 - (v - lo) / rng * (h - 4):.1f}" for i, v in enumerate(values))
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" aria-hidden="true"><polyline fill="none" stroke="{color}" '
            f'stroke-width="1.8" stroke-linejoin="round"{d} points="{pts}"/></svg>')


def kpi(label, value_html, delta_html, values=None, color=None, swatch=None):
    s = spark(values, color or T["plum500"]) if values else ""
    sw = f'<i style="background:{swatch}"></i>' if swatch else ""
    return f'<div class="mw-kpi"><div class="k">{sw}{esc(label)}</div><div class="v">{value_html}</div><div class="d">{delta_html}</div>{s}</div>'


def counter(prefix, number, suffix=""):
    """Animated integer count-up (CSS @property), with prefix/suffix text."""
    return f'{esc(prefix)}<span class="cnt" style="--n:{int(number)}"></span>{esc(suffix)}'


def header(title, sub, cap, sample=False):
    c = "mw-cap sample" if sample else "mw-cap"
    return f'<div class="mw-h"><div><h1>{esc(title)}</h1><p>{esc(sub)}</p></div><span class="{c}">{cap}</span></div>'


def pill(band):
    return f'<span class="mw-pill {band}">{esc(BAND_LABEL.get(band, band))}</span>'


def diag_pill(d):
    return f'<span class="mw-pill {DIAG.get(d, "churned")}">{esc(d)}</span>'


def verdict(status):
    if status == "verified":
        return '<span class="mw-pill healthy">Verified</span>'
    return '<span class="mw-pill at-risk">Needs review</span>'


def bandbar(counts):
    tot = sum(counts.get(b, 0) for b in BAND) or 1
    segs = "".join(f'<i style="width:{counts.get(b, 0) / tot * 100:.2f}%;background:{BAND[b][2]}" '
                   f'title="{BAND_LABEL[b]}: {counts.get(b, 0)}"></i>' for b in BAND)
    return f'<div class="mw-bandbar" role="img" aria-label="Risk bands">{segs}</div>'


def legend():
    return '<div class="mw-legend">' + "".join(
        f'<span><i style="background:{BAND[b][2]}"></i>{BAND_LABEL[b]}</span>' for b in BAND) + \
        f'<span><i style="background:{T["demand"]};height:2px;width:14px"></i>Category demand</span></div>'


def skeleton(rows=((4, 96), (2, 300))):
    out = []
    for n, h in rows:
        cells = "".join(f'<div class="mw-skel" style="height:{h}px"></div>' for _ in range(n))
        out.append(f'<div style="display:grid;grid-template-columns:repeat({n},minmax(0,1fr));gap:.8rem;margin-bottom:.9rem">{cells}</div>')
    return "".join(out)


def steps_html(steps, current, finished=False):
    items = []
    for i, s in enumerate(steps):
        cls = "done" if (i < current or finished) else ("now" if i == current else "")
        items.append(f'<li class="{cls}"><span class="ic"></span><span>{esc(s)}</span></li>')
    return f'<ul class="mw-steps">{"".join(items)}</ul>'


def md_safe(text):
    """Model markdown for st.markdown: dollar signs are not LaTeX, "•" lines become list items."""
    lines = []
    for ln in (text or "").replace("$", "\\$").split("\n"):
        s = ln.lstrip()
        lines.append("- " + s[1:].lstrip() if s.startswith("•") else ln)
    return "\n".join(lines)
