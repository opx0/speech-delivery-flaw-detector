"""Judge-facing live CUDA API validation: real audio in, progress and an actual report out."""

import argparse
import hashlib
import json
import time
from pathlib import Path

import httpx
from pydantic import TypeAdapter

from speech_delivery.contract import AnalyzeOptions, JobCreated, JobEvent, LibraryListing, Report

EVENTS: TypeAdapter[JobEvent] = TypeAdapter(JobEvent)


def analyse(
    client: httpx.Client, audio: bytes, filename: str, options: AnalyzeOptions, timeout: float
) -> tuple[Report, list[str], float]:
    started = time.monotonic()
    response = client.post(
        "/api/jobs",
        files={"audio": (filename, audio, "application/octet-stream")},
        data={"options": options.model_dump_json()},
    )
    response.raise_for_status()
    job = JobCreated.model_validate(response.json())
    stages: list[str] = []
    with client.stream("GET", f"/api/jobs/{job.job_id}/events") as stream:
        stream.raise_for_status()
        for line in stream.iter_lines():
            if time.monotonic() - started > timeout:
                raise TimeoutError("analysis did not complete within the requested deadline")
            if not line.startswith("data:"):
                continue
            event = EVENTS.validate_json(line[5:].strip())
            if event.job_id != job.job_id:
                raise RuntimeError("received an event for a different analysis job")
            if event.type == "failed":
                raise RuntimeError(f"analysis failed: {event.code}: {event.message}")
            if event.type == "progress" and event.stage.value not in stages:
                stages.append(event.stage.value)
                print(f"  {event.stage.value}: {event.message}", flush=True)
            if event.type == "done":
                if stages != ["decode", "align", "extract", "compare", "explain"]:
                    raise RuntimeError(f"incomplete or out-of-order progress: {stages}")
                if event.report.participant.audio_sha256 != hashlib.sha256(audio).hexdigest():
                    raise RuntimeError("returned report does not belong to the uploaded audio")
                return event.report, stages, time.monotonic() - started
    raise RuntimeError("event stream ended without a completed analysis")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--demo", default="new-colossus.drag-l3")
    parser.add_argument(
        "--audio", type=Path, help="Use your own actual recording instead of a demo"
    )
    parser.add_argument("--transcript", type=Path, help="UTF-8 words actually spoken in --audio")
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--output", type=Path, default=Path("runs/live-validation"))
    args = parser.parse_args()
    if bool(args.audio) != bool(args.transcript):
        parser.error("provide both --audio and --transcript for a personal recording")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    args.output.mkdir(parents=True, exist_ok=True)
    summary: dict[str, object] = {"url": args.url, "workflow_passed": False}
    exit_code = 1
    try:
        with httpx.Client(base_url=args.url.rstrip("/"), timeout=args.timeout) as client:
            runtime_response = client.get("/api/runtime")
            runtime_response.raise_for_status()
            runtime = runtime_response.json()
            summary["runtime_before"] = runtime
            if runtime.get("requested_alignment_device") != "cuda" or not runtime.get(
                "cuda_available"
            ):
                raise RuntimeError("the running server must use CUDA; no CPU inference fallback")
            listing_response = client.get("/api/library")
            listing_response.raise_for_status()
            library = LibraryListing.model_validate(listing_response.json())
            summary["library_texts"] = len(library.entries)
            summary["library_demos"] = len(library.demos)
            expected_kinds: list[str] = []
            if args.audio:
                audio = args.audio.read_bytes()
                filename = args.audio.name
                options = AnalyzeOptions(transcript=args.transcript.read_text(encoding="utf-8"))
            else:
                demo = next((item for item in library.demos if item.clip_id == args.demo), None)
                if demo is None:
                    raise ValueError(f"demo not available in the running library: {args.demo}")
                entry = next(item for item in library.entries if item.text_id == demo.text_id)
                # Construct a same-origin path, never follow a URL supplied by library metadata.
                audio_response = client.get(f"/api/audio/{demo.clip_id}")
                audio_response.raise_for_status()
                audio, filename = audio_response.content, f"{demo.clip_id}.flac"
                options = AnalyzeOptions(transcript=entry.transcript, library_text_id=entry.text_id)
                expected_kinds = [kind.value for kind in demo.flaw_kinds]
            print(f"Live analysis: {filename}", flush=True)
            report, stages, elapsed = analyse(client, audio, filename, options, args.timeout)
            runtime_response = client.get("/api/runtime")
            runtime_response.raise_for_status()
            runtime_after = runtime_response.json()
            if not str(runtime_after.get("loaded_alignment_device", "")).startswith("cuda"):
                raise RuntimeError("completed analysis did not confirm a CUDA-loaded model")
            detected = sorted({region.kind.value for region in report.regions})
            for region in report.regions:
                print(f"  Finding: {region.explanation.headline}", flush=True)
            covered = set(expected_kinds) <= set(detected) if expected_kinds else None
            summary.update(
                workflow_passed=True,
                runtime_after=runtime_after,
                uploaded_audio_sha256=hashlib.sha256(audio).hexdigest(),
                seconds=elapsed,
                stages=stages,
                reference_mode=report.reference.basis,
                overall_score=report.overall,
                findings=len(report.regions),
                detected_flaw_kinds=detected,
                expected_flaw_kinds=expected_kinds,
                expected_flaws_observed=covered,
                limitation="One live workflow is not a full accuracy or generalization benchmark.",
            )
            (args.output / "report.json").write_text(report.model_dump_json(indent=2) + "\n")
            exit_code = 1 if covered is False else 0
    except Exception as error:
        summary["error"] = str(error)
    finally:
        text = json.dumps(summary, indent=2) + "\n"
        (args.output / "summary.json").write_text(text, encoding="utf-8")
        print(text, end="")
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
