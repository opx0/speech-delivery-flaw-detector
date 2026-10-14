# GPU verification — 2026-10-14

All speech-model inference used CUDA on an RTX 3050 Laptop GPU. Internal development suites
were not run for the evaluation/stress checks below; focused UI/history checks are recorded separately.
Internal checks live in the separate QA Lab workspace. Logs and full outputs remain locally
under ignored `runs/verification-2026-10-14/`.

| Check | Actual outcome |
| --- | --- |
| Calibration-only candidate generation | Passed; nine reference recordings, three reader pairs; test readers excluded |
| Full dataset evaluation | Completed in 428.8 seconds; six metrics passed, recall and reader false positives failed |
| 600-second live API processing | Passed; 1,152 aligned words, 32.7 seconds of analysis |
| Live file upload | Passed with a genuine library recording; not a new user/speaker recording |
| Normative-mode upload | Passed with a short genuine excerpt; band-reference mode confirmed |
| CUDA Docker construction | Passed, including locked dependencies, frontend build, and verified model/dataset downloads |
| CUDA Docker homepage and setup guide | HTTP 200 for both |
| CUDA Docker upload and dragging-pace demo | Passed |
| Native/CUDA Docker report comparison | Byte-identical for one uploaded gold clip; score and word-boundary differences zero |
| Source rebuild | Passed in 94.3 seconds; all 12 source checksums and all 186 regenerated audio hashes matched |
| Revised technical report | Rendered to four A4 pages, below the six-page limit |

Stress memory evidence: server RSS high-water mark was 2,636,640 KiB (about 2.51 GiB). GPU usage
reached 3,770 MiB in one-second samples of total device memory, including unrelated applications.
The stress input was repeated reference audio padded to 600 seconds, not a human-held-out take.

## Single-server history dashboard

The demo launcher now serves the built UI, API, and `/history` together on port 8000.
Ports 5173 and 5179 were confirmed closed; no separate frontend/mock server was left running.
Frontend type checking and production build passed. No scoring or calibration change was made.

- One actual CUDA UI analysis, `job-3725f3cdc733`, processed the default-calibration dragging-pace
  demo in 15.84 seconds and recorded two findings. The saved input hash matched the served audio
  and report hash; the full saved calibration matched `data/dataset/calibration.json`.
- The run journal preserved original scores, full report, options, runtime (`cuda:0`), server stage
  events, and confirmed temporary-upload cleanup. JSON evidence export matched the saved run.
- Refresh reopened the saved run without submitting another job. Desktop and 390px mobile
  screenshots were inspected; hidden skip-link and long-array presentation issues were fixed.
  The subsequent reopen-only check passed with zero inference runs.
- Five isolated history/storage/API checks passed in QA Lab using a fake analyzer and a saved
  report fixture, not CPU inference. They covered persistence, unchanged calibration snapshots,
  failures/interruption, concurrent writes, pagination/validation, and upload cleanup on rejection.

Internal check code, exports, screenshots, and JSON check summaries are kept in a separate QA Lab
workspace outside this repository; they are not submission dependencies.
The live journal is ignored `runs/history.sqlite3`. This reports-only history starts with newly
admitted runs; previous analyses and human visual sign-off are not backfilled. It does not prove
detection accuracy, hardware microphone capture, or satisfactory human listening review.

## Accuracy remains insufficient

The full run used `calibration-cuda-2026-10-14.json`, retained here so judges can reproduce it.
Dataset v1's default calibration was not overwritten. Live API/container checks used that default.

| Metric | Result | Target |
| --- | ---: | ---: |
| Precision | 80.31% | ≥70% |
| Recall | **21.98% — failed** | ≥70% |
| Median matched boundary error | 260.00 ms | <300 ms |
| Flaw-type accuracy | 96.06% | ≥80% |
| Mean severity correlation | 0.931 | ≥0.90 |
| Reader false-positive rate | **66.67% — failed** | ≤10% |
| Mean shifted-control score difference | 0.278 points | ≤5 points |
| Three-run report byte identity | 100% | 100% |

There were 102 true positives, 25 false positives, and 362 false negatives across 464 labels.
Two of three independent test readers received findings. That tiny reader sample cannot establish
generalization. Sample sizes, spreads, and interval assumptions are in the technical report.

## Blocked or still pending

- Three additional independent readers and the sixteen genuine human-held-out takes are absent.
  Human-import and human-evaluation checks cannot be completed without them.
- Hardware microphone capture needs browser permission and a genuinely spoken take. API upload
  of an existing recording is not evidence of hardware capture.
- A fresh native VM and Windows/macOS hosts were not available. Linux Docker does not establish
  those installations.
- Human listening/transcript-quality review is not established by hashes or successful decoding.
- The video has not been recorded/published. Final commit/publication was not performed.
- The source rebuild reproduced audio, not the earlier calibration; calibration changed with the
  detector revision. No CPU/CUDA report-identity check was run.

Passing the live checks does not make the submission complete while accuracy gates and required
human/video deliverables remain outstanding.
