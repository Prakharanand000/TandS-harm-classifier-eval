import { useState } from "react";
import LiveScanner   from "./tabs/LiveScanner.jsx";
import AttackLab     from "./tabs/AttackLab.jsx";
import SliceExplorer from "./tabs/SliceExplorer.jsx";
import Calibration   from "./tabs/Calibration.jsx";

const TABS = [
  ["scanner", "Live Scanner",   LiveScanner],
  ["attack",  "Attack Lab",     AttackLab],
  ["slices",  "Slice Explorer", SliceExplorer],
  ["calib",   "Calibration",    Calibration],
];

export default function App() {
  const [active, setActive] = useState("scanner");
  const Tab = TABS.find(t => t[0] === active)[2];

  return (
    <div className="wrap">
      <header className="hdr">
        <div className="hdr-logo">🛡️</div>
        <div>
          <div className="hdr-title">T&amp;S Analyst Workstation</div>
          <div className="hdr-sub">Harm Classifier Robustness Review</div>
        </div>
        <div className="hdr-right">
          <span className="model-tag">Detoxify · unbiased</span>
          <div className="status-pill">
            <div className="status-dot" />
            API live
          </div>
        </div>
      </header>

      <nav className="nav">
        {TABS.map(([id, label]) => (
          <div
            key={id}
            className={"nav-tab" + (active === id ? " active" : "")}
            onClick={() => setActive(id)}
          >
            {label}
          </div>
        ))}
      </nav>

      <Tab />

      <footer className="foot">
        <span>Harm Classifier Robustness Review · Detoxify (unbiased) · threshold 0.5</span>
        <span>
          <a href="https://github.com/Prakharanand000/TandS-harm-classifier-eval" target="_blank" rel="noreferrer">
            GitHub
          </a>
          {" · "}
          <a href="/api/health" target="_blank" rel="noreferrer">API health</a>
        </span>
      </footer>
    </div>
  );
}
