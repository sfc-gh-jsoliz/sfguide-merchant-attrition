"""AI calls: the grounded attrition note (draft + verify with AI_COMPLETE) and Ask the
agent (ATTRITION_AGENT, a Cortex Agent over the ATTRITION_SV semantic view, via
DATA_AGENT_RUN).

Sample mode replays responses captured from Live runs (sample/ai.json) after a
4-8 s staged wait, and the UI labels them "Sample AI response".
"""
import json
import random
import time
from pathlib import Path

from data import SCHEMA, session

MODEL = "claude-sonnet-4-5"
AGENT = f"{SCHEMA}.ATTRITION_AGENT"
SAMPLE_AI = Path(__file__).parent / "sample" / "ai.json"

SCOPES = {
    "ALL": "All categories",
    "RESTAURANTS": "Restaurants & Food Service", "APPAREL": "Clothing & Accessories",
    "ELECTRONICS": "Electronics & Appliances", "GROCERY": "Food & Beverage Stores",
    "FURNITURE": "Furniture & Home Furnishings", "HEALTH": "Health & Personal Care",
}

QUESTIONS = [
    "Which categories have the most at-risk and watch merchants in June 2026, and is their category demand growing or shrinking?",
    "What was net revenue retention by category in June 2026?",
    "How did the number of churned merchants in Electronics & Appliances change between June 2025 and June 2026?",
    "Which tenure band has the highest churn rate in June 2026?",
]

RULES = (
    "You are a payments merchant-retention analyst. Write a concise attrition early-warning note using ONLY the FACTS JSON.\n"
    "DATA RULES: use only numbers in FACTS, copy exactly; churn_rate_pct, net_revenue_retention_pct and the *_yoy_pct fields are percentages; "
    "book_volume_yoy_pct is the merchant book's processed-volume change vs the same month a year earlier; "
    "category_demand_yoy_pct is the category demand backdrop: contrast the book with it, and call a category a retention problem when its book "
    "shrinks much faster than its demand, or a market slowdown when demand itself is shrinking; "
    "dollars are USD; no estimates, no hedging, no outside benchmarks; missing = n/d. "
    "Do not name any real company, processor or merchant. Write in plain English only.\n"
    "OUTPUT markdown starting with '# ', a one-line takeaway (where attrition is worst), a table "
    "(category | active | watch | at-risk | churned | churn rate % | NRR % | book YoY % | category demand YoY %), "
    "3 bullets prioritizing a save-list, ending with '## Data Coverage'."
)


def sample_ai():
    return json.loads(SAMPLE_AI.read_text()) if SAMPLE_AI.exists() else {"notes": {}, "ask": {}}


def note_steps(scope):
    n = 1 if scope != "ALL" else len(SCOPES) - 1
    return [
        f"Building the fact pack: {n} categor{'y' if n == 1 else 'ies'} from ATTRITION_BENCHMARK (latest month and a year earlier)",
        f"Drafting the note with AI_COMPLETE ({MODEL}) under the DATA RULES",
        "Fact-checking every number against the fact pack with a second AI_COMPLETE pass",
        "Saving the note and verdict to ATTRITION_REPORTS",
    ]


ASK_STEPS = [
    "Sending the question to the Merchant Attrition Agent (DATA_AGENT_RUN)",
    "Cortex Analyst writes SQL over the ATTRITION_SV semantic view",
    "Running the SQL on SNOWPACK_MERCHANT_ATTRITION_WH",
    "Composing the answer from the result set",
]


def sample_wait(on_step, steps):
    """Spread a 4-8 s jittered wait over the staged steps (Sample mode only)."""
    total = random.uniform(4.0, 8.0)
    for i, s in enumerate(steps):
        on_step(i, s)
        time.sleep(total / len(steps))


# ---------------------------------------------------------------- attrition note (Live)
def fact_pack(scope):
    where = "" if scope == "ALL" else "WHERE l.category_code = ?"
    params = [] if scope == "ALL" else [scope]
    raw = session().sql(f"""
        WITH z AS (SELECT MAX(month_end) z FROM {SCHEMA}.ATTRITION_BENCHMARK),
        g AS (
          SELECT b.category_code, b.category_name, b.month_end,
                 SUM(b.merchant_count) AS total_merchants, SUM(b.active_merchant_count) AS active_merchants,
                 SUM(b.churned_count) AS churned_merchants, SUM(b.at_risk_count) AS at_risk_merchants,
                 SUM(b.watch_count) AS watch_merchants, SUM(b.monthly_volume_usd) AS volume,
                 SUM(b.baseline_volume_usd) AS baseline, AVG(b.category_yoy_growth_pct) AS cat_yoy
          FROM {SCHEMA}.ATTRITION_BENCHMARK b, z
          WHERE b.month_end IN (z.z, LAST_DAY(DATEADD(month, -12, z.z)))
          GROUP BY 1, 2, 3)
        SELECT ARRAY_AGG(OBJECT_CONSTRUCT(
          'category', l.category_name, 'month', l.month_end::string,
          'total_merchants', l.total_merchants, 'active_merchants', l.active_merchants,
          'watch_merchants', l.watch_merchants, 'at_risk_merchants', l.at_risk_merchants,
          'churned_merchants', l.churned_merchants,
          'churn_rate_pct', ROUND(l.churned_merchants * 100.0 / NULLIF(l.total_merchants, 0), 1),
          'net_revenue_retention_pct', ROUND(l.volume * 100.0 / NULLIF(l.baseline, 0), 1),
          'book_volume_usd', l.volume, 'book_volume_year_earlier_usd', y.volume,
          'book_volume_yoy_pct', ROUND((l.volume / NULLIF(y.volume, 0) - 1) * 100, 1),
          'churned_merchants_year_earlier', y.churned_merchants,
          'category_demand_yoy_pct', ROUND(l.cat_yoy, 1))) WITHIN GROUP (ORDER BY l.category_name)
        FROM g l JOIN z ON l.month_end = z.z
        JOIN g y ON y.category_code = l.category_code AND y.month_end <> z.z
        {where}
    """, params=params).collect()[0][0]
    return json.loads(raw)


def complete(prompt):
    raw = session().sql("SELECT AI_COMPLETE(?, ?)", params=[MODEL, prompt]).collect()[0][0]
    # The string result can arrive JSON-encoded ("..." with escapes); decode it once.
    if isinstance(raw, str) and raw.startswith('"'):
        try:
            raw = json.loads(raw)
        except ValueError:
            pass
    return raw.strip()


def draft_note(fp):
    return complete(RULES + f"\n\nFACTS: {json.dumps(fp)}")


def _last_json(raw):
    """The verifier may re-check itself and emit several JSON objects; keep the last one."""
    dec, i, last = json.JSONDecoder(), 0, None
    while True:
        s = raw.find("{", i)
        if s < 0:
            return last
        try:
            obj, end = dec.raw_decode(raw, s)
            if isinstance(obj, dict) and "status" in obj:
                last = obj
            i = end
        except ValueError:
            i = s + 1


def verify(fp, draft):
    vp = (
        "You are a fact-checker. Compare the DRAFT against the FACTS JSON (only allowed source). Return ONLY a JSON object with keys "
        "status (exactly 'verified' if every number/claim is supported and no hedge words like likely/approximately/around/could, else exactly 'needs_review'), "
        "residual_hedges (int), edits (array of strings, each naming the unsupported or hedged claim). "
        "Exact figures written with thousands separators, and rounding a FACTS number to the draft's display units ($M/$K with one or two decimals, whole or one-decimal "
        "percentages) counts as supported, and so do differences of two FACTS numbers (e.g. percentage-point gaps) when the "
        "arithmetic is right, rounded to whole or one-decimal points. The draft was told to label categories 'retention problem' "
        "(book shrinking much faster than category demand) or 'market slowdown' (demand itself shrinking) and to recommend "
        "save-list priorities: such labels and recommendations are allowed when they follow from FACTS. Flag only wrong numbers, "
        "invented facts, hedges and any non-English text.\n\n"
        f"FACTS: {json.dumps(fp)}\n\nDRAFT:\n{draft}"
    )
    v = _last_json(complete(vp))
    if v is None:
        v = {"status": "needs_review", "residual_hedges": None, "edits": ["The verifier output could not be parsed."]}
    v["status"] = "verified" if v.get("status") == "verified" else "needs_review"
    return v


def save_note(scope, draft, v, fp, latency_ms):
    session().sql(
        f"""INSERT INTO {SCHEMA}.ATTRITION_REPORTS
            (subject, draft_md, report_md, status, edits_applied, residual_hedges, edits, fact_pack, model, latency_ms)
            SELECT ?, ?, ?, ?, ?, ?, PARSE_JSON(?), PARSE_JSON(?), ?, ?""",
        params=[SCOPES[scope], draft, draft, v["status"], len(v.get("edits") or []), v.get("residual_hedges"),
                json.dumps(v.get("edits") or []), json.dumps(fp), MODEL, latency_ms],
    ).collect()


def run_note_live(scope, on_step):
    t0 = time.time()
    steps = note_steps(scope)
    on_step(0, steps[0])
    fp = fact_pack(scope)
    on_step(1, steps[1])
    draft = draft_note(fp)
    on_step(2, steps[2])
    v = verify(fp, draft)
    latency = int((time.time() - t0) * 1000)
    on_step(3, steps[3])
    save_note(scope, draft, v, fp, latency)
    return {"scope": scope, "subject": SCOPES[scope], "markdown": draft, "status": v["status"],
            "edits": v.get("edits") or [], "residual_hedges": v.get("residual_hedges"),
            "fact_pack": fp, "model": MODEL, "latency_ms": latency}


# ---------------------------------------------------------------- ask the agent (Live)
def parse_agent(raw):
    """Final answer = text and table blocks after the last tool block; SQL from the tool result."""
    j = json.loads(raw) if isinstance(raw, str) else raw
    content = j.get("content", [])
    last_tool = max([i for i, b in enumerate(content) if b.get("type") in ("tool_use", "tool_result")], default=-1)
    text, table, sql = [], None, None
    for b in content:
        if b.get("type") == "tool_result":
            for c in b["tool_result"].get("content", []):
                if isinstance(c.get("json"), dict) and c["json"].get("sql"):
                    sql = c["json"]["sql"]
    for b in content[last_tool + 1:]:
        if b.get("type") == "text":
            text.append(b["text"])
        elif b.get("type") == "table" and table is None:
            rs = b["table"].get("result_set", {})
            cols = [c["name"] for c in rs.get("resultSetMetaData", {}).get("rowType", [])]
            table = {"columns": cols, "rows": rs.get("data", [])}
    return {"text": "\n\n".join(text).strip(), "sql": sql, "table": table}


def ask_live(question, on_step):
    t0 = time.time()
    on_step(0, ASK_STEPS[0])
    body = json.dumps({"messages": [{"role": "user", "content": [{"type": "text", "text": question}]}], "stream": False})
    raw = session().sql("SELECT SNOWFLAKE.CORTEX.DATA_AGENT_RUN(?, ?)", params=[AGENT, body]).collect()[0][0]
    for i in (1, 2, 3):
        on_step(i, ASK_STEPS[i])
    out = parse_agent(raw)
    out.update({"question": question, "latency_ms": int((time.time() - t0) * 1000)})
    return out
