import { describe, it, expect } from 'vitest';
import type { Report } from '../../contract';
import { formatTime } from '../format';
import { mapTimeWarp } from '../warp';
import { computeOverall, adjustWeights } from '../reweight';
import { reduceSSE, type SSEState } from '../sse';
import { validatePayload } from '../validate';
import { ERROR_MESSAGES } from '../errors';
import reportContrast from '../../../../contract/fixtures/report_contrast.json';
import libraryJson from '../../../../contract/fixtures/library.json';

describe('format', () => {
  it('formats time in mm:ss', () => {
    expect(formatTime(0)).toBe('00:00');
    expect(formatTime(65.5)).toBe('01:05');
  });
});

describe('warp', () => {
  it('maps participant time to baseline time', () => {
    const anchors = [
      { participant_s: 0.0, baseline_s: 0.0 },
      { participant_s: 10.0, baseline_s: 12.0 },
      { participant_s: 20.0, baseline_s: 20.0 }
    ];
    expect(mapTimeWarp(0, anchors)).toBeCloseTo(0);
    expect(mapTimeWarp(5, anchors)).toBeCloseTo(6);
    expect(mapTimeWarp(10, anchors)).toBeCloseTo(12);
    expect(mapTimeWarp(15, anchors)).toBeCloseTo(16);
    expect(mapTimeWarp(20, anchors)).toBeCloseTo(20);
    expect(mapTimeWarp(25, anchors)).toBeCloseTo(24);
  });
});

describe('reweight', () => {
  it('computes overall exactly matching fixture', () => {
    const report = reportContrast as unknown as Report;
    const overall = computeOverall(report.axis_scores, report.weights);
    expect(overall).toBeCloseTo(report.overall, 9);
  });
  it('adjusts weights and sums to 1', () => {
    const w = { cadence: 0.25, pauses: 0.25, tone: 0.25, volume: 0.25 };
    const w2 = adjustWeights(w, 'cadence', 0.5);
    expect(w2.cadence).toBe(0.5);
    const sum = w2.cadence + w2.pauses + w2.tone + w2.volume;
    expect(sum).toBeCloseTo(1);
    expect(w2.pauses).toBeCloseTo(0.5 / 3);
  });
});

describe('sse', () => {
  it('reduces events correctly', () => {
    let state: SSEState = { status: 'idle' };
    state = reduceSSE(state, { type: 'progress', job_id: '1', stage: 'decode', fraction: 0.1, message: 'm' });
    expect(state.status).toBe('running');
    state = reduceSSE(state, { type: 'done', job_id: '1', report: reportContrast as any });
    expect(state.status).toBe('done');
    state = reduceSSE(state, { type: 'progress', job_id: '1', stage: 'decode', fraction: 0.1, message: 'm' });
    expect(state.status).toBe('done');
  });
});

describe('errors', () => {
  it('covers every ErrorCode', () => {
    const codes = ["unsupported_audio", "too_long", "too_large", "transcript_mismatch", "alignment_failed", "internal"];
    for (const code of codes) {
      expect(typeof ERROR_MESSAGES[code as keyof typeof ERROR_MESSAGES]).toBe('string');
    }
  });
});

describe('validate', () => {
  it('validates a valid fixture', () => {
    expect(() => validatePayload('LibraryListing', libraryJson)).not.toThrow();
  });
  it('rejects an invalid payload', () => {
    expect(() => validatePayload('LibraryListing', { nope: true })).toThrow();
  });
});
