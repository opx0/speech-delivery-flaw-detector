import type { JobEvent, Report } from "./index";

// Compiles only if the generated types keep each discriminated union narrowable and exhaustive.
export function describeReference(reference: Report["reference"]): string {
  switch (reference.basis) {
    case "baseline":
      return reference.clip_id;
    case "band":
      return `${reference.n_reference_clips} reference clips`;
  }
}

export function describeEvent(event: JobEvent): string {
  switch (event.type) {
    case "progress":
      return `${event.stage} ${event.fraction}`;
    case "done":
      return `done ${event.report.overall}`;
    case "failed":
      return event.code;
  }
}
