import { useState } from "react";
import {
  Activity,
  AudioLines,
  RotateCcw,
  SlidersHorizontal,
  Timer,
  Volume2,
} from "lucide-react";
import type { Axis, AxisScore, RubricWeights } from "../../../contract";
import { AXES, AXIS_LABELS } from "../../../entities/flaw";
import { adjustWeights } from "../../../features/rubric-reweighting";

export interface ScoreBreakdownProps {
  axisScores: AxisScore[];
  weights: RubricWeights;
  overallScore: number;
  adjusted: boolean;
  onWeightsChange: (weights: RubricWeights) => void;
}

const ICONS = {
  cadence: Activity,
  tone: AudioLines,
  pauses: Timer,
  volume: Volume2,
};

const NOTES: Record<Axis, string> = {
  cadence: "Flow and speaking pace",
  tone: "Expressiveness in pitch",
  pauses: "Space between your words",
  volume: "Consistency of energy",
};

export function ScoreBreakdown({
  axisScores,
  weights,
  overallScore,
  adjusted,
  onWeightsChange,
}: ScoreBreakdownProps) {
  const [editing, setEditing] = useState(false);
  return (
    <section className="score-section" aria-label="Delivery scores">
      <div className="score-grid">
        <div className="overall-card">
          <span className="eyebrow">
            {adjusted ? "Adjusted score" : "Delivery score"}
          </span>
          <div>
            <strong data-testid="overall-score">
              {overallScore.toFixed(1)}
            </strong>
            <span>/ 100</span>
          </div>
          <small>
            {adjusted ? "Your custom rubric" : "Weighted across four axes"}
          </small>
        </div>
        {AXES.map((axis) => {
          const score =
            axisScores.find((item) => item.axis === axis)?.score ?? 0;
          const Icon = ICONS[axis];
          return (
            <div className="axis-card" key={axis}>
              <div className="axis-heading">
                <span>
                  <Icon size={16} />
                  {AXIS_LABELS[axis]}
                </span>
                <span className="weight-label">
                  {Math.round(weights[axis] * 100)}% weight
                </span>
              </div>
              <div className="axis-score">
                <strong>{score.toFixed(0)}</strong>
                <span>/ 100</span>
              </div>
              <div className="score-track">
                <span style={{ width: `${score}%` }} />
              </div>
              <small>{NOTES[axis]}</small>
            </div>
          );
        })}
      </div>
      <div className="rubric-summary">
        <span>Higher scores mean closer agreement with the reference.</span>
        <button
          className="text-button"
          aria-expanded={editing}
          onClick={() => setEditing((value) => !value)}
        >
          <SlidersHorizontal size={14} />
          {editing ? "Close rubric" : "Adjust rubric"}
        </button>
      </div>
      {editing && (
        <div className="rubric-editor">
          <div>
            <h3>What matters most to you?</h3>
            <p>
              Weights always total 100%. Acoustic measurements stay the same.
            </p>
          </div>
          <div className="rubric-sliders">
            {AXES.map((axis) => (
              <label key={axis}>
                <span>
                  {AXIS_LABELS[axis]}
                  <output>{Math.round(weights[axis] * 100)}%</output>
                </span>
                <input
                  aria-label={`${AXIS_LABELS[axis]} weight`}
                  type="range"
                  min="0"
                  max="1"
                  step="0.01"
                  value={weights[axis]}
                  onChange={(event) =>
                    onWeightsChange(
                      adjustWeights(weights, axis, Number(event.target.value)),
                    )
                  }
                />
              </label>
            ))}
          </div>
          <button
            className="text-button"
            onClick={() =>
              onWeightsChange({
                cadence: 0.25,
                tone: 0.25,
                pauses: 0.25,
                volume: 0.25,
              })
            }
          >
            <RotateCcw size={14} /> Equal weights
          </button>
        </div>
      )}
    </section>
  );
}
