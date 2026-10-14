"""Opt-in GPU ten-minute API checks. Never invoked by setup or image builds."""

import argparse
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event, Thread

import httpx
import numpy as np
import torch

from speech_delivery.audio import SAMPLE_RATE, from_samples, write_flac
from speech_delivery.contract import AnalyzeOptions, Report
from speech_delivery.library import Library

ROOT = Path(__file__).resolve().parents[1]


def sample_gpu_memory(stop: Event, values: list[int]) -> None:
    while not stop.is_set():
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if result.returncode == 0:
                values.extend(int(line) for line in result.stdout.splitlines() if line.isdigit())
        except (OSError, subprocess.TimeoutExpired):
            return
        stop.wait(1.0)


def long_audio(library: Library, directory: Path) -> tuple[Path, str]:
    gold = library.gold_for("new-colossus")
    audio = library.audio(gold.id)
    target = 600 * SAMPLE_RATE
    count = target // len(audio.samples)
    if count < 2:
        raise ValueError("stress fixture requires a short reference recording")
    repeated = np.tile(audio.samples, count)
    samples = np.pad(repeated, (0, target - len(repeated)))
    path = directory / "ten-minute-repeated-reference.flac"
    write_flac(path, from_samples(samples))
    transcript = " ".join([library.text(gold.text_id).transcript] * count)
    return path, transcript


def stress(url: str, library: Library, directory: Path) -> dict[str, object]:
    path, transcript = long_audio(library, directory)
    started = time.monotonic()
    options = AnalyzeOptions(transcript=transcript)
    stages: list[str] = []
    with httpx.Client(base_url=url, timeout=1800.0) as client, path.open("rb") as audio:
        created = client.post(
            "/api/jobs",
            files={"audio": (path.name, audio, "audio/flac")},
            data={"options": options.model_dump_json()},
        )
        created.raise_for_status()
        job_id = created.json()["job_id"]
        with client.stream("GET", f"/api/jobs/{job_id}/events") as events:
            events.raise_for_status()
            for line in events.iter_lines():
                if not line.startswith("data:"):
                    continue
                event = json.loads(line[5:])
                if event["type"] == "failed":
                    raise RuntimeError(
                        f"stress analysis failed: {event['code']}: {event['message']}"
                    )
                if event["type"] == "progress":
                    stages.append(event["stage"])
                if event["type"] == "done":
                    report = Report.model_validate(event["report"])
                    if abs(report.participant.duration_s - 600.0) > 0.001:
                        raise RuntimeError("stress recording was truncated")
                    if len(report.words.words) != len(transcript.split()):
                        raise RuntimeError("stress alignment did not retain every transcript word")
                    if not {"decode", "align", "extract", "compare", "explain"} <= set(stages):
                        raise RuntimeError("stress analysis skipped required progress stages")
                    (directory / "ten-minute-report.json").write_text(report.model_dump_json())
                    return {
                        "passed": True,
                        "seconds": time.monotonic() - started,
                        "duration_s": report.participant.duration_s,
                        "aligned_words": len(report.words.words),
                        "reference_mode": report.reference.basis,
                        "fixture": "repeated genuine reference, padded to exactly 600 seconds",
                        "limitation": "synthetic concatenation; not a new human recording",
                    }
    raise RuntimeError("stress event stream ended without a report")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stress", action="store_true")
    parser.add_argument("--port", type=int, default=18082)
    parser.add_argument("--dataset", type=Path, default=ROOT / "data/dataset")
    parser.add_argument("--output", type=Path, default=ROOT / "runs/gpu-verification")
    args = parser.parse_args()
    if not args.stress:
        parser.error("select --stress to explicitly enable the ten-minute API check")
    if os.environ.get("SPEECH_DEVICE") != "cuda" or not torch.cuda.is_available():
        parser.error("use the CUDA interpreter with SPEECH_DEVICE=cuda; no CPU fallback")
    args.dataset = args.dataset.resolve()
    args.output = args.output.resolve()
    with socket.socket() as probe:
        probe.settimeout(1.0)
        if probe.connect_ex(("127.0.0.1", args.port)) == 0:
            parser.error("verification port is occupied; choose a different --port")
    args.output.mkdir(parents=True, exist_ok=True)
    url = f"http://127.0.0.1:{args.port}"
    results: dict[str, object] = {"device": "cuda", "torch": torch.__version__}
    env = dict(os.environ, SPEECH_DEVICE="cuda", CUBLAS_WORKSPACE_CONFIG=":4096:8")
    env.setdefault("TORCH_HOME", str(ROOT / "models/torch"))
    if not (Path(env["TORCH_HOME"]) / "hub/checkpoints/model.pt").is_file():
        parser.error("prepare the local alignment checkpoint before verification")
    with (args.output / "api.log").open("w") as log:
        server = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "speech_delivery.api",
                "--data",
                str(args.dataset),
                "--calibration",
                str(args.dataset / "calibration.json"),
                "--web",
                str(ROOT / "web/dist"),
                "--host",
                "127.0.0.1",
                "--port",
                str(args.port),
            ],
            cwd=ROOT,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        stop = Event()
        gpu_memory: list[int] = []
        sampler = Thread(target=sample_gpu_memory, args=(stop, gpu_memory), daemon=True)
        sampler.start()
        try:
            for _ in range(120):
                if server.poll() is not None:
                    raise RuntimeError("verification API exited; inspect api.log")
                try:
                    response = httpx.get(f"{url}/api/library", timeout=2.0)
                    response.raise_for_status()
                    break
                except httpx.HTTPError:
                    time.sleep(0.5)
            else:
                raise RuntimeError("verification API startup timed out")
            if args.stress:
                with TemporaryDirectory(prefix="stress-", dir=args.output) as temporary:
                    result = stress(url, Library.load(args.dataset), Path(temporary))
                    report_path = Path(temporary) / "ten-minute-report.json"
                    (args.output / report_path.name).write_bytes(report_path.read_bytes())
                    results["stress"] = result
            status = Path(f"/proc/{server.pid}/status")
            if status.exists():
                results["server_memory"] = [
                    line
                    for line in status.read_text().splitlines()
                    if line.startswith(("VmHWM:", "VmPeak:"))
                ]
        except Exception as error:
            results["error"] = str(error)
            raise
        finally:
            stop.set()
            sampler.join(timeout=6)
            results["sampled_gpu_memory_peak_mib"] = max(gpu_memory) if gpu_memory else None
            results["gpu_memory_scope"] = (
                "one-second samples of total device usage, including unrelated processes"
            )
            (args.output / "results.json").write_text(json.dumps(results, indent=2) + "\n")
            server.terminate()
            try:
                server.wait(timeout=15)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()


if __name__ == "__main__":
    main()
