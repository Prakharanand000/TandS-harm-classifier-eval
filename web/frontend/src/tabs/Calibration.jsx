import { useEffect, useState } from "react";
import { get } from "../api.js";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  ReferenceLine, Tooltip, ResponsiveContainer, Legend,
} from "recharts";

const DATASETS = ["civil_comments", "hatecheck"];

function eceColor(v) {
  if (v <= 0.05) return "good";
  if (v <= 0.12) return "warn";
  return "bad";
}

function MetricGrid({ label, sweep, threshold }) {
  if (!sweep?.length) return null;
  const row = sweep.reduce((best, r) => Math.abs(r.t - threshold) < Math.abs(best.t - threshold) ? r : best, sweep[0]);
  return (
    <div className="grid-3">
      {[
        ["Precision", row.precision?.toFixed(3), null],
        ["Recall",    row.recall?.toFixed(3),    null],
        ["FPR",       row.fpr?.toFixed(3),        "warn"],
      ].map(([lbl, val]) => (
        <div key={lbl} className="card">
          <div className="cal-label">{lbl}</div>
          <div className="cal-val" style={{color:"var(--text2)", fontSize:18}}>{val ?? "—"}</div>
        </div>
      ))}
    </div>
  );
}

const tooltipStyle = {
  background:"#222b42", border:"1px solid #3a4f7a",
  borderRadius:6, color:"#eef2ff", fontSize:11,
};

export default function Calibration() {
  const [data, setData] = useState(null);
  const [err,  setErr]  = useState(null);
  const [threshold, setThreshold] = useState(0.5);
  const [ds, setDs] = useState("civil_comments");

  useEffect(() => {
    get("/api/calibration")
      .then(d => setData(d))
      .catch(e => setErr(e.message));
  }, []);

  const cur = data?.[ds];

  return (
    <div className="tab-body">
      <div className="sec-label">Calibration Dashboard</div>

      {err && <div style={{color:"#f85149", fontSize:12}}>{err}</div>}
      {!data && !err && <div className="spinner" />}

      {data && (
        <>
          <div className="row-flex">
            <div className="chips-row">
              {DATASETS.map(d => (
                <div
                  key={d}
                  className={"chip" + (ds === d ? " active" : "")}
                  onClick={() => setDs(d)}
                >
                  {d === "civil_comments" ? "Civil Comments" : "HateCheck"}
                </div>
              ))}
            </div>
          </div>

          {/* ECE summary row */}
          <div className="grid-2">
            {DATASETS.map(d => {
              const ece = data?.[d]?.ece;
              return (
                <div key={d} className="card">
                  <div className="cal-label">ECE · {d === "civil_comments" ? "Civil Comments" : "HateCheck"}</div>
                  <div className={"cal-val " + eceColor(ece ?? 1)}>{ece?.toFixed(3) ?? "—"}</div>
                </div>
              );
            })}
          </div>

          {cur && (
            <>
              <div className="card">
                <div className="card-title">Reliability Curve — {ds === "civil_comments" ? "Civil Comments" : "HateCheck"}</div>
                <ResponsiveContainer width="100%" height={220}>
                  <LineChart data={cur.reliability ?? []}>
                    <CartesianGrid stroke="#2a3550" strokeDasharray="3 3" />
                    <XAxis dataKey="conf" tick={{fill:"#8899bb", fontSize:10}} label={{value:"Mean predicted prob", position:"insideBottom", offset:-2, fill:"#7d8fbb", fontSize:10}} />
                    <YAxis tick={{fill:"#8899bb", fontSize:10}} label={{value:"Fraction positive", angle:-90, position:"insideLeft", fill:"#7d8fbb", fontSize:10}} />
                    <Tooltip contentStyle={tooltipStyle} />
                    <ReferenceLine stroke="#4a6090" strokeDasharray="4 4" segment={[{x:0,y:0},{x:1,y:1}]} />
                    <Line type="monotone" dataKey="acc" stroke="#f59e0b" strokeWidth={2} dot={{r:3, fill:"#f59e0b"}} name="Calibration" />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              <div className="card">
                <div className="card-title">Precision / Recall / FPR vs Threshold</div>
                <ResponsiveContainer width="100%" height={220}>
                  <LineChart data={cur.sweep ?? []}>
                    <CartesianGrid stroke="#2a3550" strokeDasharray="3 3" />
                    <XAxis dataKey="t" tick={{fill:"#8899bb", fontSize:10}} label={{value:"Threshold", position:"insideBottom", offset:-2, fill:"#7d8fbb", fontSize:10}} />
                    <YAxis tick={{fill:"#8899bb", fontSize:10}} domain={[0,1]} />
                    <Tooltip contentStyle={tooltipStyle} />
                    <Legend wrapperStyle={{fontSize:11, color:"#8899bb"}} />
                    <ReferenceLine x={threshold} stroke="#f59e0b" strokeWidth={1.5} strokeDasharray="4 3" label={{value:`t=${threshold}`, fill:"#f59e0b", fontSize:10}} />
                    <Line type="monotone" dataKey="precision" stroke="#3fb950" strokeWidth={2} dot={false} name="Precision" />
                    <Line type="monotone" dataKey="recall"    stroke="#58a6ff" strokeWidth={2} dot={false} name="Recall" />
                    <Line type="monotone" dataKey="fpr"       stroke="#f85149" strokeWidth={2} dot={false} name="FPR" />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              <div>
                <div className="card-title" style={{marginBottom:6}}>Threshold slider</div>
                <div className="row-flex">
                  <input
                    type="range" min={0} max={1} step={0.01}
                    value={threshold}
                    onChange={e => setThreshold(+e.target.value)}
                    style={{flex:1}}
                  />
                  <span style={{fontFamily:"var(--mono)", fontSize:14, fontWeight:700, color:"var(--amber)", minWidth:38, textAlign:"right"}}>
                    {threshold.toFixed(2)}
                  </span>
                </div>
              </div>

              <MetricGrid label={ds} sweep={cur.sweep} threshold={threshold} />
            </>
          )}
        </>
      )}
    </div>
  );
}
