import { useState } from "react";
import { CheckCircle2, ChevronRight, ListFilter } from "lucide-react";
import type { Axis, FlawRegion } from "../../../contract";
import {
  AXES,
  AXIS_LABELS,
  KIND_LABELS,
  severityLabel,
} from "../../../entities/flaw";
import { formatTime } from "../../../shared/lib";

export interface FlawCardListProps {
  regions: FlawRegion[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export function FlawCardList({
  regions,
  selectedId,
  onSelect,
}: FlawCardListProps) {
  const [filter, setFilter] = useState<Axis | "all">("all");
  const filtered = [...regions]
    .sort((a, b) => a.start - b.start)
    .filter((region) => filter === "all" || region.axis === filter);
  return (
    <section className="panel findings-panel">
      <div className="panel-heading">
        <div className="panel-title">
          <h2>Delivery findings</h2>
          <span className="count-badge">{regions.length}</span>
        </div>
        <ListFilter size={16} />
      </div>
      <div className="findings-filter">
        <label htmlFor="finding-filter">Show</label>
        <select
          id="finding-filter"
          value={filter}
          onChange={(event) => {
            const value = event.target.value;
            setFilter(AXES.find((axis) => axis === value) ?? "all");
          }}
        >
          <option value="all">All delivery axes</option>
          {AXES.map((axis) => (
            <option key={axis} value={axis}>
              {AXIS_LABELS[axis]}
            </option>
          ))}
        </select>
      </div>
      <div className="findings-list">
        {filtered.map((region) => (
          <button
            key={region.id}
            className={`finding-card${region.id === selectedId ? " selected" : ""}`}
            aria-pressed={region.id === selectedId}
            onClick={() => onSelect(region.id)}
          >
            <div className="finding-meta">
              <span>
                {formatTime(region.start)} – {formatTime(region.end)}
              </span>
              <span
                className={`impact impact-${severityLabel(region.severity).toLowerCase().replaceAll(" ", "-")}`}
              >
                {severityLabel(region.severity)}
              </span>
            </div>
            <div className="finding-title">
              <strong>{KIND_LABELS[region.kind]}</strong>
              <ChevronRight size={15} />
            </div>
            <p>“{region.explanation.quoted_text}”</p>
            <span className="finding-axis">{AXIS_LABELS[region.axis]}</span>
          </button>
        ))}
        {!filtered.length && (
          <div className="empty-findings">
            <CheckCircle2 size={25} />
            <h3>
              {regions.length
                ? "No findings on this axis"
                : "No delivery deviations flagged"}
            </h3>
            <p>
              {regions.length
                ? "Try another delivery axis."
                : "This recording is within the comparison thresholds."}
            </p>
          </div>
        )}
      </div>
    </section>
  );
}
