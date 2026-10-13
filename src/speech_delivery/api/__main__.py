"""Serve the dashboard and API: `python -m speech_delivery.api --data data/dataset ...`."""

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m speech_delivery.api")
    parser.add_argument("--data", type=Path, default=Path("data/dataset"))
    parser.add_argument("--calibration", type=Path, default=Path("data/dataset/calibration.json"))
    parser.add_argument("--web", type=Path, default=Path("web/dist"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    # Imported here so that importing the api package never imports torch.
    import uvicorn

    from ..analysis.analyzer import build_analyzer
    from ..analysis.calibration import load_calibration
    from ..library import Library
    from .app import create_app

    library = Library.load(args.data)
    analyzer = build_analyzer(library, load_calibration(args.calibration))
    uvicorn.run(create_app(library, analyzer, args.web), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
