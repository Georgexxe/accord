"""Human-authorized version changes with explicit verification and rollback."""
from .domain import Asset, Project, Proposal, digest, presentation_errors


def validate_proposal(project: Project, proposal: Proposal) -> list[Asset]:
    if proposal.status != "PROPOSED":
        raise ValueError("Only an unapproved proposal can be applied")
    if not project.spec or project.approved_spec_digest != digest(project.spec.model_dump()):
        raise ValueError("Story specification is not approved")
    if proposal.spec_digest != project.approved_spec_digest:
        raise ValueError("Proposal belongs to a different story specification; investigate again")
    candidates = {a.id: a.model_copy(deep=True) for a in project.assets}
    touched = set()
    for change in proposal.changes:
        if change.asset_id not in candidates:
            raise ValueError("Unknown target asset")
        original = project.asset(change.asset_id)
        if original.content_hash() != change.base_hash:
            raise ValueError("Asset has changed since proposal; investigate again")
        key = (change.asset_id, change.cue_id)
        if key in touched:
            raise ValueError("Duplicate changes to a cue are not allowed")
        touched.add(key)
        asset = candidates[change.asset_id]
        index = next((i for i,c in enumerate(asset.cues) if c.id == change.cue_id), None)
        if change.operation == "INSERT":
            if index is not None:
                raise ValueError("Inserted cue ID already exists")
            asset.cues.append(change.replacement.model_copy(deep=True))
        elif index is None:
            raise ValueError("Exact cue ID was not found")
        elif change.operation == "DELETE":
            asset.cues.pop(index)
        else:
            asset.cues[index] = change.replacement.model_copy(deep=True)
    result = []
    for asset_id in {c.asset_id for c in proposal.changes}:
        asset = Asset.model_validate(candidates[asset_id].model_dump())
        errors = presentation_errors(asset)
        if errors:
            raise ValueError("; ".join(errors))
        asset.revision += 1
        result.append(asset)
    return result


def preview_proposal(project: Project, proposal: Proposal):
    """Run configured checks on an isolated candidate; never approve, save or index it."""
    from .detectors import scan
    replacements={a.id:a for a in validate_proposal(project,proposal)}
    candidate=project.model_copy(deep=True)
    candidate.assets=[replacements.get(a.id,a) for a in candidate.assets]
    return scan(candidate)


def apply(project: Project, proposal: Proposal, approved_digest: str, actor: str):
    if proposal.approval_digest() != approved_digest:
        raise ValueError("The reviewed proposal has changed; approval digest does not match")
    replacements = validate_proposal(project, proposal)
    proposal.snapshots = [project.asset(a.id).model_copy(deep=True) for a in replacements]
    proposal.result_hashes = {a.id: a.content_hash() for a in replacements}
    replacement_map = {a.id: a for a in replacements}
    project.assets = [replacement_map.get(a.id, a) for a in project.assets]
    proposal.approved_digest = approved_digest
    proposal.approved_by = actor
    proposal.status = "APPLIED"
    project.status = "VERIFICATION_PENDING"
    project.snapshot_id = None
    project.record("patch_applied", actor, proposal_id=proposal.id, approval_digest=approved_digest, result_hashes=proposal.result_hashes)


def rollback(project: Project, proposal: Proposal, actor: str):
    if proposal.status != "APPLIED":
        raise ValueError("Only applied proposals can be rolled back")
    for asset_id, expected in proposal.result_hashes.items():
        if project.asset(asset_id).content_hash() != expected:
            raise ValueError("A later edit exists; rollback would overwrite it")
    restored = {a.id: a.model_copy(deep=True) for a in proposal.snapshots}
    for asset_id, asset in restored.items():
        asset.revision = project.asset(asset_id).revision + 1
    project.assets = [restored.get(a.id, a) for a in project.assets]
    proposal.status = "ROLLED_BACK"
    project.status = "VERIFICATION_PENDING"
    project.snapshot_id = None
    project.record("patch_rolled_back", actor, proposal_id=proposal.id)
