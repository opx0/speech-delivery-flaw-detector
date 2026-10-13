import type { Axis, FeatureName, FlawKind } from '../../../contract';

export const AXES: Axis[] = ['cadence', 'tone', 'pauses', 'volume'];

export const AXIS_LABELS: Record<Axis, string> = {
  cadence: 'Cadence',
  tone: 'Tone',
  pauses: 'Pauses',
  volume: 'Volume',
};

export const KIND_LABELS: Record<FlawKind, string> = {
  rush: 'Rushed pacing',
  drag: 'Dragging pace',
  monotone: 'Limited pitch variation',
  hesitation: 'Hesitation',
  pause_collapse: 'Missing pause',
  energy_fade: 'Fading energy',
};

export const FEATURES: Record<FeatureName, { label: string; unit: string }> = {
  speech_rate: { label: 'Speaking pace', unit: 'words/s' },
  pitch: { label: 'Pitch', unit: 'semitones' },
  pitch_variation: { label: 'Pitch variation', unit: 'semitones' },
  energy: { label: 'Energy', unit: 'dB' },
  pause: { label: 'Silence', unit: 'fraction' },
  clarity: { label: 'Clarity', unit: 'dB HNR' },
};

export function severityLabel(value: number): string {
  return value >= 0.7 ? 'High impact' : value >= 0.35 ? 'Moderate' : 'Subtle';
}
