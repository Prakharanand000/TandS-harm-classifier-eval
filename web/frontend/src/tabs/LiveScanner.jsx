import { useState } from "react";
import { post } from "../api.js";

const EXAMPLES = [
  "you are an idiot and everyone knows it",
  "have a wonderful afternoon, thanks for the help",
  "people like that are pathetic trash",
  "the meeting went really well today",
];

function color(score) {
  if (score >= 0.7) return "var(--red)";
  if (score >= 0.35) return "var(--amber)";
  return "var(--green)";
}

export default function LiveScanner() {
  const [text, setText] = useState(EXAMPLES[0]);
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false);

  async function run() {
    setBusy(true);
    try { setRes(await post("/api/score", { text })); }
    catch (e) { setRes({ error: String(e) }); }
    finally { setBusy(false); }
  }

  return (
    <div>
      <div className="byline">The Front Desk · Live scoring</div>
      <div className="lead sm">Score any comment</div>
      <div className="standfirst">
        A lightweight lexical model scores in real time, after a Bloom-filter tier-0
        pre-filter checks a denylist of known-bad terms. (The real Detoxify numbers
        are in the other tabs, precomputed.)
      </div>

      <label className="lbl">Comment</label>
      <textarea rows={3} value={text} onChange={(e) => setText(e.target.value)} />
      <div className="row" style={{ marginTop: 10 }}>
        <button className="go" onClick={run} disabled={busy}>
          {busy ? "Scoring…" : "Score it"}
        </button>
        {EXAMPLES.map((ex) => (
          <button key={ex} className="go" style={{ background: "#fff", color: "#111", border: "1px solid #ccc", fontWeight: 600 }}
            onClick={() => setText(ex)}>
            {ex.length > 28 ? ex.slice(0, 26) + "…" : ex}
          </button>
        ))}
      </div>

      {res && res.error && <div className="note red"><b>Error.</b> {res.error}</div>}
      {res && !res.error && (
        <>
          <div className="verdict">
            <div>
              <div className="vnum" style={{ color: color(res.score) }}>{res.score.toFixed(2)}</div>
              <div className="vlbl">Toxicity score</div>
            </div>
            <div className="gauge">
              <div style={{ width: `${res.score * 100}%`, background: color(res.score) }} />
            </div>
            <div>
              <span className={`pill ${res.decision}`}>{res.decision}</span>
              <div className="vlbl" style={{ marginTop: 8 }}>{res.model}</div>
            </div>
          </div>

          <div className="panel">
            <div className="byline" style={{ marginBottom: 8 }}>Tier-0 Bloom pre-filter</div>
            {res.prefilter.tier0_hit ? (
              <p style={{ marginBottom: 6 }}>
                <span className="t-evaded">Known-bad term(s) matched:</span>{" "}
                <span className="mono">{res.prefilter.matched.join(", ")}</span>
              </p>
            ) : (
              <p className="muted" style={{ marginBottom: 6 }}>No denylist hit — would fall through to the model.</p>
            )}
            <p className="muted" style={{ fontSize: 12, margin: 0 }}>
              {res.prefilter.bloom_bits.toLocaleString()} bits · {res.prefilter.bloom_hashes} hash functions ·
              cheap O(k) check before any model call.
            </p>
          </div>

          <div className="note">
            <b>Likely slice:</b> {res.slice_guess}
          </div>
        </>
      )}
    </div>
  );
}
