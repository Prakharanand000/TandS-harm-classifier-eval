import { useState } from "react";
import { post } from "../api.js";

const EXAMPLES = [
  "You are absolutely worthless and should disappear.",
  "I love how diverse this community is!",
  "Get out of our country you don't belong here.",
  "The meeting is scheduled for Tuesday at 3pm.",
];

function scoreColor(s) {
  if (s >= 0.7) return "#f85149";
  if (s >= 0.5) return "#f59e0b";
  if (s >= 0.3) return "#d29922";
  return "#3fb950";
}

function Verdict({ decision }) {
  if (!decision) return null;
  const map = {
    FLAGGED:    ["vp-flag",   "🚨 FLAGGED"],
    BORDERLINE: ["vp-border", "⚠️ BORDERLINE"],
    CLEAN:      ["vp-clean",  "✅ CLEAN"],
  };
  const [cls, label] = map[decision] || ["vp-clean", decision];
  return <div className={"verdict-pill " + cls}>{label}</div>;
}

export default function LiveScanner() {
  const [text, setText] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState(null);

  async function score(t) {
    const txt = t ?? text;
    if (!txt.trim()) return;
    setLoading(true); setErr(null); setResult(null);
    try {
      const r = await post("/api/score", { text: txt });
      setResult(r);
    } catch (e) {
      setErr(e.message);
    } finally {
      setLoading(false);
    }
  }

  const pf = result?.prefilter;
  const sc = result?.score ?? 0;

  return (
    <div className="two-pane">
      {/* ── left: input ── */}
      <div className="pane">
        <div className="sec-label">Input</div>

        <div>
          <div className="card-title" style={{marginBottom:6}}>Quick examples</div>
          <div className="chips-row">
            {EXAMPLES.map((ex, i) => (
              <div
                key={i}
                className="chip"
                onClick={() => { setText(ex); score(ex); }}
              >
                Example {i + 1}
              </div>
            ))}
          </div>
        </div>

        <div>
          <div className="card-title" style={{marginBottom:6}}>Or type your own</div>
          <textarea
            className="tin"
            value={text}
            onChange={e => setText(e.target.value)}
            placeholder="Paste or type a comment to score…"
            onKeyDown={e => { if (e.key === "Enter" && e.ctrlKey) score(); }}
          />
        </div>

        <div
          className="big-btn"
          onClick={() => score()}
          style={{ opacity: loading ? .6 : 1 }}
        >
          {loading ? "Scoring…" : "Score It"}
        </div>

        {err && (
          <div style={{color:"#f85149", fontSize:12, background:"rgba(248,81,73,.1)", border:"1px solid rgba(248,81,73,.3)", borderRadius:8, padding:"10px 14px"}}>
            {err}
          </div>
        )}

        {/* bloom info */}
        {pf && (
          <div className="card">
            <div className="card-title">Tier-0 Bloom Filter</div>
            <div style={{display:"grid", gridTemplateColumns:"1fr 1fr", gap:8}}>
              <div>
                <div className="cal-label">Hit</div>
                <div style={{fontFamily:"var(--mono)", fontSize:16, fontWeight:700, color: pf.tier0_hit ? "#f59e0b" : "#3fb950"}}>
                  {pf.tier0_hit ? "YES" : "NO"}
                </div>
              </div>
              <div>
                <div className="cal-label">Matched</div>
                <div style={{fontFamily:"var(--mono)", fontSize:16, fontWeight:700, color:"var(--text2)"}}>
                  {pf.matched ?? "—"}
                </div>
              </div>
              <div>
                <div className="cal-label">Bits</div>
                <div style={{fontFamily:"var(--mono)", fontSize:13, color:"var(--muted2)"}}>{pf.bloom_bits ?? "—"}</div>
              </div>
              <div>
                <div className="cal-label">Hash fns</div>
                <div style={{fontFamily:"var(--mono)", fontSize:13, color:"var(--muted2)"}}>{pf.bloom_hashes ?? "—"}</div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ── right: result ── */}
      <div className="pane">
        <div className="sec-label">Result</div>

        {loading && <div className="spinner" />}

        {result && (
          <>
            <div className="card">
              <div className="score-label">Toxicity Score</div>
              <div className="score-num">{sc.toFixed(3)}</div>
              <div className="score-track">
                <div className="score-fill" style={{width: `${sc * 100}%`, background: scoreColor(sc)}} />
              </div>
              <Verdict decision={result.decision} />
            </div>

            <div className="grid-2">
              <div className="card">
                <div className="card-title">Model</div>
                <div className="mono-tag" style={{display:"inline-block"}}>{result.model}</div>
              </div>
              <div className="card">
                <div className="card-title">Predicted Slice</div>
                <div style={{fontSize:13, color:"var(--text2)", fontWeight:600}}>{result.slice_guess ?? "—"}</div>
              </div>
            </div>

            <div className="card">
              <div className="card-title">Score breakdown</div>
              {[
                ["Toxicity",         sc],
                ["Severe Toxicity",  result.severe_toxicity ?? null],
                ["Obscene",          result.obscene ?? null],
                ["Threat",           result.threat ?? null],
                ["Insult",           result.insult ?? null],
                ["Identity Attack",  result.identity_attack ?? null],
              ].filter(([,v]) => v !== null).map(([lbl, v]) => (
                <div key={lbl} style={{display:"flex", alignItems:"center", gap:10, marginBottom:6}}>
                  <span style={{fontSize:11, color:"var(--muted2)", width:110, flexShrink:0}}>{lbl}</span>
                  <div className="score-track" style={{flex:1, marginTop:0}}>
                    <div className="score-fill" style={{width:`${v*100}%`, background: scoreColor(v)}} />
                  </div>
                  <span style={{fontSize:11, fontFamily:"var(--mono)", color:"var(--muted)", width:40, textAlign:"right"}}>{v.toFixed(3)}</span>
                </div>
              ))}
            </div>
          </>
        )}

        {!result && !loading && (
          <div style={{color:"var(--muted2)", fontSize:13, marginTop:20}}>
            Pick an example or type a comment and click <strong style={{color:"var(--amber)"}}>Score It</strong>.
          </div>
        )}
      </div>
    </div>
  );
}
