# Launch the speech review demo

Use Docker as the cross-platform launch path. Native instructions below target Debian or Ubuntu
Linux. These launch paths have not been exercised from a clean environment. Further tests and
clean-environment runs were paused at the owner's request.

## What is included

- `data/dataset/` contains 186 FLAC recordings, transcripts and word alignments in `manifest.json`,
  and the sealed `calibration.json`. Setup does not rebuild or reacquire this dataset.
- The library exposes six texts and 42 examples, including clean controls and injected delivery flaws.
- `.env.example` documents optional native settings. No API key or account is required.
- The Dockerfile downloads MMS alignment weights and checks their SHA-256 checksum during
  image construction. Native users run the download commands documented below.
  GitHub Actions caching is not required on a judge's machine.
- The UI uses bundled application assets and system-font fallbacks, without remote font requests.

Use the complete project checkout, including `data/dataset/`. The separate
`data/speech_delivery_dataset_v1.tar.gz` is a dataset distribution artifact, not a runtime dependency.

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
checks the model weights, and copies the provided dataset. Open **http://localhost:8000**.

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
3. Choose **Rushed pacing**. The browser submits the actual provided FLAC, not placeholder bytes.
4. Follow Decode, Align words, Extract, Compare, and Explain.
5. Select a finding to inspect its words, timestamps, observed value, reference value, and explanation.
6. Use **Play passage**, **Loop passage**, or **Gold reference** to hear the comparison.
7. Open **Acoustic features** to inspect pace, pitch, energy, and pauses.
8. Use **Adjust rubric** to change the overall weighting, or **Export report** to download the review.

For a command-line demonstration after native setup:

```bash
uv run --no-sync python -m speech_delivery.analysis \
  data/dataset/audio/new-colossus.rush-l3.flac --text new-colossus
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

## Verification status

Before testing was paused, the redesigned UI passed a frontend type check, eight logic tests,
and a production build. A Chromium check rendered the welcome page and submitted a real demo,
but timed out during backend alignment before displaying a report.

Subsequent UI, runtime-pin, model-provisioning, and packaging edits have not been executed or
tested. The Docker launch, clean Linux installation, and Windows/macOS Docker launch remain
unverified. See [the clean-environment procedure](CLEAN_ENVIRONMENT.md) for the checks to run
when verification resumes.
