# Launch the speech review demo

Use Docker as the cross-platform launch path. Native instructions below target Debian or Ubuntu
Linux. See the verification status at the end for the checks completed on this host.

## What is included

- The repository includes dataset transcripts and word alignments in `data/dataset/manifest.json`
  and the sealed `calibration.json`. The versioned dataset release provides 186 FLAC recordings.
- The library exposes six texts and 42 examples, including clean controls and injected delivery flaws.
- `.env.example` documents optional native settings. No API key or account is required.
- The Dockerfile downloads MMS alignment weights and checks their SHA-256 checksum during
  image construction. Native users run the download commands documented below.
  GitHub Actions caching is not required on a judge's machine.
- The UI uses bundled application assets and system-font fallbacks, without remote font requests.

Docker downloads and verifies the dataset during its build. For native use, follow
[the dataset download instructions](../README.md#dataset) before launching the server.
The application reads the extracted files, not the archive.

## Pinned versions

| Component | Pin |
| --- | --- |
| Python | 3.12.14, declared in `.python-version` and `pyproject.toml` |
| Python packages | Exact resolutions and hashes in `uv.lock` |
| Python build backend | Hatchling 1.28.0 |
| uv | 0.13.0 |
| Node.js | 26.11.1, declared in `.node-version`, `.nvmrc`, and `web/package.json` |
| npm | 12.2.0 |
| Node packages | Exact direct versions and `package-lock.json`; install with `npm ci` |
| Docker base images | Exact versions and immutable image-index digests in `Dockerfile` |
| Alignment weights | MMS `ctc_alignment_mling_uroman`, checksum `20ef12963ab4924bef49ac4fc7f58ad5da2ee43b2c11bc8c853c9b90ecdbc680` |

The model is approximately 1.2 GB. Initial setup needs internet access for the base images,
packages, and model download. After image construction or native setup, the main feature uses
local audio, local model weights, and local computation. No GPU is required.

## Docker launch

Install Docker with its Compose plugin. On Windows and macOS, Docker Desktop provides a Linux
runtime. Compose selects `linux/amd64` so the Python CPU wheel set is consistent across hosts.
On an ARM host, this uses emulation. Allow sufficient memory and disk space for Torch and the
alignment model; 6 GB of Docker memory and 8 GB of free disk space are a practical starting point.

From the project root, run:

```bash
docker compose up --build
```

The first build installs locked dependencies, compiles the React dashboard, downloads and
checks the model weights, and downloads and verifies the dataset release. Open **http://localhost:8000**.

Use a different host port if 8000 is occupied:

```bash
PORT=8080 docker compose up --build
```

On Windows PowerShell, set `$env:PORT = "8080"` before the Compose command. Containers still
listen on port 8000 internally.

Stop the demo with:

```bash
docker compose down
```

The image contains the dataset and model. No host model cache, bind mount, CI cache, or personal
configuration is required for normal analysis.

## Native Linux launch

Install the system tools on Debian or Ubuntu:

```bash
sudo apt-get update
sudo apt-get install -y curl git ffmpeg espeak-ng libgomp1 libsndfile1
```

Install uv 0.13.0 using its versioned installer:

```bash
curl --proto '=https' --tlsv1.2 -LsSf https://astral.sh/uv/0.13.0/install.sh | sh
```

Open a new terminal so uv is on your path. Install Node.js 26.11.1 using your Node version
manager. If nvm is already installed, the project pin is sufficient:

```bash
nvm install
nvm use
npm install --global npm@12.2.0
```

If you do not use nvm, install the exact Node version from
[the Node.js distribution directory](https://nodejs.org/dist/v26.11.1/), then select npm 12.2.0.
The frontend rejects other runtime versions through `web/.npmrc`.

From the project root, run:

```bash
cp .env.example .env
set -a
. ./.env
set +a
uv sync --locked
npm --prefix web ci
npm --prefix web run build
```

uv selects Python 3.12.14 through `.python-version`. The Node commands install from the lockfile
and build the dashboard. No launcher script or Makefile is required.

Download and verify the model once:

```bash
mkdir -p "$TORCH_HOME/hub/checkpoints"
MODEL="$TORCH_HOME/hub/checkpoints/model.pt"
curl --fail --location --retry 3 \
  https://dl.fbaipublicfiles.com/mms/torchaudio/ctc_alignment_mling_uroman/model.pt \
  --output "$MODEL.download"
printf '%s  %s\n' \
  20ef12963ab4924bef49ac4fc7f58ad5da2ee43b2c11bc8c853c9b90ecdbc680 \
  "$MODEL.download" | sha256sum --check
```

Only after the checksum command reports **OK**, install the verified checkpoint:

```bash
mv "$MODEL.download" "$MODEL"
```

Start the Python server with the built React dashboard:

```bash
uv run --no-sync python -m speech_delivery.api \
  --data "$DATA" --calibration "$DATA/calibration.json" \
  --web web/dist --port "$PORT"
```

Open **http://127.0.0.1:8000**, or the port set in `.env`. These commands do not run tests.

## Demonstrate the main feature

1. Open **Explore examples** or **Reference library**.
2. Select **The New Colossus** for a short example.
3. Choose **Dragging pace**. The browser submits the actual release FLAC, not placeholder bytes.
4. Follow Decode, Align words, Extract, Compare, and Explain.
5. Select a finding to inspect its words, timestamps, observed value, reference value, and explanation.
6. Use **Play passage**, **Loop passage**, or **Gold reference** to hear the comparison.
7. Open **Acoustic features** to inspect pace, pitch, energy, and pauses.
8. Use **Adjust rubric** to change the overall weighting, or **Export report** to download the review.

For a command-line demonstration after native setup:

```bash
uv run --no-sync python -m speech_delivery.analysis \
  data/dataset/audio/new-colossus.drag-l3.flac --text new-colossus
```

For your own voice, use **Add your recording**, upload audio or record with the microphone, and
select a library text or paste the words you spoke. The limit is 10 minutes and 50 MB. Transcripts
are required; the system aligns supplied words rather than generating a transcript.

## Development modes

Keep the API running, then open another terminal in `web/`:

```bash
npm run dev
```

The dashboard at **http://localhost:5173** proxies to the real API. Root `.env` can set
`SPEECH_API_URL` when the API uses another port.

For an explicitly labeled fixture preview:

```bash
npm run dev:mock
```

Mock preview does not analyze uploaded audio. It is a UI preview only.

## Model setup and offline provisioning

Retry a failed download with the native download commands above. Docker retries the download
during construction and refuses to install a checkpoint whose checksum does not match.
Native users must move the checkpoint into place only after its checksum passes.

To provision a machine without internet access, place the matching `model.pt` at
`models/torch/hub/checkpoints/model.pt` before native launch. Use the same dependencies from
a prepared environment. Docker users can transfer a previously built image with `docker save`
and `docker load`; building the image itself requires initial network access.

`TORCH_HOME` identifies the same cache during setup and analysis. Keep the native environment
variables exported in the server's terminal. Docker sets its paths internally.
Do not assume the GitHub Actions cache exists.

## Optional NVIDIA GPU execution

The normal lockfile and Docker image use CPU PyTorch. To use CUDA on Linux with an NVIDIA GPU,
create a separate environment. These commands keep the other runtime dependencies at their
lockfile versions and install PyTorch 2.6.0 with CUDA 12.4 support:

```bash
uv venv --python 3.12.14 .cache/gpu-venv
uv pip install --python .cache/gpu-venv/bin/python \
  --index-url https://download.pytorch.org/whl/cu124 torch==2.6.0 torchaudio==2.6.0
uv export --locked --no-dev --no-hashes --no-emit-package torch --no-emit-package torchaudio \
  --output-file .cache/gpu-requirements.txt
uv pip install --python .cache/gpu-venv/bin/python --requirement .cache/gpu-requirements.txt
```

Download the dataset and model using the native instructions above. Check CUDA access:

```bash
.cache/gpu-venv/bin/python -c 'import torch; print(torch.__version__, torch.cuda.is_available())'
```

The result must include `True`. Start the GPU backend:

```bash
TORCH_HOME="$PWD/models/torch" SPEECH_DEVICE=cuda CUBLAS_WORKSPACE_CONFIG=:4096:8 \
  .cache/gpu-venv/bin/python -m speech_delivery.api --web web/dist --port 8000
```

Run the full evaluation on the GPU:

```bash
TORCH_HOME="$PWD/models/torch" CUBLAS_WORKSPACE_CONFIG=:4096:8 \
  .cache/gpu-venv/bin/python -m speech_delivery.evaluation \
  --device cuda --output runs/full-evaluation-cuda.json
```

MMS model inference runs on CUDA. Alignment decoding and acoustic feature extraction stay on CPU.
An RTX 3050 Laptop GPU with 4 GB of VRAM completed this run in float32. This does not establish
byte identity with CPU execution. The command writes its results and exits with code 1 if any
evaluation target fails.

## Render the technical report

Install the frontend dependencies and Playwright Chromium. Install Poppler's `pdfinfo`, provided
by `poppler-utils` on Debian or Ubuntu. Render the Markdown and check the PDF page count:

```bash
mkdir -p runs
uv run --no-project --with markdown==3.8.2 python -m markdown \
  docs/TECHNICAL_REPORT.md -x tables -x fenced_code -f runs/technical-report.html
node web/scripts/render-report.mjs runs/technical-report.html runs/technical-report.pdf
```

The renderer fails if the PDF exceeds six pages.
Generated HTML, PDFs, and evaluation outputs remain local in the ignored `runs/` directory.

## Verification status

The CPU environment passed 158 Python tests. The frontend passed eight logic tests,
type checking, fixture validation, and a production
build. Nine alignment and signal tests passed on CUDA. All three Chromium workflow tests passed
against the real GPU API, including report export and mobile layout.
The same suite passed against the production Docker app:

```bash
PLAYWRIGHT_BASE_URL=http://127.0.0.1:8000 npm --prefix web run test:e2e
```

Docker downloaded and verified the dataset and model without local audio or model files in its
build context. All 186 recordings passed hash and decode checks inside the image.
The technical report rendered to four A4 pages using the commands above.

The full evaluation still fails recall and held-out natural-reader false-positive targets.
See [the technical report](TECHNICAL_REPORT.md) for the measured results.
Native installation on a fresh VM and Windows or macOS deployment remain unverified.
See [the clean-environment procedure](CLEAN_ENVIRONMENT.md).
