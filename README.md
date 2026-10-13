# speech-delivery-flaw-detector

Compare a speech with a gold-standard recording of the same text. The app identifies delivery
differences and explains their acoustic causes with timestamps.

The dashboard plots your pitch, pace, energy, and pauses alongside the gold recording's curves.
It marks differences and links each region to an explanation. For example, "Rushed pacing,
00:14 to 00:18, 4.7 words per second against an expected 2.6 words per second".

## Status

Updated on 2026-10-13. The React dashboard lets you review the transcript, listen to the gold
recording, navigate the waveform, and inspect acoustic charts and timestamped findings.
You can also change the scoring weights. See [the UI design references](docs/UI_DESIGN.md).
The repository includes the backend, dataset builder, and evaluation code. Submission checks
remain incomplete.

Completed checks:

| Check | Recorded result |
| --- | --- |
| Python formatting and lint | Passed |
| Python strict type checking | Passed with no errors or warnings |
| Python tests | 158 passed |
| Frontend type checking and contract fixture validation | Passed |
| Frontend tests | 8 passed |
| Real browser workflow | 3 Chromium tests passed against both the GPU API and the Docker app |
| GPU alignment and signal tests | 9 passed |
| Production frontend build | Passed |
| Dataset integrity | Decoded 186 audio files across 6 texts and verified their SHA-256 hashes |
| Technical report | Rendered to 4 A4 pages, below the 6-page limit |

The local dataset contains 6 gold recordings, 6 natural-reader recordings, 6 controls, 156 flawed
recordings, and 12 speaker-shifted recordings. The library offers 42 demo clips.

Remaining work:

- Improve detection accuracy. The full GPU evaluation measured 80.34% precision and 20.26% recall.
  All three held-out natural readers received false-positive findings. Recall and false-positive
  rate fail their targets. See [the technical report](docs/TECHNICAL_REPORT.md).
- Add the [held-out human recordings](docs/HUMAN_RECORDINGS.md).
- Verify native installation on a fresh VM and deployment on Windows or macOS.
- Record and publish the [demo video](docs/VIDEO_SCRIPT.md).

The local Docker build and launch passed. The homepage returned HTTP 200, and `/api/library`
returned 6 texts and 42 demos. The full browser workflow passes on the native GPU backend and
the production Docker app.

## Dataset

Dataset v1 is available in [the GitHub Release](https://github.com/opx0/speech-delivery-flaw-detector/releases/tag/dataset-v1).
The repository keeps the manifest, calibration, and dataset README. Download the audio separately
for native use. Docker downloads and verifies the release archive during its build.
Older Git commits still contain the audio, so a full clone includes that history.
Use `git clone --depth 1` to download only the current files.

For native use, run these commands from the project root to download, verify,
and extract the audio:

```bash
mkdir -p data
curl --fail --location \
  -o data/speech_delivery_dataset_v1.tar.gz \
  https://github.com/opx0/speech-delivery-flaw-detector/releases/download/dataset-v1/speech_delivery_dataset_v1.tar.gz

echo "ca5c16fa9f0503c9f13b60dfdb1f0f2f5322581ff7a51a2bb3e111d91a0cb6da  data/speech_delivery_dataset_v1.tar.gz" \
  | sha256sum --check

tar -xzf data/speech_delivery_dataset_v1.tar.gz -C data dataset/audio
```

The archive contains a `dataset/` directory. The command extracts its 186 recordings into
`data/dataset/audio/` and keeps the repository's manifest, calibration, and documentation.

## Launch the demo

Setup downloads the alignment model. You do not need the GitHub Actions cache or an API key.

### Docker

From the project root, run:

```bash
docker compose up --build
```

Open http://localhost:8000. Docker installs dependencies from the lockfiles and builds the React UI.
It downloads and verifies the pinned MMS alignment model and dataset release.
The first build needs internet access to download approximately 1.2 GB of model weights and
192 MB of dataset archive data.

### Native Linux launch

Use Python 3.12.14, uv 0.13.0, Node.js 26.11.1, npm 12.2.0, FFmpeg, and espeak-ng.
Follow [the native Linux guide](docs/LOCAL_SETUP.md#native-linux-launch) for dependency installation,
model download, and Python server commands. The default address is http://127.0.0.1:8000.

Choose **Explore examples**, select **The New Colossus**, and analyze **Dragging pace**.
The guide also includes a direct command-line analysis example.

See [the complete launch guide](docs/LOCAL_SETUP.md) for configuration, offline setup,
development modes, and verification status. The guide includes
[optional NVIDIA GPU setup](docs/LOCAL_SETUP.md#optional-nvidia-gpu-execution).
Follow [the clean-environment procedure](docs/CLEAN_ENVIRONMENT.md) to verify another host.

## How it works

The app chooses one of two modes based on the transcript you upload.

| Mode | When it applies | What the speech is compared with |
| --- | --- | --- |
| Contrast | The transcript matches a text in the dataset library. | The gold delivery of the same text, aligned word by word. |
| Normative | The transcript is not in the library, or the speech is unscripted. | Percentile bands learned from the gold and natural-reader clips. The app marks these findings as lower confidence. |

Scores cover cadence, tone, pauses, and volume. The app does not score content quality.
In contrast mode, both recordings use the same text.

The app normalizes pitch to each speaker's median and energy to their 95th-percentile
speech-frame energy. This lets it compare delivery changes rather than raw pitch or gain.

## Repository layout

| Path | Contents |
| --- | --- |
| `src/speech_delivery/contract/` | Pydantic models for every data payload. |
| `contract/schema/` | The JSON Schema bundle exported from the models. |
| `contract/fixtures/` | Synthetic example payloads for every contract root. |
| `web/` | The TypeScript dashboard and the types generated from the schema. |
| `data/dataset/` | Benchmark audio, transcripts, alignment labels, and calibration. |
| `scripts/` | Contract schema and fixture export. |
| `docs/` | Launch guide, UI references, technical report, and video script. |
| `tests/` | Python tests. |

## Develop

The repository pins runtime and dependency versions in `.python-version`, `.node-version`,
`web/package.json`, `uv.lock`, and `web/package-lock.json`. Docker base images use immutable
digests. See `.env.example` for native settings.

1. Install locked dependencies with `uv sync --locked` and `npm --prefix web ci`.
2. Start the API, then run `npm run dev` in `web/`. Use `npm run dev:mock` to preview fixture data.
3. Run Python checks with `uv run --no-sync` commands for Ruff,
   Pyright, and pytest. Frontend checks use `npm run typecheck`, `npm run validate:fixtures`,
   `npm test`, and `npm run test:e2e` in `web/`. CI lists these commands.
4. After changing a contract model, regenerate its schema, fixtures, and TypeScript types:

   ```bash
   uv run --no-sync python scripts/export_contract.py
   npm --prefix web run contract:ts
   ```

## Licenses

The code uses the MIT license. See `LICENSE`. The planned license for dataset labels and derived
audio is CC BY 4.0. Each source recording keeps its public-domain status.
The dataset manifest records each recording's source and rights evidence.
