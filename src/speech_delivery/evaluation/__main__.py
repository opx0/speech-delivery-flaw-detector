"""CLI entrypoint for running the seven-metric evaluation harness."""

import argparse
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

from .benchmark import run_evaluation


def main() -> None:
    parser = argparse.ArgumentParser(description="Seven-metric evaluation harness for Track C.")
    parser.add_argument(
        "--device",
        choices=("cpu", "cuda"),
        default=os.environ.get("SPEECH_DEVICE", "cpu"),
        help="Device for alignment inference. CUDA requires a CUDA-enabled PyTorch installation.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write metrics and per-clip findings to a JSON file",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("data/dataset"),
        help="Path to dataset directory containing manifest.json (default: data/dataset)",
    )
    parser.add_argument(
        "--calibration",
        type=Path,
        default=None,
        help="Path to calibration.json (default: <dataset>/calibration.json)",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run a quick smoke test on a subset of clips",
    )
    args = parser.parse_args()
    os.environ["SPEECH_DEVICE"] = args.device

    if not (args.dataset / "manifest.json").is_file():
        print(
            f"Error: dataset not found at {args.dataset}.\n"
            "Download and extract dataset v1 using the README instructions first."
        )
        sys.exit(1)

    limit = 10 if args.quick else None
    results = run_evaluation(args.dataset, args.calibration, max_clips_per_category=limit)
    print(results.format_table())
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(asdict(results), indent=2) + "\n", encoding="utf-8")

    all_passed = all(m.passed for m in results.metrics)
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
