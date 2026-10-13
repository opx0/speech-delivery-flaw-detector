# Project requirements

This record preserves the requirements agreed in the recovered project discussion. It describes
the intended scope, not proof that every requirement has been implemented or verified.
See [the README](../README.md#status) for the current status.

## Speech analysis

- Compare recordings of the same text against a gold recording.
- Use normative mode for transcripts outside the library. Compare these recordings against
  calibrated percentile bands and mark the findings as lower confidence.
- Use forced alignment to map transcript words to audio timestamps.
- Normalize pitch relative to each speaker's median and energy relative to their speech energy.
- Score cadence, tone, pauses, and volume from 0 to 100, with equal default weights.
  Let users change the weights in the dashboard. Do not score content quality.
- Keep scoring deterministic and derive explanations from measured acoustic differences.
- Compute evidence on 10 ms frames with about 250 ms smoothing. Snap flaw regions to word
  boundaries and require a minimum duration of about 0.5 seconds.
- Include the affected words, start and end timestamps, and measured differences in each explanation.
- Extract vocal clarity measurements as supporting evidence. Do not inject artificial mumbling.

## Dataset

- Use verified public-domain source recordings and keep per-recording source and rights evidence.
- Produce six injected flaw types: rush, drag, monotone, hesitation, pause collapse, and energy fade.
- Give each flaw four severity levels with recorded physical parameters and word-aligned region labels.
  Include mixed-flaw clips.
- Include a level-zero control processed through the same pipeline with neutral parameters.
- Include independent good readers to measure natural variation. The original target was three
  texts with three readers each.
- Keep human recordings separate from calibration. The original held-out target was 16 clips:
  two speakers, two texts, and one clean plus three flawed readings per speaker and text.
- Publish audio, transcripts, alignment labels, and dataset documentation through a public link
  in the README. The original challenge accepts GitHub or a public Google Drive link.
- Use MIT for code and CC BY 4.0 for labels and derived audio. Source recordings retain their
  public-domain status.

## Dashboard and deployment

- Accept audio and transcript uploads. Show analysis progress while jobs run.
- Display participant and gold feature curves, marked flaw regions, and explanations.
- Let users click a flaw region to seek the audio player to its timestamp.
- Use FastAPI and a Vite TypeScript frontend, with one Docker image for deployment.
- Limit uploads to 50 MB and recordings to 10 minutes. Decode uploads to 16 kHz mono with FFmpeg.
  Process uploads in temporary storage and delete them after processing.
- Pin dependencies, model assets, and dataset generation settings for repeatable setup.

## Evaluation and submission

Report sample sizes and spread for these measurements:

- Region precision and recall at an intersection-over-union threshold of 0.5.
- Median flaw-boundary error in milliseconds.
- Flaw-type classification accuracy.
- Severity monotonicity using Spearman correlation across levels zero through four.
- False-positive rate on independent good readers.
- Score invariance for pitch- and formant-shifted good recordings, with a stated tolerance.
- Output reproducibility across three runs and between local and Docker execution.

Use the human-recorded set only for held-out evaluation. Submit the code and documentation,
the public dataset, and a working dashboard. Keep the technical report within six pages.
Publish a 3 to 10 minute YouTube video that demonstrates dataset construction, stress tests,
and timestamped delivery findings.
