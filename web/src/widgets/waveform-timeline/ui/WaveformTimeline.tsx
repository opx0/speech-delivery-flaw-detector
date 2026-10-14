import { useEffect, useRef, useState } from "react";
import WaveSurfer from "wavesurfer.js";
import type { FlawRegion } from "../../../contract";
import { formatTime } from "../../../shared/lib";
import { KIND_LABELS } from "../../../entities/flaw";

export interface WaveformTimelineProps {
  audioUrl: string;
  duration: number;
  currentTime: number;
  regions: FlawRegion[];
  selectedId: string | null;
  onSeek: (time: number) => void;
  onSelectRegion: (id: string) => void;
}

export function WaveformTimeline({
  audioUrl,
  duration,
  currentTime,
  regions,
  selectedId,
  onSeek,
  onSelectRegion,
}: WaveformTimelineProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    if (!ref.current) return;
    const controller = new AbortController();
    setError(false);
    setLoading(true);
    const color = getComputedStyle(ref.current).getPropertyValue("--accent").trim();
    const wave = WaveSurfer.create({
      container: ref.current,
      height: 74,
       waveColor: color,
       progressColor: color,
      barWidth: 2,
      barGap: 2,
      barRadius: 2,
      cursorWidth: 0,
      interact: false,
      normalize: true,
      fetchParams: { signal: controller.signal },
    });
    wave
      .load(audioUrl)
      .then(() => {
        if (!controller.signal.aborted) setLoading(false);
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setError(true);
          setLoading(false);
        }
      });
    return () => {
      controller.abort();
      wave.destroy();
    };
  }, [audioUrl]);
  return (
    <div className="waveform-timeline">
      <div className="waveform-label">
        <span>
          <span className="tiny-dot teal-dot" /> Recording waveform
        </span>
        <span>
          {regions.length} marked{" "}
          {regions.length === 1 ? "passage" : "passages"}
        </span>
      </div>
      <div
        className="waveform-area"
        onClick={(event) => {
          const rect = event.currentTarget.getBoundingClientRect();
          onSeek(((event.clientX - rect.left) / rect.width) * duration);
        }}
      >
        <div ref={ref} className="waveform-canvas" />
        {loading && <span className="waveform-status">Loading waveform…</span>}
        {error && (
          <span className="waveform-status">
            Waveform unavailable. Playback controls remain available.
          </span>
        )}
        <div className="waveform-regions">
          {regions.map((region) => (
            <button
              key={region.id}
              className={`waveform-region${selectedId === region.id ? " selected" : ""}`}
              style={{
                left: `${(region.start / duration) * 100}%`,
                width: `${Math.max(0.7, ((region.end - region.start) / duration) * 100)}%`,
              }}
              aria-label={`${KIND_LABELS[region.kind]} at ${formatTime(region.start)}`}
              title={`${KIND_LABELS[region.kind]} · ${formatTime(region.start)}`}
              onClick={(event) => {
                event.stopPropagation();
                onSelectRegion(region.id);
              }}
            >
              <span />
            </button>
          ))}
        </div>
        <div
          className="waveform-playhead"
          style={{ left: `${duration ? (currentTime / duration) * 100 : 0}%` }}
        />
      </div>
      <div className="waveform-ruler">
        {[0, 0.25, 0.5, 0.75, 1].map((part) => (
          <span key={part}>{formatTime(duration * part)}</span>
        ))}
      </div>
    </div>
  );
}
