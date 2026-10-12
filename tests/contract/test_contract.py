"""Behavior tests for the contract: what it accepts, what it refuses, and that it stays in sync."""

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import TypeAdapter, ValidationError

from speech_delivery.contract import (
    FLAW_SPECS,
    Axis,
    ClipRole,
    DatasetManifest,
    FlawKind,
    JobEvent,
    Report,
    RubricWeights,
    WordAlignment,
    WordSpan,
)
from speech_delivery.contract import fixtures as fx
from speech_delivery.contract.schema_export import render_bundle

ROOT = Path(__file__).resolve().parents[2]


def dump(model: Any) -> dict[str, Any]:
    return json.loads(model.model_dump_json())


def test_committed_fixtures_and_schema_match_the_models() -> None:
    for name, text in fx.render_all().items():
        assert (ROOT / "contract/fixtures" / name).read_text() == text, (
            f"{name} is stale, run make contract"
        )
    assert (ROOT / "contract/schema/contract.schema.json").read_text() == render_bundle()


def test_reports_round_trip_through_json_unchanged() -> None:
    for basis in ("baseline", "band"):
        original = fx.report(basis)
        assert Report.model_validate_json(original.model_dump_json()) == original


def test_job_events_parse_into_their_own_types() -> None:
    events = TypeAdapter(list[JobEvent]).validate_json(
        TypeAdapter(list[JobEvent]).dump_json(fx.job_events())
    )
    assert [event.type for event in events] == ["progress"] * 5 + ["failed"]


def test_every_flaw_kind_names_the_axis_and_feature_that_judge_it() -> None:
    assert {kind: spec.axis for kind, spec in FLAW_SPECS.items()} == {
        FlawKind.RUSH: Axis.CADENCE,
        FlawKind.DRAG: Axis.CADENCE,
        FlawKind.MONOTONE: Axis.TONE,
        FlawKind.HESITATION: Axis.PAUSES,
        FlawKind.PAUSE_COLLAPSE: Axis.PAUSES,
        FlawKind.ENERGY_FADE: Axis.VOLUME,
    }


class TestWordAlignment:
    def test_rejects_overlapping_words(self) -> None:
        data = dump(fx.BASELINE_WORDS)
        data["words"][1]["start"] = data["words"][0]["end"] - 0.1
        with pytest.raises(ValidationError, match="overlap"):
            WordAlignment.model_validate(data)

    def test_rejects_sentences_that_leave_words_uncovered(self) -> None:
        data = dump(fx.BASELINE_WORDS)
        data["sentences"] = data["sentences"][:-1]
        with pytest.raises(ValidationError, match="cover every word"):
            WordAlignment.model_validate(data)

    def test_quotes_the_words_in_a_span(self) -> None:
        assert fx.BASELINE_WORDS.quote(WordSpan(first=0, last=2)) == "Four score and"


class TestRubricWeights:
    def test_defaults_are_equal_and_sum_to_one(self) -> None:
        weights = RubricWeights()
        assert [weights.weight(axis) for axis in Axis] == [0.25, 0.25, 0.25, 0.25]

    def test_rejects_weights_that_do_not_sum_to_one(self) -> None:
        with pytest.raises(ValidationError, match="sum to 1"):
            RubricWeights(cadence=0.5, tone=0.5, pauses=0.5, volume=0.0)


class TestReport:
    def test_rejects_baseline_evidence_inside_a_normative_report(self) -> None:
        data = dump(fx.report("band"))
        data["regions"][0]["deviation"]["expected"] = {"basis": "baseline", "value": 2.6}
        with pytest.raises(ValidationError, match="was not measured against the band"):
            Report.model_validate(data)

    def test_rejects_an_overall_score_that_is_not_the_weighted_mean(self) -> None:
        data = dump(fx.report("baseline"))
        data["overall"] = data["overall"] + 1
        with pytest.raises(ValidationError, match="weighted mean"):
            Report.model_validate(data)

    def test_rejects_a_flaw_filed_under_the_wrong_axis(self) -> None:
        data = dump(fx.report("baseline"))
        data["regions"][0]["axis"] = "tone"
        with pytest.raises(ValidationError, match="belongs to the cadence axis"):
            Report.model_validate(data)

    def test_rejects_a_missing_axis_score(self) -> None:
        data = dump(fx.report("baseline"))
        data["axis_scores"] = data["axis_scores"][:-1]
        with pytest.raises(ValidationError, match="one score per axis"):
            Report.model_validate(data)

    def test_rejects_unknown_fields(self) -> None:
        data = dump(fx.report("baseline"))
        data["confidence"] = "high"
        with pytest.raises(ValidationError, match="confidence"):
            Report.model_validate(data)


class TestDatasetManifest:
    def test_fixture_covers_every_clip_role_shape(self) -> None:
        roles = {clip.role for clip in fx.manifest().clips}
        assert roles == {
            ClipRole.GOLD,
            ClipRole.CONTROL,
            ClipRole.FLAWED,
            ClipRole.SPEAKER_SHIFTED,
            ClipRole.NATURAL_READER,
            ClipRole.HUMAN_FLAWED,
        }

    def clip(self, data: dict[str, Any], clip_id: str) -> dict[str, Any]:
        return next(c for c in data["clips"] if c["id"].endswith(clip_id))

    def test_rejects_a_flawed_clip_without_flaw_labels(self) -> None:
        data = dump(fx.manifest())
        self.clip(data, "rush-l3")["flaws"] = []
        with pytest.raises(ValidationError, match="need flaw labels"):
            DatasetManifest.model_validate(data)

    def test_rejects_a_control_clip_that_carries_a_flaw(self) -> None:
        data = dump(fx.manifest())
        self.clip(data, "control")["flaws"] = self.clip(data, "rush-l3")["flaws"]
        with pytest.raises(ValidationError, match="must not have flaw labels"):
            DatasetManifest.model_validate(data)

    def test_rejects_human_recordings_in_the_calibration_split(self) -> None:
        data = dump(fx.manifest())
        self.clip(data, "human-mono")["split"] = "calibration"
        with pytest.raises(ValidationError, match="held out for testing"):
            DatasetManifest.model_validate(data)

    def test_rejects_injection_parameters_that_contradict_the_flaw_kind(self) -> None:
        data = dump(fx.manifest())
        flaw = self.clip(data, "rush-l3")["flaws"][0]
        flaw["kind"] = "drag"
        with pytest.raises(ValidationError, match="do not match the flaw kind"):
            DatasetManifest.model_validate(data)

    def test_rejects_a_baseline_that_is_not_a_gold_clip_of_the_same_text(self) -> None:
        data = dump(fx.manifest())
        self.clip(data, "control")["baseline_clip_id"] = self.clip(data, "rush-l3")["id"]
        with pytest.raises(ValidationError, match="gold clip of the same text"):
            DatasetManifest.model_validate(data)

    def test_rejects_a_path_that_escapes_the_dataset(self) -> None:
        data = dump(fx.manifest())
        self.clip(data, "gold")["audio"]["path"] = "../elsewhere.flac"
        with pytest.raises(ValidationError, match="relative"):
            DatasetManifest.model_validate(data)

    def test_rejects_a_mirror_of_an_extemporaneous_text(self) -> None:
        data = dump(fx.manifest())
        data["texts"][0]["category"] = "extemporaneous"
        with pytest.raises(ValidationError, match="can only be a normative reference"):
            DatasetManifest.model_validate(data)


class TestLibraryListing:
    def test_round_trips_and_keeps_demo_flaw_kinds(self) -> None:
        from speech_delivery.contract import LibraryListing

        original = fx.library_listing()
        restored = LibraryListing.model_validate_json(original.model_dump_json())
        assert restored == original
        assert restored.demos[0].flaw_kinds == (FlawKind.RUSH,)
        assert restored.entries[0].baseline_audio_url == "/api/audio/gettysburg-address.gold"

    def test_rejects_a_demo_level_above_four(self) -> None:
        from speech_delivery.contract import LibraryListing

        data = dump(fx.library_listing())
        data["demos"][0]["level"] = 5
        with pytest.raises(ValidationError):
            LibraryListing.model_validate(data)
