"""Serve the dashboard and API: `python -m speech_delivery.api --data data/dataset ...`."""

import argparse
import hashlib
import logging
import os
from copy import deepcopy
from pathlib import Path


class ComponentFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.__dict__["component"] = (
            "ALIGNMENT"
            if record.name.endswith(".align")
            else "ANALYSIS"
            if record.name.endswith(".registry")
            else "STARTUP"
        )
        return True


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m speech_delivery.api")
    parser.add_argument("--data", type=Path, default=Path("data/dataset"))
    parser.add_argument("--calibration", type=Path, default=Path("data/dataset/calibration.json"))
    parser.add_argument("--web", type=Path, default=Path("web/dist"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--log-file", type=Path, help="Append readable processing logs to this file"
    )
    parser.add_argument(
        "--history",
        type=Path,
        default=Path("runs/history.sqlite3"),
        help="Local report-only run journal",
    )
    args = parser.parse_args()

    processing_logger = logging.getLogger("speech_delivery")
    processing_logger.setLevel(logging.INFO)
    processing_logger.propagate = False
    formatter = logging.Formatter(
        "[BACKEND][%(component)s] %(asctime)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    processing_logger.addFilter(ComponentFilter())
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    console.addFilter(ComponentFilter())
    processing_logger.addHandler(console)
    if args.log_file:
        args.log_file.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(args.log_file, encoding="utf-8")
        handler.setFormatter(formatter)
        handler.addFilter(ComponentFilter())
        processing_logger.addHandler(handler)

    # Imported here so that importing the api package never imports torch.
    import uvicorn
    from uvicorn.config import LOGGING_CONFIG

    from ..analysis.align import runtime_info
    from ..analysis.analyzer import ALIGNER, MATCH_THRESHOLD, build_analyzer
    from ..analysis.calibration import load_calibration
    from ..library import Library
    from .app import create_app
    from .history import RunHistory

    library = Library.load(args.data)
    calibration = load_calibration(args.calibration)
    analyzer = build_analyzer(library, calibration)
    history = RunHistory(
        args.history,
        {
            "calibration": calibration.model_dump(mode="json"),
            "alignment_model": ALIGNER.model_dump(mode="json"),
            "transcript_match_threshold": MATCH_THRESHOLD,
            "runtime_at_startup": runtime_info(),
            "dataset_manifest_sha256": hashlib.sha256(
                (args.data / "manifest.json").read_bytes()
            ).hexdigest(),
        },
    )
    processing_logger.info(
        "RUN HISTORY | reports only | local journal=%s | audio is not retained", args.history
    )
    processing_logger.info(
        "API starting | requested_alignment_device=%s | texts=%d demos=%d | "
        "model loads on first analysis",
        os.environ.get("SPEECH_DEVICE", "cpu"),
        len(library.listing().entries),
        len(library.listing().demos),
    )
    log_config = deepcopy(LOGGING_CONFIG)
    log_config["formatters"]["default"]["fmt"] = "[BACKEND][SERVER] %(levelprefix)s %(message)s"
    log_config["formatters"]["access"]["fmt"] = (
        "[BACKEND][HTTP] %(levelprefix)s %(request_line)s %(status_code)s"
    )
    uvicorn.run(
        create_app(library, analyzer, args.web, history=history),
        host=args.host,
        port=args.port,
        log_config=log_config,
    )


if __name__ == "__main__":
    main()
