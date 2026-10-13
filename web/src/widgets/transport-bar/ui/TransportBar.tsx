import {
  Pause,
  Play,
  Repeat2,
  RotateCcw,
  RotateCw,
  Volume2,
  VolumeX,
} from "lucide-react";
import type { usePlayback } from "../../../features/playback";
import { formatTime } from "../../../shared/lib";

export interface TransportBarProps {
  playback: ReturnType<typeof usePlayback>;
}

export function TransportBar({ playback }: TransportBarProps) {
  return (
    <div className="transport">
      <div className="transport-main">
        <button
          className="icon-button"
          aria-label="Back five seconds"
          onClick={() => playback.seek(playback.currentTime - 5)}
        >
          <RotateCcw size={17} />
          <small>5</small>
        </button>
        <button
          className="play-button"
          aria-label={playback.isPlaying ? "Pause audio" : "Play audio"}
          onClick={playback.togglePlay}
        >
          {playback.isPlaying ? (
            <Pause size={20} fill="currentColor" />
          ) : (
            <Play size={20} fill="currentColor" />
          )}
        </button>
        <button
          className="icon-button"
          aria-label="Forward five seconds"
          onClick={() => playback.seek(playback.currentTime + 5)}
        >
          <RotateCw size={17} />
          <small>5</small>
        </button>
        <span className="time-display">
          {formatTime(playback.currentTime)}{" "}
          <span>/ {formatTime(playback.duration)}</span>
        </span>
      </div>
      <input
        className="seek-slider"
        aria-label="Playback position"
        type="range"
        min="0"
        max={playback.duration}
        step="0.05"
        value={playback.currentTime}
        onChange={(event) => playback.seek(Number(event.target.value))}
      />
      <div className="transport-options">
        <button
          className={`icon-button${playback.isLooping ? " enabled" : ""}`}
          aria-label="Loop audio"
          aria-pressed={playback.isLooping}
          onClick={() => (playback.isLooping ? playback.stopRegionLoop() : null)}
        >
          <Repeat2 size={17} />
        </button>
        <select
          aria-label="Playback speed"
          value={playback.playbackRate}
          onChange={(event) => playback.setRate(Number(event.target.value))}
        >
          {[0.75, 1, 1.25, 1.5, 2].map((rate) => (
            <option key={rate} value={rate}>
              {rate}×
            </option>
          ))}
        </select>
        <button
          className="icon-button"
          aria-label={playback.isMuted ? "Unmute audio" : "Mute audio"}
          onClick={playback.toggleMute}
        >
          {playback.isMuted ? <VolumeX size={17} /> : <Volume2 size={17} />}
        </button>
        <input
          aria-label="Audio volume"
          className="volume-slider"
          type="range"
          min="0"
          max="1"
          step="0.01"
          value={playback.isMuted ? 0 : playback.volume}
          onChange={(event) => playback.setVolume(Number(event.target.value))}
        />
      </div>
    </div>
  );
}
