# Speech review interface

## References

The user supplied an [Amplemarket section](https://mobbin.com/sites/sections/887f98cc-5dbf-4655-860e-bdd5faaeee19)
and an [Amigo section](https://mobbin.com/sites/sections/e07ba966-7fda-4699-b107-2147745a8d81).
The public links identify the sites, but do not expose the section screenshots without login.
Mobbin search returned these preview images for the design review:

- [Amigo hero](https://mobbin.com/sites/sections/7bb61cbf-bc3c-4ff1-aa04-5163dc65521a).
  Large serif text sits beside a product demonstration, with white space, thin dividers,
  and a rust-colored primary action.
- [Amigo company section](https://mobbin.com/sites/sections/9d33790b-ca6c-4653-b660-c22c4e13268f).
  A large statement and a smaller explanation occupy separate columns. The layout uses simple
  vertical rules and restrained image borders.
- [Amigo comparison section](https://mobbin.com/sites/sections/fbe3ead5-d14c-4e5e-ac01-a9a239ebbaa3).
  A sparse table reserves the rust accent for the main comparison column.
- [Descript editor](https://mobbin.com/screens/c13adb46-5c67-4cae-b45c-559443094fb4).
  The transcript occupies the main area, with an attached timeline and a contextual panel to the right.

The app adapts these layout and typography choices. Mobbin screenshots, logos, and healthcare
imagery are not application assets.

## Layout decision

Two local HTML prototypes compared a top-navigation layout with a compact sidebar layout.
The top-navigation version is the chosen design. It gives the transcript more horizontal room
and keeps overview, library, guide, and recording actions in one header.

The welcome screen has a two-column introduction, one upload action, an examples action,
and three real library examples. The decorative transcript and waveform are labeled as an
illustration and hidden from assistive technology. They contain no fabricated scores.

The review screen keeps the score summary above the transcript. The audio player attaches to
the transcript panel, while findings and measured evidence occupy the right column. On narrow
screens, the score cards form two columns and the findings follow the transcript and player.

The palette uses white backgrounds, warm-neutral borders, rust controls, green reference values,
and amber findings. Georgia provides the display and transcript type, with system sans-serif
and monospace fonts for controls and measurements. Setup needs no external font request.

`web/src/index.css` defines one set of color tokens and component styles, with responsive rules
at the end. The old green and blue palette overrides have been removed. WaveSurfer and uPlot
read the same CSS color tokens as the surrounding interface.

## Ownership

| Module | Responsibility |
| --- | --- |
| `web/src/app/App.tsx` | Header actions, analysis-state layout, and dialogs |
| `features/analysis-session/` | Library requests, uploads, job events, and recording URLs |
| `features/playback/` | The audible player, seeking, looping, and reference-clock mapping |
| `features/speech-ingestion/` | File input, microphone recording, transcript input, and library selection |
| `features/rubric-reweighting/` | Local scoring weights and consistent overall scores |
| `widgets/` | Header, welcome screen, transcript, waveform, charts, scores, and evidence |
| `shared/ui/` | Help dialog and shared interface elements |

Reports stay immutable. The rubric editor derives the displayed score and weights together.
Exported JSON includes the adjusted rubric. Demo headings use the library's display title
rather than an internal clip identifier.

## Interaction checks

- Only the playback hook plays audio. WaveSurfer renders the waveform without a second player.
- Transcript, waveform, findings, and charts use participant time. Gold playback uses the report's alignment map.
- New requests abort the previous fetch and close its event stream. Overview releases the active local review.
- Request and analysis failures remain visible. A failed request never becomes a successful fixture report.
- Dialogs support Escape and return focus to their opener when they close.
- Mock mode is explicit and separate from the real API mode.

The former browser suite checked real demo analysis, passage playback, gold-reference playback, rubric
changes, chart seeking, transcript search, report export, and return to the overview. It also checks
mobile navigation, dialog focus, failed uploads, and unavailable library data. Screenshots cover
the desktop welcome and review screens, mobile welcome and review screens, and the mobile library.

The suite and its configuration were removed at the owner's request after one final native-CUDA
run with no retries. Five checks passed. The valid-upload check reached the review screen but
failed while Playwright retrieved its SSE response body; its later identity/export assertions
were not verified. Logs, screenshots, source snapshots, and the failure trace remain in the
separate QA Lab workspace outside this repository.
Internal unit/debug tests were moved into that separate QA workspace as well.
Future verification uses the manual browser walkthrough and judge-facing live API validation.

## Action and waiting feedback

- Demo selection immediately shows audio loading, then upload/connection status; it does not wait
  for the recording download to finish before acknowledging the click.
- Analysis displays elapsed time and a bounded activity history of the backend's actual progress
  messages. Stage-based progress is not an ETA. The activity history remains available after completion.
- Stop waiting detaches the request and returns home; it explicitly does not cancel an accepted server job.
  Stale aborted requests cannot overwrite newer UI state.
- Microphone capture shows permission/saving states, a real input waveform, a signal-level meter,
  elapsed capture time, quiet/loud hints, and a ten-minute maximum. Captured files can be previewed.
  Streams and visualization resources are released when recording ends or the dialog closes.
- Existing review playback pauses when opening the intake dialog, avoiding microphone feedback.
- Export acknowledges the download request; backend failure messages remain specific rather than
  being replaced with a generic analysis error.

Focused checks live outside the submission in QA Lab. Recording visualization was checked with
a simulated browser microphone, including mobile width; a separate real CUDA analysis checked
progress, retained activity, and export feedback. These checks do not establish hardware-microphone
capture or full detector accuracy. Frontend type checking and production build passed.

## Setup documentation

`/docs` is a lazy-loaded setup page. It renders `docs/LOCAL_SETUP.md`, which remains the
repository's editable guide. Markdown section annotations select Docker CPU, native CPU, or
native CUDA steps. The parser derives step order and navigation from the document, not from
a second list of commands. Build checks validate metadata and shell syntax without executing commands.

The guide includes copying, a parameter reference, troubleshooting, mobile section shortcuts,
and shareable links such as `/docs?runtime=cuda`. Relative document links open the matching
repository files. The guide works without a successful reference-library request.

App owns pathname navigation and browser history. It keeps the review mounted while the guide
is visible, pauses audio, and retains the rubric, selected passage, and playback position.
Returning to the review does not automatically resume audio. The former browser tests covered these transitions
as well as exact clipboard output and a failed clipboard write.
