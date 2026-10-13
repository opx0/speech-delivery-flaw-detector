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
