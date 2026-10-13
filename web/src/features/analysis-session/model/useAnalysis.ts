import { useCallback, useEffect, useRef, useState } from 'react';
import type { AnalyzeOptions, DemoClip, LibraryEntry, LibraryListing, Report, Stage } from '../../../contract';
import { validatePayload } from '../../../entities/report';
import { ERROR_MESSAGES } from '../../../entities/error';

export interface RecordingSource {
  name: string;
  url: string;
}

export type AnalysisState =
  | { status: 'idle' }
  | { status: 'submitting'; recording: RecordingSource }
  | {
      status: 'running';
      recording: RecordingSource;
      stage: Stage;
      fraction: number;
      message: string;
    }
  | { status: 'ready'; recording: RecordingSource; report: Report }
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

      let file: Blob;
      let url: string;
      if (typeof audio === 'string') {
        url = audio;
        const res = await fetch(audio, { signal: controller.signal });
        if (!res.ok) throw new Error(`Could not load reference audio (${res.status}).`);
        file = await res.blob();
      } else {
        file = audio;
        url = URL.createObjectURL(audio);
        ownedUrl.current = url;
      }

      const recording: RecordingSource = { name, url };
      setState({ status: 'submitting', recording });

      const form = new FormData();
      form.append('audio', file, typeof audio === 'string' ? `${name}.flac` : audio.name);
      const options: AnalyzeOptions = {
        transcript,
        library_text_id: textId ?? null,
        weights: null,
      };
      form.append('options', JSON.stringify(options));

      const jobResponse = await fetch('/api/jobs', {
        method: 'POST',
        body: form,
        signal: controller.signal,
      });
      const data = (await responseJson(jobResponse)) as { job_id: string };
      const jobId = data.job_id;

      const events = new EventSource(`/api/jobs/${jobId}/events`);
      stream.current = events;

      events.onmessage = (messageEvent) => {
        try {
          const raw = JSON.parse(messageEvent.data as string) as {
            type: string;
            stage?: Stage;
            fraction?: number;
            message?: string;
            report?: unknown;
            error?: { code: keyof typeof ERROR_MESSAGES; message: string };
          };
          if (raw.type === 'progress' && raw.stage) {
            setState({
              status: 'running',
              recording,
              stage: raw.stage,
              fraction: raw.fraction ?? 0,
              message: raw.message ?? '',
            });
          } else if (raw.type === 'done' && raw.report) {
            events.close();
            setState({
              status: 'ready',
              recording,
              report: validatePayload('Report', raw.report),
            });
          } else if (raw.type === 'failed') {
            events.close();
            const text = raw.error?.code ? ERROR_MESSAGES[raw.error.code] : raw.error?.message;
            setState({ status: 'failed', message: text ?? 'Analysis failed.' });
          }
        } catch (e) {
          events.close();
          setState({ status: 'failed', message: message(e) });
        }
      };

      events.onerror = () => {
        events.close();
        setState((current) =>
          current.status === 'ready'
            ? current
            : { status: 'failed', message: 'Connection to analysis worker lost.' },
        );
      };
    },
    [],
  );

  return {
    state,
    library,
    retryLibrary: () => setLibraryAttempt((n) => n + 1),
    analyzeUpload: (file: File, transcript: string, textId: string | null) =>
      start(file.name.replace(/\.[^/.]+$/, ''), transcript, textId, file).catch((error) =>
        setState({ status: 'failed', message: message(error) }),
      ),
    analyzeDemo: (demo: DemoClip, entry: LibraryEntry) =>
      start(`${entry.title} (${demo.clip_id})`, entry.transcript, entry.text_id, demo.audio_url).catch(
        (error) => setState({ status: 'failed', message: message(error) }),
      ),
    reset: () => {
      request.current?.abort();
      stream.current?.close();
      if (ownedUrl.current) {
        URL.revokeObjectURL(ownedUrl.current);
        ownedUrl.current = null;
      }
      setState({ status: 'idle' });
    },
  };
}
