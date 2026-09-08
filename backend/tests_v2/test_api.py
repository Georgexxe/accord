"""HTTP contract tests. All external analytics/model calls below are test doubles."""
import io
import json
import zipfile

import pytest
from fastapi.testclient import TestClient

from backend.app import api
from backend.app.domain import uid
from backend.app.store import Store
from .fixtures import make_project
from .test_workflow import repair_case

TOKEN = "test-only-reviewer-secret-32-characters"


class FakeAnalytics:
    """An explicit in-process test double; this is not MCP validation."""
    def __init__(self):
        self.fail = False
        self.snapshots = {}

    def index(self, project, snapshot):
        if self.fail:
            raise ConnectionError("Test-injected database outage")
        self.snapshots[snapshot] = [a.model_copy(deep=True) for a in project.assets]

    async def snapshot(self, project, snapshot):
        return self.snapshots[snapshot], {"source": "test-double-only"}


class FakeGemini:
    async def extract(self, project, media):
        return make_project().spec, {"source": "test-double-only", "model": "no-model-called"}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("STORYPARITY_REVIEWER_TOKEN", TOKEN)
    monkeypatch.setattr(api, "store", Store(tmp_path / "api.sqlite"))
    monkeypatch.setattr(api, "analytics", FakeAnalytics())
    monkeypatch.setattr(api, "gemini", FakeGemini())
    with TestClient(api.app) as value:
        value.headers["Authorization"] = f"Bearer {TOKEN}"
        yield value


def create(client):
    response = client.post("/api/projects", json={"title": "Synthetic API test", "script": make_project().script})
    assert response.status_code == 200, response.text
    return response.json()


def seed_repair():
    project, proposal = repair_case()
    project.id = uid()
    api.store.save(project, None)
    return project, proposal


def test_authentication_required_and_not_configured_is_explicit(client, monkeypatch):
    assert client.get("/api/health", headers={"Authorization": ""}).status_code == 200
    assert client.get("/api/projects", headers={"Authorization": ""}).status_code == 401
    assert client.get("/api/projects", headers={"Authorization": "Bearer wrong"}).status_code == 401
    monkeypatch.delenv("STORYPARITY_REVIEWER_TOKEN")
    assert client.get("/api/session").status_code == 503


def test_create_upload_extract_approve_scan_and_export(client):
    project = create(client)
    base = f'/api/projects/{project["id"]}'
    response = client.post(base + "/assets", data={"locale": "es", "kind": "SUBTITLE", "revision": project["revision"]},
        files={"file": ("spanish.srt", "1\n00:00:10,000 --> 00:00:14,000\nHay 114 supervivientes.\n", "text/plain")})
    assert response.status_code == 200, response.text
    project = response.json()
    response = client.post(base + "/extract", json={"revision": project["revision"]})
    assert response.status_code == 200, response.text
    project = response.json()
    assert project["status"] == "SPEC_REVIEW"
    assert client.post(base + "/scan", json={"revision": project["revision"]}).status_code == 422
    response = client.post(base + "/spec/approve", json={"revision": project["revision"], "digest": project["spec_digest"]})
    assert response.status_code == 200, response.text
    project = response.json()
    response = client.post(base + "/scan", json={"revision": project["revision"]})
    assert response.status_code == 200, response.text
    project = response.json()
    assert project["status"] == "FINDINGS_OPEN"
    assert [(f["kind"], f["cue_id"]) for f in project["findings"]] == [("NUMBER", "1")]
    assert project["indexed_revision"] == project["revision"]
    response = client.get(base + "/export")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        report = json.loads(archive.read("delivery-report.json"))
        assert report["status"] == "FINDINGS_OPEN"
        assert "114" in archive.read(f'tracks/{project["assets"][0]["id"]}.srt').decode()
        assert "Unresolved findings: 1" in archive.read("README.txt").decode()


def test_stale_revision_and_wrong_spec_digest_are_conflicts(client):
    project = create(client)
    base = f'/api/projects/{project["id"]}'
    edited = client.put(base + "/spec", json={"revision": 1, "spec": make_project().spec.model_dump()})
    assert edited.status_code == 200
    assert client.put(base + "/spec", json={"revision": 1, "spec": make_project().spec.model_dump()}).status_code == 409
    assert client.post(base + "/spec/approve", json={"revision": 2, "digest": "0" * 64}).status_code == 409
    assert api.store.get(project["id"]).approved_spec_digest is None


def test_apply_requires_auth_and_exact_reviewed_digest(client):
    project, proposal = seed_repair()
    url = f"/api/projects/{project.id}/proposals/{proposal.id}/apply"
    payload = {"revision": 1, "digest": proposal.approval_digest()}
    assert client.post(url, json=payload, headers={"Authorization": ""}).status_code == 401
    assert client.post(url, json={"revision": 1, "digest": "f" * 64}).status_code == 422
    assert api.store.get(project.id).proposals[0].status == "PROPOSED"
    project.approved_spec_digest = None
    api.store.save(project, 1)
    assert client.post(url, json={"revision": 2, "digest": proposal.approval_digest()}).status_code == 422
    assert api.store.get(project.id).proposals[0].status == "PROPOSED"


def test_database_outage_preserves_applied_patch_as_pending_then_retry_verifies(client):
    project, proposal = seed_repair()
    base = f"/api/projects/{project.id}"
    api.analytics.fail = True
    response = client.post(base + f"/proposals/{proposal.id}/apply", json={"revision": 1, "digest": proposal.approval_digest()})
    assert response.status_code == 503, response.text
    saved = api.store.get(project.id)
    assert saved.proposals[0].status == "APPLIED"
    assert saved.status == "VERIFICATION_PENDING"
    assert saved.assets[0].cues[0].text == "Hay 14 supervivientes."
    assert saved.events[-1].action == "verification_failed"
    api.analytics.fail = False
    response = client.post(base + "/scan", json={"revision": saved.revision})
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "VERIFIED"
    assert response.json()["findings"] == []
    assert all("snapshots" not in p for p in response.json()["proposals"])


def test_invalid_upload_formats_and_missing_resources_return_client_errors(client):
    project = create(client)
    base = f'/api/projects/{project["id"]}'
    fields = {"locale": "en", "kind": "SUBTITLE", "revision": 1}
    assert client.post(base + "/assets", data=fields, files={"file": ("bad.txt", "text")}).status_code == 415
    assert client.post(base + "/assets", data=fields, files={"file": ("bad.json", "[invalid")}).status_code == 422
    assert client.get("/api/projects/not-a-valid-id").status_code == 404
    assert client.get(base + "/media").status_code == 404


@pytest.mark.parametrize("payload", ["null", "42", '"text"', '{"cues": []}'])
def test_json_track_requires_an_array(client, payload):
    project = create(client)
    response = client.post(f'/api/projects/{project["id"]}/assets',
        data={"locale": "en", "kind": "SUBTITLE", "revision": 1},
        files={"file": ("bad.json", payload)})
    assert response.status_code == 422
    assert api.store.get(project["id"]).assets == []


def test_failed_model_extraction_does_not_invent_spec_or_mutate_project(client, monkeypatch):
    async def fail(*args):
        raise ConnectionError("Test-injected Google outage")
    monkeypatch.setattr(api.gemini, "extract", fail)
    project = create(client)
    response = client.post(f'/api/projects/{project["id"]}/extract', json={"revision": 1})
    assert response.status_code == 503
    saved = api.store.get(project["id"])
    assert saved.spec is None
    assert saved.revision == 1
    assert saved.status == "INGESTED"


@pytest.mark.parametrize("payload", [
    "1\nbroken --> 00:00:14,000\nInvalid timestamp\n",
    "1\n00:00:10,000 --> 00:00:14,000\nValid\n\n2\nMISSING TIMECODE\nDo not silently discard this block\n",
    "1\n00:00:10,000 --> 00:00:14,000\nValid\n\n2\n00:00:16,000 -->\nIncomplete timestamp\n",
])
def test_malformed_srt_is_rejected_without_partial_import(client, payload):
    project = create(client)
    response = client.post(f'/api/projects/{project["id"]}/assets',
        data={"locale": "en", "kind": "SUBTITLE", "revision": 1},
        files={"file": ("malformed.srt", payload)})
    assert response.status_code == 422
    assert api.store.get(project["id"]).assets == []

def test_applied_preview_exposes_original_cues_without_changing_proposal_contract():
    from backend.app.workflow import apply
    project, proposal = repair_case()
    originals = {a.id:a.model_dump(mode="json") for a in project.assets}
    apply(project, proposal, proposal.approval_digest(), "test reviewer")
    data = api.public(project)
    assert "snapshots" not in data["proposals"][0]
    assert "preview_assets" not in data["proposals"][0]
    for asset in data["proposal_previews"][proposal.id]:
        assert asset == originals[asset["id"]]
