import pytest
from pydantic import ValidationError

from backend.app.domain import Asset, Box, Change, Cue, Proposal, StorySpec, presentation_errors
from backend.app.validators.parsers import seconds_to_srt_timecode
from .fixtures import make_project


@pytest.mark.parametrize("data", [
    {"id": "x", "start": 5, "end": 4, "text": "invalid timing"},
    {"id": "../unsafe", "start": 1, "end": 4, "text": "unsafe identifier"},
    {"id": "x", "start": 1, "end": 4, "text": ""},
    {"id": "x", "start": float("nan"), "end": 4, "text": "invalid number"},
])
def test_invalid_input_cues_are_rejected(data):
    with pytest.raises(ValidationError):
        Cue.model_validate(data)


def test_out_of_frame_clue_boxes_are_rejected():
    with pytest.raises(ValidationError, match="inside"):
        Box(x=.9, y=.1, width=.2, height=.1)


def test_asset_hash_tracks_actual_content_not_revision_counter():
    asset = make_project().assets[0]
    original_hash = asset.content_hash()
    asset.revision += 1
    assert asset.content_hash() == original_hash
    asset.cues[0].text = "Hay 14 supervivientes."
    assert asset.content_hash() != original_hash


def test_asset_hash_is_stable_across_persistence_round_trip():
    asset = make_project().assets[0]
    recovered = Asset.model_validate_json(asset.model_dump_json())
    assert recovered.content_hash() == asset.content_hash()


def test_approval_digest_detects_changed_patch_or_rationale():
    asset = make_project().assets[0]
    replacement = asset.cues[0].model_copy(update={"text": "Hay 14 supervivientes."})
    proposal = Proposal(finding_ids=["finding"], rationale="Restore canonical count", changes=[
        Change(asset_id=asset.id, base_hash=asset.content_hash(), cue_id=replacement.id, replacement=replacement)
    ])
    expected = proposal.approval_digest()
    proposal.approved_by = "reviewer"
    assert proposal.approval_digest() == expected
    proposal.changes[0].replacement.text = "Hay 114 supervivientes."
    assert proposal.approval_digest() != expected


def test_mismatched_replacement_cue_cannot_be_constructed():
    with pytest.raises(ValidationError, match="ID must match"):
        Change(asset_id="asset", base_hash="hash", cue_id="one", replacement=Cue(id="two", start=1, end=3, text="bad"))


def test_presentation_detects_overlap_and_excessive_reading_speed():
    asset = make_project(clean=True).assets[0]
    asset.cues = [Cue(id="one", start=1, end=2, text="x" * 30), Cue(id="two", start=1.5, end=4, text="Second")]
    assert presentation_errors(asset) == [
        "one: exceeds configured 25 characters/second", "two: overlaps cue one"
    ]


def test_duplicate_invariant_ids_cannot_make_evidence_ambiguous():
    spec = make_project().spec
    spec.invariants.append(spec.invariants[0].model_copy(deep=True))
    with pytest.raises(ValidationError, match="unique"):
        StorySpec.model_validate(spec.model_dump())


@pytest.mark.parametrize("seconds,expected", [(59.9996, "00:01:00,000"), (3599.9996, "01:00:00,000")])
def test_export_timecode_rounds_across_minute_and_hour_boundaries(seconds, expected):
    assert seconds_to_srt_timecode(seconds) == expected
