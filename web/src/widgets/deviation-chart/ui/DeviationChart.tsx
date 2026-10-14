import { useEffect, useRef, useState } from "react";
import uPlot from "uplot";
import type { FeatureName, OverlaySeries } from "../../../contract";
import { FEATURES } from "../../../entities/flaw";
import { formatTime } from "../../../shared/lib";

export interface DeviationChartProps {
  overlaySeries: OverlaySeries[];
  currentTime: number;
  onSeek: (time: number) => void;
  inspectionOnly?: boolean;
}

export function DeviationChart({
  overlaySeries,
  currentTime,
  onSeek,
  inspectionOnly = false,
}: DeviationChartProps) {
  const [feature, setFeature] = useState<FeatureName>("speech_rate");
  const series =
    overlaySeries.find((item) => item.feature === feature) ?? overlaySeries[0];
  const root = useRef<HTMLDivElement>(null);
  const chart = useRef<uPlot | null>(null);
  const seek = useRef(onSeek);
  seek.current = onSeek;
  useEffect(() => {
    if (!root.current || !series) return;
    const styles = getComputedStyle(root.current);
    const accent = styles.getPropertyValue("--accent").trim();
    const reference = styles.getPropertyValue("--reference").trim();
    const expected = series.expected;
    const x = series.participant.map((_, i) => i * series.hop_s);
    const data: uPlot.AlignedData =
      expected.basis === "baseline"
        ? [x, series.participant, expected.values]
        : [x, series.participant, expected.high, expected.low];
    const plotSeries: uPlot.Series[] = [
      {},
      {
        label: "Your recording",
        stroke: accent,
        width: 2,
        points: { show: false },
      },
      {
        label:
          expected.basis === "baseline"
            ? "Gold reference"
            : "Expected upper range",
        stroke: reference,
        width: 1.5,
        dash: [5, 4],
        points: { show: false },
      },
    ];
    if (expected.basis === "band")
      plotSeries.push({
        label: "Expected lower range",
        stroke: reference,
        width: 1.5,
        dash: [5, 4],
        points: { show: false },
      });
    const plot = new uPlot(
      {
        width: Math.max(200, root.current.clientWidth),
        height: 300,
        scales: { x: { time: false } },
        series: plotSeries,
        legend: { show: false },
        cursor: { drag: { setScale: false } },
        bands:
          expected.basis === "band"
            ? [{ series: [2, 3], fill: "rgba(95,120,103,0.12)" }]
            : [],
        axes: [
          {
            stroke: "#76857e",
            grid: { show: false },
            ticks: { show: false },
            font: `14px ${styles.fontFamily}`,
            values: (_plot, values) => values.map((value) => formatTime(value)),
          },
          {
            stroke: "#76857e",
            grid: { stroke: "#edf0eb", width: 1 },
            ticks: { show: false },
            size: 55,
            font: `14px ${styles.fontFamily}`,
          },
        ],
      },
      data,
      root.current,
    );
    chart.current = plot;
    const click = (event: MouseEvent) => {
      const rect = plot.over.getBoundingClientRect();
      seek.current(Math.max(0, plot.posToVal(event.clientX - rect.left, "x")));
    };
    plot.over.addEventListener("click", click);
    const observer = new ResizeObserver(() => {
      if (root.current)
        plot.setSize({
          width: Math.max(200, root.current.clientWidth),
          height: 300,
        });
    });
    observer.observe(root.current);
    return () => {
      observer.disconnect();
      plot.over.removeEventListener("click", click);
      plot.destroy();
      chart.current = null;
    };
  }, [series]);
  useEffect(() => {
    const plot = chart.current;
    if (plot)
      plot.setCursor({
        left: plot.valToPos(currentTime, "x"),
        top: plot.valToPos(
          series?.participant[
            Math.round(currentTime / (series.hop_s || 0.05))
          ] ?? 0,
          "y",
        ),
      });
  }, [currentTime, series]);
  if (!series)
    return (
      <div className="empty-library">
        No feature curves are available for this report.
      </div>
    );
  const sample = Math.min(
    series.participant.length - 1,
    Math.round(currentTime / series.hop_s),
  );
  const observed = series.participant[sample];
  const expected =
    series.expected.basis === "baseline"
      ? series.expected.values[sample]?.toFixed(2)
      : `${series.expected.low[sample]?.toFixed(2) ?? "—"}–${series.expected.high[sample]?.toFixed(2) ?? "—"}`;
  return (
    <div className="feature-view">
      <div
        className="feature-tabs"
        role="tablist"
        aria-label="Acoustic feature"
      >
        {overlaySeries.map((item) => (
          <button
            key={item.feature}
            role="tab"
            aria-selected={item.feature === series.feature}
            className={item.feature === series.feature ? "active" : ""}
            onClick={() => setFeature(item.feature)}
          >
            {FEATURES[item.feature].label}
          </button>
        ))}
      </div>
      <div className="chart-heading">
        <div>
          <h3>{FEATURES[series.feature].label}</h3>
          <p>{FEATURES[series.feature].unit} · aligned to your recording</p>
        </div>
        <div className="chart-legend">
          <span>
            <i /> Your recording
          </span>
          <span>
            <i />{" "}
            {series.expected.basis === "baseline"
              ? "Gold reference"
              : "Expected range"}
          </span>
        </div>
      </div>
      <div
        ref={root}
        className="feature-chart"
        aria-label={`${FEATURES[series.feature].label} comparison chart`}
      />
      <div className="chart-readout">
        <span>At {formatTime(currentTime)}</span>
        <span>
          Your recording <strong>{observed?.toFixed(2) ?? "Unvoiced"}</strong>
        </span>
        <span>
          Reference <strong>{expected ?? "Unavailable"}</strong>
        </span>
      </div>
      <p className="chart-note">
        {inspectionOnly ? 'Click the curve to inspect measured values. Use the inspection slider for keyboard navigation.'
          : 'Click the curve to seek. Use the playback slider for keyboard navigation.'}
      </p>
    </div>
  );
}
