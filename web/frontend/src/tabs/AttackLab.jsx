import { useEffect, useState, useRef } from "react";
import { get, post } from "../api.js";

function scoreColor(s) {
  if (s >= 0.7) return "#f85149";
  if (s >= 0.5) return "#f59e0b";
  return "#3fb950";
}

function Δ(base, after) {
  const d = after - base;
  const sign = d >= 0 ? "+" : "";
  const color = d < -0.05 ? "#3fb950" : d > 0.05 ? "#f85149" : "#8899bb";
  return <span style={{color, fontFamily:"var(--mono)", fontSize:11}}>{sign}{d.toFixed(3)}</span>;
}

function AtkRows({ rows }) {
  const [visible, setVisible] = useState([]);
  const idx = useRef(0);
  useEffect(() => {
    setVisible([]);
    idx.current = 0;
    const timer = setInterval(() => {
      if (idx.current >= rows.length) { clearInterval(timer); return; }
      setVisible(v => [...v, rows[idx.current]]);
      idx.current++;
    }, 110);
    return () => clearInterval(timer);
  }, [rows]);

  return (
    <table className="atk-table">
      <thead>
        <tr>
          <th>Attack</th>
          <th>Effort</th>
          <th>Score (attacked)</th>
          <th>Δ base</th>
          <th>Evaded?</th>
          <th>Score (defended)</th>
          <th>Recovered?</th>
        </tr>
      </thead>
      <tbody>
        {visible.map((r, i) => (
          <tr key={i}>
            <td className="atk-name">{r.evasion}</td>
            <td>{r.effort}</td>
            <td style={{color: scoreColor(r.score_attacked), fontWeight:700}}>{r.score_attacked?.toFixed(3)}</td>
            <td>{Δ(rows[0]?.score_attacked ?? r.score_attacked, r.score_attacked)}</td>
            <td>
              {r.evaded
                ? <span className="tag tag-ev">EVADED</span>
                : <span className="tag tag-ct">CAUGHT</span>}
            </td>
            <td style={{color: scoreColor(r.score_defended)}}>{r.score_defended?.toFixed(3)}</td>
            <td>
              {r.recovered != null
                ? r.recovered
                  ? <span className="tag tag-rec">RECOVERED</span>
                  : <span className="tag tag-ev">NOT REC.</span>
                : "—"}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function AttackLab() {
  const [bank, setBank]     = useState(null);
  const [sem,  setSem]      = useState([]);
  const [sel,  setSel]      = useState(0);
  const [text, setText]     = useState("");
  const [custom, setCustom] = useState(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr]       = useState(null);
  const [bankErr, setBankErr] = useState(null);

  useEffect(() => {
    get("/api/attack-bank")
      .then(d => { setBank(d.bank || []); setSem(d.semantic || []); })
      .catch(e => setBankErr(e.message));
  }, []);

  async function runCustom() {
    if (!text.trim()) return;
    setLoading(true); setErr(null); setCustom(null);
    try {
      const r = await post("/api/attack", { text });
      setCustom(r);
    } catch (e) {
      setErr(e.message);
    } finally {
      setLoading(false);
    }
  }

  const entry = bank?.[sel];

  return (
    <div className="tab-body">
      <div className="sec-label">Precomputed Attack Bank</div>

      {bankErr && (
        <div style={{color:"#f85149", fontSize:12}}>{bankErr}</div>
      )}

      {bank && (
        <>
          <div className="chips-row">
            {bank.map((b, i) => (
              <div
                key={i}
                className={"chip" + (sel === i ? " active" : "")}
                onClick={() => setSel(i)}
              >
                Seed {i + 1}
              </div>
            ))}
          </div>

          {entry && (
            <>
              <div className="verdict-box">
                <div className="verdict-num">{entry.score_base?.toFixed(3)}</div>
                <div className="verdict-txt">
                  <strong>Base score</strong> for seed {sel + 1}.&ensp;
                  "{entry.text?.slice(0, 90)}{entry.text?.length > 90 ? "…" : ""}"
                </div>
              </div>
              <div style={{overflowX:"auto"}}>
                <AtkRows rows={entry.attacks || []} />
              </div>
            </>
          )}
        </>
      )}

      {sem.length > 0 && (
        <>
          <div className="sec-label" style={{marginTop:8}}>Semantic Paraphrase Evasions (LLM)</div>
          <table className="atk-table">
            <thead>
              <tr>
                <th>Original</th>
                <th>Score before</th>
                <th>Paraphrase</th>
                <th>Score after</th>
                <th>Evaded?</th>
              </tr>
            </thead>
            <tbody>
              {sem.map((r, i) => (
                <tr key={i}>
                  <td className="atk-name">{r.original?.slice(0,60)}{r.original?.length > 60 ? "…" : ""}</td>
                  <td style={{color: scoreColor(r.score_before), fontWeight:700}}>{r.score_before?.toFixed(3)}</td>
                  <td className="atk-name">{r.variant?.slice(0,60)}{r.variant?.length > 60 ? "…" : ""}</td>
                  <td style={{color: scoreColor(r.score_after),  fontWeight:700}}>{r.score_after?.toFixed(3)}</td>
                  <td>
                    {r.evaded
                      ? <span className="tag tag-ev">EVADED</span>
                      : <span className="tag tag-ct">CAUGHT</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      <div className="sec-label" style={{marginTop:8}}>Run Custom Attack</div>
      <div className="row-flex">
        <input
          className="ain"
          placeholder="Type a comment to attack…"
          value={text}
          onChange={e => setText(e.target.value)}
          onKeyDown={e => { if (e.key === "Enter") runCustom(); }}
        />
        <div
          className="big-btn sm"
          onClick={runCustom}
          style={{opacity: loading ? .6 : 1}}
        >
          {loading ? "Running…" : "Attack"}
        </div>
      </div>

      {err && <div style={{color:"#f85149", fontSize:12}}>{err}</div>}

      {custom && (
        <>
          <div className="verdict-box">
            <div className="verdict-num">
              {custom.flagged
                ? <span style={{color:"#f85149"}}>FLAGGED</span>
                : <span style={{color:"#3fb950"}}>CLEAN</span>}
            </div>
            <div className="verdict-txt">{custom.note}</div>
          </div>
          <div style={{overflowX:"auto"}}>
            <AtkRows rows={custom.rows || []} />
          </div>
        </>
      )}
    </div>
  );
}
