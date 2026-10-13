# Speech review workspace

## References

- [Descript editor](https://mobbin.com/screens/c13adb46-5c67-4cae-b45c-559443094fb4): readable transcript, attached audio timeline, and contextual inspector.
- [ElevenLabs studio](https://mobbin.com/screens/7339a0f8-2733-4ea4-a8f9-3e4ad0d0b647): inline passage markers and timestamped feedback.
- [Hume evaluation](https://mobbin.com/screens/71393937-6a06-4b94-acb6-9ba9d7a68208): scores and evidence beside the transcript.

These references inform layout and interactions. Screenshots are not application assets.

## Usage

Select a real demo or upload a recording and supply the spoken text. Follow job progress, then
review the transcript, listen to marked passages, inspect measured deviations, and compare with
the gold recording when available. Acoustic charts share the participant's timeline.

The initial screen contains no fabricated scores. Network, decoding, and analysis failures remain
visible. Mock mode is explicitly labeled and enabled separately from normal development.

## Synthesis decision

Two designs were considered: a transcript-first review workspace and a timeline-first studio.
The transcript-first design is the base because quoted words and explanations are central to
speech coaching. The independent review favored it 20 to 17 across five design criteria.

The timeline-first design contributes explicit media ownership, bounded stream recovery, and
participant/reference clock mapping. Custom subscription controllers, blanket branded types,
and precomputed indexes are omitted because React hooks and the existing contract suffice.

## Module boundaries

| Module | Responsibility |
| --- | --- |
| `App.tsx` | Workspace layout, selected flaw, local rubric, ingestion and help dialogs |
| `hooks/useAnalysis.ts` | Validated library and job requests, stream lifecycle, recording ownership |
| `hooks/usePlayback.ts` | One audible player, source switching, participant clock, seeking, interval playback and looping |
| `logic/validate.ts` | JSON Schema validation at HTTP and event boundaries |
| `logic/warp.ts` | Participant/reference clock conversion |
| `components/` | Transcript, waveform visualization, feature chart, evidence, scores, intake, and controls |
| `index.css` | Authored design tokens, component styles, responsive layout, and focus states |

## State sketch

```ts
type AnalysisState =
	| { status: 'idle' }
	| { status: 'submitting'; recording: RecordingSource }
	| { status: 'running'; recording: RecordingSource; stage: Stage; fraction: number; message: string }
	| { status: 'ready'; recording: RecordingSource; report: Report }
	| { status: 'failed'; message: string };

// App calls the session owner, rather than coordinating HTTP and SSE.
analysis.analyzeDemo(demo, entry);
analysis.analyzeUpload(file, transcript, textId);
playback.seek(region.start);
playback.playRegion(region, { loop: true });
```

The report remains immutable. Local rubric changes derive the overall score and displayed row
weights together. Exported review JSON includes the adjusted rubric and consistent axis weights.

## Invariants and verification

- Only the playback hook plays audio. WaveSurfer renders the participant waveform without playback.
- Participant time is the shared coordinate for transcript, flaws, charts, and seeking.
- Source changes preserve the aligned passage. Gold audition uses the report's warp anchors.
- New requests abort prior fetches, close prior streams, and discard obsolete callbacks.
- Temporary browser URLs and media resources are released when replaced or unmounted.
- A stream disconnect is not a successful report. Replayed progress is idempotent, and exhausted
  recovery produces an explicit error.
- Keyboard controls, dialog focus, readable narrow layouts, and non-color finding labels are required.
- Frontend checks and real-backend browser tests verify ingestion, review, error states, and reweighting.
