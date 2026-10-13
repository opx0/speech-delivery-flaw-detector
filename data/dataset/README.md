# Speech delivery benchmark dataset v1

A benchmark for comparing speech delivery and testing timestamped flaw detection.

## Overview

The dataset contains 186 recordings in 16 kHz, 16-bit mono FLAC format. Source recordings come
from public-domain LibriVox releases hosted on the Internet Archive. The manifest includes
transcripts, alignments, audio hashes, and labels for injected flaw regions.

Download the recordings from [the dataset v1 release](https://github.com/opx0/speech-delivery-flaw-detector/releases/tag/dataset-v1).
Follow [the download and checksum instructions](../../README.md#dataset). Git tracks the metadata
and this README, but ignores extracted audio and the local archive. The release archive's
documentation is a snapshot from publication. This README reflects the current code.

```
data/dataset/
├── manifest.json       # Dataset catalog with text transcripts, alignments, and ground truth flaw bounds
├── calibration.json    # Calibrated normative tolerance bands (p10 to p90) from natural human readers
├── README.md           # Dataset documentation and guide for judges
└── audio/              # 186 mono 16 kHz FLAC audio recordings
    ├── <text_id>.gold.flac             # Master orator reference reading
    ├── <text_id>.reader-<name>.flac    # Alternative fluent human readings
    ├── <text_id>.control.flac          # Level 0 resynthesis control (neutral acoustic baseline)
    ├── <text_id>.<kind>-l<1..4>.flac   # Single-flaw injections across severity levels 1 through 4
    ├── <text_id>.mix-<name>.flac       # Compound multi-flaw injections
    └── <text_id>.shifted-<name>.flac   # Pitch/formant shifted copies for speaker invariance testing
```

---

## Source texts and provenance

| Text ID | Title | Speaker | Category | Source Archive URL | License |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `new-colossus` | The New Colossus | ALG | Poetry | `archive.org/details/newcolossus_1207_librivox` | Public Domain |
| `ozymandias` | Ozymandias | ADD | Poetry | `archive.org/details/ozymandias_librivox` | Public Domain |
| `gettysburg-address` | The Gettysburg Address | AMB | Speech | `archive.org/details/gettysburgaddress_150anniv_1311_librivox` | Public Domain |
| `declaration-of-independence` | Declaration of Independence | Michael Scherer | Historical Document | `archive.org/details/declaration_independence_librivox` | Public Domain |
| `coming-of-the-end` | The Coming of the End | Ian King | Narrative Prose | `archive.org/details/short_poetry_043_librivox` | Public Domain |
| `dover-beach` | Dover Beach | WT | Poetry | `archive.org/details/short_poetry_001_librivox` | Public Domain |

Every source record includes cryptographic SHA-256 hashes and URL-verified public-domain rights declarations in `manifest.json`.

---

## Flaw types and severity levels

The values below come from `src/speech_delivery/dataset/levels.py`. Each row lists levels 1 through 4.

| Flaw | Injection parameters |
| --- | --- |
| `rush` | Rate factors 1.15, 1.30, 1.50, 1.80 |
| `drag` | Rate factors 0.87, 0.77, 0.67, 0.55 |
| `monotone` | Pitch excursion retained 0.70, 0.45, 0.25, 0.05 |
| `hesitation` | Inserted silence 0.25, 0.50, 0.90, 1.50 seconds |
| `pause_collapse` | Pause retained 0.70, 0.45, 0.20, 0.00 |
| `energy_fade` | Final loss 3, 6, 10, 16 dB across the final 60% of the passage |

These injection settings are not the detector's decision thresholds. The manifest labels each
affected passage. Three natural readers belong to calibration and three to the test split.

---

## Verification and inspection

To load and inspect the dataset programmatically:

```python
from pathlib import Path
from speech_delivery.library import Library

# Load the dataset catalog
lib = Library.load(Path("data/dataset"))
print(f"Loaded {len(lib.manifest.clips)} clips across {len(lib.manifest.texts)} speeches.")

# audio() verifies the clip's SHA-256 before decoding
gold_clip = lib.gold_for("gettysburg-address")
audio = lib.audio(gold_clip.id)
print(f"Gold clip duration: {audio.duration_s:.2f} seconds")
```

To run the seven-metric evaluation benchmark against this dataset:

```bash
uv run --no-sync python -m speech_delivery.evaluation
```
