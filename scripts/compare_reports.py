"""Compare native/container reports without rerunning audio or ignoring run stamps."""

import argparse
import json
from pathlib import Path

from speech_delivery.contract import Report


def compare(left: Report, right: Report) -> dict[str, object]:
    same_words = tuple(word.text for word in left.words.words) == tuple(
        word.text for word in right.words.words
    )
    boundary_delta = None
    if same_words:
        boundary_delta = max(
            abs(getattr(a, edge) - getattr(b, edge))
            for a, b in zip(left.words.words, right.words.words, strict=True)
            for edge in ("start", "end")
        )
    return {
        "canonical_byte_identity": left.model_dump_json() == right.model_dump_json(),
        "same_input_audio": left.participant.audio_sha256 == right.participant.audio_sha256,
        "same_run_stamp_and_weights": left.run == right.run and left.weights == right.weights,
        "same_transcript": same_words,
        "overall_score_difference": abs(left.overall - right.overall),
        "maximum_word_boundary_difference_s": boundary_delta,
        "left_region_count": len(left.regions),
        "right_region_count": len(right.regions),
        "limitation": (
            "Use reports from the same input and checkout; different configurations "
            "are not a reproducibility test."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("left", type=Path)
    parser.add_argument("right", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    left = Report.model_validate_json(args.left.read_text(encoding="utf-8"))
    right = Report.model_validate_json(args.right.read_text(encoding="utf-8"))
    result = compare(left, right)
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    raise SystemExit(0 if result["canonical_byte_identity"] else 1)


if __name__ == "__main__":
    main()
