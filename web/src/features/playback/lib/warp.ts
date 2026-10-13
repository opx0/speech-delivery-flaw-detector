import type { WarpAnchor } from '../../../contract';

export function mapTimeWarp(
  participantTime: number,
  anchors: readonly WarpAnchor[],
): number {
  if (!anchors || anchors.length === 0) return participantTime;
  if (participantTime <= anchors[0]!.participant_s) {
    const rate =
      anchors.length > 1
        ? (anchors[1]!.baseline_s - anchors[0]!.baseline_s) /
          (anchors[1]!.participant_s - anchors[0]!.participant_s || 1)
        : 1;
    return anchors[0]!.baseline_s + (participantTime - anchors[0]!.participant_s) * rate;
  }
  const last = anchors[anchors.length - 1]!;
  if (participantTime >= last.participant_s) {
    const prev = anchors.length > 1 ? anchors[anchors.length - 2]! : last;
    const rate =
      (last.baseline_s - prev.baseline_s) / (last.participant_s - prev.participant_s || 1);
    return last.baseline_s + (participantTime - last.participant_s) * rate;
  }
  for (let i = 0; i < anchors.length - 1; i++) {
    const a1 = anchors[i]!;
    const a2 = anchors[i + 1]!;
    if (participantTime >= a1.participant_s && participantTime <= a2.participant_s) {
      const frac =
        (participantTime - a1.participant_s) / (a2.participant_s - a1.participant_s || 1);
      return a1.baseline_s + frac * (a2.baseline_s - a1.baseline_s);
    }
  }
  return participantTime;
}

export function mapBaselineTime(
  baselineTime: number,
  anchors: readonly WarpAnchor[],
  fallback: number,
): number {
  if (!anchors || anchors.length === 0) return baselineTime;
  for (let i = 0; i < anchors.length - 1; i++) {
    const a1 = anchors[i]!;
    const a2 = anchors[i + 1]!;
    if (baselineTime >= a1.baseline_s && baselineTime <= a2.baseline_s) {
      const frac = (baselineTime - a1.baseline_s) / (a2.baseline_s - a1.baseline_s || 1);
      return a1.participant_s + frac * (a2.participant_s - a1.participant_s);
    }
  }
  return fallback;
}
