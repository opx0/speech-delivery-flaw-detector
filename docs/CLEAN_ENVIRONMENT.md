# Verify a clean demo environment

Use these procedures to check deployment without relying on the developer's local dependencies
or audio files. Record completed checks separately from procedures that still need another host.

## Recorded Linux checks

On 2026-10-13, the Docker build installed the locked Python dependencies, rebuilt the UI,
and downloaded and checksum-verified the model and dataset. Its build context excluded local
environments, model files, and audio. A container check verified and decoded all 186 recordings.
The initial three-test Chromium suite passed against the production Docker application at port 8000.
After the visual redesign, the expanded four-test suite also passed against that application.
The later five-test suite also checked the shared setup guide, clipboard output and failure,
deep links, browser history, and review-state preservation against the production image.

The native GPU backend also passed the three browser tests. These checks used the current Linux
host. They do not establish a fresh native VM installation or Windows and macOS deployment.

## Disposable Docker run

Additional 2026-10-14 Linux checks: the opt-in CUDA image built and launched, its real API demo
and file upload passed, and homepage/setup-guide requests returned HTTP 200. A native/CUDA Docker
report pair for one gold upload was byte-identical. These checks still used the current Linux host,
not a fresh native VM or Windows/macOS machine. See [the verification record](evaluation/VERIFICATION.md).

Use a fresh checkout of the intended submission in a disposable VM or another computer. Confirm
that the checkout contains the lockfiles and dataset metadata. Docker retrieves audio from the
pinned release archive. A local uncommitted working tree does not establish that the submission
contains these files.

Build without reusing application layers:

```bash
docker compose build --no-cache
docker compose up
```

The build context excludes local `.venv`, `web/node_modules`, `web/dist`, `.cache`, `models`, and dataset audio.
The image must install from the lockfiles, rebuild the UI, and download the pinned weights and dataset.
Do not delete the developer's existing caches or environment to simulate a clean run.

Complete the main-feature walkthrough in [the launch guide](LOCAL_SETUP.md). Record whether
the report appears, whether the selected audio matches the displayed transcript, and whether
playback, seeking, reference audition, and reweighting work. Check a clean control as well as
a flawed clip; the detector may miss release gates, so report actual findings rather than
assuming that every injected flaw appears.

## Disposable native Linux run

Use a new Debian or Ubuntu VM with no uv, Node, Torch, or project caches. Follow the native
instructions exactly. Do not transfer the GitHub Actions model cache or a developer `.venv`.
Use the documented direct installation and model-download commands, then start the Python
server with `--web web/dist` to serve the React dashboard.

## Cross-platform run

Repeat the Docker procedure on a Windows or macOS machine with Docker Desktop. Record the
host OS, CPU architecture, Docker memory allocation, and whether emulation is involved.
Do not claim native Windows or macOS support based on a Linux-container run.

## Record the results

Capture the checkout commit, runtime versions, image digests, setup errors, browser and OS,
and observed workflow results. Label a timed-out or incomplete analysis as incomplete.
Test output and screenshot artifacts belong outside the submission or in ignored directories.

The automated browser suite was removed after its requested one-time native-CUDA run: five checks
passed and one response-body assertion failed. Continue browser verification with the manual
walkthrough above. No tests run automatically through native installation, server launch, or
Docker image construction. Playwright is retained for technical-report PDF rendering only.
