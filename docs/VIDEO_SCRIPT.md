# Demo-first UI walkthrough and video plan

Target: a 5–6 minute video, within the 3–10 minute submission limit. The video is not yet recorded
or published. Lead with a useful working experience, not a long apology or a list of benchmarks.
Describe the prototype confidently while keeping evidence and claims accurate.

## Before recording: manually check the UI

Open http://localhost:8000 with the built UI and native CUDA API served by the same process.
The UI should say **Local processing**, not **Mock preview**.

| Your action | What to check |
| --- | --- |
| Explore examples → The New Colossus → Dragging pace | A real analysis starts; stage progress appears |
| Wait for the report | Scores, transcript, waveform, and findings belong to this recording |
| While waiting → inspect Analysis activity | Real progress messages and elapsed time appear; stage progress is not a time estimate |
| After completion → View activity | The completed activity history remains available |
| Select a finding | Its quoted words, timestamps, observed pace, and reference pace appear |
| Play passage | Playback starts at the selected passage and stops at its end |
| Loop passage, then turn looping off | The passage repeats; the loop indicator changes |
| Gold reference → play | You hear the reference and see the source indicator change |
| Return to Your recording | Participant playback resumes as the selected source |
| Acoustic features → choose a feature → click the chart | Curves appear and clicking seeks playback |
| Transcript → search a word → click a word | Matching words highlight and clicking seeks |
| Adjust rubric → change Cadence weight → Close rubric | The displayed weight and overall score respond |
| Export report | A download starts and a visible `Download requested: speech-review.json` confirmation appears |
| Header → Run history | Saved runs appear with status, score, findings, and time; a completed run opens with its report, parameters, and stage activity |
| In a saved run → Parameters & provenance | The exact calibration snapshot, input hash, submitted options, and runtime device are shown |
| In a saved run → Export run evidence | A `job-…-evidence.json` download starts |
| Back to workspace → open a saved run after a refresh | Reopening never re-runs analysis and never offers playback |
| Setup guide → Back to workspace | Your existing review is preserved |
| Reference library → Clean control | A separate real analysis completes; inspect its actual findings |
| Add your recording → upload audio and its spoken words | Your own file goes through the real workflow |
| Record audio → allow microphone → speak → Stop recording | Live waveform, input level, and elapsed timer appear; the saved take shows its length and a playback preview |

“Stop waiting” leaves the current review request without pretending to cancel server-side processing.
The submitted job may finish in the background. A microphone permission prompt, saving state,
quiet/loud-input hint, and specific backend error are shown when applicable.

Check microphone permission and recording before filming it. If capture is unavailable, use a
real file upload instead; do not present that as a working microphone demonstration. Inspect
clean-control output rather than assuming a perfect score or zero findings.

For GPU evidence after an analysis, show this optional terminal command:

```bash
curl --fail http://127.0.0.1:8000/api/runtime
```

The loaded alignment device should be `cuda:0`. Do not start another benchmark, stress runner,
or source rebuild alongside the live API on the 4 GB GPU; use the saved evidence instead.

### Show real server logs beside the UI

The server on port 8000 serves both the built UI and API. Use this single-server mode for filming,
and show this terminal beside it:

```bash
tail -f runs/demo.log
```

Build the latest frontend once with `npm --prefix web run build`, then start a fresh session with:

```bash
.cache/gpu-venv/bin/python scripts/start_demo.py
```

The launcher identifies the static UI at startup with `[UI]`, backend request logs `[BACKEND][HTTP]`,
processing events `[BACKEND][ANALYSIS]`, model loading `[BACKEND][ALIGNMENT]`, and lifecycle
messages `[SYSTEM]`. It appends to `runs/demo.log`; Ctrl+C gracefully stops its server.
It refuses occupied ports and CPU-only interpreters instead of starting a second or mock backend.
No separate frontend server is started. Open **Run history** on the same port to inspect a saved
run's original report, exact parameters, input hash, and server-stage activity. Export run evidence
if useful. The history is reports-only: no saved-upload playback, no retroactive visual sign-off,
and no claim that a successful run establishes detection accuracy.

Saved history may already contain earlier runs (including prior checks). Either present them as
already-saved runs, or start a clean journal before filming by stopping the server and deleting
`runs/history.sqlite3`. Do not present an older saved run as a fresh analysis performed on camera.

Backend-only processing logs are also retained in `runs/server.log`. They contain actual
queued/started jobs, stage updates, model device, elapsed time, numeric findings, completion, and
temporary-upload cleanup. It does not print transcript text or audio contents. Stage percentages
are progress within that stage, not an overall ETA or detection accuracy.

Microphone waveform and capture time are browser-local. Server logs begin when the take is
submitted, not while you are speaking. Do not narrate that the server has received audio before
upload. Show the browser timer/waveform for capture, then the server log for analysis.

## Recording setup

- Use a 1440×900 or larger browser window with readable text.
- Capture your microphone narration and system audio; check that both recording voices are audible.
- Have the dataset manifest, public release, technical report, and verification record ready.
- Warm the model with one manual analysis, then return to Overview before filming.
- The dragging-pace demo previously produced two findings. Read the current screen; do not promise
  exact scores, counts, or processing times before this run finishes.
- Keep waits visible, or label shortened footage as an edited wait. Never substitute mock results.

## Suggested 5–6 minute sequence

| Time | Screen/action | Suggested narration |
| --- | --- | --- |
| 0:00–0:25 | Welcome screen | “A speech score tells you very little on its own. Delivery links measured differences to the exact passage, so you can hear and inspect them.” |
| 0:25–1:05 | Explore examples → The New Colossus → Dragging pace; show progress | “We compare recordings of the same words. Audio is decoded, words are aligned, acoustic features are extracted, and the differences are explained.” |
| 1:05–2:05 | Select a finding; play participant passage, then gold reference | “Here are the affected words and timestamps. This passage is slower than the reference; the card gives the measured pace for both recordings.” Read the actual values. |
| 2:05–2:45 | Acoustic features, chart seeking, transcript seeking/search | “The finding is backed by these curves. I can jump between the measurement, the words, and the audio rather than trust an opaque score.” |
| 2:45–3:15 | Adjust rubric and export | “The rubric separates cadence, tone, pauses, and volume. I can change their importance and export the review. This grades delivery—not content.” |
| 3:15–3:55 | Run history → open the run just completed → Parameters & provenance → Stage activity | “Every run is saved, not just shown once. I can reopen what ran, the exact calibration and weights it used, the input fingerprint, and the server-side stage timings. Reports only—the audio is not kept, so there is no playback here.” |
| 3:55–4:30 | Manifest, one labeled injection, public dataset release | “The benchmark has 186 recordings across six texts, with public-domain provenance, neutral controls, six injected flaw types at four levels, mixed flaws, and voice-shifted controls.” Show a real region and its physical parameters. |
| 4:30–5:00 | Saved stress/rebuild/comparison evidence and full evaluation table | “We also checked long inputs, reproducibility, and detection quality separately.” Show the complete table, with its labels, rather than a single accuracy number. |
| 5:00–5:30 | Optional real upload or already checked microphone workflow | “For my own recording, I provide the words I spoke. The app aligns that transcript; it is not a transcription service.” Show the result only if it actually completes. |
| 5:30–5:55 | Return to review; repository, dataset, and report links | “The result is an inspectable speech-delivery review: hear the comparison, see the measurements, and navigate each passage.” Briefly name broader reader calibration and held-out human evaluation as the next development work. |

If the optional recording takes longer, keep the finished video below ten minutes. A clean-control
comparison can replace that segment, clearly identified as a dataset control rather than your voice.

## Evidence to show without rerunning it

- Source build: 186 regenerated audio hashes matched dataset v1; 12 source checksums verified.
- GPU stress: a stitched 600-second reference fixture processed in 32.7 seconds, with 1,152 words
  aligned. Identify it as a stress fixture, not a new human recording.
- Reproducibility: three repeated GPU reports matched; one native/CUDA Docker gold-upload pair
  was byte-identical. Do not generalize this to every environment or input.
- Evaluation: use the complete latest table in `docs/TECHNICAL_REPORT.md`. It uses a separate
  calibration candidate; the demo app retains the published calibration.

## Claims and framing

- Strong claim: “Timestamped, measurement-backed findings with synchronized audio comparison.”
- Strong claim: “A reproducible public benchmark and GPU-backed end-to-end workflow.”
- Keep the full benchmark visible or linked. Precision and recall describe different things;
  96.06% flaw-type accuracy is not overall detection accuracy.
- A concise qualification is enough: “This is a prototype; broader reader calibration and
  held-out human evaluation remain ongoing.” Do not claim those checks already passed.
- Do not call a delivery score a detection-confidence percentage, or promise every flaw is found.

Publish the finished recording on YouTube and add its URL to the README. This checklist prepares
the recording; it does not establish that the video or manual microphone checks have been completed.
