import { Check, LoaderCircle } from "lucide-react";
import type { Stage } from "../../../contract";

export interface StageProgressProps {
  currentStage: Stage;
  fraction: number;
  message: string;
}

const STAGES: { stage: Stage; label: string }[] = [
  { stage: "decode", label: "Decode" },
  { stage: "align", label: "Align words" },
  { stage: "extract", label: "Extract" },
  { stage: "compare", label: "Compare" },
  { stage: "explain", label: "Explain" },
];

export function StageProgress({
  currentStage,
  fraction,
  message,
}: StageProgressProps) {
  const index = STAGES.findIndex((item) => item.stage === currentStage);
  const value = Math.round(((index + fraction) / STAGES.length) * 100);
  return (
    <div className="stage-progress">
      <ol>
        {STAGES.map((item, i) => (
          <li
            key={item.stage}
            className={i < index ? "complete" : i === index ? "current" : ""}
          >
            <span>
              {i < index ? (
                <Check size={15} />
              ) : i === index ? (
                <LoaderCircle className="spin" size={16} />
              ) : (
                i + 1
              )}
            </span>
            <strong>{item.label}</strong>
          </li>
        ))}
      </ol>
      <progress value={value} max={100} aria-label="Analysis progress" />
      <p role="status">{message}</p>
    </div>
  );
}
