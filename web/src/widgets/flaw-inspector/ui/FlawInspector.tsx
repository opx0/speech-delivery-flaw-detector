import {
  ArrowUpRight,
  Headphones,
  Lightbulb,
  Play,
  Repeat2,
} from "lucide-react";
import type { FlawRegion } from "../../../contract";
import { FEATURES, KIND_LABELS, severityLabel } from "../../../entities/flaw";
import { formatTime } from "../../../shared/lib";

export interface FlawInspectorProps {
  region: FlawRegion | null;
  onPlayRegion: (region: FlawRegion) => void;
  onLoopRegion: (region: FlawRegion) => void;
}

export function FlawInspector({
  region,
  onPlayRegion,
  onLoopRegion,
}: FlawInspectorProps) {
  if (!region)
    return (
      <section className="panel evidence-panel empty-evidence">
        <Headphones size={28} />
        <h2>Every moment has context</h2>
        <p>
          Select a finding to see its measured evidence and hear the passage.
        </p>
      </section>
    );
  const deviation = region.deviation;
  const expected =
    deviation.expected.basis === "baseline"
      ? deviation.expected.value.toFixed(2)
      : `${deviation.expected.low.toFixed(2)}–${deviation.expected.high.toFixed(2)}`;
  return (
    <section className="panel evidence-panel">
      <div className="panel-heading">
        <span className="eyebrow">A closer look</span>
        <ArrowUpRight size={17} />
      </div>
      <div className="evidence-content">
        <div className="evidence-meta">
          <span className="pill amber-pill">
            {severityLabel(region.severity)}
          </span>
          <span>
            {formatTime(region.start)} – {formatTime(region.end)}
          </span>
        </div>
        <h2>{KIND_LABELS[region.kind]}</h2>
        <blockquote>“{region.explanation.quoted_text}”</blockquote>
        <div className="evidence-actions">
          <button
            className="button primary"
            onClick={() => onPlayRegion(region)}
          >
            <Play size={15} /> Play passage
          </button>
          <button
            className="button secondary"
            aria-label="Loop passage"
            onClick={() => onLoopRegion(region)}
          >
            <Repeat2 size={16} />
          </button>
        </div>
        <div className="evidence-label">
          Measured evidence <span>{FEATURES[deviation.feature].label}</span>
        </div>
        <div className="measurement-grid">
          <div>
            <span>Your recording</span>
            <strong>{deviation.observed.toFixed(2)}</strong>
            <small>{deviation.unit}</small>
          </div>
          <div>
            <span>
              {deviation.expected.basis === "baseline"
                ? "Gold reference"
                : "Expected range"}
            </span>
            <strong>{expected}</strong>
            <small>{deviation.unit}</small>
          </div>
        </div>
        <dl className="evidence-details">
          <div>
            <dt>Difference</dt>
            <dd>
              {deviation.delta >= 0 ? "+" : ""}
              {deviation.delta.toFixed(2)} {deviation.unit}
            </dd>
          </div>
          <div>
            <dt>Standardized deviation</dt>
            <dd>{deviation.z_score.toFixed(2)} σ</dd>
          </div>
          <div>
            <dt>Severity</dt>
            <dd>{Math.round(region.severity * 100)} / 100</dd>
          </div>
        </dl>
        <div className="explanation-box">
          <Lightbulb size={17} />
          <div>
            <h3>What this means</h3>
            <p>{region.explanation.headline}</p>
            <p>{region.explanation.detail}</p>
          </div>
        </div>
      </div>
    </section>
  );
}
