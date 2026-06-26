import { useState } from "react";
import LiveScanner from "./tabs/LiveScanner.jsx";
import AttackLab from "./tabs/AttackLab.jsx";
import SliceExplorer from "./tabs/SliceExplorer.jsx";
import Calibration from "./tabs/Calibration.jsx";

const TABS = [
  ["scanner", "Live Scanner", LiveScanner],
  ["attack", "Attack Lab", AttackLab],
  ["slices", "Slice Explorer", SliceExplorer],
  ["calib", "Calibration", Calibration],
];

export default function App() {
  const [tab, setTab] = useState("scanner");
  const today = new Date().toLocaleDateString("en-US", {
    weekday: "long", month: "long", day: "numeric", year: "numeric",
  });
  const Active = TABS.find((t) => t[0] === tab)[2];

  return (
    <div className="wrap">
      <div className="masthead">
        <div className="mh-top">
          <span>{today}</span>
          <span>Trust &amp; Safety · Adversarial Robustness</span>
        </div>
        <div className="mh-title">The Robustness Review</div>
        <div className="mh-sub">
          Where a content-safety classifier breaks, before an adversary finds it
        </div>
      </div>

      <nav className="nav">
        {TABS.map(([id, label]) => (
          <button key={id} className={tab === id ? "active" : ""} onClick={() => setTab(id)}>
            {label}
          </button>
        ))}
      </nav>

      <Active />

      <div className="foot">
        <span>Public proxy data only · a methodology demonstrator, not an egregious-harms detector</span>
        <a href="https://github.com/Prakharanand000/TandS-harm-classifier-eval" target="_blank" rel="noreferrer">
          github.com/Prakharanand000/TandS-harm-classifier-eval
        </a>
      </div>
    </div>
  );
}
