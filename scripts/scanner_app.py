"""Harm-classifier robustness scanner: an interactive console.

An editorial-styled console: a Front Page that leads with the findings, a Lab to
attack a classifier live, a Scan Report with the full evidence, and a Method &
Ethics note. Built for a Trust & Safety reviewer to read in 60 seconds.

    pip install -r requirements-app.txt
    streamlit run scripts/scanner_app.py

Runs on PUBLIC PROXY DATA ONLY. It demonstrates the *methodology* a content-
safety team would apply to a production detector; it does not, and must not, be
pointed at egregious-harms material. The methods transfer; the data does not.
"""
import datetime
import html
import json
import os
import sys

import pandas as pd
import streamlit as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
OUT = os.path.join(ROOT, "outputs")

from src.perturbations import EVASIONS, ZERO_WIDTH
from src.defenses import normalize_pipeline

EXAMPLES = [
    "you are an idiot and everyone knows it",
    "what a stupid worthless take",
    "i hate this loser so much",
    "people like that are pathetic trash",
]

st.set_page_config(page_title="The Robustness Review · Harm-Classifier Scanner",
                   page_icon="🛡️", layout="wide")

# --------------------------------------------------------------------------- #
# Editorial (NYT-style) skin
# --------------------------------------------------------------------------- #
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;0,900;1,400&family=Inter:wght@400;500;600;700;800&display=swap');
:root{ --ink:#111; --soft:#555; --mute:#888; --rule:#e5e5e5; --red:#b91c1c; --green:#15803d; }
html,body,[class*="css"],.stApp{ font-family:'Inter',-apple-system,sans-serif; }
.stApp{ background:#fff; color:var(--ink); }
[data-testid="stHeader"]{ background:transparent; }
.block-container{ max-width:1080px; padding-top:1.2rem; padding-bottom:4rem; }
.serif{ font-family:'Playfair Display','Georgia',serif; }
h1,h2,h3,h4{ font-family:'Playfair Display',serif; color:var(--ink); letter-spacing:-.3px; }
a{ color:var(--ink); text-decoration:underline; text-underline-offset:2px; }

/* masthead */
.masthead{ background:var(--ink); color:#fff; padding:16px 26px 20px; border-radius:4px; margin-bottom:6px; }
.mh-top{ display:flex; justify-content:space-between; align-items:center; font-size:10.5px;
         letter-spacing:2px; text-transform:uppercase; color:#9a9a9a; font-weight:600;
         border-bottom:1px solid #333; padding-bottom:10px; margin-bottom:14px; }
.mh-title{ font-family:'Playfair Display',serif; font-weight:900; font-size:42px;
           letter-spacing:-1.5px; text-align:center; line-height:1; color:#fff; }
.mh-sub{ text-align:center; font-size:10.5px; letter-spacing:4px; text-transform:uppercase;
         color:#aaa; font-weight:600; margin-top:11px; }

/* tabs -> section nav */
.stTabs [data-baseweb="tab-list"]{ gap:0; border-bottom:2px solid var(--ink); justify-content:center; }
.stTabs [data-baseweb="tab"]{ font-family:'Inter'; text-transform:uppercase; letter-spacing:1.6px;
                              font-size:12px; font-weight:700; color:var(--mute); padding:11px 22px; }
.stTabs [aria-selected="true"]{ color:var(--ink)!important; }
.stTabs [data-baseweb="tab-highlight"]{ background:var(--ink); height:2px; }

/* metrics */
[data-testid="stMetricValue"]{ font-family:'Playfair Display',serif; font-weight:700; color:var(--ink); }
[data-testid="stMetricLabel"]{ text-transform:uppercase; letter-spacing:1px; font-size:11px; color:var(--mute); }

/* buttons */
.stButton button, .stDownloadButton button{ background:var(--ink); color:#fff; border:none;
    border-radius:6px; font-weight:700; letter-spacing:.3px; }
.stButton button:hover, .stDownloadButton button:hover{ opacity:.85; color:#fff; background:var(--ink); }

/* rules */
.nyt-thin{ border:none; border-top:1px solid var(--rule); margin:18px 0; }
.nyt-thick{ border:none; border-top:2px solid var(--ink); margin:20px 0; }

/* editorial bits */
.kicker{ font-size:11px; letter-spacing:2.5px; text-transform:uppercase; color:var(--red); font-weight:700; }
.lead-head{ font-family:'Playfair Display',serif; font-weight:900; font-size:34px; line-height:1.06;
            letter-spacing:-.6px; margin:6px 0 10px; }
.standfirst{ font-family:'Playfair Display',serif; font-style:italic; font-size:18px; color:#444;
             line-height:1.45; margin-bottom:18px; }
.statstrip{ display:grid; grid-template-columns:repeat(4,1fr); border-top:2px solid var(--ink);
            border-bottom:2px solid var(--ink); margin:6px 0 22px; }
.statcell{ padding:14px 18px; border-right:1px solid var(--rule); }
.statcell:last-child{ border-right:none; }
.statnum{ font-family:'Playfair Display',serif; font-weight:900; font-size:30px; line-height:1; }
.statnum .red{ color:var(--red); }
.statlbl{ font-size:11px; color:#666; margin-top:7px; line-height:1.35; letter-spacing:.2px; }
.cols3{ display:grid; grid-template-columns:1fr 1fr 1fr; gap:0 26px; }
@media(max-width:760px){ .cols3{ grid-template-columns:1fr; } .statstrip{ grid-template-columns:1fr 1fr; } }
.finding{ padding-top:14px; border-top:1px solid var(--rule); }
.finding .fh{ font-family:'Playfair Display',serif; font-weight:700; font-size:18px; margin:0 0 5px; }
.finding p{ font-size:13.5px; color:#333; line-height:1.55; margin:0; }
.finding .big{ font-family:'Playfair Display',serif; font-weight:900; font-size:22px; color:var(--red); }
.byline{ font-size:11px; letter-spacing:1.5px; text-transform:uppercase; color:var(--mute);
         font-weight:600; margin-bottom:4px; }
.ethics-band{ border-left:3px solid var(--red); background:#fcfbfa; padding:11px 16px;
              font-size:13px; color:#555; line-height:1.5; margin:6px 0 18px; }
.ethics-band b{ color:var(--red); text-transform:uppercase; letter-spacing:1px; font-size:10.5px;
                display:block; margin-bottom:3px; }

/* hand-built editorial tables */
.nyt-table{ width:100%; border-collapse:collapse; font-size:13px; border-top:2px solid var(--ink);
            border-bottom:2px solid var(--ink); margin:8px 0; }
.nyt-table th{ font-family:'Inter'; text-transform:uppercase; letter-spacing:.8px; font-size:10.5px;
               color:var(--mute); text-align:left; padding:8px 10px; border-bottom:1px solid var(--ink); font-weight:700; }
.nyt-table td{ padding:8px 10px; border-bottom:1px solid var(--rule); vertical-align:middle; }
.nyt-table tr:last-child td{ border-bottom:none; }
.nyt-table .mono{ font-family:'JetBrains Mono','SF Mono',monospace; font-size:12px; }
.nyt-table .dim{ color:var(--mute); }
.tag-evaded{ color:var(--red); font-weight:700; }
.tag-caught{ color:var(--mute); font-weight:600; }
.tag-rec{ color:var(--green); font-weight:700; }
.tag-no{ color:var(--soft); }
.row-evaded{ background:#fdf5f4; }

/* bar list */
.bars{ margin:8px 0 6px; }
.bar-row{ display:flex; align-items:center; gap:10px; margin-bottom:6px; font-size:12.5px; }
.bar-lab{ width:150px; flex-shrink:0; text-align:right; color:var(--soft); }
.bar-track{ flex:1; height:14px; background:#f0f0f0; }
.bar-fill{ height:100%; display:block; }
.bar-val{ width:42px; font-family:'JetBrains Mono',monospace; font-size:12px; color:#333; }

.verdict{ border:2px solid var(--ink); padding:14px 18px; margin:6px 0 14px; display:flex;
          align-items:baseline; gap:18px; flex-wrap:wrap; }
.verdict .vnum{ font-family:'Playfair Display',serif; font-weight:900; font-size:32px; line-height:1; }
.verdict .vlbl{ font-size:11px; text-transform:uppercase; letter-spacing:1.5px; color:var(--mute); font-weight:700; }
</style>
""", unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Data / model helpers
# --------------------------------------------------------------------------- #
@st.cache_resource(show_spinner="Loading classifier…")
def _load_model(choice: str):
    if choice.startswith("Detoxify"):
        from src.models import DetoxifyModel
        return DetoxifyModel("unbiased")
    from src.models import ToyClassifier
    return ToyClassifier()


def load_model(choice: str):
    """Return (model, warning|None). Falls back to the offline ToyClassifier if
    the real model can't load (e.g. detoxify isn't installed on a lightweight
    public deployment), so the demo never hard-crashes on model choice."""
    try:
        return _load_model(choice), None
    except Exception as e:
        return _load_model("ToyClassifier"), (
            f"Real model unavailable here ({type(e).__name__}); using the offline "
            "ToyClassifier. Install `detoxify` to run the real model locally.")


@st.cache_data(show_spinner=False)
def load_cache(path: str):
    with open(path, "r", encoding="utf-8") as f:
        d = json.load(f)
    return d["results"], d["meta"]


def available_caches():
    if not os.path.isdir(OUT):
        return {}
    return {fn.replace(".results.json", ""): os.path.join(OUT, fn)
            for fn in sorted(os.listdir(OUT)) if fn.endswith(".results.json")}


def slice_recall(results, target):
    for col, rows in results.get("slices", {}).items():
        for r in rows:
            if str(r.get(col)) == target:
                return r.get("recall")
    return None


# --------------------------------------------------------------------------- #
# Sidebar
# --------------------------------------------------------------------------- #
st.sidebar.markdown("### The Robustness Review")
st.sidebar.caption("Adversarial evaluation desk")
st.sidebar.markdown("---")
model_choice = st.sidebar.selectbox(
    "Classifier under test",
    ["ToyClassifier (offline, instant)", "Detoxify (real model, slower)"],
    help="ToyClassifier is a brittle keyword baseline that runs instantly. "
         "Detoxify is a real production-grade RoBERTa model (needs `pip install "
         "detoxify`; first load downloads weights).",
)
threshold = st.sidebar.slider("Flagging threshold", 0.1, 0.9, 0.5, 0.05,
                              help="Score at or above this counts as 'flagged'.")
st.sidebar.markdown("---")
st.sidebar.caption("Public proxy data only. A methodology demonstrator, not an "
                   "egregious-harms detector.")

# --------------------------------------------------------------------------- #
# Masthead
# --------------------------------------------------------------------------- #
_today = datetime.date.today().strftime("%A, %B %-d, %Y") if os.name != "nt" \
    else datetime.date.today().strftime("%A, %B %d, %Y")
st.markdown(f"""
<div class="masthead">
  <div class="mh-top">
    <span>{_today}</span>
    <span>Trust &amp; Safety · Adversarial Robustness</span>
  </div>
  <div class="mh-title">The Robustness Review</div>
  <div class="mh-sub">Where a content-safety classifier breaks, before an adversary finds it</div>
</div>
""", unsafe_allow_html=True)

tab_front, tab_lab, tab_scan, tab_about = st.tabs(
    ["Front Page", "Attack Lab", "Scan Report", "Method & Ethics"])

_caches = available_caches()


# --------------------------------------------------------------------------- #
# Tab:FRONT PAGE
# --------------------------------------------------------------------------- #
with tab_front:
    # headline numbers, pulled live from the committed caches where possible
    civ = load_cache(_caches["civil_comments"])[0] if "civil_comments" in _caches else None
    hate = load_cache(_caches["hatecheck"])[0] if "hatecheck" in _caches else None
    f1_civ = civ["baseline"]["f1"] if civ else 0.70
    f1_hate = hate["baseline"]["f1"] if hate else 0.76
    impl = slice_recall(hate, "derog_impl_h") if hate else 0.53
    impl = impl if impl is not None else 0.53
    sem = next((r for r in (civ["adversarial"] if civ else []) if r["evasion"] == "llm_paraphrase"), None)
    sem_esr = sem["esr"] if sem else 0.57
    ece_civ = civ["baseline"].get("ece", 0.022) if civ else 0.022
    ece_hate = hate["baseline"].get("ece", 0.226) if hate else 0.226

    st.markdown('<div class="kicker">Lead Investigation · Detoxify (unbiased)</div>',
                unsafe_allow_html=True)
    st.markdown('<div class="lead-head">A Healthy F1 Score Hides Three Real Failures</div>',
                unsafe_allow_html=True)
    st.markdown('<div class="standfirst">A production toxicity classifier looks fine on '
                'the one number everyone reports. Read below the aggregate, by slice, '
                'under attack, and at its operating point, and the failures a Trust &amp; '
                'Safety team is paid to find appear at once.</div>', unsafe_allow_html=True)

    st.markdown(f"""
    <div class="statstrip">
      <div class="statcell"><div class="statnum">{f1_civ:.2f}/{f1_hate:.2f}</div>
        <div class="statlbl">Aggregate F1<br>(Civil Comments / HateCheck)</div></div>
      <div class="statcell"><div class="statnum red">{impl:.2f}</div>
        <div class="statlbl">Recall on implicit hate<br>~{round((1-impl)*100)}% of it missed</div></div>
      <div class="statcell"><div class="statnum red">{sem_esr:.2f}</div>
        <div class="statlbl">LLM-paraphrase evasion rate<br>defense cannot recover it</div></div>
      <div class="statcell"><div class="statnum">{ece_civ:.3f}→{ece_hate:.2f}</div>
        <div class="statlbl">Calibration error<br>does not transfer across data</div></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="cols3">
      <div class="finding">
        <div class="fh">The slice cliff</div>
        <p>Aggregate recall near 0.77 averages away the misses. The model catches
        <b>99%</b> of blunt threats and just <span class="big">{impl:.2f}</span>
        of <i>implicit</i> derogation, the coded hostility that matters most.</p>
      </div>
      <div class="finding">
        <div class="fh">Two kinds of evasion</div>
        <p>Character tricks (homoglyphs, leetspeak, invisible characters) hit ~100%
        evasion but a normalizer recovers them. An LLM paraphrase evades
        <span class="big">{sem_esr:.0%}</span> and a normalizer <b>cannot</b> touch it.</p>
      </div>
      <div class="finding">
        <div class="fh">Calibration drifts</div>
        <p>The same model is well-calibrated on one dataset (ECE {ece_civ:.3f}) and
        badly off on another (ECE {ece_hate:.2f}). A threshold tuned in one place
        <b>misfires</b> in the next.</p>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<hr class="nyt-thick">', unsafe_allow_html=True)
    st.markdown('<div class="ethics-band"><b>Scope &amp; ethics</b>'
                'Runs on public toxic-comment proxy data only. It never touches, and '
                'must not be pointed at, CSAM, NCII, or violent-extremism material, '
                'which belong in a sanctioned, legally-authorized pipeline. The '
                '<i>methods</i> transfer to that setting; the data deliberately does not.'
                '</div>', unsafe_allow_html=True)
    st.markdown("**Inside this issue:** open **Attack Lab** to break a classifier "
                "yourself, **Scan Report** for the full evidence, or **Method & Ethics** "
                "for how it is framed and why.")


# --------------------------------------------------------------------------- #
# Tab:ATTACK LAB
# --------------------------------------------------------------------------- #
with tab_lab:
    st.markdown('<div class="byline">The Lab · Live adversarial test</div>',
                unsafe_allow_html=True)
    st.markdown('<div class="lead-head" style="font-size:26px;">Break the filter '
                'yourself</div>', unsafe_allow_html=True)
    st.markdown('<div class="standfirst" style="font-size:15px;">Type a comment the '
                'filter should catch, then watch which cheap disguises slip it past, '
                'and which a normalization defense recovers.</div>', unsafe_allow_html=True)

    c1, c2 = st.columns([3, 1])
    seed_text = c1.text_input("Comment to test", value=EXAMPLES[0])
    pick = c2.selectbox("…or pick an example", ["(none)"] + EXAMPLES, index=0)
    if pick != "(none)":
        seed_text = pick

    model, warn = load_model(model_choice)
    if warn:
        st.warning(warn)
    base = float(model.predict_proba([seed_text])[0])
    flagged = base >= threshold

    if not flagged:
        st.markdown(f'<div class="verdict"><div><div class="vnum">{base:.2f}</div>'
                    '<div class="vlbl">Baseline score</div></div>'
                    '<div style="color:#555;font-size:14px;align-self:center;">'
                    'The filter does not flag this at baseline, so there is nothing to '
                    'evade. Try a clearly toxic example.</div></div>',
                    unsafe_allow_html=True)
    else:
        rows = []
        for name, meta in EVASIONS.items():
            atk = meta["fn"](seed_text)
            s_atk = float(model.predict_proba([atk])[0])
            s_def = float(model.predict_proba([normalize_pipeline(atk)])[0])
            shown = atk.replace(ZERO_WIDTH, "·")
            rows.append({
                "name": name, "effort": meta["effort"],
                "stealth": meta["fluency_penalty"],
                "shown": shown if len(shown) < 52 else shown[:50] + "…",
                "s_atk": s_atk, "evaded": s_atk < threshold,
                "s_def": s_def, "recovered": s_def >= threshold,
            })
        rows.sort(key=lambda r: r["s_atk"])
        n_evaded = sum(r["evaded"] for r in rows)

        st.markdown(f"""
        <div class="verdict">
          <div><div class="vnum">{base:.2f}</div><div class="vlbl">Baseline · flagged</div></div>
          <div><div class="vnum red" style="color:var(--red);">{n_evaded}/{len(rows)}</div>
               <div class="vlbl">Evasions that slip through</div></div>
        </div>""", unsafe_allow_html=True)

        trows = []
        for r in rows:
            cls = "row-evaded" if r["evaded"] else ""
            res = ('<span class="tag-evaded">slips through</span>' if r["evaded"]
                   else '<span class="tag-caught">caught</span>')
            rec = ('<span class="tag-rec">recovered</span>' if r["recovered"]
                   else '<span class="tag-no">no</span>')
            trows.append(
                f'<tr class="{cls}"><td><b>{html.escape(r["name"])}</b></td>'
                f'<td class="dim">{r["effort"]}</td><td class="dim">{r["stealth"]}</td>'
                f'<td class="mono dim">{html.escape(r["shown"])}</td>'
                f'<td class="mono">{r["s_atk"]:.2f}</td><td>{res}</td>'
                f'<td class="mono">{r["s_def"]:.2f}</td><td>{rec}</td></tr>')
        st.markdown(
            '<table class="nyt-table"><thead><tr><th>Evasion</th><th>Effort</th>'
            '<th>Stealth</th><th>Disguised text</th><th>Score</th><th>Result</th>'
            '<th>After defense</th><th>Recovered</th></tr></thead><tbody>'
            + "".join(trows) + "</tbody></table>", unsafe_allow_html=True)
        st.caption("`·` marks an injected invisible (zero-width) character. **Score** "
                   "is after the attack; **after defense** is after the normalization "
                   "preprocessor cleans the text first.")

        with st.expander("Add a semantic attack (LLM paraphrase)"):
            if "ANTHROPIC_API_KEY" not in os.environ:
                st.caption("Set `ANTHROPIC_API_KEY` to enable. The LLM rewrites the "
                           "comment into clean prose with the same intent, the attack "
                           "a normalization defense cannot reverse. Disabled on the "
                           "public demo by design.")
            elif st.button("Generate paraphrase attacks"):
                try:
                    from src.redteam import generate_variants, judge_preserved
                    with st.spinner("Asking the model for label-preserving rewrites…"):
                        prows = []
                        for v in generate_variants(seed_text, n=3):
                            if not isinstance(v, str) or not v.strip():
                                continue
                            keep = judge_preserved(seed_text, v)
                            sv = float(model.predict_proba([v])[0])
                            prows.append((v, keep, sv, sv < threshold and keep))
                    tr = "".join(
                        f'<tr><td>{html.escape(v)}</td>'
                        f'<td class="dim">{"yes" if keep else "drifted"}</td>'
                        f'<td class="mono">{sv:.2f}</td>'
                        f'<td>{"<span class=tag-evaded>slips through</span>" if ev else "<span class=tag-caught>caught</span>"}</td></tr>'
                        for (v, keep, sv, ev) in prows)
                    st.markdown('<table class="nyt-table"><thead><tr><th>Paraphrase</th>'
                                '<th>Intent kept</th><th>Score</th><th>Result</th></tr>'
                                '</thead><tbody>' + tr + "</tbody></table>",
                                unsafe_allow_html=True)
                    st.caption("Normalization is not applied here, there is no surface "
                               "disguise to strip. The fix is training-data augmentation.")
                except Exception as e:  # pragma: no cover
                    st.error(f"Red-team call failed: {e}")


# --------------------------------------------------------------------------- #
# Tab:SCAN REPORT
# --------------------------------------------------------------------------- #
with tab_scan:
    st.markdown('<div class="byline">The Report · Full weakness audit</div>',
                unsafe_allow_html=True)
    if not _caches:
        st.warning("No scan results found in `outputs/`. Generate one first:\n\n"
                   "`python scripts/run_eval.py --dataset civil_comments --redteam`")
    else:
        ds = st.selectbox("Dataset scan", list(_caches.keys()))
        results, meta = load_cache(_caches[ds])
        b = results["baseline"]
        st.markdown(f'<div class="lead-head" style="font-size:24px;">'
                    f'{html.escape(str(meta.get("model_name","classifier")))} '
                    f'on {html.escape(str(meta.get("dataset_name", ds)))}</div>',
                    unsafe_allow_html=True)
        st.caption(f"n={results['n']} · operating threshold {results['threshold']}")

        k = st.columns(5)
        k[0].metric("F1", f"{b['f1']:.2f}")
        k[1].metric("Precision", f"{b['precision']:.2f}")
        k[2].metric("Recall", f"{b['recall']:.2f}")
        k[3].metric("False-positive rate", f"{b['fpr']:.2f}")
        k[4].metric("Calibration (ECE)", f"{b.get('ece', float('nan')):.3f}")

        st.markdown('<hr class="nyt-thin">', unsafe_allow_html=True)
        st.markdown("#### Prioritized weaknesses")
        head = results["headline"]
        ws, cb = head.get("worst_slice"), head.get("cheapest_break")
        if ws:
            gap = b["recall"] - ws["recall"]
            st.markdown(f"- **Slice cliff**: `{ws['column']}={ws['value']}` recall "
                        f"**{ws['recall']:.2f}** vs {b['recall']:.2f} overall "
                        f"(gap {gap:.2f}, on {ws['support']} positives).")
        if cb:
            st.markdown(f"- **Cheap evasion**: `{cb['evasion']}` (effort {cb['effort']}) "
                        f"drops recall to **{cb['recall_after']:.2f}** (ESR {cb['esr']:.2f}); "
                        f"defense recovers it to {cb['recall_after_defense']:.2f}.")
        sem = next((r for r in results["adversarial"] if r["evasion"] == "llm_paraphrase"), None)
        if sem:
            st.markdown(f"- **Semantic evasion**: `llm_paraphrase` ESR **{sem['esr']:.2f}**; "
                        f"defense does *not* recover it ({sem['recall_after']:.2f} → "
                        f"{sem['recall_after_defense']:.2f}). Fix is training data, not preprocessing.")
        if b.get("ece", 0) > 0.1:
            st.markdown(f"- **Miscalibrated**: ECE {b['ece']:.2f}; scores can't be trusted "
                        f"to mean what they say on this distribution.")

        if results["slices"]:
            st.markdown('<hr class="nyt-thin">', unsafe_allow_html=True)
            st.markdown("#### Recall by slice")
            col = list(results["slices"].keys())[0]
            sl = sorted([r for r in results["slices"][col] if r.get("support", 0) >= 1],
                        key=lambda r: r["recall"])[:12]
            bars = "".join(
                f'<div class="bar-row"><span class="bar-lab">{html.escape(str(r[col]))}</span>'
                f'<span class="bar-track"><span class="bar-fill" style="width:{r["recall"]*100:.0f}%;'
                f'background:{"#b91c1c" if r["recall"]<0.6 else "#111"};"></span></span>'
                f'<span class="bar-val">{r["recall"]:.2f}</span></div>' for r in sl)
            st.markdown(f'<div class="bars">{bars}</div>', unsafe_allow_html=True)
            st.caption("Red bars: recall below 0.60, the failing slices the aggregate hides.")

        st.markdown('<hr class="nyt-thin">', unsafe_allow_html=True)
        st.markdown("#### Adversarial robustness")
        trows = ""
        for r in results["adversarial"]:
            ev_red = "color:var(--red);" if r["recall_after"] < 0.5 else ""
            rec_grn = "color:var(--green);font-weight:700;" if r["recall_after_defense"] >= 0.8 else "color:var(--red);font-weight:700;"
            sem_tag = ' <span class="tag-evaded">semantic</span>' if r["evasion"] == "llm_paraphrase" else ""
            trows += (f'<tr><td><b>{html.escape(r["evasion"])}</b>{sem_tag}</td>'
                      f'<td class="dim">{r["effort"]}</td><td class="dim">{r["fluency_penalty"]}</td>'
                      f'<td class="mono">{r["esr"]:.2f}</td>'
                      f'<td class="mono" style="{ev_red}">{r["recall_after"]:.2f}</td>'
                      f'<td class="mono" style="{rec_grn}">{r["recall_after_defense"]:.2f}</td></tr>')
        st.markdown('<table class="nyt-table"><thead><tr><th>Evasion</th><th>Effort</th>'
                    '<th>Stealth</th><th>ESR</th><th>Recall · attacked</th>'
                    '<th>Recall · defended</th></tr></thead><tbody>' + trows
                    + "</tbody></table>", unsafe_allow_html=True)

        try:
            import altair as alt
            sc = pd.DataFrame(results["adversarial"])
            sc["recovered"] = sc["recall_after_defense"] >= 0.8
            chart = (alt.Chart(sc).mark_circle(size=150, opacity=0.85).encode(
                x=alt.X("esr:Q", title="evasion success rate  (stronger →)",
                        scale=alt.Scale(domain=[0, 1])),
                y=alt.Y("recall_after_defense:Q", title="recall the defense recovers",
                        scale=alt.Scale(domain=[0, 1])),
                color=alt.Color("recovered:N",
                                scale=alt.Scale(domain=[True, False], range=["#111", "#b91c1c"]),
                                legend=alt.Legend(title="recovered by defense")),
                tooltip=["evasion", "esr", "recall_after", "recall_after_defense"],
            ).properties(height=320))
            rule = alt.Chart(pd.DataFrame({"y": [0.8]})).mark_rule(
                strokeDash=[4, 4], color="#999").encode(y="y:Q")
            st.altair_chart(chart + rule, width="stretch")
            st.caption("Bottom-right (red) = strong attacks the defense can't recover. "
                       "That is where `llm_paraphrase` lands, the real threat.")
        except Exception:
            pass


# --------------------------------------------------------------------------- #
# Tab:METHOD & ETHICS
# --------------------------------------------------------------------------- #
with tab_about:
    st.markdown('<div class="byline">Editor\'s Note · Method &amp; Ethics</div>',
                unsafe_allow_html=True)
    st.markdown("""
This is a **methodology demonstrator** for evaluating content-safety classifiers,
built to be read by a Trust & Safety reviewer in under a minute.

**The thesis.** A single aggregate accuracy score hides the failures a T&S team
is paid to find. The tool reads *below* the aggregate in three ways:

- **By slice:** where does recall collapse? (Implicit/coded hate, an
  under-protected group, a language the model never learned.)
- **Under attack:** which evasions break it, how cheap are they, and does a
  normalization preprocessor recover them? Mechanical character tricks are cheap
  but defendable; **LLM paraphrase attacks are not**, and those need training
  data, not filters.
- **At the operating point:** are the confidence scores calibrated, and does a
  threshold tuned on one distribution transfer to another?

**Why public proxy data.** Egregious-harms detection is an adversarial,
cat-and-mouse problem, which is exactly what this measures. But the worst content
can only be handled inside a sanctioned, legally-authorized pipeline. So the
engine is proven on ordinary public toxic-comment data and the **methods
transfer**, deliberately demonstrating judgment about what *not* to touch.

**Both error directions matter.** For an egregious flag, a false negative lets
harm through, but a false positive can mean a wrongful report against a real
person. The report surfaces precision, false-positive rate, and calibration
alongside recall for that reason.
""")
    st.markdown('<hr class="nyt-thin">', unsafe_allow_html=True)
    st.markdown("**Code & paper:** "
                "[github.com/Prakharanand000/TandS-harm-classifier-eval]"
                "(https://github.com/Prakharanand000/TandS-harm-classifier-eval)")
