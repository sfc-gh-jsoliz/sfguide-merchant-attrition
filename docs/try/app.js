/* Merchant Attrition Early-Warning: hosted no-account example. The numbers come from the
   Streamlit app's own data layer (app/data.py, Sample mode) via scripts/build_example.py.
   Always Sample mode; AI answers were captured from Live runs and are labeled
   "Sample AI response". No dependencies. */
(function () {
  "use strict";
  var D = window.MAEW;
  var BANDS = ["healthy", "watch", "at-risk", "churned"];
  var LABEL = { healthy: "Healthy", watch: "Watch", "at-risk": "At risk", churned: "Churned" };
  var COLOR = { healthy: "#3AA588", watch: "#D9A21B", "at-risk": "#F07A5E", churned: "#8D8697" };
  var DIAG = { "Retention problem": "at-risk", "Market slowdown": "watch", "Watch": "churned", "Healthy": "healthy" };
  var PLUM = "#6D3B8C", DEMAND = "#245F8C";
  var TENURES = ["New (<1yr)", "Established (1-3yr)", "Mature (3yr+)"];
  var MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  var LONG = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
  var SCOPES = { ALL: "All categories", RESTAURANTS: "Restaurants & Food Service", APPAREL: "Clothing & Accessories",
    ELECTRONICS: "Electronics & Appliances", GROCERY: "Food & Beverage Stores", FURNITURE: "Furniture & Home Furnishings",
    HEALTH: "Health & Personal Care" };
  var MODEL = "claude-sonnet-4-5";
  var ASK_STEPS = ["Sending the question to the Merchant Attrition Agent (DATA_AGENT_RUN)",
    "Cortex Analyst writes SQL over the ATTRITION_SV semantic view",
    "Running the SQL on SNOWPACK_MERCHANT_ATTRITION_WH", "Composing the answer from the result set"];
  var VIEWS = [["overview", "Overview"], ["save-list", "Save list"], ["categories", "Categories"], ["notes", "Attrition notes"], ["ask", "Ask the agent"]];
  var months = D.months, N = months.length, LAST = months[N - 1], YAGO = months[N - 13];
  var state = { bands: ["at-risk", "watch"], cats: "", q: "", sort: null, dir: 1, cat: null, note: null, answer: null, outreach: [] };

  // ---------------------------------------------------------------- format
  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  function mlab(s) { var p = s.split("-"); return MON[+p[1] - 1] + " " + p[0].slice(2); }
  function mlong(s) { var p = s.split("-"); return LONG[+p[1] - 1] + " " + p[0]; }
  function mshort(s) { var p = s.split("-"); return MON[+p[1] - 1] + " " + p[0]; }
  function pct(x, d) { d = d == null ? 1 : d; return (x >= 0 ? "+" : "") + x.toFixed(d) + "%"; }
  function usd(x) { var a = Math.abs(x); if (a >= 1e6) return "$" + (x / 1e6).toFixed(2) + "M"; if (a >= 1e3) return "$" + Math.round(x / 1e3) + "K"; return "$" + Math.round(x); }
  function delta(x, t, goodUp) { var good = (x >= 0) === (goodUp !== false); return '<span class="' + (good ? "up" : "down") + '">' + (x >= 0 ? "▲ " : "▼ ") + esc(t) + "</span>"; }
  function pill(b) { return '<span class="pill ' + b + '">' + esc(LABEL[b] || b) + "</span>"; }
  function dpill(d) { return '<span class="pill ' + (DIAG[d] || "churned") + '">' + esc(d) + "</span>"; }
  function verdict(s) { return s === "verified" ? '<span class="pill healthy">Verified</span>' : '<span class="pill at-risk">Needs review</span>'; }
  function head(t, s, c) { return '<div class="h"><div><h1>' + esc(t) + "</h1><p>" + esc(s) + '</p></div><span class="cap">Sample data · ' + esc(c) + "</span></div>"; }
  function sum(a) { return a.reduce(function (s, x) { return s + x; }, 0); }

  // ---------------------------------------------------------------- tooltip
  var tip = document.getElementById("tip");
  function showTip(e, html) { tip.innerHTML = html; tip.hidden = false; var x = e.clientX + 14, y = e.clientY + 14, w = tip.offsetWidth, h = tip.offsetHeight; if (x + w > innerWidth - 8) x = e.clientX - w - 14; if (y + h > innerHeight - 8) y = e.clientY - h - 14; tip.style.left = Math.max(8, x) + "px"; tip.style.top = Math.max(8, y) + "px"; }
  function bindTips(root) { root.querySelectorAll("[data-tip]").forEach(function (el) { el.addEventListener("mousemove", function (e) { showTip(e, el.getAttribute("data-tip")); }); el.addEventListener("mouseleave", function () { tip.hidden = true; }); }); }

  // ---------------------------------------------------------------- charts (SVG)
  function spark(vals, color) {
    var w = 86, h = 28, lo = Math.min.apply(null, vals), hi = Math.max.apply(null, vals), r = (hi - lo) || 1;
    var pts = vals.map(function (v, i) { return (i * w / (vals.length - 1)).toFixed(1) + "," + (h - 2 - (v - lo) / r * (h - 4)).toFixed(1); }).join(" ");
    return '<svg width="' + w + '" height="' + h + '" viewBox="0 0 ' + w + " " + h + '" aria-hidden="true"><polyline fill="none" stroke="' + (color || PLUM) + '" stroke-width="1.8" stroke-linejoin="round" points="' + pts + '"/></svg>';
  }
  function ticks(lo, hi, n) {
    var span = hi - lo || 1, step = Math.pow(10, Math.floor(Math.log10(span / n))), err = span / n / step;
    step *= err >= 7.5 ? 10 : err >= 3 ? 5 : err >= 1.5 ? 2 : 1;
    var t = []; for (var v = Math.floor(lo / step) * step; v <= hi + step * 0.01; v += step) t.push(+v.toFixed(10)); return t;
  }
  var PAD = { l: 44, r: 12, t: 10, b: 26 };
  function axes(W, H, yt, y, ylab, xl) {
    var g = "";
    yt.forEach(function (v) { var yy = y(v); g += '<line x1="' + PAD.l + '" x2="' + (W - PAD.r) + '" y1="' + yy + '" y2="' + yy + '" stroke="#ECE5F0"/><text x="' + (PAD.l - 6) + '" y="' + (yy + 4) + '" text-anchor="end">' + v + "</text>"; });
    xl.forEach(function (p) { g += '<text x="' + p[0] + '" y="' + (H - 8) + '" text-anchor="middle">' + esc(p[1]) + "</text>"; });
    if (ylab) g += '<text transform="translate(11,' + (H / 2) + ') rotate(-90)" text-anchor="middle" style="font-weight:600;fill:#463A51">' + esc(ylab) + "</text>";
    return g;
  }
  // series: [{name, values, color, dash}] over labels (month strings)
  function lineChart(labels, series, opt) {
    opt = opt || {}; var W = opt.W || 720, H = opt.h || 250;
    var all = []; series.forEach(function (s) { s.values.forEach(function (v) { if (v != null) all.push(v); }); });
    if (opt.zero) all.push(0);
    var lo = Math.min.apply(null, all), hi = Math.max.apply(null, all), pad = (hi - lo) * 0.08 || 1;
    var yt = ticks(lo - pad, hi + pad, 5), y0 = yt[0], y1 = yt[yt.length - 1];
    var x = function (i) { return PAD.l + i * (W - PAD.l - PAD.r) / Math.max(1, labels.length - 1); };
    var y = function (v) { return PAD.t + (y1 - v) / (y1 - y0) * (H - PAD.t - PAD.b); };
    var every = Math.ceil(labels.length / 8), xl = [];
    labels.forEach(function (l, i) { if (i % every === 0) xl.push([x(i), mlab(l)]); });
    var g = axes(W, H, yt, y, opt.ylab, xl);
    if (opt.zero) g += '<line x1="' + PAD.l + '" x2="' + (W - PAD.r) + '" y1="' + y(0) + '" y2="' + y(0) + '" stroke="#C9B5D6"/>';
    (opt.rules || []).forEach(function (r) { g += '<line x1="' + PAD.l + '" x2="' + (W - PAD.r) + '" y1="' + y(r[0]) + '" y2="' + y(r[0]) + '" stroke="#F07A5E" stroke-dasharray="2 3" opacity=".75"/><text x="' + (W - PAD.r) + '" y="' + (y(r[0]) - 4) + '" text-anchor="end" style="fill:#A63A20">' + esc(r[1]) + "</text>"; });
    series.forEach(function (s) {
      var pts = [], d = "";
      s.values.forEach(function (v, i) { if (v != null) { pts.push([x(i), y(v), v, i]); d += (d ? " L" : "M") + x(i).toFixed(1) + " " + y(v).toFixed(1); } });
      g += '<path d="' + d + '" fill="none" stroke="' + s.color + '" stroke-width="' + (s.w || 2.3) + '"' + (s.dash ? ' stroke-dasharray="6 4"' : "") + ' stroke-linejoin="round" opacity="' + (s.op || 1) + '"/>';
      if (!s.noPts) pts.forEach(function (p) { g += '<circle cx="' + p[0] + '" cy="' + p[1] + '" r="8" fill="transparent" data-tip="<b>' + esc(s.name) + "</b><br>" + mlong(labels[p[3]]) + ": " + p[2].toFixed(1) + (opt.unit || "") + '"/>'; });
    });
    return '<div class="chart"><svg viewBox="0 0 ' + W + " " + H + '" role="img" aria-label="' + esc(opt.aria || "Line chart") + '">' + g + "</svg></div>";
  }
  function stackBars(labels, stacks, opt) {
    opt = opt || {}; var W = 720, H = opt.h || 290;
    var tot = labels.map(function (_, i) { return sum(stacks.map(function (s) { return s.values[i]; })); });
    var yt = ticks(0, Math.max.apply(null, tot) * 1.08, 5), y1 = yt[yt.length - 1];
    var bw = (W - PAD.l - PAD.r) / labels.length;
    var y = function (v) { return PAD.t + (y1 - v) / y1 * (H - PAD.t - PAD.b); };
    var xl = []; labels.forEach(function (l, i) { if (i % 3 === 0) xl.push([PAD.l + (i + 0.5) * bw, mlab(l)]); });
    var g = axes(W, H, yt, y, opt.ylab, xl);
    labels.forEach(function (l, i) {
      var acc = 0;
      stacks.forEach(function (s) {
        var v = s.values[i]; if (!v) return;
        g += '<rect x="' + (PAD.l + i * bw + bw * 0.15).toFixed(1) + '" y="' + y(acc + v).toFixed(1) + '" width="' + (bw * 0.7).toFixed(1) + '" height="' + (y(acc) - y(acc + v)).toFixed(1) + '" fill="' + s.color + '" rx="1.5" data-tip="<b>' + esc(s.name) + "</b><br>" + mlong(l) + ": " + v + ' merchants"/>';
        acc += v;
      });
    });
    return '<div class="chart"><svg viewBox="0 0 ' + W + " " + H + '" role="img" aria-label="' + esc(opt.aria || "Bar chart") + '">' + g + "</svg></div>";
  }
  function hbars(rows) { // rows: [{label, parts:{band:n}}]
    var W = 560, rowH = 46, H = rows.length * rowH + 30, L = 130;
    var mx = Math.max.apply(null, rows.map(function (r) { return sum(BANDS.map(function (b) { return r.parts[b]; })); })) || 1;
    var xt = ticks(0, mx, 5), x1 = xt[xt.length - 1], g = "";
    var x = function (v) { return L + v / x1 * (W - L - 12); };
    xt.forEach(function (v) { g += '<line x1="' + x(v) + '" x2="' + x(v) + '" y1="4" y2="' + (H - 24) + '" stroke="#ECE5F0"/><text x="' + x(v) + '" y="' + (H - 8) + '" text-anchor="middle">' + v + "</text>"; });
    rows.forEach(function (r, i) {
      var yy = 8 + i * rowH, acc = 0;
      g += '<text x="' + (L - 8) + '" y="' + (yy + 21) + '" text-anchor="end">' + esc(r.label) + "</text>";
      BANDS.forEach(function (b) { var v = r.parts[b]; if (!v) return; g += '<rect x="' + x(acc) + '" y="' + yy + '" width="' + (x(acc + v) - x(acc)) + '" height="30" fill="' + COLOR[b] + '" rx="2" data-tip="<b>' + esc(r.label) + "</b><br>" + LABEL[b] + ": " + v + '"/>'; acc += v; });
    });
    return '<div class="chart"><svg viewBox="0 0 ' + W + " " + H + '" role="img" aria-label="Risk bands by tenure">' + g + "</svg></div>";
  }
  function bandbar(c) { var t = c.healthy + c.watch + c.at_risk + c.churned || 1, v = { healthy: c.healthy, watch: c.watch, "at-risk": c.at_risk, churned: c.churned };
    return '<div class="bandbar">' + BANDS.map(function (b) { return '<i style="width:' + (v[b] / t * 100).toFixed(2) + "%;background:" + COLOR[b] + '" data-tip="' + LABEL[b] + ": " + v[b] + '"></i>'; }).join("") + "</div>"; }
  function legend(bands, demand) { return '<div class="legend">' + bands.map(function (b) { return '<span><i style="background:' + COLOR[b] + '"></i>' + LABEL[b] + "</span>"; }).join("") + (demand ? '<span><i class="dash"></i>Category demand</span>' : "") + "</div>"; }
  function lineLegend(items) { return '<div class="legend">' + items.map(function (s) { return "<span>" + (s.dash ? '<i class="dash"></i>' : '<i style="background:' + s.color + ';height:3px;width:16px"></i>') + esc(s.name) + "</span>"; }).join("") + "</div>"; }

  // ---------------------------------------------------------------- views
  function overview(el) {
    var M = D.monthly, i = N - 1, j = N - 13;
    var t0 = new Date(YAGO), t1 = new Date(LAST), tp = new Date(months[N - 25] || "1900-01-01");
    var ch12 = D.first_churn.filter(function (d) { var x = new Date(d); return x > t0 && x <= t1; }).length;
    var chp = D.first_churn.filter(function (d) { var x = new Date(d); return x > tp && x <= t0; }).length;
    var flag = M.watch[i] + M["at-risk"][i], flagY = M.watch[j] + M["at-risk"][j];
    var trail = function (k) { return M[k].slice(-12); };
    var cats = D.categories, worst = cats[0];
    var slow = cats.filter(function (c) { return c.diagnosis === "Market slowdown"; }).sort(function (a, b) { return a.demand_yoy - b.demand_yoy; })[0];
    function kpi(label, val, d, vals, col, sw) { return '<div class="kpi"><div class="k">' + (sw ? '<i style="background:' + sw + '"></i>' : "") + esc(label) + '</div><div class="v" data-count="' + val + '">' + val + '</div><div class="d">' + d + "</div>" + spark(vals, col) + "</div>"; }
    var flagTrail = M.watch.slice(-12).map(function (v, k) { return v + M["at-risk"].slice(-12)[k]; });
    var html = head("Merchant health overview", "Month-end " + mlong(LAST) + " across 120 merchants in 6 categories. Every figure comes from ATTRITION_MERCHANT_HEALTH.", "ATTRITION_MERCHANT_HEALTH view") +
      '<div class="kpis">' +
      kpi("Active merchants", M.active[i], delta(M.active[i] - M.active[j], (M.active[i] - M.active[j] >= 0 ? "+" : "") + (M.active[i] - M.active[j]) + " vs " + mshort(YAGO)), trail("active"), PLUM, COLOR.healthy) +
      kpi("On the save list (watch + at risk)", flag, delta(flag - flagY, (flag - flagY >= 0 ? "+" : "") + (flag - flagY) + " vs " + mshort(YAGO), false), flagTrail, COLOR["at-risk"], COLOR["at-risk"]) +
      kpi("Churned in the last 12 months", ch12, delta(ch12 - chp, (ch12 - chp >= 0 ? "+" : "") + (ch12 - chp) + " vs prior 12 months", false), trail("churned"), COLOR.churned, COLOR.churned) +
      kpi("Net revenue retention", M.nrr[i].toFixed(1) + "%", delta(M.nrr[i] - M.nrr[j], (M.nrr[i] - M.nrr[j]).toFixed(1).replace(/^(?!-)/, "+") + " pts vs " + mshort(YAGO)), trail("nrr"), PLUM) +
      "</div>" +
      '<div class="insight"><b>Early warning.</b> ' + esc(worst.name) + ": the book is " + pct(worst.book_yoy) + " year on year while category demand is " + pct(worst.demand_yoy) + ", a gap of " + Math.abs(worst.gap).toFixed(1) + " points. That is a retention problem, not the market. " +
      (slow ? esc(slow.name) + " is shrinking too (" + pct(slow.book_yoy) + "), but its demand is also down (" + pct(slow.demand_yoy) + "): mostly a market slowdown. " : "") +
      'Open <b>Save list</b> to work the merchants, or <b>Attrition notes</b> for a verified write-up.</div>' +
      '<div class="grid2"><div class="card"><p class="card-h">Merchants off healthy, by band</p><p class="card-s">Watch, at-risk and churned merchants per month-end, stacked; the other ' + M.healthy[i] + " of 120 are healthy in " + mlong(LAST) + ". Hover for the band and month.</p>" +
      stackBars(months, ["watch", "at-risk", "churned"].map(function (b) { return { name: LABEL[b], values: M[b], color: COLOR[b] }; }), { ylab: "Merchants", aria: "Watch, at-risk and churned merchants by month" }) + legend(["watch", "at-risk", "churned"]) + "</div>" +
      '<div class="card"><p class="card-h">Book vs market, year on year</p><p class="card-s">Merchant book volume change against category demand change. Widest gap first.</p>' +
      cats.map(function (c) { return '<div class="cat"><div><div style="font-weight:600">' + esc(c.name) + "</div>" + bandbar(c) + '</div><div class="vs">book <span class="' + (c.book_yoy >= 0 ? "up" : "down") + '">' + pct(c.book_yoy) + '</span><br>demand <span style="color:var(--demand);font-weight:700">' + pct(c.demand_yoy) + "</span></div><div>" + dpill(c.diagnosis) + "</div></div>"; }).join("") + legend(BANDS) + "</div></div>" +
      '<div class="card"><p class="card-h">Processed volume vs category demand</p><p class="card-s">Both indexed to July 2024 = 100. Solid: the merchant book. Dashed: category demand. A solid line falling under its dashed line is attrition the market does not explain.</p>' +
      '<label class="f" style="max-width:320px">Category <select id="ovcat"><option value="">All categories</option>' + cats.map(function (c) { return '<option value="' + c.code + '">' + esc(c.name) + "</option>"; }).join("") + "</select></label><div id=\"ovidx\"></div></div>";
    el.innerHTML = html;
    function idx() {
      var code = document.getElementById("ovcat").value, book, dem;
      if (code) { book = D.cat_series[code].volume; dem = D.cat_series[code].demand; }
      else { book = D.monthly.volume; dem = months.map(function (_, k) { return sum(Object.keys(D.cat_series).map(function (c) { return D.cat_series[c].demand[k]; })); }); }
      var s = [{ name: "Merchant book", values: book.map(function (v) { return v / book[0] * 100; }), color: PLUM },
               { name: "Category demand", values: dem.map(function (v) { return v / dem[0] * 100; }), color: DEMAND, dash: true }];
      var box = document.getElementById("ovidx"); box.innerHTML = ""; box.innerHTML = lineChart(months, s, { ylab: "Index (Jul 2024 = 100)", h: 280, W: Math.max(560, Math.min(1160, box.clientWidth || 720)), aria: "Book volume vs category demand, indexed" }) + lineLegend(s); bindTips(box);
    }
    document.getElementById("ovcat").addEventListener("change", idx); idx(); countUp(el);
  }

  function why(m) {
    var o = [];
    if (m.ratio < 0.6) o.push("Volume is " + Math.round(m.ratio * 100) + "% of baseline (at-risk line: 60%).");
    else if (m.ratio < 0.85) o.push("Volume is " + Math.round(m.ratio * 100) + "% of baseline (watch line: 85%).");
    if (m.idle > 45) o.push(m.idle + " days since the last transaction (at-risk line: 45).");
    else if (m.idle > 20) o.push(m.idle + " days since the last transaction (watch line: 20).");
    if (m.tickets >= 2) o.push(m.tickets + " support tickets this month.");
    if (m.declining >= 2) o.push("Below 85% of baseline for " + m.declining + " months in a row.");
    if (m.band === "churned" && m.churned_since) o.push("Churned since " + mlong(m.churned_since) + ".");
    return o.length ? o : ["Inside every threshold this month."];
  }
  var COLS = [["id", "Merchant"], ["cat_name", "Category"], ["band", "Band"], ["ratio", "Volume % of baseline", 1], ["chg3", "3-mo change %", 1], ["idle", "Days idle", 1], ["tickets", "Tickets", 1], ["declining", "Months declining", 1], ["tenure", "Tenure"], ["series", "24-month volume"]];
  var SEV = { "at-risk": 0, watch: 1, churned: 2, healthy: 3 };
  function saveList(el) {
    var counts = {}; BANDS.forEach(function (b) { counts[b] = 0; }); D.merchants.forEach(function (m) { counts[m.band]++; });
    el.innerHTML = head("Save list", "Merchants to call this month (" + mlong(LAST) + "), most urgent first. Select a row for the merchant's signals and to queue outreach.", "ATTRITION_MERCHANT_HEALTH view") +
      '<div class="filters"><div><span class="f" style="font-size:.8rem;font-weight:600;color:var(--ink2)">Risk band</span><div class="checks">' + BANDS.map(function (b) { return '<label><input type="checkbox" value="' + b + '"' + (state.bands.indexOf(b) >= 0 ? " checked" : "") + "> " + pill(b) + "</label>"; }).join("") + "</div></div>" +
      '<label class="f">Category<select id="slcat"><option value="">All categories</option>' + D.categories.map(function (c) { return '<option value="' + c.code + '"' + (state.cats === c.code ? " selected" : "") + ">" + esc(c.name) + "</option>"; }).join("") + "</select></label>" +
      '<label class="f">Search merchant ID<input type="text" id="slq" placeholder="e.g. ELECTRONICS-0" value="' + esc(state.q) + '"></label></div>' +
      '<p style="margin:.2rem 0 .8rem">' + BANDS.map(function (b) { return pill(b) + ' <span style="font-family:var(--mono);margin-right:.9rem">' + counts[b] + "</span>"; }).join(" ") + "</p>" +
      '<div class="card" id="sltable"></div><div id="slq-list"></div>';
    el.querySelectorAll(".checks input").forEach(function (cb) { cb.addEventListener("change", function () { state.bands = [].slice.call(el.querySelectorAll(".checks input:checked")).map(function (x) { return x.value; }); table(); }); });
    document.getElementById("slcat").addEventListener("change", function (e) { state.cats = e.target.value; table(); });
    document.getElementById("slq").addEventListener("input", function (e) { state.q = e.target.value; table(); });
    function table() {
      var rows = D.merchants.filter(function (m) { return (state.bands.length ? state.bands : BANDS).indexOf(m.band) >= 0 && (!state.cats || m.cat === state.cats) && (!state.q || m.id.toLowerCase().indexOf(state.q.trim().toLowerCase()) >= 0); });
      if (state.sort) { var k = state.sort; rows.sort(function (a, b) { var x = k === "band" ? SEV[a.band] : a[k], y = k === "band" ? SEV[b.band] : b[k]; if (x == null) return 1; if (y == null) return -1; return (x < y ? -1 : x > y ? 1 : 0) * state.dir; }); }
      var box = document.getElementById("sltable");
      if (!rows.length) { box.innerHTML = '<div class="empty"><b>No merchants match</b>Clear a filter or add the Healthy band.</div>'; return; }
      box.innerHTML = '<div class="tbl-wrap"><table class="t"><thead><tr>' + COLS.map(function (c) { return '<th scope="col" data-k="' + c[0] + '"' + (state.sort === c[0] ? ' aria-sort="' + (state.dir > 0 ? "ascending" : "descending") + '"' : "") + ">" + esc(c[1]) + "</th>"; }).join("") + "</tr></thead><tbody>" +
        rows.map(function (m) { return '<tr data-id="' + m.id + '" tabindex="0"><td style="font-family:var(--mono)">' + m.id + "</td><td>" + esc(m.cat_name) + "</td><td>" + pill(m.band) + '</td><td class="n">' + (m.ratio * 100).toFixed(1) + '%</td><td class="n">' + (m.chg3 == null ? "n/d" : pct(m.chg3)) + '</td><td class="n">' + m.idle + '</td><td class="n">' + m.tickets + '</td><td class="n">' + m.declining + "</td><td>" + esc(m.tenure) + "</td><td>" + spark(m.series, PLUM) + "</td></tr>"; }).join("") +
        '</tbody></table></div><p class="card-s" style="margin:.6rem 0 0">' + rows.length + " merchants · sort by any column header · thresholds: watch under 85% of baseline or 20+ idle days, at risk under 60% or 45+ idle days.</p>";
      box.querySelectorAll("th").forEach(function (th) { th.addEventListener("click", function () { var k = th.getAttribute("data-k"); if (k === "series") return; state.dir = state.sort === k ? -state.dir : 1; state.sort = k; table(); }); });
      box.querySelectorAll("tbody tr").forEach(function (tr) { function open() { drawer(tr.getAttribute("data-id")); } tr.addEventListener("click", open); tr.addEventListener("keydown", function (e) { if (e.key === "Enter") open(); }); });
    }
    table(); queueList();
  }
  function queueList() {
    var box = document.getElementById("slq-list"); if (!box) return;
    box.innerHTML = state.outreach.length ? '<div class="card"><p class="card-h">Outreach queued this session</p>' + state.outreach.map(function (x) { return '<div class="cat"><div style="font-family:var(--mono)">' + esc(x.id) + "</div><div>" + esc(x.action) + '</div><div style="color:var(--muted);font-size:.8rem">' + esc(x.owner) + "</div></div>"; }).join("") + "</div>" : "";
  }
  var drawerEl = document.getElementById("drawer"), scrim = document.getElementById("scrim");
  function closeDrawer() { drawerEl.classList.remove("open"); drawerEl.setAttribute("aria-hidden", "true"); scrim.hidden = true; }
  scrim.addEventListener("click", function () { closeDrawer(); closeRail(); });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") { closeDrawer(); closeRail(); } });
  function drawer(id) {
    var m = D.merchants.filter(function (x) { return x.id === id; })[0], cs = D.cat_series[m.cat];
    var dem = cs.demand.map(function (v) { return v / cs.demand[0] * 100; });
    var s = [{ name: "Merchant volume, % of baseline", values: m.series, color: PLUM }, { name: "Category demand, indexed", values: dem, color: DEMAND, dash: true }];
    var box = document.getElementById("drawer-in");
    box.innerHTML = '<div style="display:flex;justify-content:space-between;align-items:center;gap:.5rem"><div style="display:flex;gap:.5rem;align-items:center;flex-wrap:wrap"><b style="font-family:var(--mono);font-size:1.05rem">' + m.id + "</b>" + pill(m.band) + '</div><button class="btn" id="dclose" aria-label="Close">Close</button></div>' +
      '<p class="card-s" style="margin:.3rem 0">' + esc(m.cat_name) + " · " + esc(m.tenure) + "</p>" +
      '<div class="facts"><div><small>Volume, ' + mshort(LAST) + "</small><b>" + usd(m.vol) + "</b></div><div><small>Baseline / month</small><b>" + usd(m.base) + "</b></div><div><small>Days idle</small><b>" + m.idle + "</b></div><div><small>Support tickets</small><b>" + m.tickets + "</b></div></div>" +
      '<ul class="why">' + why(m).map(function (w) { return "<li>" + esc(w) + "</li>"; }).join("") + "</ul>" +
      lineChart(months, s, { ylab: "%", h: 260, W: 520, unit: "", rules: [[85, "watch 85%"], [60, "at risk 60%"]], aria: "Merchant volume vs category demand" }) + lineLegend(s) +
      (m.band === "watch" || m.band === "at-risk" ? '<form id="oform" style="margin-top:.8rem"><div class="grid2e"><label class="f">Next step<select name="a"><option>Relationship call</option><option>Pricing review</option><option>Service recovery</option><option>Monitor only</option></select></label><label class="f">Owner<input type="text" name="o" value="Retention desk" maxlength="60"></label></div><label class="f" style="margin-top:.5rem">Note<input type="text" name="n" placeholder="Optional" maxlength="300"></label><button class="btn primary wide" style="margin-top:.7rem">Add to outreach queue</button></form><div id="omsg"></div>' : "") +
      '<div class="src">Source: <code>ATTRITION_MERCHANT_HEALTH</code> and <code>ATTRITION_CATEGORY_HEALTH</code>. In Live mode the queue is saved to <code>ATTRITION_OUTREACH</code>.</div>';
    bindTips(box);
    document.getElementById("dclose").addEventListener("click", closeDrawer);
    var f = document.getElementById("oform");
    if (f) f.addEventListener("submit", function (e) { e.preventDefault(); var a = f.a.value, o = f.o.value || "Retention desk"; state.outreach.unshift({ id: m.id, action: a, owner: o }); document.getElementById("omsg").innerHTML = '<div class="ok-msg">' + esc(m.id) + " added: " + esc(a) + ", owner " + esc(o) + ". Sample mode: kept in this session only.</div>"; queueList(); });
    drawerEl.classList.add("open"); drawerEl.setAttribute("aria-hidden", "false"); scrim.hidden = false; document.getElementById("dclose").focus();
  }

  function categories(el) {
    var cats = D.categories; if (!state.cat) state.cat = cats[0].code;
    var CC = [["name", "Category"], ["diagnosis", "Diagnosis"], ["book_yoy", "Book YoY %", 1], ["demand_yoy", "Demand YoY %", 1], ["gap", "Gap (pts)", 1], ["nrr", "NRR %", 1], ["churn_rate", "Churn rate %", 1], ["active", "Active", 1], ["watch", "Watch", 1], ["at_risk", "At risk", 1], ["churned", "Churned", 1], ["trend", "Volume trend ($M)"]];
    el.innerHTML = head("Categories", "Each MCC category's book against its demand backdrop, " + mlong(LAST) + " vs a year earlier. A book shrinking 10+ points faster than demand is a retention problem; a book shrinking with its market is a slowdown.", "ATTRITION_MERCHANT_HEALTH + ATTRITION_CATEGORY_HEALTH") +
      '<div class="card"><div class="tbl-wrap"><table class="t"><thead><tr>' + CC.map(function (c) { return '<th scope="col">' + esc(c[1]) + "</th>"; }).join("") + "</tr></thead><tbody>" +
      cats.map(function (c) { return '<tr data-c="' + c.code + '" tabindex="0"' + (c.code === state.cat ? ' class="sel"' : "") + "><td>" + esc(c.name) + "</td><td>" + dpill(c.diagnosis) + '</td><td class="n">' + pct(c.book_yoy) + '</td><td class="n">' + pct(c.demand_yoy) + '</td><td class="n">' + (c.gap >= 0 ? "+" : "") + c.gap.toFixed(1) + '</td><td class="n">' + c.nrr.toFixed(1) + '%</td><td class="n">' + c.churn_rate.toFixed(1) + '%</td><td class="n">' + c.active + '</td><td class="n">' + c.watch + '</td><td class="n">' + c.at_risk + '</td><td class="n">' + c.churned + "</td><td>" + spark(c.trend, PLUM) + "</td></tr>"; }).join("") +
      '</tbody></table></div><p class="card-s" style="margin:.6rem 0 0">Gap = book YoY minus demand YoY. Churn rate = churned merchants / all 20 merchants in the category. Select a row to drill in.</p></div><div id="catd"></div>';
    el.querySelectorAll("tbody tr").forEach(function (tr) { function go() { state.cat = tr.getAttribute("data-c"); categories(el); } tr.addEventListener("click", go); tr.addEventListener("keydown", function (e) { if (e.key === "Enter") go(); }); });
    var c = cats.filter(function (x) { return x.code === state.cat; })[0], cs = D.cat_series[c.code];
    var l12 = months.slice(-12), yoy = [{ name: "Merchant book", values: cs.book_yoy.slice(-12), color: PLUM }, { name: "Category demand", values: cs.demand_yoy.slice(-12), color: DEMAND, dash: true }];
    var nrr = cats.map(function (k) { return { name: k.name, values: D.cat_series[k.code].nrr, color: k.code === c.code ? PLUM : "#CDBFD8", w: k.code === c.code ? 3 : 1.4, noPts: k.code !== c.code }; });
    nrr.sort(function (a) { return a.color === PLUM ? 1 : -1; });
    var box = document.getElementById("catd");
    box.innerHTML = '<div style="display:flex;gap:.6rem;align-items:center;flex-wrap:wrap;margin:.2rem 0 .7rem"><b style="font-size:1.1rem">' + esc(c.name) + "</b>" + dpill(c.diagnosis) + '<span class="card-s" style="margin:0">book ' + pct(c.book_yoy) + " · demand " + pct(c.demand_yoy) + " · NRR " + c.nrr.toFixed(1) + "%</span></div>" +
      '<div class="grid2e"><div class="card"><p class="card-h">Year-on-year change, last 12 months</p><p class="card-s">Solid: merchant book volume. Dashed: category demand.</p>' + lineChart(l12, yoy, { ylab: "YoY change (%)", zero: true, unit: "%", h: 240, aria: "Book vs demand year-on-year change" }) + lineLegend(yoy) + "</div>" +
      '<div class="card"><p class="card-h">Risk bands by tenure, this month</p><p class="card-s">Merchants per tenure band. Hover for counts.</p>' + hbars(TENURES.map(function (t) { return { label: t, parts: cs.tenure[t] }; }).filter(function (r) { return sum(BANDS.map(function (b) { return r.parts[b]; })) > 0; })) + legend(BANDS) + "</div></div>" +
      '<div class="card"><p class="card-h">Net revenue retention by category</p><p class="card-s">Processed volume as % of baseline, per month-end. The selected category is drawn bold.</p>' + lineChart(months, nrr, { ylab: "NRR (%)", unit: "%", h: 260, W: Math.max(560, Math.min(1160, main.clientWidth - 40)), aria: "NRR by category" }) + "</div>";
    bindTips(el);
  }

  // ---------------------------------------------------------------- AI (Sample replay)
  function stepsHtml(steps, cur, fin) { return '<ul class="steps">' + steps.map(function (s, i) { var c = fin || i < cur ? "done" : i === cur ? "now" : ""; return '<li class="' + c + '"><span class="ic"></span><span>' + esc(s) + "</span></li>"; }).join("") + "</ul>"; }
  function noteSteps(scope) { var n = scope === "ALL" ? 6 : 1; return ["Building the fact pack: " + n + " categor" + (n === 1 ? "y" : "ies") + " from ATTRITION_BENCHMARK (latest month and a year earlier)", "Drafting the note with AI_COMPLETE (" + MODEL + ") under the DATA RULES", "Fact-checking every number against the fact pack with a second AI_COMPLETE pass", "Saving the note and verdict to ATTRITION_REPORTS"]; }
  function staged(box, steps, done) {
    var total = 4000 + Math.random() * 4000, i = 0;
    (function tick() { box.innerHTML = '<div class="card">' + stepsHtml(steps, i) + "</div>"; if (i++ < steps.length) setTimeout(tick, total / steps.length); else { box.innerHTML = '<div class="card">' + stepsHtml(steps, 0, true) + "</div>"; done(); } })();
  }
  function inline(s) { return esc(s).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/`([^`]+)`/g, "<code>$1</code>"); }
  function md(text) {
    var L = (text || "").split("\n"), out = [], i = 0;
    while (i < L.length) {
      var l = L[i];
      if (/^\s*\|/.test(l)) { var rows = []; while (i < L.length && /^\s*\|/.test(L[i])) { rows.push(L[i]); i++; }
        var cells = rows.filter(function (r) { return !/^\s*\|[\s:|-]+\|\s*$/.test(r); }).map(function (r) { return r.trim().replace(/^\||\|$/g, "").split("|").map(function (c) { return c.trim(); }); });
        out.push("<table><thead><tr>" + cells[0].map(function (c) { return "<th>" + inline(c) + "</th>"; }).join("") + "</tr></thead><tbody>" + cells.slice(1).map(function (r) { return "<tr>" + r.map(function (c) { return "<td>" + inline(c) + "</td>"; }).join("") + "</tr>"; }).join("") + "</tbody></table>"); continue; }
      if (/^\s*([-*•]|\d+\.)\s+/.test(l)) { var items = []; while (i < L.length && /^\s*([-*•]|\d+\.)\s+/.test(L[i])) { items.push("<li>" + inline(L[i].replace(/^\s*([-*•]|\d+\.)\s+/, "")) + "</li>"); i++; } out.push("<ul>" + items.join("") + "</ul>"); continue; }
      var h = /^(#{1,3})\s+(.*)$/.exec(l);
      if (h) out.push("<h" + Math.min(h[1].length, 2) + ">" + inline(h[2]) + "</h" + Math.min(h[1].length, 2) + ">");
      else if (l.trim()) out.push("<p>" + inline(l) + "</p>");
      i++;
    }
    return out.join("");
  }
  function reveal(el, html) { // streaming-style reveal, block by block then word by word inside paragraphs
    var tmp = document.createElement("div"); tmp.innerHTML = html; var blocks = [].slice.call(tmp.children); el.innerHTML = "";
    var reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
    (function next() { var b = blocks.shift(); if (!b) return; el.appendChild(b);
      if (!reduce && (b.tagName === "P" || b.tagName === "UL")) { b.style.opacity = 0; b.style.transition = "opacity .25s"; requestAnimationFrame(function () { b.style.opacity = 1; }); }
      setTimeout(next, reduce ? 0 : 140); })();
  }
  function noteCard(n, animate) {
    var fp = n.fact_pack || [], cats = fp.map(function (r) { return r.category; });
    return '<div class="card"><div style="display:flex;gap:.5rem;flex-wrap:wrap;align-items:center">' + verdict(n.status) + '<span class="cap">Sample AI response · captured from a Live run</span><span style="font-size:.8rem;color:var(--muted)">residual hedges: ' + n.residual_hedges + " · flagged: " + (n.edits || []).length + "</span></div>" +
      ((n.edits || []).length ? '<div class="flag"><b>Verifier flagged</b><br>' + n.edits.map(function (e) { return "• " + esc(e); }).join("<br>") + "</div>" : "") +
      '<div class="md" id="mdbody">' + (animate ? "" : md(n.markdown)) + '</div><div class="src">Sources: ' + fp.length + " categor" + (fp.length === 1 ? "y" : "ies") + " rolled up from <code>ATTRITION_BENCHMARK</code> · month <code>" + esc((fp[0] || {}).month || "") + "</code> (and a year earlier) · " + esc(cats.join(", ")) + " · model <code>" + esc(n.model) + "</code> · " + (n.latency_ms / 1000).toFixed(1) + " s measured in Live</div></div>";
  }
  function notes(el) {
    var lib = Object.keys(D.ai.notes).map(function (k) { return D.ai.notes[k]; });
    el.innerHTML = head("Attrition notes", "A one-page save-list note written only from a fact pack of allowed numbers, contrasting each category with its demand backdrop, then fact-checked by a second model pass.", "Sample AI responses · Cortex AI_COMPLETE in Live") +
      '<div class="grid2" style="grid-template-columns:minmax(0,1fr) minmax(0,2.2fr)"><div class="card"><p class="card-h">Write a note</p><p class="card-s">Latest month vs a year earlier, per category.</p><label class="f">Scope<select id="scope">' + Object.keys(SCOPES).map(function (k) { return '<option value="' + k + '">' + esc(SCOPES[k]) + "</option>"; }).join("") + '</select></label><button class="btn primary wide" id="run" style="margin-top:.7rem">Run attrition analysis</button><div id="pre">' + stepsHtml(noteSteps("ALL"), -1) + '</div></div><div id="out">' + (state.note ? noteCard(state.note) : '<div class="card empty"><b>No note yet</b>Pick a scope and run the analysis to see the staged steps, the note and the verifier verdict.</div>') + "</div></div>" +
      '<p class="card-h" style="margin-top:.4rem">Note library</p><div class="lib">' + lib.map(function (n, i) { var t = (n.markdown || "").split("\n")[0].replace(/^#+\s*/, ""); return '<div class="card" data-i="' + i + '" tabindex="0">' + verdict(n.status) + '<p class="card-h" style="margin-top:.45rem">' + esc(n.subject) + '</p><p class="card-s">' + esc(t.slice(0, 90)) + "</p></div>"; }).join("") + "</div>";
    var sc = document.getElementById("scope"); sc.addEventListener("change", function () { document.getElementById("pre").innerHTML = stepsHtml(noteSteps(sc.value), -1); });
    document.getElementById("run").addEventListener("click", function () {
      var btn = this, n = D.ai.notes[sc.value], out = document.getElementById("out"); btn.disabled = true;
      staged(out, noteSteps(sc.value), function () { state.note = n; out.innerHTML += noteCard(n, true); reveal(document.getElementById("mdbody"), md(n.markdown)); btn.disabled = false; });
    });
    el.querySelectorAll(".lib .card").forEach(function (c) { function o() { state.note = lib[+c.getAttribute("data-i")]; document.getElementById("out").innerHTML = noteCard(state.note); window.scrollTo({ top: 0, behavior: "smooth" }); } c.addEventListener("click", o); c.addEventListener("keydown", function (e) { if (e.key === "Enter") o(); }); });
  }
  function answerCard(a, animate) {
    var t = a.table, tbl = "";
    if (t && t.rows && t.rows.length) tbl = '<div class="tbl-wrap" style="margin-top:.6rem"><table class="t" style="min-width:0"><thead><tr>' + t.columns.map(function (c) { return "<th>" + esc(c) + "</th>"; }).join("") + "</tr></thead><tbody>" + t.rows.map(function (r) { return "<tr>" + r.map(function (v) { var n = v != null && !isNaN(+v) && v !== ""; return "<td" + (n ? ' class="n"' : "") + ">" + esc(n ? String(+(+v).toFixed(2)) : v == null ? "" : v) + "</td>"; }).join("") + "</tr>"; }).join("") + "</tbody></table></div>";
    return '<div class="card"><div style="display:flex;gap:.5rem;align-items:center;flex-wrap:wrap"><b>' + esc(a.question) + '</b><span class="cap">Sample AI response · captured from a Live run</span></div><div class="md" id="ansbody">' + (animate ? "" : md(a.text)) + "</div>" + tbl +
      (a.sql ? '<details class="sql"><summary>SQL written by Cortex Analyst</summary><pre>' + esc(a.sql) + "</pre></details>" : "") +
      '<div class="src">Source: semantic view <code>ATTRITION_SV</code> via agent <code>ATTRITION_AGENT</code> · ' + (a.latency_ms / 1000).toFixed(1) + " s measured in Live</div></div>";
  }
  function ask(el) {
    var qs = Object.keys(D.ai.ask);
    el.innerHTML = head("Ask the agent", "Plain-English questions about merchant health. The agent writes SQL over the semantic view and answers only from the result.", "Sample AI responses · Cortex Agents in Live") +
      '<div class="card"><p class="card-s">Try a question</p><div class="qs">' + qs.map(function (q, i) { return '<button type="button" data-i="' + i + '"' + (state.answer && state.answer.question === q ? ' class="on"' : "") + ">" + esc(q) + "</button>"; }).join("") + '</div><p class="card-s" style="margin:.6rem 0 0">Sample mode replays the four suggested questions. Run it Live to ask your own.</p></div><div id="ans">' + (state.answer ? answerCard(state.answer) : '<div class="card empty"><b>No question yet</b>Pick a suggested question to see the agent at work.</div>') + "</div>";
    el.querySelectorAll(".qs button").forEach(function (b) { b.addEventListener("click", function () {
      el.querySelectorAll(".qs button").forEach(function (x) { x.classList.remove("on"); x.disabled = true; }); b.classList.add("on");
      var a = D.ai.ask[qs[+b.getAttribute("data-i")]], box = document.getElementById("ans");
      staged(box, ASK_STEPS, function () { state.answer = a; box.innerHTML += answerCard(a, true); reveal(document.getElementById("ansbody"), md(a.text)); el.querySelectorAll(".qs button").forEach(function (x) { x.disabled = false; }); });
    }); });
  }

  function countUp(root) {
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    root.querySelectorAll("[data-count]").forEach(function (el) {
      var txt = el.textContent, m = /^(-?\d+(?:\.\d+)?)(.*)$/.exec(txt); if (!m) return;
      var target = +m[1], dec = (m[1].split(".")[1] || "").length, t0 = performance.now();
      (function f(t) { var p = Math.min(1, (t - t0) / 700); el.textContent = (target * (1 - Math.pow(1 - p, 3))).toFixed(dec) + m[2]; if (p < 1) requestAnimationFrame(f); })(t0);
    });
  }

  // ---------------------------------------------------------------- shell
  var RENDER = { overview: overview, "save-list": saveList, categories: categories, notes: notes, ask: ask };
  var nav = document.getElementById("nav"), main = document.getElementById("main"), rail = document.getElementById("rail"), menu = document.getElementById("menu");
  nav.innerHTML = VIEWS.map(function (v) { return '<a href="#' + v[0] + '">' + esc(v[1]) + "</a>"; }).join("");
  function closeRail() { rail.classList.remove("open"); menu.setAttribute("aria-expanded", "false"); if (!drawerEl.classList.contains("open")) scrim.hidden = true; }
  menu.addEventListener("click", function () { rail.classList.add("open"); menu.setAttribute("aria-expanded", "true"); scrim.hidden = false; });
  function route() {
    var k = (location.hash || "#overview").slice(1); if (!RENDER[k]) k = "overview";
    nav.querySelectorAll("a").forEach(function (a) { if (a.getAttribute("href") === "#" + k) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current"); });
    closeDrawer(); closeRail(); tip.hidden = true;
    RENDER[k](main); bindTips(main); main.focus({ preventScroll: true }); window.scrollTo(0, 0);
    document.title = VIEWS.filter(function (v) { return v[0] === k; })[0][1] + " · Merchant Attrition Early-Warning (sample data)";
  }
  window.addEventListener("hashchange", route);
  document.querySelectorAll(".seg button").forEach(function (b) { b.addEventListener("click", function () {
    if (b.getAttribute("data-mode") !== "Live") return;
    var m = document.createElement("div"); m.className = "modal"; m.innerHTML = '<div class="card" role="dialog" aria-modal="true" aria-label="Live mode"><p class="card-h">Live mode runs on your Snowflake account</p><p style="font-size:.9rem;color:var(--ink2)">This hosted example is always Sample mode and never asks for credentials. To run the same app Live: run <code>sql/setup.sql</code> in a Snowsight worksheet, then start the Streamlit app with key-pair auth or deploy it as Streamlit in Snowflake.</p><p><a href="https://github.com/sfc-gh-jsoliz/sfguide-merchant-attrition#live-mode">Live-mode guide in the repository</a></p><button class="btn primary" type="button">Stay in Sample mode</button></div>';
    document.body.appendChild(m); var close = function () { m.remove(); }; m.querySelector("button").addEventListener("click", close); m.addEventListener("click", function (e) { if (e.target === m) close(); }); m.querySelector("button").focus();
  }); });
  route();
})();
