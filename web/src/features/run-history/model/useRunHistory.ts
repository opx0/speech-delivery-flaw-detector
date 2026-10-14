import { useEffect, useState } from 'react';
import type { AnalyzeOptions, Report, RubricWeights } from '../../../contract';
import { validatePayload } from '../../../entities/report';

export type RunStatus = 'queued' | 'running' | 'done' | 'failed' | 'interrupted';
export interface RunSummary {
  job_id: string;
  filename: string;
  created_at: number;
  status: RunStatus;
  elapsed_s: number | null;
  overall: number | null;
  findings: number | null;
  reference_basis: 'baseline' | 'band' | null;
}
export interface SavedRun {
  schema_version: 1;
  job_id: string;
  filename: string;
  created_at: number;
  started_at: number | null;
  finished_at: number | null;
  elapsed_s: number | null;
  status: RunStatus;
  upload_bytes: number;
  audio_sha256: string;
  audio_retained: false;
  upload_cleanup: 'pending' | 'removed' | 'incomplete';
  options: AnalyzeOptions;
  parameters: {
    calibration: Record<string, unknown>;
    effective_weights: RubricWeights;
    alignment_model: { name: string; revision: string };
    transcript_match_threshold: number;
    runtime_at_startup: Record<string, unknown>;
    dataset_manifest_sha256: string;
  };
  runtime_after: Record<string, unknown> | null;
  events: { at: number; elapsed_s: number | null; stage?: string; fraction?: number; message: string }[];
  report: Report | null;
  error: { code: string; message: string } | null;
}
interface Listing {
  runs: RunSummary[];
  counts: Record<RunStatus, number>;
  total: number;
  offset: number;
  limit: number;
}

async function getJson(url: string, signal: AbortSignal): Promise<unknown> {
  const response = await fetch(url, { signal });
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    throw new Error(body && typeof body === 'object' && 'detail' in body && typeof body.detail === 'string'
      ? body.detail : `Could not load run history (${response.status}).`);
  }
  return response.json();
}

export function useRunHistory(selectedId: string | null) {
  const [listing, setListing] = useState<Listing | null>(null);
  const [detail, setDetail] = useState<SavedRun | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [offset, setOffset] = useState(0);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    setListing(null);
    const load = async () => {
      try {
        const result = await getJson(`/api/history?limit=30&offset=${offset}`, controller.signal) as Listing;
        if (controller.signal.aborted) return;
        if (!Array.isArray(result.runs) || !result.counts) throw new Error('Invalid history response.');
        setListing(result);
        setError(null);
      } catch (cause) {
        if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : 'History unavailable.');
      } finally {
        if (!controller.signal.aborted) timer = setTimeout(load, 5000);
      }
    };
    void load();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [offset, attempt]);

  useEffect(() => {
    setDetail(null);
    setDetailError(null);
    if (!selectedId) return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    const load = async () => {
      try {
        const result = await getJson(`/api/history/${encodeURIComponent(selectedId)}`, controller.signal) as SavedRun;
        if (controller.signal.aborted) return;
        if (result.schema_version !== 1 || result.job_id !== selectedId || !Array.isArray(result.events)) {
          throw new Error('Invalid saved run response.');
        }
        if (result.report) result.report = validatePayload('Report', result.report);
        setDetail(result);
        setDetailError(null);
        if (result.status === 'queued' || result.status === 'running') timer = setTimeout(load, 3000);
      } catch (cause) {
        if (!controller.signal.aborted) setDetailError(cause instanceof Error ? cause.message : 'Saved run unavailable.');
      }
    };
    void load();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [selectedId, attempt]);

  return { listing, detail, error, detailError, offset, setOffset, refresh: () => setAttempt(n => n + 1) };
}
