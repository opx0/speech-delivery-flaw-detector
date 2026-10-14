# speech-delivery-flaw-detector

Compare a speech with a gold-standard recording of the same text. The app identifies delivery
differences and explains their acoustic causes with timestamps.

The dashboard plots your pitch, pace, energy, and pauses alongside the gold recording's curves.
It marks differences and links each region to an explanation. For example, "Rushed pacing,
00:14 to 00:18, 4.7 words per second against an expected 2.6 words per second".

## Status

Updated on 2026-10-14. The React dashboard lets you review the transcript, listen to the gold
recording, navigate the waveform, and inspect acoustic charts and timestamped findings.
You can also change the scoring weights. The Amigo-inspired layout uses top navigation,
serif headings, and a transcript panel with an attached audio timeline.
See [the UI design references](docs/UI_DESIGN.md).
The repository includes the backend, dataset builder, and evaluation code. Submission checks
remain incomplete.

Completed checks:

These are historical records from earlier revisions, not verification of the latest code.
Internal development test suites are no longer distributed; live evaluation tools remain.

| Check | Recorded result |
| --- | --- |
| Python formatting and lint | Passed |
| Python strict type checking | Passed with no errors or warnings |
| Python tests | 158 passed |
| Frontend type checking and contract fixture validation | Passed |
| Frontend tests | 13 passed, including shared setup-guide checks |
| Real browser workflow | Real review, playback, export, mobile navigation, and failure states covered by Chromium tests |
| GPU alignment and signal tests | 9 passed |
| Production frontend build | Passed |
| Dataset integrity | Decoded 186 audio files across 6 texts and verified their SHA-256 hashes |
| Technical report | Rendered to 4 A4 pages, below the 6-page limit |

The local dataset contains 6 gold recordings, 6 natural-reader recordings, 6 controls, 156 flawed
recordings, and 12 speaker-shifted recordings. The library offers 42 demo clips.

Remaining work:

- Improve detection accuracy. The latest full GPU evaluation with a separate recalibration
  candidate measured 80.31% precision and 21.98% recall. Two of three held-out natural readers
  received false-positive findings (66.67%). Recall and false-positive
  rate fail their targets. See [the technical report](docs/TECHNICAL_REPORT.md).
- Add the [held-out human recordings](docs/HUMAN_RECORDINGS.md).
- Add three independent reader recordings to reach the original three-readers-per-text target.
- Complete hardware microphone capture and human listening/transcript-quality review.
- Verify native installation on a fresh VM and deployment on Windows or macOS.
- Record and publish the [demo video](docs/VIDEO_SCRIPT.md).

The CUDA Docker build and live launch passed. The homepage and setup guide returned HTTP 200,
and the library contained 6 texts and 42 demos. A sampled native/CUDA Docker upload produced
byte-identical reports. Native CUDA also passed a 600-second API stress check and normative-mode
upload. A source rebuild regenerated all 186 audio files with matching published hashes.
These checks do not establish full detector accuracy, microphone capture, or cross-platform support.
See [the complete verification record](docs/evaluation/VERIFICATION.md) for measured outcomes,
configuration differences, and outstanding checks.

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
Follow [the complete setup guide](docs/LOCAL_SETUP.md) for cloning, Docker CPU, native CPU,
native NVIDIA GPU, parameters, and troubleshooting. The app renders that same guide at
[http://localhost:8000/docs](http://localhost:8000/docs), with path selection and copyable commands.

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
| `scripts/` | Live validation, stress/reproducibility tools, and contract export. |
| `docs/` | Launch guide, UI references, technical report, and video script. |

## Develop

The repository pins runtime and dependency versions in `.python-version`, `.node-version`,
`web/package.json`, `uv.lock`, and `web/package-lock.json`. Docker base images use immutable
digests. See `.env.example` for native settings.

1. Install locked dependencies with `uv sync --locked` and `npm --prefix web ci`.
2. Start the API, then run `npm run dev` in `web/`. Use `npm run dev:mock` to preview fixture data.
3. Static build tooling remains available through Ruff, Pyright, and `npm run typecheck`.
   Internal unit/debug/UI test suites and their runners were removed at the owner's request.
   Use the live validation commands below to exercise the actual running application.
4. After changing a contract model, regenerate its schema, fixtures, and TypeScript types:

   ```bash
   uv run --no-sync python scripts/export_contract.py
   npm --prefix web run contract:ts
   ```

## Live validation for users and judges

For a native CUDA demo session with one server and categorized terminal output:

```bash
.cache/gpu-venv/bin/python scripts/start_demo.py
```

Open http://localhost:8000. The GPU API also serves the built UI; no frontend server is needed.
The launcher appends categorized logs to `runs/demo.log`; use `tail -f runs/demo.log` in a second
terminal. Ctrl+C stops the session. It does not run tests, submit audio, or enable mock mode.
This launcher starts no Vite server.

### Report-only run history

Open **Run history** (http://localhost:8000/history) to inspect saved analyses, including failures.
Each run preserves its input hash and transcript, submitted options, effective weights, full
calibration snapshot, runtime device, server stage events, and original report. Export run evidence
as JSON for later inspection. Scores are delivery scores, not detection-accuracy percentages.

The local journal is `runs/history.sqlite3` (`--history` on the API CLI changes it). Uploaded audio
is still temporary and removed after analysis; saved history intentionally has no playback. Reports
and transcripts may be sensitive: the journal is unencrypted, local, and ignored by Git. There is
no account/authentication layer; keep the API bound to localhost or on a trusted network.
Earlier runs are not backfilled. Rejected uploads/options are not admitted analysis runs and are
not journaled. This is run accountability, not a log of human visual sign-off or
independent evaluation. Compose preserves the journal in its named `speech-delivery-runs` volume.

Start the native CUDA API or the opt-in CUDA Docker app first, then run from the checkout:

```bash
.cache/gpu-venv/bin/python scripts/validate_live.py --url http://127.0.0.1:8000
```

This uploads a real dragging-pace demo through the API, displays live progress, confirms the
uploaded audio hash and actual CUDA model device, and saves findings to `runs/live-validation/`.
Workflow success and expected-flaw detection are reported separately. It exits with code 1 on
a failed workflow or missing expected demo flaw. On 2026-10-14, this live workflow passed on
native CUDA (`cuda:0`): all five stages completed, the audio hash matched, and two dragging-pace
findings appeared in approximately 16.7 seconds. This is one demo, not a full accuracy benchmark.

For your own recording and the words you actually spoke:

```bash
.cache/gpu-venv/bin/python scripts/validate_live.py \
  --audio your-recording.wav --transcript your-transcript.txt
```

Also retained: the full dataset evaluator, `scripts/verify_gpu.py --stress` for the live ten-minute
API limit, and `scripts/compare_reports.py` for native/container reports. These are explicit
evaluation tools, not internal code or UI test suites. Nothing runs automatically during launch.
Follow [the browser walkthrough](docs/LOCAL_SETUP.md#verify-a-first-analysis) to inspect the UI manually.

Internal development suites and historical browser evidence live separately in a QA Lab workspace
outside this repository. They are not submission dependencies and do not run during setup or live
validation.

## Licenses

The code uses the MIT license. See `LICENSE`. Dataset labels and project-derived audio use
CC BY 4.0; see [the dataset license](data/dataset/LICENSE). Each source recording keeps its public-domain status.
The dataset manifest records each recording's source and rights evidence.
