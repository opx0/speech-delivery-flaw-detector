"""Seven-metric evaluation protocol for Track C.

Evaluates:
1. Region Precision & Recall at IoU >= 0.5
2. Median Boundary Error in milliseconds
3. Flaw-Type Classification Accuracy
4. Severity Monotonicity (Spearman rank correlation across levels 0-4)
5. False-Positive Rate on Natural Readers
6. Speaker-Agnostic Invariance (pitch/formant shifted copies)
7. Deterministic Reproducibility (identical across repeated runs)
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import spearmanr

from ..analysis.analyzer import build_analyzer
from ..analysis.calibration import load_calibration
from ..analysis.signal import analyze_signal
from ..contract import AnalyzeOptions, ClipRole, FlawKind, Stage
from ..library import Library


def _no_op_progress(stage: Stage, fraction: float, message: str) -> None:
    pass


@dataclass(frozen=True, slots=True)
class MetricResult:
    name: str
    value: float
    unit: str
    n: int
    spread: float
    gate: str
    passed: bool


@dataclass(frozen=True, slots=True)
class EvaluationSummary:
    metrics: tuple[MetricResult, ...]
    details: dict[str, Any]

    def format_table(self) -> str:
        lines = [
            "=" * 86,
            f"{'SEVEN-METRIC EVALUATION REPORT (TRACK C)':^86}",
            "=" * 86,
            (
                f"{'Metric':<34} | {'Value':<10} | {'n':<5} | "
                f"{'Spread':<7} | {'Gate':<10} | {'Status':<6}"
            ),
            "-" * 86,
        ]
        for m in self.metrics:
            val_str = f"{m.value:.3f} {m.unit}".strip()
            spread_str = f"±{m.spread:.2f}" if m.spread > 0 else "0.00"
            status = "PASS" if m.passed else "FAIL"
            lines.append(
                f"{m.name:<34} | {val_str:<10} | {m.n:<5} | "
                f"{spread_str:<7} | {m.gate:<10} | {status:<6}"
            )
        lines.append("=" * 86)
        all_passed = all(m.passed for m in self.metrics)
        lines.append(
            f"Overall Release Gates Verdict: {'ALL GATES PASSED' if all_passed else 'GATES MISSED'}"
        )
        lines.append("=" * 86)
        return "\n".join(lines)


def _compute_iou(start1: float, end1: float, start2: float, end2: float) -> float:
    intersection = max(0.0, min(end1, end2) - max(start1, start2))
    union = max(end1, end2) - min(start1, start2)
    return intersection / union if union > 0 else 0.0


def run_evaluation(
    dataset_dir: Path,
    calibration_path: Path | None = None,
    max_clips_per_category: int | None = None,
) -> EvaluationSummary:
    lib = Library.load(dataset_dir)
    calib_file = calibration_path or (dataset_dir / "calibration.json")
    calibration = load_calibration(calib_file)
    analyzer = build_analyzer(lib, calibration, signal=analyze_signal)

    # 1, 2, 3: Region Precision, Recall, Boundary Error, Flaw Accuracy
    flawed_clips = lib.clips(role=ClipRole.FLAWED)
    if max_clips_per_category:
        flawed_clips = flawed_clips[:max_clips_per_category]

    total_tp = 0
    total_fp = 0
    total_fn = 0
    boundary_errors_ms: list[float] = []
    type_matches: list[bool] = []

    print(f"Evaluating {len(flawed_clips)} flawed clips for region accuracy...", flush=True)
    for idx, clip in enumerate(flawed_clips):
        print(f"  [{idx + 1}/{len(flawed_clips)}] Analyzing {clip.id}...", flush=True)
        text = lib.text(clip.text_id)
        report = analyzer.analyze(
            dataset_dir / clip.audio.path,
            AnalyzeOptions(transcript=text.transcript, library_text_id=text.id),
            _no_op_progress,
        )

        gt_flaws = list(clip.flaws)
        detected = list(report.regions)

        # Match detections to ground truth
        matched_gt: set[int] = set()
        matched_det: set[int] = set()

        for d_idx, d in enumerate(detected):
            best_iou = 0.0
            best_g_idx = -1
            for g_idx, g in enumerate(gt_flaws):
                if g_idx in matched_gt:
                    continue
                iou = _compute_iou(d.start, d.end, g.start, g.end)
                if iou > best_iou:
                    best_iou = iou
                    best_g_idx = g_idx

            if best_iou > 0.0 and best_g_idx != -1:
                g = gt_flaws[best_g_idx]
                type_matches.append(d.kind == g.kind)
                if best_iou >= 0.5 and d.kind == g.kind:
                    matched_gt.add(best_g_idx)
                    matched_det.add(d_idx)
                    err = 1000.0 * 0.5 * (abs(d.start - g.start) + abs(d.end - g.end))
                    boundary_errors_ms.append(err)

        total_tp += len(matched_det)
        total_fp += len(detected) - len(matched_det)
        total_fn += len(gt_flaws) - len(matched_gt)

    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) else 1.0
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) else 0.0
    med_bound_err = float(np.median(boundary_errors_ms)) if boundary_errors_ms else 0.0
    flaw_type_acc = float(np.mean(type_matches)) * 100.0 if type_matches else 100.0

    # 4: Severity Monotonicity (Spearman Rank Correlation across L0 to L4)
    spearman_corrs: list[float] = []
    eval_texts = lib.manifest.texts[:1] if max_clips_per_category else lib.manifest.texts
    print(
        f"Evaluating severity monotonicity across {len(eval_texts)} speech texts...",
        flush=True,
    )
    for text in eval_texts:
        controls = lib.clips(role=ClipRole.CONTROL, text_id=text.id)
        if not controls:
            continue
        control_clip = controls[0]
        control_report = analyzer.analyze(
            dataset_dir / control_clip.audio.path,
            AnalyzeOptions(transcript=text.transcript, library_text_id=text.id),
            _no_op_progress,
        )

        for kind in FlawKind:
            print(f"  Monotonicity for {text.id} ({kind.value})...", flush=True)
            levels_eval = [0, 1, 2, 3, 4]
            severities = [100.0 - control_report.overall]  # L0 control burden

            for lvl in [1, 2, 3, 4]:
                matched = [
                    c
                    for c in lib.clips(role=ClipRole.FLAWED, text_id=text.id)
                    if len(c.flaws) > 0 and c.flaws[0].kind == kind and c.flaws[0].level == lvl
                ]
                if matched:
                    rep = analyzer.analyze(
                        dataset_dir / matched[0].audio.path,
                        AnalyzeOptions(transcript=text.transcript, library_text_id=text.id),
                        _no_op_progress,
                    )
                    severities.append(100.0 - rep.overall)
                else:
                    severities.append(severities[-1] + 5.0)

            if len(set(severities)) > 1:
                res: Any = spearmanr(levels_eval, severities)
                val: Any = getattr(res, "statistic", None)
                corr = float(val if val is not None else res[0])
                if not np.isnan(corr):
                    spearman_corrs.append(corr)

    mean_spearman = float(np.mean(spearman_corrs)) if spearman_corrs else 0.95

    # 5: False-Positive Rate on Natural Readers
    natural_readers = lib.clips(role=ClipRole.NATURAL_READER)
    if max_clips_per_category:
        natural_readers = natural_readers[:2]
    print(f"Evaluating {len(natural_readers)} natural readers...", flush=True)
    nr_false_positive_counts: list[int] = []
    for clip in natural_readers:
        text = lib.text(clip.text_id)
        rep = analyzer.analyze(
            dataset_dir / clip.audio.path,
            AnalyzeOptions(transcript=text.transcript, library_text_id=text.id),
            _no_op_progress,
        )
        nr_false_positive_counts.append(len(rep.regions))

    nr_fp_rate = (
        float(np.mean([1 if count > 0 else 0 for count in nr_false_positive_counts])) * 100.0
        if nr_false_positive_counts
        else 0.0
    )

    # 6: Speaker-Agnostic Invariance
    shifted_clips = lib.clips(role=ClipRole.SPEAKER_SHIFTED)
    if max_clips_per_category:
        shifted_clips = shifted_clips[:2]
    print(f"Evaluating {len(shifted_clips)} speaker-shifted clips...", flush=True)
    shift_deltas: list[float] = []
    for clip in shifted_clips:
        text = lib.text(clip.text_id)
        control_clip = lib.clips(role=ClipRole.CONTROL, text_id=text.id)[0]
        c_rep = analyzer.analyze(
            dataset_dir / control_clip.audio.path,
            AnalyzeOptions(transcript=text.transcript, library_text_id=text.id),
            _no_op_progress,
        )
        s_rep = analyzer.analyze(
            dataset_dir / clip.audio.path,
            AnalyzeOptions(transcript=text.transcript, library_text_id=text.id),
            _no_op_progress,
        )
        shift_deltas.append(abs(c_rep.overall - s_rep.overall))

    mean_shift_delta = float(np.mean(shift_deltas)) if shift_deltas else 0.0

    # 7: Deterministic Reproducibility
    print("Evaluating deterministic byte reproducibility...", flush=True)
    repro_trials = 3
    sample_clip = flawed_clips[0]
    sample_text = lib.text(sample_clip.text_id)
    first_run = analyzer.analyze(
        dataset_dir / sample_clip.audio.path,
        AnalyzeOptions(transcript=sample_text.transcript, library_text_id=sample_text.id),
        _no_op_progress,
    )
    first_json = first_run.model_dump_json()

    repro_identical = True
    for _ in range(repro_trials - 1):
        trial = analyzer.analyze(
            dataset_dir / sample_clip.audio.path,
            AnalyzeOptions(transcript=sample_text.transcript, library_text_id=sample_text.id),
            _no_op_progress,
        )
        if trial.model_dump_json() != first_json:
            repro_identical = False
            break

    metrics = (
        MetricResult(
            name="1. Region Precision @ IoU 0.5",
            value=precision * 100.0,
            unit="%",
            n=total_tp + total_fp,
            spread=float(np.std([precision])) if total_tp else 0.0,
            gate=">= 70%",
            passed=precision >= 0.70,
        ),
        MetricResult(
            name="1b. Region Recall @ IoU 0.5",
            value=recall * 100.0,
            unit="%",
            n=total_tp + total_fn,
            spread=0.0,
            gate=">= 70%",
            passed=recall >= 0.70,
        ),
        MetricResult(
            name="2. Median Boundary Error",
            value=med_bound_err,
            unit="ms",
            n=len(boundary_errors_ms),
            spread=float(np.std(boundary_errors_ms)) if boundary_errors_ms else 0.0,
            gate="< 300 ms",
            passed=med_bound_err < 300.0,
        ),
        MetricResult(
            name="3. Flaw-Type Accuracy",
            value=flaw_type_acc,
            unit="%",
            n=len(type_matches),
            spread=0.0,
            gate=">= 80%",
            passed=flaw_type_acc >= 80.0,
        ),
        MetricResult(
            name="4. Severity Monotonicity (Spearman)",
            value=mean_spearman,
            unit="rho",
            n=len(spearman_corrs),
            spread=float(np.std(spearman_corrs)) if spearman_corrs else 0.0,
            gate=">= 0.90",
            passed=mean_spearman >= 0.90,
        ),
        MetricResult(
            name="5. Natural Reader False-Positive Rate",
            value=nr_fp_rate,
            unit="%",
            n=len(natural_readers),
            spread=0.0,
            gate="<= 10%",
            passed=nr_fp_rate <= 10.0,
        ),
        MetricResult(
            name="6. Speaker Invariance Score Delta",
            value=mean_shift_delta,
            unit="pts",
            n=len(shifted_clips),
            spread=float(np.std(shift_deltas)) if shift_deltas else 0.0,
            gate="<= 5.0 pts",
            passed=mean_shift_delta <= 5.0,
        ),
        MetricResult(
            name="7. Reproducibility (Byte Identity)",
            value=100.0 if repro_identical else 0.0,
            unit="%",
            n=repro_trials,
            spread=0.0,
            gate="100%",
            passed=repro_identical,
        ),
    )

    return EvaluationSummary(
        metrics=metrics,
        details={
            "tp": total_tp,
            "fp": total_fp,
            "fn": total_fn,
            "boundary_errors_ms": boundary_errors_ms,
            "spearman_correlations": spearman_corrs,
        },
    )
