import { useEffect, useRef, useState } from 'react';
import { formatTime } from '../../../shared/lib';

interface RecordingFeedbackProps {
  stream: MediaStream;
  startedAt: number;
  onLimit: () => void;
}

export function RecordingFeedback({ stream, startedAt, onLimit }: RecordingFeedbackProps) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const stopAtLimit = useRef(onLimit);
  stopAtLimit.current = onLimit;
  const [seconds, setSeconds] = useState(0);
  const [level, setLevel] = useState<number | null>(null);
  const [clipping, setClipping] = useState(false);

  useEffect(() => {
    const tick = () => {
      const elapsed = Math.max(0, (performance.now() - startedAt) / 1000);
      setSeconds(elapsed);
      if (elapsed >= 599) stopAtLimit.current(); // Leave a margin for final recorder chunks.
    };
    tick();
    const timer = window.setInterval(tick, 200);
    return () => window.clearInterval(timer);
  }, [startedAt]);

  useEffect(() => {
    let context: AudioContext | null = null;
    let source: MediaStreamAudioSourceNode | null = null;
    let animation = 0;
    let closed = false;
    try {
      context = new AudioContext();
      const analyser = context.createAnalyser();
      analyser.fftSize = 1024;
      source = context.createMediaStreamSource(stream);
      source.connect(analyser); // No destination connection: do not echo microphone audio.
      const samples = new Float32Array(analyser.fftSize);
      const drawing = canvas.current?.getContext('2d');
      const color = canvas.current ? getComputedStyle(canvas.current).color : '#aa6848';
      let lastFrame = 0;
      const draw = (now: number) => {
        if (closed) return;
        animation = requestAnimationFrame(draw);
        if (now - lastFrame < 100 || context?.state !== 'running') return;
        lastFrame = now;
        analyser.getFloatTimeDomainData(samples);
        let power = 0;
        let peak = 0;
        for (const sample of samples) {
          power += sample * sample;
          peak = Math.max(peak, Math.abs(sample));
        }
        setLevel(Math.min(100, Math.sqrt(power / samples.length) * 250));
        setClipping(peak >= 0.98);
        if (!drawing) return;
        drawing.clearRect(0, 0, 640, 80);
        drawing.strokeStyle = color;
        drawing.lineWidth = 2;
        drawing.beginPath();
        for (let index = 0; index < samples.length; index += 8) {
          const x = index / (samples.length - 8) * 640;
          const y = 40 - Math.max(-1, Math.min(1, (samples[index] ?? 0) * 3)) * 34;
          if (index === 0) drawing.moveTo(x, y);
          else drawing.lineTo(x, y);
        }
        drawing.stroke();
      };
      void context.resume().catch(() => { if (!closed) setLevel(null); });
      animation = requestAnimationFrame(draw);
    } catch {
      setLevel(null);
    }
    return () => {
      closed = true;
      cancelAnimationFrame(animation);
      source?.disconnect();
      if (context && context.state !== 'closed') void context.close().catch(() => {});
    };
  }, [stream]);

  const hint = level === null ? 'Recording is active; live meter is unavailable.'
    : clipping ? 'Input is loud. Move a little farther from the microphone.'
    : level < 1 ? (seconds > 2 ? 'Very little sound detected. Check your microphone or speak closer.' : 'Listening for microphone input…')
    : 'Microphone is picking up sound. Read your transcript aloud.';

  return <section className="microphone-feedback" aria-label="Microphone recording feedback">
    <div className="microphone-feedback-heading">
      <span><i className="recording-dot" /> Recording live</span>
      <span className="recording-clock"><output aria-label="Recording elapsed time" aria-live="off">{formatTime(seconds)}</output><small> / 10:00 max</small></span>
    </div>
    <canvas ref={canvas} width={640} height={80} role="img" aria-label="Live microphone waveform" />
    <div className="microphone-level" role="meter" aria-label="Microphone input level" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(level ?? 0)}>
      <span style={{ width: `${level ?? 0}%` }} />
    </div>
    <p>{hint}</p>
  </section>;
}
