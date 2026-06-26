import { useEffect, useState } from "react";
import { get, post } from "../api.js";

function Matrix({ rows, model }) {
  const evaded = rows.filter((r) => r.evaded).length;
  return (
    <>
      <table className="nyt">
        <thead>
          <tr>
            <th>Evasion</th><th>Effort</th><th>Stealth</th><th>Disguised text</th>
            <th>Score</th><th>Result</th><th>After defense</th><th>Recovered</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.evasion} className={r.evaded ? "evaded" : ""}>
              <td><b>{r.evasion}</b></td>
              <td className="dim">{r.effort}</td>
              <td className="dim">{r.fluency_penalty}</td>
              <td className="m dim">{r.disguised}</td>
              <td className="m">{r.score_attacked.toFixed(2)}</td>
              <td>{r.evaded ? <span className="t-evaded">slips through</span> : <span className="t-caught">caught</span>}</td>
              <td className="m">{r.score_defended.toFixed(2)}</td>
              <td>{r.recovered ? <span className="t-rec">recovered</span> : <span className="muted">no</span>}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="muted" style={{ fontSize: 12 }}>
        {model} · {evaded}/{rows.length} evasions slip through · `·` marks an injected
        invisible character.
      </p>
    </>
  );
}

export default function AttackLab() {
  const [bank, setBank] = useState(null);
  const [idx, setIdx] = useState(0);
  const [custom, setCustom] = useState("");
  const [live, setLive] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => { get("/api/attack-bank").then(setBank).catch(() => setBank({ bank: [], semantic: [] })); }, []);

  async function runCustom() {
    if (!custom.trim()) return;
    setBusy(true);
    try { setLive(await post("/api/attack", { text: custom })); }
    catch (e) { setLive({ error: String(e) }); }
    finally { setBusy(false); }
  }

  if (!bank) return <div className="spinner" />;
  const ex = bank.bank[idx];

  return (
    <div>
      <div className="byline">The Lab · Adversarial attack matrix</div>
      <div className="lead sm">Watch evasions defeat the filter</div>
      <div className="standfirst">
        Every harmful comment can be disguised. See which cheap tricks slip past the
        model, and which a normalization defense recovers. The bank below runs on the
        real Detoxify model (precomputed); typing your own runs the live lexical model.
      </div>

      <h3 className="sec">Real Detoxify · pick an example</h3>
      <select value={idx} onChange={(e) => setIdx(Number(e.target.value))}>
        {bank.bank.map((b, i) => (
          <option key={i} value={i}>{b.text} (base {b.score_base.toFixed(2)})</option>
        ))}
      </select>
      {ex && (
        <div style={{ marginTop: 8 }}>
          <div className="verdict">
            <div><div className="vnum">{ex.score_base.toFixed(2)}</div><div className="vlbl">Baseline · flagged</div></div>
            <div><div className="vnum" style={{ color: "var(--red)" }}>
              {ex.attacks.filter((a) => a.evaded).length}/{ex.attacks.length}</div>
              <div className="vlbl">Evasions that slip through</div></div>
          </div>
          <Matrix rows={ex.attacks} model="Detoxify (unbiased), precomputed" />
        </div>
      )}

      {bank.semantic && bank.semantic.length > 0 && (
        <>
          <h3 className="sec">The semantic attack <span className="tag sem">undefended</span></h3>
          <p className="muted">
            A character disguise is reversible. A fluent paraphrase that keeps the meaning is not:
            normalization has nothing to strip. Same intent, clean words, real Detoxify scores.
          </p>
          <table className="nyt">
            <thead><tr><th>Original (flagged)</th><th>Score</th><th>Paraphrase</th><th>Score</th><th>Result</th></tr></thead>
            <tbody>
              {bank.semantic.map((s, i) => (
                <tr key={i} className={s.evaded ? "evaded" : ""}>
                  <td>{s.original}</td>
                  <td className="m">{s.score_before.toFixed(2)}</td>
                  <td><i>{s.variant}</i></td>
                  <td className="m">{s.score_after.toFixed(2)}</td>
                  <td>{s.evaded ? <span className="t-evaded">slips through</span> : <span className="t-caught">caught</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      <hr className="thick" />
      <h3 className="sec">Try your own (live lexical model)</h3>
      <textarea rows={2} placeholder="Type a toxic comment to attack…" value={custom}
        onChange={(e) => setCustom(e.target.value)} />
      <div style={{ marginTop: 10 }}>
        <button className="go" onClick={runCustom} disabled={busy}>
          {busy ? "Running…" : "Run attack matrix"}
        </button>
      </div>
      {live && live.error && <div className="note red"><b>Error.</b> {live.error}</div>}
      {live && !live.error && (
        live.flagged
          ? <div style={{ marginTop: 12 }}>
              <div className="note">{live.note}</div>
              <Matrix rows={live.rows} model={live.model} />
            </div>
          : <div className="note" style={{ marginTop: 12 }}>
              The lexical model does not flag this at baseline, so there is nothing to evade.
              Try a clearly toxic example.
            </div>
      )}
    </div>
  );
}
