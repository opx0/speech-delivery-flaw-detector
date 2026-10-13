# Verify a clean demo environment

This is a procedure for a future verification run. It has not been executed. The owner requested
that further tests and clean-environment runs stop during the current redesign and packaging work.

## Disposable Docker run

Use a fresh checkout of the intended submission in a disposable VM or another computer. Confirm
that the checkout contains the lockfiles and `data/dataset/`; a local uncommitted working tree
does not establish that the submission contains these files.

Build without reusing application layers:

```bash
docker compose build --no-cache
docker compose up
```

The build context excludes local `.venv`, `web/node_modules`, `web/dist`, `.cache`, and `models`.
The image must install from the lockfiles, rebuild the UI, and download the pinned weights.
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

The existing automated browser suite is optional and requires the real API plus Playwright's
Chromium installation. It is separate from normal setup and launch; no tests run automatically
through the documented native installation, native server launch, or Docker image construction.
