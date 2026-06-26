import { useEffect, useState } from "react";
import { get } from "../api.js";

function barColor(v) {
  if (v >= 0.75) return "#3fb950";
  if (v >= 0.6)  return "#d29922";
  return "#f85149";
}

function SliceRow({ row, expanded, onToggle }) {
  const pct = Math.round((row.recall ?? 0) * 100);
  return (
    <>
      <div className="slice-row" onClick={onToggle}>
        <div className="slice-cat" title={row.slice}>{row.slice}</div>
        <div className="slice-track">
          <div
            className="slice-bar"
            style={{width: `${pct}%`, background: barColor(row.recall ?? 0)}}
          />
        </div>
        <div className="slice-pct" style={{color: barColor(row.recall ?? 0)}}>
          {pct}%
        </div>
        <div style={{color:"var(--muted2)", fontSize:11, width:48, textAlign:"right", flexShrink:0}}>
          n={row.support}
        </div>
        <div style={{color:"var(--muted2)", fontSize:11, width:14, textAlign:"right", flexShrink:0}}>
          {expanded ? "▾" : "▸"}
        </div>
      </div>

      {expanded && row.missed_examples?.length > 0 && (
        <div style={{padding:"10px 14px 14px", background:"var(--panel)", borderBottom:"1px solid var(--border)"}}>
          <div className="missed-note">
            Examples the model missed (false negatives):
          </div>
          {row.missed_examples.map((ex, i) => (
            <div key={i} className="missed-ex">
              <span>"{ex}"</span>
            </div>
          ))}
        </div>
      )}
    </>
  );
}

export default function SliceExplorer() {
  const [data,     setData]     = useState(null);
  const [err,      setErr]      = useState(null);
  const [dataset,  setDataset]  = useState("hatecheck");
  const [expanded, setExpanded] = useState(null);

  useEffect(() => {
    setData(null);
    get("/api/slices")
      .then(d => setData(d))
      .catch(e => setErr(e.message));
  }, []);

  const ds = data?.[dataset];
  const rows = ds?.rows ?? [];
  const sorted = [...rows].sort((a, b) => (a.recall ?? 0) - (b.recall ?? 0));

  return (
    <div className="tab-body">
      <div className="sec-label">Slice Performance</div>

      <div className="row-flex">
        <select
          className="sel"
          style={{width:"auto"}}
          value={dataset}
          onChange={e => { setDataset(e.target.value); setExpanded(null); }}
        >
          <option value="hatecheck">HateCheck (18 slices)</option>
          <option value="civil_comments">Civil Comments</option>
        </select>
        {ds && (
          <div style={{fontSize:12, color:"var(--muted2)"}}>
            Overall recall:&ensp;
            <span style={{fontFamily:"var(--mono)", fontWeight:700, color: ds.overall_recall >= 0.7 ? "#3fb950" : "#f59e0b"}}>
              {(ds.overall_recall * 100).toFixed(1)}%
            </span>
          </div>
        )}
      </div>

      {err && <div style={{color:"#f85149", fontSize:12}}>{err}</div>}
      {!data && !err && <div className="spinner" />}

      {ds && (
        <div className="card" style={{padding:0, overflow:"hidden"}}>
          <div style={{padding:"10px 14px", borderBottom:"1px solid var(--border)", display:"flex", gap:10, alignItems:"center"}}>
            <div style={{fontSize:11, color:"var(--muted2)"}}>
              Sorted by recall (worst first). Click a row to see missed examples.
            </div>
            <div style={{marginLeft:"auto", display:"flex", gap:10}}>
              {[["#3fb950","≥75%"],["#d29922","60–74%"],["#f85149","<60%"]].map(([c,l]) => (
                <span key={l} style={{display:"flex", alignItems:"center", gap:5, fontSize:10, color:"var(--muted2)"}}>
                  <span style={{width:8,height:8,borderRadius:2,background:c,display:"inline-block"}} />
                  {l}
                </span>
              ))}
            </div>
          </div>
          {sorted.map((row, i) => (
            <SliceRow
              key={i}
              row={row}
              expanded={expanded === i}
              onToggle={() => setExpanded(expanded === i ? null : i)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
