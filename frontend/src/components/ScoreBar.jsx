import React from "react";

// A labelled 0-100 score bar.
export default function ScoreBar({ label, value, kind = "alpha", suffix = "" }) {
  const pct = Math.max(0, Math.min(100, Number(value) || 0));
  return (
    <div className="score">
      <div className="top">
        <span>{label}</span>
        <span className="val">
          {value == null ? "—" : Number(value).toFixed(0)}
          {suffix}
        </span>
      </div>
      <div className={`bar ${kind}`}>
        <span style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
