# Set up speech delivery

Choose a launch path, clone the repository, and follow its steps in order. Docker handles the
CPU environment and asset downloads. Native CPU and GPU instructions target Debian or Ubuntu
Linux. No API key, account, or GitHub Actions cache is required.

The in-app setup guide renders this file. Comments after section headings select the relevant
instructions for each runtime. Edit this Markdown file to update both guides.

## Clone the repository
<!-- setup: all; step -->

Install [Git](https://git-scm.com/downloads) first if it is missing. Clone the public repository:

```bash
git clone --depth 1 https://github.com/opx0/speech-delivery-flaw-detector.git
cd speech-delivery-flaw-detector
```

Run the remaining commands from this directory. A shallow clone omits older commits that
contained dataset audio. The checkout includes transcripts, word alignments, and calibration.
The recordings come from the versioned dataset release.

## Docker launch
<!-- setup: docker; step -->

Install [Docker Engine and Compose](https://docs.docker.com/engine/install/) on Linux, or
[Docker Desktop](https://docs.docker.com/desktop/) on Windows or macOS. Check the installation:

```bash
docker --version
docker compose version
```

Allow about 6 GB of Docker memory and at least 8 GB of free disk space as a starting point.
The image uses `linux/amd64`; ARM hosts run it through emulation. The first build needs internet
access for dependencies, approximately 1.2 GB of model weights, and a 192 MB dataset archive.

```bash
docker compose up --build
```

The build installs pinned dependencies, builds the dashboard, downloads the model and dataset,
and verifies both SHA-256 checksums. Wait for the server to report that it is running, then
open http://localhost:8000. The Docker image runs on CPU and includes its own model and dataset.
It does not need your host Python, Node, model cache, or extracted audio.

If port 8000 is occupied, choose another host port:

```bash
PORT=8080 docker compose up --build
```

In Windows PowerShell, use:

```powershell
$env:PORT = "8080"
docker compose up --build
```

The container still listens on port 8000. The example above opens at http://localhost:8080.
To stop the application, press Ctrl+C and then run:

```bash
docker compose down
```

## Check the GPU
<!-- setup: cuda; step -->

The native GPU path requires Linux, an NVIDIA GPU, and a working NVIDIA driver. Check the driver:

```bash
nvidia-smi
```

The command must list your GPU. If it does not, install the appropriate
[NVIDIA driver](https://www.nvidia.com/en-us/drivers/) before continuing. The verified hardware
is an RTX 3050 Laptop GPU with 4 GB of VRAM. Other applications also consume VRAM.
The CUDA environment needs several additional gigabytes of disk space for its packages.

MMS model inference runs on CUDA. Alignment decoding and acoustic feature extraction stay on CPU.
These instructions do not enable GPU execution inside the standard Docker image.

An opt-in NVIDIA container configuration is also available in `compose.gpu.yml`. It requires
Linux and [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
configured for Docker:

```bash
docker compose -f compose.gpu.yml up --build
```

This selects the `cuda` Docker target with PyTorch and torchaudio 2.6.0+cu124, requests one GPU,
and sets `SPEECH_DEVICE=cuda`. It does not fall back to CPU inference. This new container path
passed Linux construction and live API checks on 2026-10-14; the standard `compose.yml` remains CPU-only.

CPU and CUDA Compose configurations use separate image tags (`speech-delivery-flaw-detector:cpu`
and `speech-delivery-flaw-detector:cuda`) so building one does not overwrite the other's image.

## Native Linux launch
<!-- setup: cpu cuda; step -->

Use Bash or Zsh. Install the system tools on Debian or Ubuntu:

```bash
sudo apt-get update
sudo apt-get install -y curl git ca-certificates ffmpeg espeak-ng libgomp1 libsndfile1
```

Install uv 0.13.0 and add its installation directory to the current shell:

```bash
curl --proto '=https' --tlsv1.2 -LsSf https://astral.sh/uv/0.13.0/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
uv --version
```

Install [nvm 0.40.3](https://github.com/nvm-sh/nvm/tree/v0.40.3) if nvm is not already installed.
Load nvm, then install the repository's Node version and npm 12.2.0:

```bash
curl --fail --location https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
export NVM_DIR="${NVM_DIR:-$([ -z "${XDG_CONFIG_HOME-}" ] && printf %s "$HOME/.nvm" || printf %s "$XDG_CONFIG_HOME/nvm")}"
. "$NVM_DIR/nvm.sh"
nvm install
nvm use
npm install --global npm@12.2.0
```

The project pins Node 26.11.1 in `.nvmrc` and `.node-version`. You can also install that exact
version from [the Node distribution directory](https://nodejs.org/dist/v26.11.1/).

Copy the example settings only if `.env` does not exist, then export them and build the dashboard:

```bash
test -f .env || cp .env.example .env
set -a
. ./.env
set +a
export HOST="${HOST:-127.0.0.1}"
export PORT="${PORT:-8000}"
export DATA="${DATA:-data/dataset}"
export CALIBRATION="${CALIBRATION:-$DATA/calibration.json}"
export WEB="${WEB:-web/dist}"
export TORCH_HOME="${TORCH_HOME:-models/torch}"
export UV_CACHE_DIR="${UV_CACHE_DIR:-.cache/uv}"
npm --prefix web ci
npm --prefix web run build
```

Python does not automatically load `.env`. Keep these variables exported in the terminal where
you start the server. The defaults also support an older `.env` that lacks the new path settings.
Compare it with `.env.example` when changing configuration. CPU and GPU dependency installation
appears in their separate launch steps.

## Download the dataset
<!-- setup: cpu cuda; step -->

The native server needs the extracted recordings. Download dataset v1 and extract its audio
without replacing the repository's manifest, calibration, or current dataset documentation:

```bash
mkdir -p data
curl --fail --location --retry 3 \
  https://github.com/opx0/speech-delivery-flaw-detector/releases/download/dataset-v1/speech_delivery_dataset_v1.tar.gz \
  --output data/speech_delivery_dataset_v1.tar.gz && \
printf '%s  %s\n' \
  ca5c16fa9f0503c9f13b60dfdb1f0f2f5322581ff7a51a2bb3e111d91a0cb6da \
  data/speech_delivery_dataset_v1.tar.gz | sha256sum --check && \
tar -xzf data/speech_delivery_dataset_v1.tar.gz -C data dataset/audio
```

The checksum command must report `OK`. The extracted `data/dataset/audio/` contains 186 FLAC
recordings. The archive and extracted audio are ignored by Git.

`DATA` defaults to `data/dataset`. A custom dataset directory must contain its own `manifest.json`
and `audio/`. Set `CALIBRATION` to a calibration file that matches that dataset.

## Download the alignment model
<!-- setup: cpu cuda; step -->

Both native paths use the same pinned MMS checkpoint. Download it into the cache selected by
`TORCH_HOME`, verify the bytes, and install it only after the checksum passes:

```bash
mkdir -p "$TORCH_HOME/hub/checkpoints"
MODEL="$TORCH_HOME/hub/checkpoints/model.pt"
curl --fail --location --retry 3 \
  https://dl.fbaipublicfiles.com/mms/torchaudio/ctc_alignment_mling_uroman/model.pt \
  --output "$MODEL.download" && \
printf '%s  %s\n' \
  20ef12963ab4924bef49ac4fc7f58ad5da2ee43b2c11bc8c853c9b90ecdbc680 \
  "$MODEL.download" | sha256sum --check && \
mv "$MODEL.download" "$MODEL"
```

Expect approximately 1.2 GB of model weights and an `OK` checksum result. Do not rename an
unverified download. Keep the same `TORCH_HOME` value when starting the server.

## Native CPU server
<!-- setup: cpu; step -->

Install the locked CPU Python dependencies. uv selects Python 3.12.14 from `.python-version`:

```bash
uv sync --locked --no-dev
```

Start the server with the exported settings:

```bash
SPEECH_DEVICE=cpu uv run --no-sync python -m speech_delivery.api \
  --data "$DATA" --calibration "$CALIBRATION" --web "$WEB" \
  --host "$HOST" --port "$PORT"
```

Open http://127.0.0.1:8000 with the default settings. Leave this terminal open while using the
application. Press Ctrl+C to stop it. No GPU is required, and setup does not run tests.

## Optional NVIDIA GPU execution
<!-- setup: cuda; step -->

Create a separate environment for PyTorch 2.6.0 and torchaudio 2.6.0 with CUDA 12.4 support.
Keep the remaining runtime dependencies at their `uv.lock` versions:

```bash
mkdir -p .cache
uv venv --python 3.12.14 .cache/gpu-venv
uv pip install --python .cache/gpu-venv/bin/python \
  --index-url https://download.pytorch.org/whl/cu124 torch==2.6.0 torchaudio==2.6.0
uv export --locked --no-dev --no-hashes --no-emit-package torch --no-emit-package torchaudio \
  --output-file .cache/gpu-requirements.txt
uv pip install --python .cache/gpu-venv/bin/python --requirement .cache/gpu-requirements.txt
```

Check the CUDA-enabled interpreter:

```bash
.cache/gpu-venv/bin/python -c 'import torch; print(torch.__version__); print("CUDA available:", torch.cuda.is_available())'
```

The output must include `2.6.0+cu124` and `CUDA available: True`. The normal `.venv` contains
CPU-only PyTorch, so use the GPU environment's interpreter to start CUDA inference:

```bash
SPEECH_DEVICE=cuda CUBLAS_WORKSPACE_CONFIG=:4096:8 \
  .cache/gpu-venv/bin/python -m speech_delivery.api \
  --data "$DATA" --calibration "$CALIBRATION" --web "$WEB" \
  --host "$HOST" --port "$PORT"
```

Open http://127.0.0.1:8000 with the default settings. Press Ctrl+C to stop the server.
The commands honor your native dataset, calibration, web directory, host, port, and model cache.
CUDA verification does not establish byte identity with CPU execution.

## Verify a first analysis
<!-- setup: all; step -->

Open the application at the port you selected. With default settings, check the API from
another terminal:

```bash
curl --fail http://127.0.0.1:8000/api/library
```

In Windows PowerShell, use `curl.exe` to avoid the PowerShell `curl` alias:

```powershell
curl.exe --fail http://127.0.0.1:8000/api/library
```

Expect six library texts and 42 demo clips. Then use the browser:

1. Choose **Explore examples** or **Reference library**.
2. Select **The New Colossus**, then **Dragging pace**.
3. Wait for Decode, Align words, Extract, Compare, and Explain. CPU alignment can take time.
4. Select a finding and use **Play passage**, then **Gold reference**.
5. Open **Acoustic features**, change the rubric, or export the review.

For your own voice, choose **Add your recording**, upload or record audio, and provide the
words you spoke. The app aligns your transcript rather than generating one. The upload limit
is 50 MB and the recording-duration limit is 10 minutes.

## Parameters
<!-- setup: all; reference -->

Native commands load `.env` into the shell and pass server values as CLI arguments.
Docker Compose does not forward this file wholesale. Its standard image remains CPU-only.

| Native setting | Default | What it controls |
| --- | --- | --- |
| `HOST` | `127.0.0.1` | Passed to `--host`. Use `0.0.0.0` to bind all network interfaces. |
| `PORT` | `8000` | Passed to `--port`. Compose uses it only for the host port. |
| `DATA` | `data/dataset` | Passed to `--data`; must contain the dataset manifest and audio. |
| `CALIBRATION` | `data/dataset/calibration.json` | Passed to `--calibration`; must match the dataset. |
| `WEB` | `web/dist` | Passed to `--web`; the built dashboard directory. |
| `SPEECH_DEVICE` | `cpu` | `cpu` or `cuda` for MMS inference. GPU commands override it to `cuda`. |
| `TORCH_HOME` | `models/torch` | Model cache. The checkpoint is `hub/checkpoints/model.pt` below this directory. |
| `UV_CACHE_DIR` | `.cache/uv` | uv's package cache, not the model or dataset directory. |
| `SPEECH_API_URL` | `http://127.0.0.1:8000` | Vite's development API proxy. Production uses same-origin requests. |
| `CUBLAS_WORKSPACE_CONFIG` | Set to `:4096:8` in GPU commands | cuBLAS workspace configuration for the CUDA run. |

After editing `.env`, export it again before restarting a native server:

```bash
set -a
. ./.env
set +a
```

The API CLI supports `--data`, `--calibration`, `--web`, `--host`, `--port`, `--log-file`, and
`--history`. The environment
does not substitute these arguments unless your launch command passes it explicitly.

Add `--log-file runs/server.log` to append readable processing logs while retaining console
output. Use `tail -f runs/server.log` in another terminal to follow real job/stage events.
Default processing logs omit transcript text and audio contents. Recording itself is browser-local;
server logs start when the file is uploaded. Failed-job logs show error codes, not private input.

For native CUDA video recording, the optional launcher serves the built UI and API from a single
server, without running tests or submitting an analysis. Build the UI first:

```bash
npm --prefix web run build
.cache/gpu-venv/bin/python scripts/start_demo.py
```

It uses port 8000 by default and labels each line with its component: `[UI]`,
`[BACKEND][HTTP]`, `[BACKEND][ANALYSIS]`, `[BACKEND][ALIGNMENT]`, or `[SYSTEM]`.
Follow the combined log with `tail -f runs/demo.log`. Ctrl+C stops the launcher's own servers
gracefully. Existing occupied ports are refused, not automatically killed. `--api-port` changes
the single-server port. No Vite server is started. Model/dependency setup must already be complete;
there is no CPU inference fallback.

The API now journals admitted runs in `runs/history.sqlite3`; `--history PATH` changes the local
database location. **Run history** at `/history` preserves the original report, transcript,
input hash, submitted options, effective weights, calibration snapshot, runtime, and server-stage
events across refresh/restart. Failed and interrupted jobs are visible too. There is no backfill
of earlier analyses or fabricated visual sign-off. Uploaded audio is deleted after analysis; saved
history has no playback. A hard crash may leave temporary uploads; interrupted entries cannot
confirm cleanup. The journal is unencrypted and contains transcript text: keep the service local.
Both Compose configurations mount a named volume at `/app/runs` to retain reports on recreation.
Changing the API port also requires changing `SPEECH_API_URL` for Vite development.

The default Docker image fixes its dataset and model paths under `/app`, binds port 8000 inside
the container, and exposes `127.0.0.1:${PORT:-8000}` on the host. Host `HOST`, `DATA`, `WEB`,
`CALIBRATION`, and `SPEECH_DEVICE` values do not change the container configuration.

| Docker build argument | Default |
| --- | --- |
| `MMS_MODEL_URL` | Pinned MMS checkpoint URL in `Dockerfile` |
| `MMS_MODEL_SHA256` | `20ef12963ab4924bef49ac4fc7f58ad5da2ee43b2c11bc8c853c9b90ecdbc680` |
| `DATASET_URL` | Dataset v1 GitHub Release URL in `Dockerfile` |
| `DATASET_SHA256` | `ca5c16fa9f0503c9f13b60dfdb1f0f2f5322581ff7a51a2bb3e111d91a0cb6da` |

Use `docker compose build --build-arg NAME=value` to override a build argument. A custom URL
needs the corresponding expected checksum. Do not use these arguments to select CPU or GPU.

The server defaults to two workers and eight queued jobs. Upload size, duration, worker count,
and queue size are implementation constants, not `.env` or public CLI options. Rubric weights
belong to an analysis request and can be changed in the dashboard.

## Troubleshooting
<!-- setup: all; reference -->

| Symptom | Check and fix |
| --- | --- |
| Port already in use | Stop the other server or choose another `PORT`. For native use, pass the new port and update the Vite proxy too. |
| `nvm` or `uv` not found | Load `nvm.sh` or export `$HOME/.local/bin` on `PATH` as shown in native prerequisites. |
| npm reports an engine mismatch | Run `nvm use`, then select npm 12.2.0. The frontend requires Node 26.11.1. |
| Missing manifest or audio | Check `DATA`, extract the release's `dataset/audio` directory, and keep the matching manifest. |
| Missing calibration | Check `CALIBRATION`. It is a separate CLI path, not automatically derived from `--data`. |
| Checksum fails | Do not install or extract that download. Repeat the pinned download and checksum commands. |
| CUDA unavailable | Check `nvidia-smi` and use `.cache/gpu-venv/bin/python`, not the CPU `.venv` interpreter. |
| CUDA out of memory | Free GPU memory used by other applications or choose the CPU launch path. |
| Blank page or no frontend | Build `web/dist` and verify `WEB`. The API only serves the dashboard if that directory exists. |
| Vite cannot reach the API | Start the backend, set `SPEECH_API_URL` to its address, and restart Vite. |
| Alignment is slow | Inspect available RAM and competing processes. The first analysis loads a large model; avoid swapping. |
| Transcript mismatch | Supply the words actually spoken. Write digits as spoken words for the aligner. |
| Microphone unavailable | Upload an audio file. Remote microphone capture needs a browser-supported secure context. |
| An injected flaw is not detected | Review the actual result. The current detector misses some benchmark regions; setup success does not imply detection accuracy. |

## Pinned versions
<!-- setup: all; reference -->

| Component | Version or source |
| --- | --- |
| Python | 3.12.14 in `.python-version` and `pyproject.toml` |
| uv | 0.13.0 |
| Node.js | 26.11.1 in `.node-version` and `.nvmrc` |
| npm | 12.2.0 in `web/package.json` |
| Python packages | `uv.lock`; CPU Torch and torchaudio 2.6.0 |
| GPU Torch and torchaudio | 2.6.0+cu124 in the separate GPU environment |
| Node packages | `web/package-lock.json` |
| Docker base images | Exact versions and image digests in `Dockerfile` |

## Development and evaluation
<!-- setup: all; reference -->

For real API development, keep the backend running and open another terminal in the checkout:

```bash
npm --prefix web run dev
```

Open http://localhost:5173. Set `SPEECH_API_URL` if the backend runs on another port.
For an explicit fixture preview, use:

```bash
npm --prefix web run dev:mock
```

Mock preview does not analyze audio. With native settings exported, analyze one recording from
the command line on CPU:

```bash
SPEECH_DEVICE=cpu uv run --no-sync python -m speech_delivery.analysis \
  "$DATA/audio/new-colossus.drag-l3.flac" --data "$DATA" --text new-colossus
```

The analysis CLI supports `--data`, `--text`, `--transcript`, and `--json`. Use a library text ID
or supply the spoken words with `--transcript`. This CLI reads `calibration.json` from its dataset
directory. For CUDA, use `SPEECH_DEVICE=cuda` and the GPU environment's interpreter.

For CPU evaluation after native setup:

```bash
uv run --no-sync python -m speech_delivery.evaluation \
  --device cpu --dataset "$DATA" --calibration "$CALIBRATION" --output runs/full-evaluation-cpu.json
```

For GPU evaluation after native GPU setup:

```bash
CUBLAS_WORKSPACE_CONFIG=:4096:8 \
  .cache/gpu-venv/bin/python -m speech_delivery.evaluation \
  --device cuda --dataset "$DATA" --calibration "$CALIBRATION" --output runs/full-evaluation-cuda.json
```

The evaluator supports `--dataset`, `--calibration`, `--device`, `--quick`, and `--output`.
Omit `--quick` for the full dataset. An evaluation target failure exits with code 1 after writing
results. The current full evaluation fails recall and held-out-reader false-positive targets.
See [the technical report](TECHNICAL_REPORT.md).

## Offline use
<!-- setup: all; reference -->

### Opt-in verification tooling

For a judge-facing validation of an already running native CUDA or CUDA Docker application:

```bash
.cache/gpu-venv/bin/python scripts/validate_live.py --url http://127.0.0.1:8000
```

It uploads real audio, follows the actual progress stream, displays findings, and saves the report
and summary under `runs/live-validation/`. `--audio FILE --transcript FILE` accepts a user's own
recording. The default demo separately reports whether its advertised flaw types were observed;
a functioning API is not automatically a passing detector. `/api/runtime` confirms the model's
actual loaded CUDA device after processing. The client refuses CPU inference servers. This new
live-validation script passed once on native CUDA on 2026-10-14: all stages completed, the upload
hash matched, and the dragging-pace demo produced two findings in about 16.7 seconds. The loaded
model reported `cuda:0`. This does not establish full dataset accuracy or other workflows.

The following commands are for the later verification phase, **not** normal setup. The new
stress tooling passed the 600-second API check on 2026-10-14. It starts its own native CUDA API, refuses an occupied port,
and stops the API when finished. It requires a prepared model and frontend build:

```bash
SPEECH_DEVICE=cuda TORCH_HOME="$PWD/models/torch" CUBLAS_WORKSPACE_CONFIG=:4096:8 \
  .cache/gpu-venv/bin/python scripts/verify_gpu.py --stress
```

It writes evidence under `runs/gpu-verification/`: a complete ten-minute
report, elapsed processing time, Linux server memory high-water marks, and sampled total GPU
memory usage. The long fixture repeats an existing genuine recording and pads it to exactly
600 seconds; it does not substitute for the human-held-out recordings. GPU memory samples
include other applications and may miss short-lived peaks.

The React browser E2E suite was removed after one native-CUDA run with no retries: five checks
passed and one failed while retrieving an SSE response body after the results screen appeared.
Remaining assertions in that test were not verified. The suite and its evidence now live in a
separate QA Lab workspace outside this submission. Use the manual browser walkthrough for future
interface verification.

For native/container reproducibility, first export reports for the identical audio, filename,
transcript, calibration, weights, and checkout in each environment. A comparison tool is ready
for the later verification phase:

```bash
.cache/gpu-venv/bin/python scripts/compare_reports.py \
  runs/native-report.json runs/container-report.json --output runs/report-comparison.json
```

It compares complete validated report serialization, including run stamps, and exits with code
1 on a mismatch. It also records score and alignment differences for CPU/CUDA characterization;
it never silently removes fields to manufacture byte identity. The script does not run inference.

The latest CUDA candidate evaluation measured 80.31% precision, 21.98% recall, and 66.67%
held-out-reader false positives. Recall and false-positive targets still fail. The candidate is
retained in `docs/evaluation/calibration-cuda-2026-10-14.json`; the default application calibration
was not overwritten. Human imports remain unverified because the actual recordings are absent.
Only calibration-split recordings were used for recalibration.

After setup, analysis uses local audio, model weights, and computation. Native use needs its
prepared environment and the verified checkpoint at the chosen `TORCH_HOME` path.
Docker users can transfer a completed image with `docker save` and `docker load`.
Building an image or installing native dependencies initially requires network access.

## Render the technical report
<!-- setup: all; reference -->

Install the frontend dependencies, Playwright Chromium, and Poppler's `pdfinfo`.
On Debian or Ubuntu, `poppler-utils` provides `pdfinfo`. Then run:

```bash
mkdir -p runs
uv run --no-project --with markdown==3.8.2 python -m markdown \
  docs/TECHNICAL_REPORT.md -x tables -x fenced_code -f runs/technical-report.html
node web/scripts/render-report.mjs runs/technical-report.html runs/technical-report.pdf
```

The renderer fails if the PDF exceeds six pages. Generated reports remain in ignored `runs/`.

## Verification status
<!-- setup: all; reference -->

Historical records: the CPU environment passed 158 Python tests and nine alignment/signal tests
passed on CUDA before later implementation changes. Internal unit, logic, fixture-validation,
and UI test suites have since been removed at the owner's request; these are not current results.
Only user/judge-facing live validation, stress checks, and dataset evaluation remain.
The earlier frontend type check and production build passed.
The interface and setup guide passed five browser tests against the production Docker application.
Guide metadata and 25 shell blocks passed validation without executing their commands.
The previous three-test suite also passed against the native GPU API.

Docker downloaded and verified its model and dataset without local asset files in the build
context. All 186 recordings passed hash and decode checks inside the image. The technical
report rendered to four A4 pages. Native installation on a fresh VM and Windows or macOS
deployment remain unverified. See [the clean-environment procedure](CLEAN_ENVIRONMENT.md).

On 2026-10-14, CUDA Docker construction and live uploads passed. The homepage and guide returned
HTTP 200. A sampled native/CUDA Docker report pair was byte-identical, with zero score or
word-boundary differences. Native CUDA processed a 600-second repeated-reference upload in
32.7 seconds, with all 1,152 words aligned. Server peak RSS was about 2.51 GiB; sampled total
GPU memory reached 3,770 MiB including unrelated processes. Personal-file and normative-mode
API uploads also passed using genuine library audio, not newly supplied human recordings.

A CUDA source rebuild regenerated all 186 clips across six texts in 94.3 seconds and matched
every published audio hash. The twelve original source checksums were verified before building.
The output stayed separate from dataset v1. Fresh native installation, hardware microphone
capture, human-held-out evaluation, and Windows/macOS execution remain unverified.
