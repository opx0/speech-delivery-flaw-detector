"""Turn audio plus a transcript into words, features, flaw regions and a report.

Modules, in dependency order:

- `align`: audio and transcript to a `WordAlignment`.
- `features`: audio and alignment to `RecordingFeatures`.
- `signal`: the two above in one call, giving a `Recording`.
- `bands`: normative percentile bands learned from reference recordings.
- `compare`: two recordings, or one recording and bands, to flaw regions and scores.
- `explain`: a measured deviation to a human-readable `Explanation`.
- `analyzer`: the `Analyzer` the API runs, wiring all of the above to a `Library`.
"""
