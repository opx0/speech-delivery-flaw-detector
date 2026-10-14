# Record the held-out speech clips

These recordings test the detector on new human speech. Keep them out of calibration and
dataset-generation tuning. The planned set contains 16 clips.

## Recording plan

Use two speakers with different voices. Each speaker reads the exact library transcript for
The New Colossus and Ozymandias. For each text, record these four takes:

- A fluent reading without intentional flaws.
- A reading with a rushed passage.
- A reading with reduced pitch variation in a passage.
- A reading with a hesitation in the middle of a phrase.

Choose a passage before recording each flawed take. Keep the rest of the reading fluent.
Do not synthesize these recordings or change their timing afterward.

## Save the clips and labels

1. Use the same microphone position and gain across one speaker's takes. Record in a quiet room.
2. Read the transcript from `data/dataset/manifest.json`, including every word.
3. Save WAV or FLAC audio. Use names such as `speaker-a.new-colossus.clean.wav` and
   `speaker-a.new-colossus.rush.wav`.
4. Note the speaker ID, text ID, take type, and affected words. Listen to each flawed take and
   label the start and end times of the intentional deviation.
5. Keep the clips under `data/work/human-held-out/` until they have been reviewed and added to
   a new dataset version with test-only labels. This directory is ignored by Git.

The project still needs these recordings. Existing LibriVox readers and pitch-shifted controls
do not fulfill this requirement. Do not report human-held-out evaluation results before the
recordings and labels exist.

## Import tooling (implemented, not yet verified)

The CUDA-only importer creates a **new** dataset directory; it never changes dataset v1 or
its calibration. Human takes are always test-only. Write a JSON array beside the original
recordings. Each item contains:

```json
{
  "clip_id": "human-a.new-colossus.rush",
  "speaker_id": "human-a",
  "speaker_sex": "unspecified",
  "text_id": "new-colossus",
  "take": "rush",
  "audio": "speaker-a.new-colossus.rush.wav",
  "license": "original-recording",
  "permission_to_publish": true,
  "flaws": [{
    "kind": "rush", "level": 3, "start": 1.0, "end": 2.0,
    "words": {"first": 1, "last": 3}, "injection": null
  }]
}
```

The values above illustrate the format; replace them with genuine permissions and manually
reviewed labels. Do not use these example timestamps as ground truth. Clean takes have
`"take": "clean"` and `"flaws": []`. Flawed takes use `rush`, `monotone`, or `hesitation`.
Word indices are zero-based and refer to the library transcript.

Once the actual 16 takes are supplied, the intended command is:

```bash
SPEECH_DEVICE=cuda TORCH_HOME="$PWD/models/torch" CUBLAS_WORKSPACE_CONFIG=:4096:8 \
  .cache/gpu-venv/bin/python -m speech_delivery.dataset.human \
  data/work/human-held-out/takes.json --dataset data/dataset \
  --out data/dataset-v2 --version 2
```

The default requires all two-speaker/two-text/four-take combinations. `--allow-partial` permits
work-in-progress imports but marks the recording plan incomplete. The importer refuses absent
publication permission, synthetic injection parameters, duplicate takes, and existing output
directories. Speaker identity and permission metadata are retained in `human-held-out.json`.
Evaluation reports human results separately under `details.human_held_out`; missing human data
is explicitly unavailable, never a successful evaluation. No import or evaluation has been run
for this new tooling yet.
