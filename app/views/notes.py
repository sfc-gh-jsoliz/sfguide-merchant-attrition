"""Attrition notes: the grounded note loop (fact pack -> AI_COMPLETE draft -> AI_COMPLETE verify)."""
import json
import time

import streamlit as st

import ai
import brand
import data


def stream(text):
    for i, w in enumerate(text.split(" ")):
        yield w + " "
        if i % 3 == 0:
            time.sleep(0.012)


def sources(note):
    fp = note.get("fact_pack") or []
    if isinstance(fp, str):
        fp = json.loads(fp)
    months = sorted({r["month"] for r in fp})
    cats = sorted({r["category"] for r in fp})
    return (f'<div class="mw-src">Sources: {len(fp)} categor{"y" if len(fp) == 1 else "ies"} rolled up from <code>ATTRITION_BENCHMARK</code> · month '
            f'{", ".join(f"<code>{m}</code>" for m in months)} (and a year earlier) · {brand.esc(", ".join(cats))} · '
            f'model <code>{brand.esc(note.get("model", ai.MODEL))}</code> · {int(note.get("latency_ms") or 0) / 1000:.1f} s</div>')


def show_note(note, mode, animate=False):
    lbl = ('<span class="mw-cap sample">Sample AI response · captured from a Live run</span>' if mode != "Live"
           else '<span class="mw-cap">Live · AI_COMPLETE</span>')
    st.markdown(f'<div style="display:flex;gap:.5rem;flex-wrap:wrap;align-items:center">{brand.verdict(note["status"])} {lbl}'
                f'<span style="font-size:.8rem;color:var(--muted)">residual hedges: {note.get("residual_hedges")} · flagged: {len(note.get("edits") or [])}</span></div>',
                unsafe_allow_html=True)
    edits = note.get("edits") or []
    if edits:
        st.markdown('<div class="mw-insight" style="border-left-color:var(--loss)"><b>Verifier flagged</b><br>' +
                    "<br>".join(f"• {brand.esc(e)}" for e in edits) + "</div>", unsafe_allow_html=True)
    box = st.container(key="note_body")
    with box:
        if animate:
            st.write_stream(stream(brand.md_safe(note["markdown"])))
        else:
            st.markdown(brand.md_safe(note["markdown"]))
    st.markdown(sources(note), unsafe_allow_html=True)


def render(mode):
    st.markdown(brand.header(
        "Attrition notes", "A one-page save-list note written only from a fact pack of allowed numbers, contrasting each category with its demand backdrop, then fact-checked by a second model pass.",
        "Powered by Cortex AI_COMPLETE" if mode == "Live" else "Sample AI responses · Cortex AI_COMPLETE in Live", mode != "Live"),
        unsafe_allow_html=True)
    left, right = st.columns([1, 2.2], gap="medium")
    with left.container(key="card_gen"):
        st.markdown('<p class="mw-card-h">Write a note</p><p class="mw-card-s">Latest month vs a year earlier, per category.</p>', unsafe_allow_html=True)
        scope = st.selectbox("Scope", list(ai.SCOPES), format_func=ai.SCOPES.get, key="note_scope")
        go = st.button("Run attrition analysis", type="primary", width="stretch")
        st.markdown(brand.steps_html(ai.note_steps(scope), -1), unsafe_allow_html=True)

    with right:
        if go:
            steps = ai.note_steps(scope)
            ph = st.empty()

            def on_step(i, _s):
                ph.markdown(f'<div class="mw-card">{brand.steps_html(steps, i)}</div>', unsafe_allow_html=True)
            try:
                if mode == "Live":
                    note = ai.run_note_live(scope, on_step)
                    data.saved_notes.clear()
                else:
                    note = ai.sample_ai()["notes"].get(scope)
                    ai.sample_wait(on_step, steps)
                    if note is None:
                        raise RuntimeError("No captured sample for this scope.")
            except Exception as e:
                ph.empty()
                st.error(f"Note run failed: {e}")
                return
            ph.markdown(f'<div class="mw-card">{brand.steps_html(steps, len(steps), True)}</div>', unsafe_allow_html=True)
            st.session_state["last_note"] = note
            with st.container(key="card_note"):
                show_note(note, mode, animate=True)
        elif st.session_state.get("last_note"):
            with st.container(key="card_note"):
                show_note(st.session_state["last_note"], mode)

    st.markdown('<p class="mw-card-h" style="margin-top:1.2rem">Note library</p>', unsafe_allow_html=True)
    try:
        lib = (data.saved_notes(mode).to_dict("records") if mode == "Live"
               else list(ai.sample_ai()["notes"].values()))
    except Exception as e:
        st.error(f"Could not read ATTRITION_REPORTS: {e}")
        return
    if not lib:
        st.markdown('<div class="mw-card mw-empty"><b>No notes yet</b>Run an analysis above; each run is saved to ATTRITION_REPORTS.</div>', unsafe_allow_html=True)
        return
    cols = st.columns(3)
    for i, n in enumerate(lib[:9]):
        for k in ("edits", "fact_pack"):
            if isinstance(n.get(k), str):
                n[k] = json.loads(n[k])
        n.setdefault("markdown", n.get("report_md"))
        with cols[i % 3].container(key=f"card_lib_{i}"):
            title = (n["markdown"] or "").split("\n")[0].lstrip("# ").strip()
            st.markdown(f'{brand.verdict(n["status"])}<p class="mw-card-h" style="margin-top:.45rem">{brand.esc(n["subject"])}</p>'
                        f'<p class="mw-card-s">{brand.esc(title[:90])}</p>', unsafe_allow_html=True)
            if st.button("Open note", key=f"open_{i}", width="stretch"):
                st.session_state["last_note"] = n
                st.rerun()
