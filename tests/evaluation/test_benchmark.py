from collections import Counter
from pathlib import Path

import pytest

from speech_delivery.analysis.analyzer import SignalFn
from speech_delivery.analysis.calibration import Calibration
from speech_delivery.analysis.protocol import Analyzer, ProgressSink
from speech_delivery.contract import AnalyzeOptions, ClipRole, Report, Split
from speech_delivery.evaluation import benchmark
from speech_delivery.library import Library

ROOT = Path(__file__).resolve().parents[2]


def test_reader_split_report_reuse_and_fresh_reproducibility(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    library = Library.load(ROOT / "data/dataset")
    report = Report.model_validate_json(
        (ROOT / "contract/fixtures/report_contrast.json").read_text("utf-8")
    )
    calls: Counter[str] = Counter()

    class FixedAnalyzer:
        def analyze(
            self, audio_path: Path, options: AnalyzeOptions, progress: ProgressSink
        ) -> Report:
            calls[audio_path.stem] += 1
            return report

    def build_fixed(library: Library, calibration: Calibration, *, signal: SignalFn) -> Analyzer:
        return FixedAnalyzer()

    monkeypatch.setattr(benchmark, "build_analyzer", build_fixed)
    results = benchmark.run_evaluation(ROOT / "data/dataset")

    reader_metric = next(metric for metric in results.metrics if "False-Positive" in metric.name)
    assert reader_metric.n == 3
    for clip in library.clips(role=ClipRole.NATURAL_READER, split=Split.CALIBRATION):
        assert calls[clip.id] == 0
    for clip in library.clips(role=ClipRole.NATURAL_READER, split=Split.TEST):
        assert calls[clip.id] == 1
    for clip in library.clips(role=ClipRole.CONTROL):
        assert calls[clip.id] == 1

    sample = library.clips(role=ClipRole.FLAWED)[0]
    assert calls[sample.id] == 4
    assert all(calls[clip.id] == 1 for clip in library.clips(role=ClipRole.FLAWED)[1:])
    monotonicity = next(metric for metric in results.metrics if "Spearman" in metric.name)
    assert monotonicity.n == 36
    assert monotonicity.value == 0.0
    assert not monotonicity.passed
