import type { JobEvent, Report, Stage } from '../../../contract';

export interface SSEState {
  status: 'idle' | 'running' | 'done' | 'failed';
  stage?: Stage;
  fraction?: number;
  message?: string;
  report?: Report;
  error?: string;
}

export function reduceSSE(state: SSEState, event: JobEvent): SSEState {
  switch (event.type) {
    case 'progress':
      if (state.status === 'done' || state.status === 'failed') return state;
      return {
        status: 'running',
        stage: event.stage,
        fraction: event.fraction,
        message: event.message,
      };
    case 'done':
      return {
        status: 'done',
        report: event.report,
      };
    case 'failed':
      return {
        status: 'failed',
        error: event.message,
      };
    default:
      return state;
  }
}
