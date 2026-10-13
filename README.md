# speech-delivery-flaw-detector

Compares a speech against a gold-standard delivery of the same text, then pinpoints where and
why the delivery deviates, with timestamps and acoustic causes.

The dashboard overlays your pitch, pace, energy, and pauses on the gold delivery's curves. It
marks the regions where your delivery departs from the gold curves. Each marked region links
to an explanation, for example "Rushed pacing, 00:14 to 00:18, 4.7 words/s against an expected
2.6 words/s".

## Status

Updated on 2026-10-12. The React dashboard has been redesigned as a light, transcript-first
speech review workspace with reference audition, waveform navigation, acoustic charts,
timestamped evidence, and editable rubric weights. See [the UI design references](docs/UI_DESIGN.md).
The backend, dataset builder, and evaluation code are present locally. Much of this work remains
uncommitted, and submission verification is incomplete.

The following results are historical checks. They predate the final UI and packaging edits:

| Earlier check | Recorded result |
| --- | --- |
| Python formatting and lint | Passed |
| Python strict type checking | Passed with no errors or warnings |
| Python tests | 157 passed |
| Frontend type checking and contract fixture validation | Passed |
| Frontend tests | 8 passed |
| Production frontend build | Passed |
| Dataset integrity | 186 audio files decoded and their SHA-256 hashes verified across 6 texts |

The local dataset contains 6 gold recordings, 6 natural readers, 6 controls, 156 flawed
recordings, and 12 speaker-shifted recordings. The library exposes 42 demo clips.

Remaining work:

- Run the full seven-metric evaluation. The recorded quick evaluation misses the recall and
  natural-reader false-positive gates; see `docs/TECHNICAL_REPORT.md` for the subset results.
- Complete browser verification of the redesigned dashboard. A browser run displayed the new
  welcome page and submitted a real demo, but timed out during alignment before a report appeared.
- Add the planned human held-out recordings, supplied by the owner.
- Verify the Docker build and deployment.
- Validate the technical report's six-page limit and record and publish the demo video.
- Review and commit the implementation, then publish the dataset or link to its public download.

Further tests and clean-environment runs are paused at the owner's request. The latest runtime
pins, model provisioning, Docker changes, and final UI edits have not been exercised.

## Launch the demo

The dataset and transcripts are included in `data/dataset/`. Model provisioning is part of setup;
the judge does not need the GitHub Actions cache or an API key.

### Docker

From the project root, run:

```bash
docker compose up --build
```

Open **http://localhost:8000**. Docker installs from the lockfiles, builds the React UI, downloads
and verifies the pinned MMS model, and packages the provided dataset. The first build needs
internet access and downloads approximately 1.2 GB of model weights.

### Native Linux

Use Python 3.12.14, uv 0.13.0, Node.js 26.11.1, npm 12.2.0, FFmpeg, and espeak-ng.
Follow [the native Linux guide](docs/LOCAL_SETUP.md#native-linux-launch). It documents the direct
`uv`, `npm`, model download, and Python server commands. Native launch does not need a Makefile
or setup script. The default address is **http://127.0.0.1:8000**.

Choose **Explore examples**, select **The New Colossus**, and analyze **Rushed pacing**.
The guide also includes a direct command-line analysis example.

See [the complete launch guide](docs/LOCAL_SETUP.md) for configuration, offline provisioning,
development modes, and verification status. Docker and native clean-environment launch remain
unverified. [A disposable-environment procedure](docs/CLEAN_ENVIRONMENT.md) is documented for
when verification resumes.

## How it works

The system has two modes. The mode follows from the transcript you upload.

| Mode | When it applies | What the speech is compared with |
| --- | --- | --- |
| Contrast | The transcript matches a text in the dataset library. | The gold delivery of the same text, aligned word by word. |
| Normative | The transcript is not in the library, or the speech is unscripted. | Percentile bands learned from the gold and natural-reader clips. Findings are marked lower confidence. |

Scores cover four delivery axes: cadence, tone, pauses, and volume. Content quality is out of
scope because the text is identical by construction in contrast mode.

Pitch is normalized to each speaker's median. Energy is relative to their 95th-percentile
speech-frame energy. Comparisons therefore measure delivery changes rather than raw pitch or gain.

## Repository layout

| Path | Contents |
| --- | --- |
| `src/speech_delivery/contract/` | The data contract: pydantic models for every payload. |
| `contract/schema/` | The JSON Schema bundle exported from the models. |
| `contract/fixtures/` | Synthetic example payloads for every contract root. |
| `web/` | The TypeScript dashboard and the types generated from the schema. |
| `data/dataset/` | Provided audio, transcripts, alignment labels, and calibration. |
| `scripts/` | Contract schema and fixture export. |
| `docs/` | Launch guide, UI references, technical report, and video script. |
| `tests/` | Python tests. |

## Develop

Runtime and dependency versions are pinned in `.python-version`, `.node-version`,
`web/package.json`, `uv.lock`, and `web/package-lock.json`. Docker base images include immutable
digests. Native settings are documented in `.env.example`.

1. Install locked dependencies with `uv sync --locked` and `npm --prefix web ci`.
2. Run `npm run dev` in `web/` while the API is running for real-backend development. Use
   `npm run dev:mock` only for an explicitly labeled fixture preview.
3. When verification resumes, Python checks are direct `uv run --no-sync` commands for Ruff,
   Pyright, and pytest. Frontend checks use `npm run typecheck`, `npm run validate:fixtures`,
   `npm test`, and `npm run test:e2e` in `web/`. CI lists these commands explicitly.
4. After changing a contract model, regenerate its schema, fixtures, and TypeScript types:

   ```bash
   uv run --no-sync python scripts/export_contract.py
   npm --prefix web run contract:ts
   ```

## Licenses

The code is MIT licensed. See `LICENSE`. Dataset labels and derived audio will be CC BY 4.0.
Each source recording keeps its public-domain status, and its provenance and rights evidence are
recorded in the dataset manifest.
