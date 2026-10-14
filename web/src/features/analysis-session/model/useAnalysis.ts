import { useCallback, useEffect, useRef, useState } from 'react';
import type { AnalyzeOptions, DemoClip, LibraryEntry, LibraryListing, Report, Stage } from '../../../contract';
import { validatePayload } from '../../../entities/report';
import { ERROR_MESSAGES } from '../../../entities/error';

export interface RecordingSource {
  name: string;
  url: string;
}

export interface ActivityEntry {
  at: number;
  message: string;
}

interface AnalysisActivity {
  startedAt: number;
  logs: ActivityEntry[];
}

export type AnalysisState =
  | { status: 'idle' }
  | ({ status: 'submitting'; recording: RecordingSource; message: string } & AnalysisActivity)
  | ({
      status: 'running';
      recording: RecordingSource;
      stage: Stage;
      fraction: number;
      message: string;
    } & AnalysisActivity)
  | ({ status: 'ready'; jobId: string; recording: RecordingSource; report: Report } & AnalysisActivity)
  | { status: 'failed'; message: string };

type LibraryState =
  | { status: 'loading' }
  | { status: 'ready'; listing: LibraryListing }
  | { status: 'failed'; message: string };

async function responseJson(response: Response): Promise<unknown> {
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    const detail = body && typeof body === 'object' && 'detail' in body ? body.detail : null;
    throw new Error(
      typeof detail === 'string' ? detail : `Request failed (${response.status}). Try again.`,
    );
  }
  return response.json();
}

function message(error: unknown): string {
  return error instanceof Error ? error.message : 'The request could not be completed.';
}

export function useAnalysis() {
  const [state, setState] = useState<AnalysisState>({ status: 'idle' });
  const [library, setLibrary] = useState<LibraryState>({ status: 'loading' });
  const [libraryAttempt, setLibraryAttempt] = useState(0);
  const request = useRef<AbortController | null>(null);
  const stream = useRef<EventSource | null>(null);
  const ownedUrl = useRef<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setLibrary({ status: 'loading' });
    fetch('/api/library', { signal: controller.signal })
      .then(responseJson)
      .then((data) => setLibrary({ status: 'ready', listing: validatePayload('LibraryListing', data) }))
      .catch((error) => {
        if (!controller.signal.aborted) setLibrary({ status: 'failed', message: message(error) });
      });
    return () => controller.abort();
  }, [libraryAttempt]);

  useEffect(
    () => () => {
      request.current?.abort();
      stream.current?.close();
      stream.current = null;
      if (ownedUrl.current) URL.revokeObjectURL(ownedUrl.current);
    },
    [],
  );

  const start = useCallback(
    async (
      name: string,
      transcript: string,
      textId: string | null,
      audio: File | string,
    ) => {
      request.current?.abort();
      stream.current?.close();
      if (ownedUrl.current) {
        URL.revokeObjectURL(ownedUrl.current);
        ownedUrl.current = null;
      }

      const controller = new AbortController();
      request.current = controller;
      const startedAt = Date.now();
      let logs: ActivityEntry[] = [];
      const log = (text: string) => {
        if (logs[logs.length - 1]?.message !== text) {
          logs = [...logs, { at: Date.now(), message: text }].slice(-100);
        }
      };
      const current = () => !controller.signal.aborted && request.current === controller;
      const url = typeof audio === 'string' ? audio : URL.createObjectURL(audio);
      if (typeof audio !== 'string') ownedUrl.current = url;
      const recording: RecordingSource = { name, url };
      const preparing = typeof audio === 'string' ? 'Loading the selected recording…' : 'Uploading your recording…';
      log(preparing);
      setState({ status: 'submitting', recording, message: preparing, startedAt, logs });

      try {
        let file: Blob;
        if (typeof audio === 'string') {
          const res = await fetch(audio, { signal: controller.signal });
          if (!res.ok) throw new Error(`Could not load reference audio (${res.status}).`);
          file = await res.blob();
          if (!current()) return;
          log('Recording loaded. Uploading for analysis…');
          setState({ status: 'submitting', recording, message: 'Uploading for analysis…', startedAt, logs });
        } else {
          file = audio;
        }

        const form = new FormData();
        form.append('audio', file, typeof audio === 'string' ? `${name}.flac` : audio.name);
        const options: AnalyzeOptions = { transcript, library_text_id: textId ?? null, weights: null };
        form.append('options', JSON.stringify(options));

        const jobResponse = await fetch('/api/jobs', {
          method: 'POST', body: form, signal: controller.signal,
        });
        const data = (await responseJson(jobResponse)) as { job_id: string };
        const jobId = data.job_id;
        if (!current()) return;
        const connecting = 'Upload received. Connecting to analysis updates…';
        log(connecting);
        setState({ status: 'submitting', recording, message: connecting, startedAt, logs });

        const events = new EventSource(`/api/jobs/${jobId}/events`);
        stream.current = events;
        events.onmessage = (messageEvent) => {
          if (!current()) return;
          try {
            const raw = JSON.parse(messageEvent.data as string) as {
              type: string;
              stage?: Stage;
              fraction?: number;
              message?: string;
              report?: unknown;
              code?: keyof typeof ERROR_MESSAGES;
              error?: { code: keyof typeof ERROR_MESSAGES; message: string };
            };
            if (raw.type === 'progress' && raw.stage) {
              log(raw.message || `Processing ${raw.stage}…`);
              setState({
                status: 'running', recording, stage: raw.stage,
                fraction: raw.fraction ?? 0, message: raw.message ?? '', startedAt, logs,
              });
            } else if (raw.type === 'done' && raw.report) {
              events.close();
              log('Analysis complete. Your review is ready.');
              setState({
                status: 'ready', jobId, recording, report: validatePayload('Report', raw.report),
                startedAt, logs,
              });
            } else if (raw.type === 'failed') {
              events.close();
              const code = raw.code ?? raw.error?.code;
              const text = raw.message || raw.error?.message || (code ? ERROR_MESSAGES[code] : undefined);
              setState({ status: 'failed', message: text ?? 'Analysis failed.' });
            }
          } catch (error) {
            events.close();
            setState({ status: 'failed', message: message(error) });
          }
        };
        events.onerror = () => {
          if (!current()) return;
          events.close();
          setState((state) => state.status === 'ready' ? state
            : { status: 'failed', message: 'Connection to analysis worker lost.' });
        };
      } catch (error) {
        if (current()) setState({ status: 'failed', message: message(error) });
      }
    },
    [],
  );

  return {
    state,
    library,
    retryLibrary: () => setLibraryAttempt((n) => n + 1),
    analyzeUpload: (file: File, transcript: string, textId: string | null) =>
      start(file.name.replace(/\.[^/.]+$/, ''), transcript, textId, file),
    analyzeDemo: (demo: DemoClip, entry: LibraryEntry) =>
      start(demo.title, entry.transcript, entry.text_id, demo.audio_url),
    reset: () => {
      request.current?.abort();
      request.current = null;
      stream.current?.close();
      if (ownedUrl.current) {
        URL.revokeObjectURL(ownedUrl.current);
        ownedUrl.current = null;
      }
      setState({ status: 'idle' });
    },
  };
}
