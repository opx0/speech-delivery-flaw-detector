# Speech Delivery Benchmark Dataset (v1)

A benchmark dataset for contrastive speech analytics, temporal flaw grounding, and oratorical scoring.

## Overview

This dataset contains **186 audio recordings** (16 kHz, 16-bit mono FLAC) and verifiable ground truth alignments for evaluating contrastive speech delivery and acoustic flaw detection algorithms. All source recordings originate from verified public-domain LibriVox releases hosted on the Internet Archive.

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

## Canonical Speeches and Provenance

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

## Flaw Taxonomy and Severity Levels

The dataset injects six atomic delivery flaw types across levels 1 (subtle departure) to 4 (severe delivery breakdown):

1. **`rush` (Cadence):** Syllable rate accelerated by 1.35x to 2.4x above baseline.
2. **`drag` (Cadence):** Syllable rate slowed down to 0.70x to 0.40x of baseline.
3. **`monotone` (Tone):** Pitch standard deviation collapsed below 0.25 semitones.
4. **`hesitation` (Pauses):** Unnatural silent pauses exceeding 1.8s inserted mid-clause.
5. **`pause_collapse` (Pauses):** Essential punctuation pauses between sentences reduced below 0.2s.
6. **`energy_fade` (Volume):** Vocal energy decay exceeding 2.0 standard deviations at clause terminals.

---

## Verification and Inspection

To load and inspect the dataset programmatically:

```python
from pathlib import Path
from speech_delivery.library import Library

# Load dataset and verify SHA-256 integrity
lib = Library.load(Path("data/dataset"))
print(f"Loaded {len(lib.manifest.clips)} clips across {len(lib.manifest.texts)} speeches.")

# Inspect Gettysburg Address gold baseline
gold_clip = lib.gold_for("gettysburg-address")
audio = lib.audio(gold_clip.id)
print(f"Gold clip duration: {audio.duration_s:.2f} seconds")
```

To run the seven-metric evaluation benchmark against this dataset:

```bash
uv run --no-sync python -m speech_delivery.evaluation
```
