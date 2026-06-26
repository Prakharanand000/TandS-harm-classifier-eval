import { useEffect, useState } from "react";
import { get } from "../api.js";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, ReferenceLine, Tooltip, ResponsiveContainer,
} from "recharts";

function nearest(sweep, t) {
  return sweep.reduce((a, b) => (Math.abs(b.t - t) < Math.abs(a.t - t) ? b : a));
}

function Metric({ label, val, accent }) {
  return (
    <div style={{ textAlign: "center", flex: 1 }}>
      <div className="serif" style={{ fontSize: 26, fontWeight: 900, color: accent || "var(--ink)" }}>
        {(val * 100).toFixed(0)}%
      </div>
      <div className="vlbl">{label}</div>
    </div>
  );
}

function Reliability({ name, ece, rel, threshold }) {
  return (
    <div style={{ flex: 1, minWidth: 280 }}>
      <div className="byline" style={{ marginBottom: 6 }}>{name} · ECE {ece.toFixed(3)}</div>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={rel} margin={{ top: 8, right: 12, bottom: 4, left: -16 }}>
          <CartesianGrid stroke="#eee" />
          <XAxis type="number" dataKey="conf" domain={[0, 1]} tick={{ fontSize: 11 }} tickFormatter={(v) => v.toFixed(1)} />
          <YAxis domain={[0, 1]} tick={{ fontSize: 11 }} tickFormatter={(v) => v.toFixed(1)} />
          <Tooltip formatter={(v) => v.toFixed(2)} labelFormatter={(v) => `conf ${(+v).toFixed(2)}`} />
          <ReferenceLine segment={[{ x: 0, y: 0 }, { x: 1, y: 1 }]} stroke="#bbb" strokeDasharray="4 4" />
          <ReferenceLine x={threshold} stroke="#b91c1c" strokeDasharray="3 3" />
          <Line type="monotone" dataKey="acc" stroke="#111" strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
      <p className="muted" style={{ fontSize: 11, textAlign: "center" }}>
        predicted confidence (x) vs. actual toxic rate (y); dashed diagonal = perfect.
      </p>
    </div>
  );
}

export default function Calibration() {
  const [data, setData] = useState(null);
  const [t, setT] = useState(0.5);

  useEffect(() => { get("/api/calibration").then(setData).catch(() => setData({})); }, []);
  if (!data) return <div className="spinner" />;
  const names = Object.keys(data);
  if (names.length === 0) return <div className="note">No calibration data.</div>;

  return (
    <div>
      <div className="byline">The Ledger · Confidence you can (not) trust</div>
      <div className="lead sm">Calibration does not travel</div>
      <div className="standfirst">
        A score of 0.70 should mean a 70% chance of toxicity. Drag the operating
        threshold and watch precision, recall, and false-positive rate move on both
        datasets at once: a cutoff tuned on one misfires on the other.
      </div>

      <label className="lbl">Operating threshold: <span className="mono">{t.toFixed(2)}</span></label>
      <input type="range" min="0.05" max="0.95" step="0.01" value={t}
        onChange={(e) => setT(Number(e.target.value))} style={{ width: "100%", accentColor: "#111" }} />

      <div className="row" style={{ gap: 22, marginTop: 16 }}>
        {names.map((n) => {
          const p = nearest(data[n].sweep, t);
          return (
            <div key={n} className="panel" style={{ flex: 1, minWidth: 260 }}>
              <div className="byline" style={{ marginBottom: 10 }}>{n} · ECE {data[n].ece.toFixed(3)}</div>
              <div className="row" style={{ gap: 6 }}>
                <Metric label="Precision" val={p.precision} />
                <Metric label="Recall" val={p.recall} />
                <Metric label="FPR" val={p.fpr} accent="var(--red)" />
              </div>
            </div>
          );
        })}
      </div>

      <hr className="thin" />
      <h3 className="sec">Reliability curves</h3>
      <div className="row" style={{ gap: 22 }}>
        {names.map((n) => (
          <Reliability key={n} name={n} ece={data[n].ece} rel={data[n].reliability} threshold={t} />
        ))}
      </div>
      <div className="note">
        The same model is well-calibrated on one distribution and badly off on the other.
        That is why a threshold cannot be copied between datasets without re-checking.
      </div>
    </div>
  );
}
