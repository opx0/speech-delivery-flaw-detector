# Speech delivery flaw detector

Technical report for Track C. Results below come from the 2026-10-14 full dataset v1 evaluation
on an NVIDIA RTX 3050 Laptop GPU with PyTorch 2.6.0+cu124 and a separately retained calibration
candidate. The published dataset calibration was not overwritten.

## 1. Purpose and architecture

The app compares a recording with a gold recording of the same text. It reports delivery scores
and timestamped findings with the affected words, observed values, and reference values.
The four scoring axes are cadence, tone, pauses, and volume. It does not score content quality.

FastAPI accepts audio and transcript uploads. A bounded job queue runs analysis and streams
progress through Server-Sent Events. The React dashboard displays the report and plays both
recordings. Pydantic models define the dataset, report, and job contracts. The repository exports
JSON Schema and generates the frontend types from those models.

The pipeline has five stages:

1. FFmpeg decodes the upload to 16 kHz mono samples. Upload limits are 50 MB and 10 minutes.
2. Torchaudio MMS CTC aligns transcript characters and produces word timestamps. Inference uses
   overlapping 30-second chunks with two seconds of context. Low-confidence transcript matches fail.
3. Praat estimates pitch. The extractor calculates energy, speaking rate, pauses, and supporting
   clarity measurements on 10 ms frames with 250 ms smoothing.
4. Contrast mode pairs words with the gold recording and measures delivery differences.
   Normative mode uses calibrated percentile bands when the transcript has no library match.
5. The explanation code converts measured differences into text. It does not call a generative model.

Pitch uses semitones relative to each speaker's median voiced pitch:

`normalized_pitch = 12 * log2(pitch / median_voiced_pitch)`

Energy uses decibels relative to the speaker's 95th-percentile speech-frame RMS:

`normalized_energy = 20 * log10(RMS / speech_RMS_p95)`

These transformations reduce differences in raw pitch and recording gain. They do not prove that
the detector treats every speaker or speaking style correctly.

## 2. Dataset construction

Dataset v1 contains 186 FLAC recordings from six public-domain LibriVox texts. The manifest
records source URLs, rights evidence, transcripts, word alignments, audio hashes, and flaw labels.
The texts are The New Colossus, Ozymandias, The Gettysburg Address, Declaration of Independence,
The Coming of the End, and Dover Beach.

| Recording role | Count |
| --- | ---: |
| Gold readings | 6 |
| Independent natural readers | 6 |
| Neutral resynthesis controls | 6 |
| Single-flaw recordings | 144 |
| Mixed-flaw recordings | 12 |
| Pitch- and formant-shifted controls | 12 |

The builder modifies word-aligned passages rather than whole recordings. It records transformed
start and end times and the physical injection parameters. Each flaw has four levels:

| Flaw | Parameter values, levels 1 through 4 |
| --- | --- |
| Rush | Rate factors 1.15, 1.30, 1.50, 1.80 |
| Drag | Rate factors 0.87, 0.77, 0.67, 0.55 |
| Monotone | Pitch excursion retained 0.70, 0.45, 0.25, 0.05 |
| Hesitation | Inserted silence 0.25, 0.50, 0.90, 1.50 seconds |
| Pause collapse | Pause retained 0.70, 0.45, 0.20, 0.00 |
| Energy fade | Final loss 3, 6, 10, 16 dB across the final 60% of a passage |

Neutral controls pass through the resynthesis pipeline without an injected flaw. Shifted controls
test sensitivity to pitch and formant changes. These controls are synthetic, not recordings of
additional speakers. Three natural readers belong to calibration and three to the test split.
The planned 16 human-recorded held-out clips have not been supplied.

The [dataset v1 release](https://github.com/opx0/speech-delivery-flaw-detector/releases/tag/dataset-v1)
contains the archive. The repository retains metadata and downloads audio separately. The archive
SHA-256 is `ca5c16fa9f0503c9f13b60dfdb1f0f2f5322581ff7a51a2bb3e111d91a0cb6da`.

## 3. Detection and scoring

Contrast mode pools speech durations across five-word neighborhoods for cadence and measures
pitch variation, gap excess, gap deficit, and energy
drop. Each measurement uses a spread learned from calibration readers, with minimum spread
floors. Candidate thresholds clear calibration-reader evidence capable of forming a sufficiently
long region. The candidate uses nine calibration clips and three reader pairs; held-out readers
were not used to generate it.

A word that reaches its threshold starts a region. The detector includes nearby words that reach
half the threshold and merges runs separated by at most one word. Fade growth is capped at one
reference spread and requires at least three words with increasing evidence. Its energy reference
uses the sentence head, rather than including the fading tail. Regions shorter than 0.5 seconds
are discarded. Reported boundaries follow the aligned words, not independently measured human annotations.

For mean region evidence `z`, severity is `1 - exp(-max(z, 0) / 4)`.
An axis score is `100 * exp(-(4 * burden + residual))`.
Burden sums each region's severity times its duration and divides by clip duration. Residual
measures sub-threshold evidence outside marked regions. The overall score is the weighted mean
of the four axis scores. Default weights are 25% each, and the dashboard permits reweighting.

Normative mode checks window statistics against calibrated bands. Its findings carry lower
confidence because no recording of the same text provides a direct reference.

## 4. Full evaluation

The evaluation processes all 156 flawed clips, six neutral controls, three held-out natural readers,
and 12 shifted controls. Gold recordings provide the baselines. It reuses reports between metric
calculations, but runs analysis afresh three times for the byte-identity check.

Region matching requires the same flaw kind and intersection over union of at least 0.5. The run
produced 102 true positives, 25 false positives, and 362 false negatives. Type accuracy uses the
best-overlapping ground-truth region. Boundary errors apply only to successful region matches.

| Metric | Result | Sample size | Target | Outcome |
| --- | ---: | --- | --- | --- |
| Region precision | 80.31% | 127 detections | At least 70% | Pass |
| Region recall | 21.98% | 464 labeled regions | At least 70% | Fail |
| Median boundary error | 260.00 ms | 102 matches | Below 300 ms | Pass |
| Flaw-type accuracy | 96.06% | 127 overlaps | At least 80% | Pass |
| Severity Spearman correlation | 0.931 | 36 series | At least 0.90 | Pass |
| Held-out reader false-positive rate | 66.67% | 3 readers | At most 10% | Fail |
| Mean shifted-control score delta | 0.278 points | 12 pairs | At most 5 points | Pass |
| Repeated-run byte identity | 100% | 3 runs of one clip | 100% | Pass |

Standard deviations are 308.88 ms for matched boundary errors, 0.141 for severity correlations,
and 0.138 points for shifted-control score deltas. Descriptive 95% Wilson intervals are
72.55–86.30% for precision, 18.45–25.97% for recall, 91.11–98.31% for type accuracy, and
20.77–93.85% for reader false positives. Wilson intervals assume independent Bernoulli trials;
regions share clips and speakers, so these intervals do not establish population generalization.

The detector misses 362 of 464 labeled regions. Two of three held-out readers receive at least one
finding. Calibration on three reader pairs does not establish reliable generalization. Changing
thresholds to fit these test readers would contaminate the evaluation. Further calibration data
and a separate held-out run are needed before claiming reliable coaching accuracy.

The command writes the metrics and per-clip findings to JSON and exits with code 1 when targets fail:

```bash
TORCH_HOME="$PWD/models/torch" CUBLAS_WORKSPACE_CONFIG=:4096:8 \
  .cache/gpu-venv/bin/python -m speech_delivery.evaluation --device cuda \
  --calibration docs/evaluation/calibration-cuda-2026-10-14.json \
  --output runs/full-evaluation-cuda.json
```

See [the GPU setup guide](LOCAL_SETUP.md#optional-nvidia-gpu-execution) to prepare that environment.
The candidate is retained under `docs/evaluation/`; the default application still uses the
published calibration. Live workflow checks below used that default, not the evaluation candidate.

## 5. Dashboard and deployment verification

Earlier browser suites passed against the real GPU backend and production CPU Docker app,
including the shared setup guide. They submitted The New Colossus dragging-pace
example and checks findings, playback, reference audio, score reweighting, charts, transcript search,
mobile layout, and report export. Separate checks cover rejected audio and library failures.
This proves the selected workflow, not detection accuracy across every demo.

Historical results were 158 Python tests, 13 frontend tests, and nine CUDA alignment/signal tests.
These predate later detector changes. Internal development suites were subsequently removed.
The final one-time browser run had five passes and one failure retrieving an SSE response body;
the failed check's later assertions were not verified. Judge-facing `scripts/validate_live.py`,
the live GPU stress script, and the dataset evaluator remain. Live validation passed on native
CUDA on 2026-10-14: two dragging-pace findings in about 16.7 seconds, with all stages and the
uploaded audio hash confirmed. This verifies one API workflow, not full accuracy. Internal suites
and browser evidence were moved to a separate local QA Lab workspace.

Docker pins base-image digests, runtime versions, and dependency lockfiles. It downloads the MMS
checkpoint and dataset release and verifies both checksums. A Linux Docker build and local launch
have been checked. Native installation on a fresh VM and Windows or macOS deployment still need verification.
The new CUDA image built successfully from locked dependencies and verified asset downloads.
Native and CUDA Docker reports for one identical uploaded gold clip were byte-identical, with
zero score and word-boundary differences. Both container homepage and setup guide returned HTTP
200, and its real demo analysis passed. This does not prove every clip or CPU/CUDA byte identity.

A native CUDA API processed a 600-second repeated-reference fixture with all 1,152 words aligned
in 32.7 seconds. Peak server RSS was approximately 2.51 GiB. Sampled total GPU memory reached
3,770 MiB, including unrelated applications. A short genuine excerpt also completed normative-mode
analysis. These are real API uploads, not proof of new-speaker accuracy or hardware microphone capture.

The source build regenerated all 186 recordings across six texts on CUDA in 94.3 seconds.
All 12 original source hashes matched their recorded checksums, and every regenerated recording
matched its published audio hash. Calibration changed with the detector revision; audio and
dataset v1 metadata were preserved. The rebuild output was kept separate from the release.

The report renders to four A4 pages with the documented Markdown and Chromium commands.
Submission work still includes the human recordings and a published 3 to 10 minute demonstration
video. The video script must use the measured results above, including the failed targets.

## References

- [Torchaudio forced alignment tutorial](https://docs.pytorch.org/audio/2.6.0/tutorials/ctc_forced_alignment_api_tutorial.html).
- [Praat manual](https://www.fon.hum.uva.nl/praat/manual/).
- Dataset source and rights URLs in `data/dataset/manifest.json`.
- Scoring and evaluation code in `src/speech_delivery/analysis/` and `src/speech_delivery/evaluation/`.
