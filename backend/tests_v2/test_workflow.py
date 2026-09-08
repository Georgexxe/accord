import pytest

from backend.app.domain import Change, Cue, Proposal, digest
from backend.app.workflow import apply, rollback, validate_proposal, preview_proposal
from .fixtures import make_project


def repair_case():
    project = make_project()
    project.approved_spec_digest = digest(project.spec.model_dump())
    clean = make_project(clean=True)
    changes = []
    for asset in project.assets:
        corrected = clean.asset(asset.id)
        for cue in asset.cues:
            replacement = next(c for c in corrected.cues if c.id == cue.id)
            if replacement != cue:
                changes.append(Change(asset_id=asset.id, base_hash=asset.content_hash(), cue_id=cue.id, replacement=replacement))
    proposal = Proposal(finding_ids=[], changes=changes, rationale="Synthetic repairs to five planted defects", spec_digest=project.approved_spec_digest)
    project.proposals.append(proposal)
    return project, proposal


@pytest.mark.parametrize("tamper", ["text", "timing", "rationale"])
def test_review_digest_rejects_patch_tampering_without_side_effects(tamper):
    project, proposal = repair_case()
    approved = proposal.approval_digest()
    if tamper == "text":
        proposal.changes[0].replacement.text = "Changed after review"
    elif tamper == "timing":
        proposal.changes[0].replacement.start += .5
    else:
        proposal.rationale = "Different rationale after review"
    before = project.model_dump()
    with pytest.raises(ValueError, match="digest"):
        apply(project, proposal, approved, "reviewer")
    assert project.model_dump() == before


@pytest.mark.parametrize("tamper", ["unapproved", "changed-spec", "stale-asset"])
def test_apply_rejects_unapproved_or_stale_inputs_atomically(tamper):
    project, proposal = repair_case()
    if tamper == "unapproved":
        project.approved_spec_digest = None
    elif tamper == "changed-spec":
        project.spec.invariants[0].value = "15"
    else:
        project.assets[-1].cues[0].text = "Later author edit"
    before = project.model_dump()
    with pytest.raises(ValueError, match="approved|changed"):
        apply(project, proposal, proposal.approval_digest(), "reviewer")
    assert project.model_dump() == before


def test_apply_changes_all_assets_and_rollback_restores_content_with_new_revisions():
    project, proposal = repair_case()
    before = {a.id: a.content_hash() for a in project.assets}
    approved = proposal.approval_digest()
    apply(project, proposal, approved, "human-reviewer")
    assert {a.id: a.content_hash() for a in project.assets} == {a.id: a.content_hash() for a in make_project(clean=True).assets}
    assert all(a.revision == 2 for a in project.assets)
    assert proposal.approved_by == "human-reviewer"
    assert proposal.approved_digest == approved
    assert proposal.status == "APPLIED"
    assert project.status == "VERIFICATION_PENDING"
    assert project.events[-1].action == "patch_applied"
    rollback(project, proposal, "human-reviewer")
    assert {a.id: a.content_hash() for a in project.assets} == before
    assert all(a.revision == 3 for a in project.assets)
    assert proposal.status == "ROLLED_BACK"
    assert project.status == "VERIFICATION_PENDING"
    assert project.events[-1].action == "patch_rolled_back"


def test_rollback_refuses_to_overwrite_any_later_edit():
    project, proposal = repair_case()
    apply(project, proposal, proposal.approval_digest(), "reviewer")
    project.assets[-1].cues[0].text = "A subsequent author correction"
    before = project.model_dump()
    with pytest.raises(ValueError, match="later edit"):
        rollback(project, proposal, "reviewer")
    assert project.model_dump() == before


def test_cue_one_replacement_does_not_touch_cue_eleven():
    project, _ = repair_case()
    asset = project.assets[0]
    asset.cues = [Cue(id="1", start=1, end=4, text="First"), Cue(id="11", start=5, end=8, text="Eleventh")]
    proposal = Proposal(finding_ids=[], rationale="Exact ID repair", spec_digest=project.approved_spec_digest, changes=[
        Change(asset_id=asset.id, base_hash=asset.content_hash(), cue_id="1", replacement=Cue(id="1", start=1, end=4, text="Correct first"))
    ])
    candidates = validate_proposal(project, proposal)
    assert [(c.id, c.text) for c in candidates[0].cues] == [("1", "Correct first"), ("11", "Eleventh")]
    assert asset.cues[0].text == "First"


def test_missing_exact_id_and_duplicate_changes_rejected():
    project, proposal = repair_case()
    proposal.changes[0].cue_id = "not-present"
    with pytest.raises(ValueError, match="Exact cue ID"):
        validate_proposal(project, proposal)
    project, proposal = repair_case()
    proposal.changes.append(proposal.changes[0].model_copy(deep=True))
    with pytest.raises(ValueError, match="Duplicate"):
        validate_proposal(project, proposal)


def test_applied_proposal_cannot_be_applied_twice():
    project, proposal = repair_case()
    approved = proposal.approval_digest()
    apply(project, proposal, approved, "reviewer")
    before = project.model_dump()
    with pytest.raises(ValueError, match="unapproved"):
        apply(project, proposal, approved, "reviewer")
    assert project.model_dump() == before


def test_insert_missing_sdh_sound_and_delete_spurious_cue():
    project, _ = repair_case()
    asset = project.assets[1]
    asset.cues = [Cue(id="before", start=10, end=13, text="[wind]"), Cue(id="spurious", start=25, end=28, text="[wrong sound]")]
    original = asset.content_hash()
    proposal = Proposal(finding_ids=[], rationale="Insert the omitted warning; remove a false cue", spec_digest=project.approved_spec_digest, changes=[
        Change(asset_id=asset.id, base_hash=original, cue_id="alarm", operation="INSERT", replacement=Cue(id="alarm", start=20, end=23, text="[alarm sounds]")),
        Change(asset_id=asset.id, base_hash=original, cue_id="spurious", operation="DELETE", replacement=None),
    ])
    apply(project, proposal, proposal.approval_digest(), "reviewer")
    assert {c.id: c.text for c in project.asset(asset.id).cues} == {"before": "[wind]", "alarm": "[alarm sounds]"}
    rollback(project, proposal, "reviewer")
    assert project.asset(asset.id).content_hash() == original


def test_invalid_timing_repair_cannot_partially_apply_other_asset_changes():
    project, proposal = repair_case()
    proposal.changes[-1].replacement.end = proposal.changes[-1].replacement.start
    before = project.model_dump()
    with pytest.raises(ValueError):
        apply(project, proposal, proposal.approval_digest(), "reviewer")
    assert project.model_dump() == before


def test_approval_of_new_spec_does_not_authorize_an_old_proposal():
    project, proposal = repair_case()
    approved = proposal.approval_digest()
    project.spec.invariants[0].value = "15"
    project.approved_spec_digest = digest(project.spec.model_dump())
    before = project.model_dump()
    with pytest.raises(ValueError, match="specification|spec"):
        apply(project, proposal, approved, "reviewer")
    assert project.model_dump() == before


def test_preview_complete_repair_clears_known_findings_without_mutation():
    project, proposal = repair_case()
    before_project = project.model_dump()
    before_proposal = proposal.model_dump()
    assert preview_proposal(project, proposal) == []
    assert project.model_dump() == before_project
    assert proposal.model_dump() == before_proposal
    assert proposal.status == "PROPOSED"
    assert all(a.revision == 1 for a in project.assets)


def test_preview_incomplete_valid_repair_reports_remaining_defects_without_mutation():
    project, proposal = repair_case()
    # A valid text replacement repairs NUMBER, leaving four independent defects.
    proposal.changes = [proposal.changes[0]]
    before_project = project.model_dump()
    before_proposal = proposal.model_dump()
    remaining = preview_proposal(project, proposal)
    assert sorted(f.kind for f in remaining) == ["CLUE", "DIALOGUE", "REVEAL", "SOUND"]
    assert project.model_dump() == before_project
    assert proposal.model_dump() == before_proposal


def test_preview_rejects_stale_proposal_without_mutation():
    project, proposal = repair_case()
    project.assets[0].cues[0].text = "Later authored text"
    before_project = project.model_dump()
    before_proposal = proposal.model_dump()
    with pytest.raises(ValueError, match="changed"):
        preview_proposal(project, proposal)
    assert project.model_dump() == before_project
    assert proposal.model_dump() == before_proposal


def test_model_version_metadata_is_bound_to_investigated_source_only():
    from backend.app.workflow import bind_investigated_versions
    project, proposal = repair_case()
    versions = {a.id:a.content_hash() for a in project.assets}
    proposal.changes[0].base_hash = "model-copy-error"
    bind_investigated_versions(project,proposal,versions)
    assert proposal.changes[0].base_hash == versions[proposal.changes[0].asset_id]
    validate_proposal(project,proposal)


def test_investigation_binding_refuses_to_rebase_a_later_edit():
    from backend.app.workflow import bind_investigated_versions
    project, proposal = repair_case()
    versions = {a.id:a.content_hash() for a in project.assets}
    project.asset(proposal.changes[0].asset_id).cues[0].text = "Later author edit"
    before = proposal.model_dump()
    with pytest.raises(ValueError,match="changed during investigation"):
        bind_investigated_versions(project,proposal,versions)
    assert proposal.model_dump() == before
