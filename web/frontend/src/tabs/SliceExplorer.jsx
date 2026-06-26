import { useEffect, useState } from "react";
import { get } from "../api.js";

export default function SliceExplorer() {
  const [data, setData] = useState(null);
  const [ds, setDs] = useState("hatecheck");
  const [sel, setSel] = useState(null);

  useEffect(() => { get("/api/slices").then(setData).catch(() => setData({})); }, []);
  useEffect(() => { setSel(null); }, [ds]);

  if (!data) return <div className="spinner" />;
  const names = Object.keys(data);
  const d = data[ds] || data[names[0]];
  if (!d) return <div className="note">No slice data.</div>;
  const worst = d.rows[0];
  const selected = sel != null ? d.rows.find((r) => r.slice === sel) : null;

  return (
    <div>
      <div className="byline">The Beat · Where recall collapses</div>
      <div className="lead sm">The slice cliff</div>
      <div className="standfirst">
        Aggregate recall of {d.overall_recall.toFixed(2)} averages away the misses.
        Slice it, and the failures appear. Click a bar to read real comments the model
        missed in that slice.
      </div>

      <div className="row" style={{ marginBottom: 14 }}>
        {names.map((n) => (
          <button key={n} className="go" onClick={() => setDs(n)}
            style={n === ds ? {} : { background: "#fff", color: "#111", border: "1px solid #ccc", fontWeight: 600 }}>
            {n}
          </button>
        ))}
      </div>

      <div className="note red" style={{ marginBottom: 16 }}>
        <b>Worst slice.</b> <code>{d.column}={worst.slice}</code> recall{" "}
        <b>{worst.recall.toFixed(2)}</b> vs {d.overall_recall.toFixed(2)} overall —{" "}
        {Math.round((1 - worst.recall / Math.max(d.overall_recall, 1e-9)) * 100)}% below the aggregate,
        on {worst.support} positives.
      </div>

      {d.rows.map((r) => (
        <div key={r.slice} className={`bar-row ${sel === r.slice ? "sel" : ""}`}
          onClick={() => setSel(sel === r.slice ? null : r.slice)}>
          <span className="bar-lab">{r.slice}</span>
          <span className="bar-track">
            <span className="bar-fill" style={{ width: `${r.recall * 100}%`, background: r.recall < 0.6 ? "var(--red)" : "var(--ink)" }} />
          </span>
          <span className="bar-val">{r.recall.toFixed(2)}</span>
        </div>
      ))}
      <p className="muted" style={{ fontSize: 12, marginTop: 8 }}>
        Red bars: recall below 0.60. Click any slice to see missed examples.
      </p>

      {selected && (
        <div className="panel">
          <div className="byline" style={{ marginBottom: 8 }}>
            Missed in <code>{selected.slice}</code> · recall {selected.recall.toFixed(2)}
          </div>
          <p className="muted" style={{ fontSize: 11, marginBottom: 8 }}>
            Content note: these are public-benchmark test cases the model <b>failed to flag</b>.
            They may target protected groups — shown only to make the detection gap concrete.
          </p>
          {selected.missed_examples && selected.missed_examples.length > 0 ? (
            <ul style={{ margin: 0, paddingLeft: 18 }}>
              {selected.missed_examples.map((m, i) => (
                <li key={i} style={{ fontStyle: "italic", color: "#444", marginBottom: 6 }}>"{m}"</li>
              ))}
            </ul>
          ) : (
            <p className="muted" style={{ margin: 0 }}>No missed examples recorded for this slice.</p>
          )}
        </div>
      )}
    </div>
  );
}
