"""Serve the built UI, run history, and CUDA API from one server with categorized logs."""

import argparse
import contextlib
import os
import signal
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import TextIO

import httpx

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-port", type=int, default=8000)
    parser.add_argument("--log-file", type=Path, default=ROOT / "runs/demo.log")
    args = parser.parse_args()
    if not 1 <= args.api_port <= 65535:
        parser.error("choose a valid API port")
    for port in (args.api_port,):
        with socket.socket() as probe:
            if probe.connect_ex(("127.0.0.1", port)) == 0:
                parser.error(f"port {port} is occupied; stop that server or choose another port")

    import torch

    if not torch.cuda.is_available():
        parser.error("use the CUDA interpreter; CPU inference is not allowed")
    cache = Path(os.environ.get("TORCH_HOME", str(ROOT / "models/torch"))).resolve()
    if not (cache / "hub/checkpoints/model.pt").is_file():
        parser.error("prepare the local alignment model before starting")
    if not (ROOT / "web/dist/index.html").is_file():
        parser.error("build the UI first with npm --prefix web run build")
    args.log_file.parent.mkdir(parents=True, exist_ok=True)
    lock = threading.Lock()
    children: list[subprocess.Popen[str]] = []
    readers: list[threading.Thread] = []
    api_url = f"http://127.0.0.1:{args.api_port}"
    ui_url = api_url
    env = dict(
        os.environ,
        SPEECH_DEVICE="cuda",
        TORCH_HOME=str(cache),
        CUBLAS_WORKSPACE_CONFIG=":4096:8",
        SPEECH_API_URL=api_url,
        PYTHONUNBUFFERED="1",
        NO_COLOR="1",
    )
    env.pop("FORCE_COLOR", None)

    with args.log_file.open("a", encoding="utf-8") as log:

        def write(category: str, text: str) -> None:
            text = text.rstrip()
            if not text:
                return
            line = (
                text
                if text.startswith(f"[{category}]")
                else (f"[{category}] {time.strftime('%H:%M:%S')} | {text}")
            )
            with lock:
                print(line, flush=True)
                log.write(line + "\n")
                log.flush()

        def forward(category: str, stream: TextIO) -> None:
            for line in stream:
                write(category, line)

        write("SYSTEM", "NEW DEMO SESSION | native CUDA | real API, not mock data")
        write("SYSTEM", "Mode: one server for the built UI, run history, and API")
        commands = [
            (
                "BACKEND",
                ROOT,
                [
                    sys.executable,
                    "-m",
                    "speech_delivery.api",
                    "--data",
                    "data/dataset",
                    "--calibration",
                    "data/dataset/calibration.json",
                    "--web",
                    "web/dist",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(args.api_port),
                    "--log-file",
                    str(ROOT / "runs/server.log"),
                ],
            ),
        ]
        write("UI", "Serving compiled frontend from web/dist; no separate frontend process")
        try:
            for category, cwd, command in commands:
                write(category, "Starting…")
                child = subprocess.Popen(
                    command,
                    cwd=cwd,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    start_new_session=True,
                )
                children.append(child)
                if child.stdout is None:
                    raise RuntimeError("server log pipe was not created")
                reader = threading.Thread(
                    target=forward, args=(category, child.stdout), daemon=True
                )
                reader.start()
                readers.append(reader)
                if category == "BACKEND":
                    for _ in range(120):
                        if child.poll() is not None:
                            raise RuntimeError("backend exited before becoming ready")
                        try:
                            response = httpx.get(f"{api_url}/api/library", timeout=2)
                            response.raise_for_status()
                            write("BACKEND", f"Ready at {api_url}")
                            break
                        except httpx.HTTPError:
                            time.sleep(0.5)
                    else:
                        raise RuntimeError("backend startup timed out")
            write("SYSTEM", f"UI: {ui_url} | API / built UI: {api_url}")
            write("SYSTEM", f"Session log: {args.log_file} | Ctrl+C stops this session")
            while all(child.poll() is None for child in children):
                time.sleep(0.5)
            raise RuntimeError("a server exited; inspect its categorized output above")
        except KeyboardInterrupt:
            write("SYSTEM", "Stopping this demo's servers gracefully…")
        finally:
            for child in reversed(children):
                with contextlib.suppress(ProcessLookupError):
                    os.killpg(child.pid, signal.SIGTERM)
            for child in children:
                try:
                    child.wait(timeout=60)
                except subprocess.TimeoutExpired:
                    write("SYSTEM", "Waiting for active analysis to finish; not force-killing it.")
                    child.wait()
            for reader in readers:
                reader.join(timeout=3)
            write("SYSTEM", "Demo session stopped.")


if __name__ == "__main__":
    main()
