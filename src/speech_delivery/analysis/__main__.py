"""Analyze one recording from the command line.

python -m speech_delivery.analysis recording.wav --text gettysburg-address
python -m speech_delivery.analysis recording.wav --transcript "words you said"
"""

import argparse
import sys
from pathlib import Path

from ..contract import AnalyzeOptions, Stage
from ..contract.report import BaselineReference
from ..library import Library
from .analyzer import build_analyzer
from .calibration import load_calibration
from .explain import clock
from .protocol import AnalysisError


def _progress(stage: Stage, fraction: float, message: str) -> None:
    print(f"  [{stage.value:<7}] {message}", file=sys.stderr, flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audio", type=Path, help="any file ffmpeg can read")
    parser.add_argument("--data", type=Path, default=Path("data/dataset"))
    parser.add_argument("--text", help="id of a library text (contrast mode)")
    parser.add_argument("--transcript", help="what was said. Defaults to the library text")
    parser.add_argument("--json", action="store_true", help="print the full report as JSON")
    args = parser.parse_args()

    library = Library.load(args.data)
    if args.text is None and args.transcript is None:
        parser.error("give --text (a library id) or --transcript")
    transcript: str = args.transcript or library.text(str(args.text)).transcript
    analyzer = build_analyzer(library, load_calibration(args.data / "calibration.json"))
    try:
        report = analyzer.analyze(
            args.audio,
            AnalyzeOptions(transcript=transcript, library_text_id=args.text),
            _progress,
        )
    except AnalysisError as error:
        print(f"{error.code.value}: {error.message}", file=sys.stderr)
        return 1

    if args.json:
        print(report.model_dump_json(indent=2))
        return 0
    mode = "contrast" if isinstance(report.reference, BaselineReference) else "normative"
    print(f"\n{args.audio.name}  {report.participant.duration_s:.1f}s  mode: {mode}")
    print(f"overall {report.overall:.0f}/100")
    for score in report.axis_scores:
        print(f"  {score.axis.value:<8} {score.score:5.0f}")
    print(f"\n{len(report.regions)} flagged region(s)")
    for region in report.regions:
        print(f"\n[{clock(region.start)}-{clock(region.end)}] {region.explanation.headline}")
        print(f'   "{region.explanation.quoted_text}"')
        print(f"   {region.explanation.detail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
