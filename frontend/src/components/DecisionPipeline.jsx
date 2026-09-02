import React from "react";
import { useI18n } from "../i18n.jsx";

// Renders the ORION decision pipeline as a row of stages.
export default function DecisionPipeline({ stages, title }) {
  const { t } = useI18n();
  return (
    <div className="panel">
      <h2>{title}</h2>
      <div className="pipeline">
        {stages.map((s) => (
          <div key={s.name} className={`stage ${s.cls}`}>
            <div className="name">{t(s.name)}</div>
            <div className="st">{s.value}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
