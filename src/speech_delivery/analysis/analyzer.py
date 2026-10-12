"""The analyzer the API runs: an upload in, a `Report` out."""

import hashlib
import threading
from collections.abc import Callable
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from ..audio import Audio, AudioDecodeError, decode
from ..contract import (
    AnalyzeOptions,
    ErrorCode,
    Report,
    RubricWeights,
    Stage,
)
from ..contract.jobs import MAX_UPLOAD_SECONDS
from ..contract.report import ModelStamp, ParticipantInfo, RunStamp
from ..library import Library
from ..text import similarity
from .calibration import Calibration
from .compare import Findings, compare_to_bands, compare_to_baseline
from .protocol import AnalysisError, Analyzer, ProgressSink
from .recording import Recording
from .signal import analyze_signal

SignalFn = Callable[[Audio, str], Recording]
MATCH_THRESHOLD = 0.9
ALIGNER = ModelStamp(name="torchaudio MMS_FA", revision="ctc_alignment_mling_uroman")


def _package_version() -> str:
    try:
        return version("speech-delivery")
    except PackageNotFoundError:
        return "0.0.0"


class _Analyzer:
    def __init__(self, library: Library, calibration: Calibration, signal: SignalFn) -> None:
        self._library = library
        self._calibration = calibration
        self._signal = signal
        self._baselines: dict[str, Recording] = {}
        self._lock = threading.Lock()

    def _baseline(self, clip_id: str) -> Recording:
        with self._lock:
            cached = self._baselines.get(clip_id)
        if cached is not None:
            return cached
        clip = self._library.clip(clip_id)
        text = self._library.text(clip.text_id)
        recording = self._signal(self._library.audio(clip_id), text.transcript)
        with self._lock:
            self._baselines[clip_id] = recording
        return recording

    def _text_for(self, options: AnalyzeOptions) -> str | None:
        """The library text this upload reads, or None for normative mode."""
        if options.library_text_id is None:
            matched = self._library.match_text(options.transcript)
            return matched.id if matched else None
        try:
            text = self._library.text(options.library_text_id)
        except KeyError:
            raise AnalysisError(
                ErrorCode.TRANSCRIPT_MISMATCH, f"Unknown library text {options.library_text_id}."
            ) from None
        if similarity(options.transcript, text.transcript) < MATCH_THRESHOLD:
            raise AnalysisError(
                ErrorCode.TRANSCRIPT_MISMATCH,
                f"The transcript does not match the library text '{text.title}'.",
            )
        return text.id

    def analyze(self, audio_path: Path, options: AnalyzeOptions, progress: ProgressSink) -> Report:
        progress(Stage.DECODE, 0.0, "Decoding the recording")
        try:
            audio = decode(audio_path)
        except AudioDecodeError as error:
            raise AnalysisError(ErrorCode.UNSUPPORTED_AUDIO, str(error)) from error
        if audio.duration_s > MAX_UPLOAD_SECONDS:
            raise AnalysisError(
                ErrorCode.TOO_LONG,
                f"The recording is {audio.duration_s / 60:.1f} minutes. The limit is "
                f"{MAX_UPLOAD_SECONDS // 60} minutes.",
            )
        digest = hashlib.sha256(audio_path.read_bytes()).hexdigest()
        progress(Stage.DECODE, 1.0, "Recording decoded")

        text_id = self._text_for(options)
        progress(Stage.ALIGN, 0.0, "Aligning the words to the audio")
        participant = self._signal(audio, options.transcript)
        progress(Stage.EXTRACT, 1.0, "Acoustic features extracted")

        weights = options.weights or RubricWeights()
        progress(Stage.COMPARE, 0.0, "Comparing with the reference")
        findings: Findings
        if text_id is None:
            findings = compare_to_bands(participant, self._calibration, weights)
        else:
            gold = self._library.gold_for(text_id)
            findings = compare_to_baseline(
                participant, self._baseline(gold.id), text_id, gold.id, self._calibration, weights
            )
        progress(Stage.COMPARE, 1.0, "Comparison finished")
        progress(Stage.EXPLAIN, 1.0, f"{len(findings.regions)} flaw regions explained")

        return Report(
            participant=ParticipantInfo(
                filename=audio_path.name, duration_s=audio.duration_s, audio_sha256=digest
            ),
            reference=findings.reference,
            words=participant.alignment,
            weights=weights,
            axis_scores=findings.axis_scores,
            overall=findings.overall,
            regions=findings.regions,
            overlay=findings.overlay,
            run=RunStamp(
                package_version=_package_version(),
                config_hash=hashlib.sha256(f"{self._calibration.version}".encode()).hexdigest(),
                seed=0,
                models=(ALIGNER,),
            ),
        )


def build_analyzer(
    library: Library, calibration: Calibration, *, signal: SignalFn = analyze_signal
) -> Analyzer:
    return _Analyzer(library, calibration, signal)
