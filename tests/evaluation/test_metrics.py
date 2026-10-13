import pytest

from speech_delivery.contract import FlawKind
from speech_delivery.evaluation.metrics import (
    Span,
    iou,
    match,
    median_boundary_error_ms,
    precision_recall,
    severity_spearman,
    type_accuracy,
)

RUSH = FlawKind.RUSH
DRAG = FlawKind.DRAG


def test_iou_is_overlap_over_union() -> None:
    assert iou(Span(RUSH, 0, 10), Span(RUSH, 5, 15)) == pytest.approx(5 / 15)
    assert iou(Span(RUSH, 0, 1), Span(RUSH, 2, 3)) == 0.0


def test_a_span_of_the_wrong_kind_never_matches_even_with_perfect_overlap() -> None:
    result = match([Span(RUSH, 0, 4)], [Span(DRAG, 0, 4)])

    assert result.pairs == ()
    assert precision_recall([result]) == (0.0, 0.0)


def test_each_span_is_used_once_so_a_duplicate_prediction_costs_precision() -> None:
    truth = [Span(RUSH, 0, 4)]
    predicted = [Span(RUSH, 0, 4), Span(RUSH, 0.2, 4.2)]

    precision, recall = precision_recall([match(truth, predicted)])

    assert precision == 0.5
    assert recall == 1.0


def test_median_boundary_error_is_in_milliseconds_over_both_edges() -> None:
    result = match([Span(RUSH, 10.0, 14.0)], [Span(RUSH, 10.1, 13.7)])

    assert median_boundary_error_ms([result]) == pytest.approx(200.0)
    assert median_boundary_error_ms([match([], [])]) is None


def test_type_accuracy_counts_only_flaws_that_something_overlaps() -> None:
    truth = [Span(RUSH, 0, 4), Span(DRAG, 10, 14), Span(RUSH, 20, 24)]
    predicted = [Span(RUSH, 0, 4), Span(RUSH, 10, 14)]

    assert type_accuracy(truth, predicted) == (1, 2)


def test_severity_spearman_is_minus_one_when_the_score_falls_with_every_level() -> None:
    assert severity_spearman([100, 96, 90, 75, 60]) == pytest.approx(-1.0)
    assert severity_spearman([100, 100, 100, 100, 100]) == 0.0
