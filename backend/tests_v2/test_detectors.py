import pytest

from backend.app.detectors import scan
from backend.app.domain import Box
from .fixtures import make_project


def test_five_planted_failures_have_specific_evidence_and_locations():
    findings = scan(make_project())
    actual = {(f.kind, f.asset_id, f.cue_id, f.severity) for f in findings}
    assert actual == {
        ("NUMBER", "es-episode", "number", "REVIEW"),
        ("REVEAL", "es-episode", "reveal", "ERROR"),
        ("CLUE", "es-episode", "clue", "ERROR"),
        ("SOUND", "en-sdh", None, "REVIEW"),
        ("DIALOGUE", "en-ad", "description", "ERROR"),
    }
    assert len(findings) == 5
    assert all(f.evidence.startswith("Synthetic") for f in findings)
    assert next(f for f in findings if f.kind == "DIALOGUE").start == 41
    assert "3.00s" in next(f.description for f in findings if f.kind == "DIALOGUE")


def test_corrected_controls_produce_no_findings():
    assert scan(make_project(clean=True)) == []


@pytest.mark.parametrize("offset", [-5, 7])
def test_derivative_timeline_maps_to_master(offset):
    project = make_project()
    for asset in project.assets:
        asset.master_offset = offset
        for cue in asset.cues:
            cue.start -= offset
            cue.end -= offset
    assert sorted(f.kind for f in scan(project)) == ["CLUE", "DIALOGUE", "NUMBER", "REVEAL", "SOUND"]


def test_reveal_matches_alias_case_insensitively_but_not_substrings():
    project = make_project(clean=True)
    cue = project.assets[0].cues[1]
    cue.start, cue.end, cue.text = 25, 29, "MARATHON starts now"
    assert scan(project) == []
    cue.text = "CAPTAIN MARA arrives"
    assert [f.kind for f in scan(project)] == ["REVEAL"]


def test_sdh_sound_accepts_approved_alias():
    project = make_project(clean=True)
    project.assets[1].cues[0].text = "[SIREN blaring]"
    assert scan(project) == []


def test_touching_clue_edge_is_not_an_occlusion():
    project = make_project(clean=True)
    project.assets[0].cues[2].box = Box(x=.7, y=.7, width=.2, height=.15)
    assert scan(project) == []


def test_absent_spec_cannot_be_scanned():
    project = make_project()
    project.spec = None
    with pytest.raises(ValueError, match="specification"):
        scan(project)


def test_short_sdh_derivative_has_no_missing_sound_outside_its_coverage():
    project = make_project(clean=True)
    project.assets[1].master_offset = 100
    project.assets[1].cues[0].text = "[wind blows]"
    assert scan(project) == []
