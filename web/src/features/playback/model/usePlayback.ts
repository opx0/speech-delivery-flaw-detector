import { useEffect, useRef, useState } from 'react';
import type { FlawRegion, Report } from '../../../contract';
import type { RecordingSource } from '../../analysis-session/model/useAnalysis';
import { mapBaselineTime, mapTimeWarp } from '../lib/warp';

export function usePlayback(recording: RecordingSource | null, report: Report | null) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [source, setSource] = useState<'participant' | 'baseline'>('participant');
  const [isPlaying, setPlaying] = useState(false);
  const [currentTime, setTime] = useState(0);
  const [playbackRate, setRate] = useState(1);
  const [volume, setVolume] = useState(0.85);
  const [isMuted, setMuted] = useState(false);
  const [isLooping, setLooping] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const interval = useRef<{ start: number; end: number; loop: boolean } | null>(null);
  const pending = useRef<{ time: number; resume: boolean } | null>(null);
  const config = useRef({ source, report, currentTime });
  config.current = { source, report, currentTime };
  const duration = report?.participant.duration_s ?? 0;

  function toMedia(time: number): number {
    const { report: current, source: selected } = config.current;
    return selected === 'baseline' && current?.reference.basis === 'baseline'
      ? mapTimeWarp(time, current.reference.warp)
      : time;
  }

  async function play() {
    try {
      await audioRef.current?.play();
      setError(null);
    } catch {
      setError('Audio playback could not start. Try pressing Play again.');
    }
  }

  function seek(time: number) {
    const value = Math.min(duration, Math.max(0, time));
    const audio = audioRef.current;
    if (audio) {
      const mediaTime = toMedia(value);
      audio.currentTime = Number.isFinite(audio.duration)
        ? Math.min(mediaTime, audio.duration)
        : mediaTime;
    }
    setTime(value);
  }

  useEffect(() => {
    const audio = new Audio();
    audio.preload = 'metadata';
    audioRef.current = audio;

    const update = () => {
      const { report: current, source: selected, currentTime: previous } = config.current;
      let value =
        selected === 'baseline' && current?.reference.basis === 'baseline'
          ? mapBaselineTime(audio.currentTime, current.reference.warp, previous)
          : audio.currentTime;
      value = Math.max(0, Math.min(current?.participant.duration_s ?? value, value));
      const region = interval.current;
      if (region && value >= region.end) {
        if (region.loop) {
          audio.currentTime =
            selected === 'baseline' && current?.reference.basis === 'baseline'
              ? mapTimeWarp(region.start, current.reference.warp)
              : region.start;
          value = region.start;
        } else {
          audio.pause();
          interval.current = null;
          value = region.end;
        }
      }
      setTime(value);
    };

    const onPlay = () => setPlaying(true);
    const onPause = () => setPlaying(false);
    const onEnded = () => {
      setPlaying(false);
      interval.current = null;
    };
    const onError = () => {
      if (audio.src) setError('Audio could not be loaded from this source.');
    };
    const onLoaded = () => {
      audio.playbackRate = playbackRate;
      audio.volume = isMuted ? 0 : volume;
      const target = pending.current;
      if (target) {
        pending.current = null;
        const mediaTime = toMedia(target.time);
        audio.currentTime = Number.isFinite(audio.duration)
          ? Math.min(mediaTime, audio.duration)
          : mediaTime;
        if (target.resume) void audio.play().catch(() => {});
      }
    };

    audio.addEventListener('timeupdate', update);
    audio.addEventListener('play', onPlay);
    audio.addEventListener('pause', onPause);
    audio.addEventListener('ended', onEnded);
    audio.addEventListener('error', onError);
    audio.addEventListener('loadedmetadata', onLoaded);

    return () => {
      audio.pause();
      audio.removeEventListener('timeupdate', update);
      audio.removeEventListener('play', onPlay);
      audio.removeEventListener('pause', onPause);
      audio.removeEventListener('ended', onEnded);
      audio.removeEventListener('error', onError);
      audio.removeEventListener('loadedmetadata', onLoaded);
      audio.src = '';
    };
  }, []);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    const url =
      source === 'baseline' && report?.reference.basis === 'baseline'
        ? `/api/audio/${report.reference.clip_id}`
        : recording?.url ?? '';
    if (!url) {
      audio.src = '';
      return;
    }
    const wasPlaying = isPlaying;
    pending.current = { time: currentTime, resume: wasPlaying };
    setError(null);
    audio.src = url;
    audio.load();
  }, [recording?.url, source, report?.reference]);

  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.volume = isMuted ? 0 : volume;
      audioRef.current.playbackRate = playbackRate;
    }
  }, [volume, isMuted, playbackRate]);

  return {
    source,
    duration,
    currentTime,
    isPlaying,
    playbackRate,
    volume,
    isMuted,
    isLooping,
    error,
    changeSource(next: 'participant' | 'baseline') {
      if (next === source) return;
      if (next === 'baseline' && report?.reference.basis !== 'baseline') return;
      interval.current = null;
      setLooping(false);
      setSource(next);
    },
    togglePlay() {
      const audio = audioRef.current;
      if (!audio) return;
      if (isPlaying) {
        audio.pause();
      } else {
        void play();
      }
    },
    pause() {
      audioRef.current?.pause();
    },
    seek,
    playRegion(region: FlawRegion, options: { loop: boolean }) {
      interval.current = { start: region.start, end: region.end, loop: options.loop };
      setLooping(options.loop);
      seek(region.start);
      void play();
    },
    stopRegionLoop() {
      interval.current = null;
      setLooping(false);
    },
    setRate(rate: number) {
      setRate(rate);
      if (audioRef.current) audioRef.current.playbackRate = rate;
    },
    setVolume(value: number) {
      const val = Math.max(0, Math.min(1, value));
      setVolume(val);
      if (isMuted && val > 0) setMuted(false);
      if (audioRef.current) audioRef.current.volume = val;
    },
    toggleMute() {
      setMuted((prev) => !prev);
      if (audioRef.current) audioRef.current.volume = isMuted ? volume : 0;
    },
  };
}
