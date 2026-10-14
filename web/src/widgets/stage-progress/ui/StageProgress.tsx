import { Check, LoaderCircle } from "lucide-react";
import { useEffect, useRef, useState } from 'react';
import type { Stage } from "../../../contract";
import { formatTime } from '../../../shared/lib';

export interface StageProgressProps {
  currentStage: Stage;
  fraction: number;
  message: string;
  startedAt: number;
  logs: { at: number; message: string }[];
  preparing: boolean;
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
  startedAt,
  logs,
  preparing,
}: StageProgressProps) {
  const [now, setNow] = useState(Date.now());
  const activityList = useRef<HTMLOListElement>(null);
  const followActivity = useRef(true);
  useEffect(() => {
    if (followActivity.current && activityList.current) {
      activityList.current.scrollTop = activityList.current.scrollHeight;
    }
  }, [logs]);
  useEffect(() => {
    setNow(Date.now());
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [startedAt]);
  const index = STAGES.findIndex((item) => item.stage === currentStage);
  const value = Math.round(((index + fraction) / STAGES.length) * 100);
  return (
    <div className="stage-progress">
      <ol>
        {STAGES.map((item, i) => (
          <li
            key={item.stage}
            className={preparing ? '' : i < index ? "complete" : i === index ? "current" : ""}
          >
            <span>
              {!preparing && i < index ? (
                <Check size={15} />
              ) : !preparing && i === index ? (
                <LoaderCircle className="spin" size={16} />
              ) : (
                i + 1
              )}
            </span>
            <strong>{item.label}</strong>
          </li>
        ))}
      </ol>
      <progress value={preparing ? undefined : value} max={100} aria-label="Analysis progress" />
      <p role="status">{message}</p>
      <div className="analysis-timing">
        <span><i className="activity-dot" /> {preparing ? 'Preparing analysis' : 'Processing locally'}</span>
        <span>Elapsed <output aria-label="Analysis elapsed time" aria-live="off">{formatTime(Math.max(0, now - startedAt) / 1000)}</output></span>
      </div>
      <p className="progress-hint">Stage progress is not a time estimate. The first run may load the alignment model; longer recordings take more time.</p>
      {now - (logs[logs.length - 1]?.at ?? startedAt) > 15000 && <p className="progress-hint">Waiting for the next worker update. You do not need to resubmit while this request is active.</p>}
      <details className="analysis-activity" open>
        <summary>Analysis activity · {logs.length} updates</summary>
        <ol ref={activityList} aria-label="Analysis activity log" onScroll={() => {
          const list = activityList.current;
          if (list) followActivity.current = list.scrollHeight - list.scrollTop - list.clientHeight < 30;
        }}>
          {logs.map((entry, i) => <li key={`${entry.at}-${i}`}>
            <time>{formatTime(Math.max(0, entry.at - startedAt) / 1000)}</time>
            <span>{entry.message}</span>
          </li>)}
        </ol>
      </details>
    </div>
  );
}
