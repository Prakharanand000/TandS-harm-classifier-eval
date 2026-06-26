import { useEffect, useState } from "react";
import { get, post } from "../api.js";

function scoreColor(s) {
  if (s == null || isNaN(s)) return "#8899bb";
  if (s >= 0.7) return "#f85149";
  if (s >= 0.5) return "#f59e0b";
  return "#3fb950";
}

function DeltaCell({ base, after }) {
  if (base == null || after == null) return <span style={{color:"#8899bb"}}>—</span>;
  const d = after - base;
  const sign = d >= 0 ? "+" : "";
  const color = d < -0.05 ? "#3fb950" : d > 0.05 ? "#f85149" : "#8899bb";
  return (
    <span style={{color, fontFamily:"var(--mono)", fontSize:11}}>
      {sign}{d.toFixed(3)}
    </span>
  );
}

function AttackTable({ rows }) {
  if (!Array.isArray(rows) || rows.length === 0) return null;
  const base = rows[0]?.score_attacked;
  return (
    <table className="atk-table">
      <thead>
        <tr>
          <th>Attack</th>
          <th>Effort</th>
          <th>Score (attacked)</th>
          <th>Delta vs base</th>
          <th>Evaded?</th>
          <th>Score (defended)</th>
          <th>Recovered?</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i}>
            <td className="atk-name">{r.evasion ?? "—"}</td>
            <td>{r.effort ?? "—"}</td>
            <td style={{color: scoreColor(r.score_attacked), fontWeight:700}}>
              {r.score_attacked != null ? r.score_attacked.toFixed(3) : "—"}
            </td>
            <td><DeltaCell base={base} after={r.score_attacked} /></td>
            <td>
              {r.evaded === true
                ? <span className="tag tag-ev">EVADED</span>
                : r.evaded === false
                  ? <span className="tag tag-ct">CAUGHT</span>
                  : "—"}
            </td>
            <td style={{color: scoreColor(r.score_defended)}}>
              {r.score_defended != null ? r.score_defended.toFixed(3) : "—"}
            </td>
            <td>
              {r.recovered === true
                ? <span className="tag tag-rec">RECOVERED</span>
                : r.recovered === false
                  ? <span className="tag tag-ev">NOT REC.</span>
                  : "—"}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function AttackLab() {
  const [bank,    setBank]    = useState([]);
  const [sem,     setSem]     = useState([]);
  const [sel,     setSel]     = useState(0);
  const [text,    setText]    = useState("");
  const [custom,  setCustom]  = useState(null);
  const [loading, setLoading] = useState(false);
  const [err,     setErr]     = useState(null);
  const [bankErr, setBankErr] = useState(null);

  useEffect(() => {
    get("/api/attack-bank")
      .then(d => {
        setBank(Array.isArray(d.bank)     ? d.bank     : []);
        setSem( Array.isArray(d.semantic) ? d.semantic : []);
      })
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

  const entry = bank[sel] ?? null;

  return (
    <div className="tab-body">
      <div className="sec-label">Precomputed Attack Bank</div>

      {bankErr && (
        <div style={{color:"#f85149", fontSize:12, background:"rgba(248,81,73,.1)", border:"1px solid rgba(248,81,73,.3)", borderRadius:8, padding:"10px 14px"}}>
          {bankErr}
        </div>
      )}

      {bank.length === 0 && !bankErr && (
        <div className="spinner" />
      )}

      {bank.length > 0 && (
        <>
          <div className="chips-row">
            {bank.map((_, i) => (
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
                <div className="verdict-num">
                  {entry.score_base != null ? entry.score_base.toFixed(3) : "—"}
                </div>
                <div className="verdict-txt">
                  <strong>Base score</strong> for seed {sel + 1}.{" "}
                  {entry.text
                    ? `"${entry.text.slice(0, 90)}${entry.text.length > 90 ? "…" : ""}"`
                    : ""}
                </div>
              </div>
              <div style={{overflowX:"auto"}}>
                <AttackTable rows={entry.attacks} />
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
                  <td className="atk-name">
                    {r.original ? `${r.original.slice(0,60)}${r.original.length > 60 ? "…" : ""}` : "—"}
                  </td>
                  <td style={{color: scoreColor(r.score_before), fontWeight:700}}>
                    {r.score_before != null ? r.score_before.toFixed(3) : "—"}
                  </td>
                  <td className="atk-name">
                    {r.variant ? `${r.variant.slice(0,60)}${r.variant.length > 60 ? "…" : ""}` : "—"}
                  </td>
                  <td style={{color: scoreColor(r.score_after), fontWeight:700}}>
                    {r.score_after != null ? r.score_after.toFixed(3) : "—"}
                  </td>
                  <td>
                    {r.evaded === true
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

      {err && (
        <div style={{color:"#f85149", fontSize:12, background:"rgba(248,81,73,.1)", border:"1px solid rgba(248,81,73,.3)", borderRadius:8, padding:"10px 14px"}}>
          {err}
        </div>
      )}

      {custom && (
        <>
          <div className="verdict-box">
            <div className="verdict-num" style={{color: custom.flagged ? "#f85149" : "#3fb950"}}>
              {custom.flagged ? "FLAGGED" : "CLEAN"}
            </div>
            <div className="verdict-txt">{custom.note}</div>
          </div>
          <div style={{overflowX:"auto"}}>
            <AttackTable rows={custom.rows} />
          </div>
        </>
      )}
    </div>
  );
}
