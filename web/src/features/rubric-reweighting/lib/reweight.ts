import type { Axis, AxisScore, RubricWeights } from '../../../contract';

export function computeOverall(
  axisScores: readonly AxisScore[],
  weights: RubricWeights,
): number {
  let weightedSum = 0;
  for (const s of axisScores) {
    weightedSum += s.score * (weights[s.axis] ?? 0);
  }
  return weightedSum;
}

export function adjustWeights(
  current: RubricWeights,
  targetAxis: Axis,
  newValue: number,
): RubricWeights {
  const clamped = Math.max(0, Math.min(1, newValue));
  const otherAxes = (Object.keys(current) as Axis[]).filter((a) => a !== targetAxis);
  const remaining = 1 - clamped;

  const currentOtherSum = otherAxes.reduce((acc, a) => acc + current[a], 0);

  const updated = { ...current, [targetAxis]: clamped };

  if (currentOtherSum > 0) {
    for (const a of otherAxes) {
      updated[a] = (current[a] / currentOtherSum) * remaining;
    }
  } else {
    const equalShare = remaining / otherAxes.length;
    for (const a of otherAxes) {
      updated[a] = equalShare;
    }
  }

  return updated;
}
