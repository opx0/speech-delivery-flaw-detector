"""The comparison on synthetic speech whose flaws sit at known places.

Recordings pair exact word times (from the synthesiser and the injector) with real feature
extraction, so these tests run without the 1 GB aligner.
"""

from pathlib import Path

import pytest
from pydantic import ValidationError
from tests.analysis.synth import synth_speech

from speech_delivery.analysis.calibration import (
    Calibration,
    default_calibration,
    load_calibration,
    save_calibration,
)
from speech_delivery.analysis.compare import Findings, compare_to_bands, compare_to_baseline
from speech_delivery.analysis.explain import Finding, explain
from speech_delivery.analysis.features import extract_features
from speech_delivery.analysis.recording import Recording
from speech_delivery.audio import Audio
from speech_delivery.contract import (
    BandReference,
    BaselineReference,
    FlawKind,
    FlawRegion,
    RubricWeights,
    WordAlignment,
)
from speech_delivery.contract.report import BandExpected, BaselineExpected
from speech_delivery.contract.taxonomy import FEATURE_SPECS, FLAW_SPECS
from speech_delivery.dataset.inject import Injected, make_control, make_flawed

PASSAGE = (
    "We gather here today to remember what came before us. "
    "The people who built this place worked through long winters and short harvests. "
    "They did not ask for praise, and they did not stop when the work grew hard. "
    "Their patience gave us the ground we now stand on. "
    "Every promise we keep is a debt we repay to them. "
    "So let us speak plainly about what lies ahead. "
    "The road will be long, but we will walk it together. "
    "And when it is done, we will say that we did not turn back."
)
BOUNDARY_TOLERANCE_S = 0.35
CALIBRATION = default_calibration()
WEIGHTS = RubricWeights()


def _recording(audio: Audio, alignment: WordAlignment) -> Recording:
    return Recording(alignment=alignment, features=extract_features(audio, alignment))


@pytest.fixture(scope="module")
def gold_source() -> tuple[Audio, WordAlignment]:
    pauses = {i: 0.6 for i, word in enumerate(PASSAGE.split()) if word.endswith(".")}
    return synth_speech(PASSAGE, pauses=pauses)


@pytest.fixture(scope="module")
def gold(gold_source: tuple[Audio, WordAlignment]) -> Recording:
    return _recording(*gold_source)


def _compare(injected: Injected, gold: Recording) -> Findings:
    return compare_to_baseline(
        _recording(injected.audio, injected.alignment),
        gold,
        "passage",
        "passage.gold",
        CALIBRATION,
        WEIGHTS,
    )


def _flawed(gold_source: tuple[Audio, WordAlignment], kind: FlawKind, level: int) -> Injected:
    audio, alignment = gold_source
    return make_flawed(audio, alignment, (kind,), level, 7)


def test_a_clean_control_has_no_flaws_and_a_perfect_score(
    gold_source: tuple[Audio, WordAlignment], gold: Recording
) -> None:
    audio, alignment = gold_source

    findings = _compare(make_control(audio, alignment), gold)

    assert findings.regions == ()
    assert findings.overall == pytest.approx(100.0, abs=0.5)


@pytest.mark.parametrize(
    "kind",
    [FlawKind.RUSH, FlawKind.DRAG, FlawKind.HESITATION, FlawKind.PAUSE_COLLAPSE],
)
def test_each_injected_region_is_found_near_where_it_was_put(
    gold_source: tuple[Audio, WordAlignment], gold: Recording, kind: FlawKind
) -> None:
    injected = _flawed(gold_source, kind, 3)

    findings = _compare(injected, gold)

    found = [(r.start, r.end) for r in findings.regions if r.kind is kind]
    assert len(found) >= len(injected.flaws) - 1
    for region_start, region_end in found:
        assert any(
            region_start < flaw.end + BOUNDARY_TOLERANCE_S
            and region_end > flaw.start - BOUNDARY_TOLERANCE_S
            for flaw in injected.flaws
        ), f"{kind.value} at {region_start:.1f}-{region_end:.1f} is not near an injected region"
    assert {r.axis for r in findings.regions if r.kind is kind} == {FLAW_SPECS[kind].axis}


def injected_words(gold_source: tuple[Audio, WordAlignment], region: FlawRegion) -> str:
    """The words the region covers, read from the gold text by index (the clips share words)."""
    words = PASSAGE.split()
    return " ".join(words[region.words.first : region.words.last + 1])


def test_a_rushed_region_reports_the_real_speed_up(
    gold_source: tuple[Audio, WordAlignment], gold: Recording
) -> None:
    findings = _compare(_flawed(gold_source, FlawKind.RUSH, 3), gold)

    region = next(r for r in findings.regions if r.kind is FlawKind.RUSH)
    assert isinstance(region.deviation.expected, BaselineExpected)
    ratio = region.deviation.observed / region.deviation.expected.value
    assert ratio == pytest.approx(1.5, abs=0.2)
    assert region.deviation.unit == FEATURE_SPECS[FLAW_SPECS[FlawKind.RUSH].feature].unit
    assert region.explanation.headline.startswith("Rushed pacing, 00:")
    assert region.explanation.quoted_text == injected_words(gold_source, region)


def test_the_cadence_score_falls_as_the_rush_gets_worse(
    gold_source: tuple[Audio, WordAlignment], gold: Recording
) -> None:
    def cadence(level: int) -> float:
        findings = _compare(_flawed(gold_source, FlawKind.RUSH, level), gold)
        return next(s.score for s in findings.axis_scores if s.axis.value == "cadence")

    scores = [cadence(level) for level in (2, 3, 4)]

    assert scores[0] > scores[1] > scores[2]
    assert scores[0] < 100.0


def test_the_report_reference_names_the_baseline_and_its_warp(
    gold_source: tuple[Audio, WordAlignment], gold: Recording
) -> None:
    findings = _compare(_flawed(gold_source, FlawKind.DRAG, 3), gold)

    assert isinstance(findings.reference, BaselineReference)
    assert findings.reference.clip_id == "passage.gold"
    assert len(findings.reference.warp) >= 2
    assert [o.feature.value for o in findings.overlay] == [
        "pitch",
        "pitch_variation",
        "speech_rate",
        "energy",
        "pause",
    ]


def test_normative_mode_flags_a_sustained_rush_but_not_a_normal_reading(
    gold: Recording,
) -> None:
    audio, alignment = synth_speech(PASSAGE, speed=360)
    participant = _recording(audio, alignment)

    findings = compare_to_bands(participant, CALIBRATION, WEIGHTS)

    assert isinstance(findings.reference, BandReference)
    rushed = [r for r in findings.regions if r.kind is FlawKind.RUSH]
    assert rushed
    assert all(isinstance(r.deviation.expected, BandExpected) for r in rushed)
    assert all("typical" in r.explanation.headline for r in rushed)
    assert all(r.deviation.observed > CALIBRATION.bands.rate.high for r in rushed)
    assert [
        r for r in compare_to_bands(gold, CALIBRATION, WEIGHTS).regions if r.kind is FlawKind.RUSH
    ] == []


def test_headline_and_detail_state_the_numbers_in_plain_words() -> None:
    finding = Finding(
        kind=FlawKind.RUSH,
        start=14.0,
        end=18.0,
        observed=4.7,
        expected=2.6,
        z=3.2,
        baseline=True,
        unit="words/s",
    )

    explanation = explain(finding, "we choose to go to the moon")

    assert explanation.headline == (
        "Rushed pacing, 00:14 to 00:18, 4.7 words/s against an expected 2.6 words/s"
    )
    assert explanation.quoted_text == "we choose to go to the moon"
    assert "81% higher than expected" in explanation.detail
    assert "3.2 reference spreads" in explanation.detail
    assert "gold reading of the same words" in explanation.detail


def test_short_regions_show_tenths_of_a_second() -> None:
    finding = Finding(FlawKind.ENERGY_FADE, 10.2, 10.7, -18.4, -12.8, 2.5, True, "dB")

    assert explain(finding, "back").headline.startswith("Fading energy, 00:10.2 to 00:10.7")


class TestCalibration:
    def test_round_trips_through_a_file_with_the_same_bytes(self, tmp_path: Path) -> None:
        path = tmp_path / "calibration.json"

        save_calibration(CALIBRATION, path)
        first = path.read_bytes()
        loaded = load_calibration(path)
        save_calibration(loaded, path)

        assert loaded == CALIBRATION
        assert path.read_bytes() == first

    def test_rejects_a_tampered_version(self) -> None:
        data = CALIBRATION.model_dump(mode="json")
        data["thresholds"]["rush"] = 3.0

        with pytest.raises(ValidationError, match="does not match its content"):
            Calibration.model_validate(data)

    def test_rejects_a_spread_below_its_floor(self) -> None:
        data = CALIBRATION.model_dump(mode="json")
        data["sigmas"]["cadence"] = 0.01

        with pytest.raises(ValidationError, match="below its floor"):
            Calibration.model_validate(data)
